import logging
from abc import ABC, abstractmethod
from math import fsum
from os import PathLike
from typing import List

from accelerate import PartialState
from accelerate.utils import set_seed

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

logger = logging.getLogger(__name__)


class Oracle(ABC):
    """A base class for objects that score potential candidate answers. This is intended
    to inform search strategies. The name "oracle" is chosen to indicate a lack of
    transparency or rigor in how this class evaluates candidates.

    Oracles are expected to return scores, not necessarily probabilities, only numerical
    values that satisfy the comparison function of a sort.

    An Oracle is a heuristic and should not be used for validation, nor does it.
    Deterministic filtering, like forcing certain sequences to appear, should happen
    elsewhere.
    """

    def score_candidates(self, candidates: List[str]) -> List[float]:
        """Evaluate a List of candidate answers. By default this will run
        `score_candidate` in a list comprehension over the it. Override it directly for
        bulk-evaluation optimizations.

        Args:
            candidates `List[str]` - a list of strings representing candidate answers
        """
        return [self.score_candidate(candidate) for candidate in candidates]

    @abstractmethod
    def score_candidate(self, candidate: str) -> float:
        """Evaluate a single candidate answer

        Args:
            candidate `str` - a string representing a candidate answer
        """
        raise NotImplementedError(
            f"""{self.__class__} is an abstract class. Only classes inheriting this
            class can be called."""
        )


class UniversalOracle(Oracle):
    """An oracle that assess every candidate with the same, universal probability.

    Probably only useful for testing.
    """

    def score_candidate(self, candidate: str) -> float:
        return -1.0  # math.log2(0.5)


class LenOracle(Oracle):
    """An oracle that assigns scores based on candidate length"""

    def score_candidate(self, candidate: str) -> float:
        return len(candidate)


class TransformerOracle(Oracle):
    """An oracle implemented by wrapping transformer.py in order get the log scores of
    candidates as if the candidates had been generated by the transformer.

    The details of using transformers are fiddly and this particular implementation is
    playing fast-and-loose with those details. Unrigorous but useful.
    """

    def __init__(
        self,
        model_name_or_path: str | PathLike[str],
        seed: int = None,
        use_cpu: bool = True,
        fp16: bool = False,
        c1663: bool = False,
    ) -> None:
        # Transformers Model Initialization
        self.distributed_state = PartialState(cpu=use_cpu)

        logger.warning(
            f"device: {self.distributed_state.device}, 16-bits inference: {fp16}"
        )

        # Initialize the model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_name_or_path)

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

        # Puzzle Specific Initialization
        self.puzzle_context = ""
        if c1663:
            self.puzzle_context = """In comparison, being an anagramist today is 
            totally boring, as nobody is encoding fundamental discoveries into word 
            games anymore.
            """

    def calc_candidate_scores(self, candidates: List[str]) -> List[(str, float)]:
        self.tokenizer.pad_token = self.tokenizer.bos_token
        # logits scores are all conditional on the next token
        # so the input needs ~ 1 token of padding in order to get the actual first token
        input_ids = self.tokenizer(
            [self.tokenizer.bos_token + c for c in candidates],
            padding=True,
            return_tensors="pt",
        ).input_ids
        outputs = self.model(input_ids)
        probabilities = torch.log(outputs.logits.softmax(dim=-1) / 100).detach()

        # collect the scores of the generated token -- score at index 0 corresponds to
        # the token at index 1
        probabilities = probabilities[:, :-1, :]
        input_ids = input_ids[:, 1:]
        gen_probs = torch.gather(probabilities, 2, input_ids[:, :, None]).squeeze(-1)

        batch = []
        for input_sentence, input_probs in zip(input_ids, gen_probs, strict=True):
            text_sequence = []
            for token, p in zip(input_sentence, input_probs, strict=True):
                if token not in self.tokenizer.all_special_ids:
                    text_sequence.append((self.tokenizer.decode(token), p.item()))
            batch.append(text_sequence)

        return batch

    def score_candidates(self, candidates: List[str]) -> List[float]:
        """Calculate the log scores of a given set of candidate sentences. This is
        theoretically more efficient than looping over single candidates, but too many
        at once can cause issues. It is recommended that consumers experiment with their
        hardware and chunk candidates into batches for improved efficiency.

        adapted from: https://discuss.huggingface.co/t/announcement-generation-get-probabilities-for-generated-output/30075/17
        """
        batch = self.calc_candidate_scores(candidates)

        batch_scores = []
        for sequence in batch:
            batch_scores.append(fsum([log_score for _, log_score in sequence]))

        return batch_scores

    def score_candidate(self, candidate: List[str]) -> float:
        """Calculate the log scores of a single candidate sentence"""
        return self.score_candidates([candidate])[0]
