import logging
import math
from collections import Counter

import torch
from torch import FloatTensor, LongTensor, gather
from transformers import AutoTokenizer, LogitsProcessor

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


class LetterBankLogitsProcessor(LogitsProcessor):
    r"""
    [`LetterBankLogitsProcessor`] restricts sampling to ensure output can be assembled out of letters in the bank.

    Args:
        letter_bank (`List[]`)
    """

    def __init__(self, letter_bank: str, tokenizer: AutoTokenizer):
        self.letter_bank = Counter(letter_bank)
        self.decode = tokenizer.decode
        self.eos_token_id = tokenizer.eos_token_id
        self.bos_token_id = tokenizer.bos_token_id

    def __call__(self, input_ids: LongTensor, scores: FloatTensor) -> FloatTensor:
        logging.debug("Begin LetterBankLogitsProcessor.__call__")
        tokens_to_ignore = set((self.eos_token_id, self.bos_token_id))
        scores_processed = scores.clone()
        for batch_scores, batch in zip(scores_processed, input_ids.tolist()):
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

            for s_id, s in enumerate(batch_scores):
                token_letters = Counter(self.decode(s_id).strip())
                if not token_letters < remaining_letters:
                    batch_scores[s_id] = -math.inf

            logging.debug(f"Candidate: {candidate}".format(candidate))
        logging.debug("End LetterBankLogitsProcessor.__call__")

        return scores_processed
