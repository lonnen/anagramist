import logging
import math
import sys
from collections import Counter
from os import PathLike

from accelerate import PartialState
from accelerate.utils import set_seed

import torch
from torch import FloatTensor, LongTensor, gather
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    LogitsProcessorList,
    LogitsProcessor,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


class Solver:
    def __init__(
        self,
        model_name_or_path: str | PathLike[str],
        seed: int = None,
        use_cpu: bool = True,
        fp16: bool = False,
        c1663: bool = False,
    ) -> None:
        self.distributed_state = PartialState(cpu=use_cpu)

        logger.warning(
            f"device: {self.distributed_state.device}, 16-bits inference: {fp16}"
        )

        # Initialize the model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_name_or_path)
        # tokenizer = GPT2Tokenizer.from_pretrained(args.model_name_or_path)
        # model = OPTForCausalLM.from_pretrained(args.model_name_or_path)

        # Set the model to the right device
        self.model.to(self.distributed_state.device)

        self.fp16 = fp16
        if fp16:
            self.model.half()

        self.seed = seed
        if seed is not None:
            set_seed(seed)

        self.use_cpu = use_cpu
        self.c1663 = c1663

    def generate_solutions(self, letters):
        prompt_text = " "
        # prompt_text = """Indeed! In comparison being an anagramist today is totally boring, as nobody is encoding anagramistal discoveries into word games anymore."""
        if self.c1663:
            prompt_text = """In comparison, being an anagramist today is totally boring, as nobody is encoding fundamental discoveries into word games anymore."""

        inputs = self.tokenizer(
            prompt_text, return_tensors="pt", add_special_tokens=False
        )

        logits = LogitsProcessorList(
            [
                LetterBankLogitsProcessor(letters + prompt_text, self.tokenizer),
            ]
        )

        if self.c1663:
            logits.extend(LogitsProcessorList([
            ]))

        output_sequences = self.model.generate(
            inputs.input_ids,
            # BEAM search params
            num_beams=10,
            num_return_sequences=5,
            no_repeat_ngram_size=1,
            remove_invalid_values=True,
            logits_processor=logits,
            # renormalization is recommended with beam search and heavy logits modification
            renormalize_logits=True,
            # tokens ~= 4 english chars, and valid answers must use exactly all the letters
            max_length=int(len(letters) / 3) + len(inputs["input_ids"][0]),
        )

        for output in output_sequences:
            logger.info(f"CANDIDATE SOLUTION: ")

            # Decode text
            text = self.tokenizer.decode(
                output,
                clean_up_tokenization_spaces=True,
                add_special_tokens=False,
            )
            logger.info(text + "\n")
        return output_sequences


def generate_text(
    letters: str,
    model_name_or_path: str | PathLike[str],
    seed: int,
    use_gpu: bool = False,
    fp16: bool = False,
    c1663: bool = False,
):
    solver = Solver(model_name_or_path, seed, (not use_gpu), fp16, c1663)
    solver.generate_solutions(letters)


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
                logger.warn(r"Batch '{}' contains letters not in the letter bank ({})".format(candidate, 
                ''.join([c * count for c, count in (-remaining_letters).items()])))
                batch_scores = torch.full_like(batch_scores, -math.inf)
                continue
            
            for s_id, s in enumerate(batch_scores):
                token_letters = Counter(self.decode(s_id).strip())
                if not token_letters < remaining_letters:
                    batch_scores[s_id] = -math.inf
            
            logging.debug(f"Candidate: {candidate}".format(candidate))
        logging.debug("End LetterBankLogitsProcessor.__call__")

        return scores_processed
