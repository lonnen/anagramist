import logging
import math
from collections import Counter

import torch
from transformers import AutoTokenizer, LogitsProcessor

logger = logging.getLogger(__name__)


class LetterBankLogitsProcessor(LogitsProcessor):
    r"""
    [`LetterBankLogitsProcessor`] attempts to restrict sampling to ensure output can be
    assembled out of letters in the bank. This can be quite expensive. Logits work over
    tokens, but this Processor needs to decode those in order to work in characters.

    This version of the processor also ignores empty spaces.

    Once the letter bank gets small this processor starts to exhibit unexpected behavior
    and doesn't work particularly well. Once most of the possible next tokens are
    illegal and set to `-Math.Inf` increasingly unlikely choices appear, like repeated
    empty whitespace, until generation breaks and begins to generate illegal choices.

    Args:
        letter_bank (`String`) - the letters that will be used as the bank of letters.
        Whitespace will be ignored
        tokenizer (`AutoTokenizer`) - the tokenizer being used to encode and decode
        Tokens for the model
    """

    def __init__(self, letter_bank: str, tokenizer: AutoTokenizer):
        self.letter_bank = Counter(letter_bank)
        self.decode = tokenizer.decode
        self.eos_token_id = tokenizer.eos_token_id
        self.bos_token_id = tokenizer.bos_token_id

    def __call__(
        self, input_ids: torch.LongTensor, scores: torch.FloatTensor
    ) -> torch.FloatTensor:
        logging.debug("Begin LetterBankLogitsProcessor.__call__")
        tokens_to_ignore = set((self.eos_token_id, self.bos_token_id))
        scores_processed = scores.clone()
        for batch_scores, batch in zip(
            scores_processed, input_ids.tolist(), strict=True
        ):
            # calculate letters used by current input_ids
            candidate = self.decode(
                [token for token in batch if token not in tokens_to_ignore],
                clean_up_tokenization_spaces=True,
            ).strip()
            candidate_letters = Counter(candidate)
            candidate_letters[" "] = 0  # remove empty spaces

            remaining_letters = self.letter_bank.copy()
            remaining_letters.subtract(candidate_letters)

            # is the batch possible to produce with the letter bank?
            if not candidate_letters < self.letter_bank:
                logger.warn(
                    r"Batch '{}' contains letters not in the letter bank ({})".format(
                        candidate,
                        "".join(
                            [c * count for c, count in (-remaining_letters).items()]
                        ),
                    )
                )
                batch_scores = torch.full_like(batch_scores, -math.inf)
                continue

            for score_id, _ in enumerate(batch_scores):
                token_letters = Counter(self.decode(score_id).strip())
                if not token_letters < remaining_letters:
                    batch_scores[score_id] = -math.inf

            logging.debug(f"Candidate: {candidate}".format(candidate))
        logging.debug("End LetterBankLogitsProcessor.__call__")

        return scores_processed
