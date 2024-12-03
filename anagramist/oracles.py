"""Oracles are intended to inform search strategies. The name "oracle" is intended to
indicate a lack of transparency or rigor in how they evaluate candidates.

* An Oracle must not modify what it is judging.
* An Oracle is a heuristic and should not be used for validation.
* Deterministic checks, like forcing or restricting certain sequences, should happen
    elsewhere.
"""

import logging
from math import fsum
from os import PathLike
from typing import List, Tuple, Union

from accelerate import PartialState
from accelerate.utils import set_seed

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

from anagramist.fragment import Fragment

logger = logging.getLogger(__name__)


class TransformerOracle:
    """A wrapper around transformer.py in order determine the log scores of candidates
    as if the candidates had been generated by the transformer.

    The details of using transformers are fiddly and this particular implementation is
    playing fast-and-loose. Unrigorous but useful.
    """

    def __init__(
        self,
        model_name_or_path: str | PathLike[str],
        seed: Union[int, None] = None,
        use_cpu: bool = True,
        fp16: bool = False,
        c1663: bool = False,
        puzzle_context: str = "",
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
        self.puzzle_context = puzzle_context
        if c1663:
            if self.puzzle_context != "":
                raise RuntimeError(
                    "Puzzle context is automatically configured when c1663 is Enabled"
                )
            self.puzzle_context = """In comparison, being an anagramist today is 
            totally boring, as nobody is encoding fundamental discoveries into word 
            games anymore.
            """
        self.puzzle_context_token_count = self.tokenizer(
            [self.puzzle_context], padding=False, return_tensors="pt"
        ).input_ids.shape[1]

    def score_candidates(
        self, candidates: List[Fragment]
    ) -> List[List[Tuple[str, float]]]:
        """Calculate the log scores of a given set of candidate sentences. This is
        theoretically more efficient than looping over single candidates, but too many
        at once can cause issues. It is recommended that consumers experiment with their
        hardware and chunk candidates into batches for improved efficiency.

        adapted from: https://discuss.huggingface.co/t/announcement-generation-get-probabilities-for-generated-output/30075/17

        Args:
            candidates (List[Fragment]): a list of candidate Fragments to be graded

        Returns:
            a list of `(word, score)` pairs that can be aggregated with `Match.fsum`
        """

        self.tokenizer.pad_token = self.tokenizer.bos_token
        # logits scores are all conditional on the next token
        # so the input needs ~ 1 token of padding in order to get the actual first token
        input_ids = self.tokenizer(
            [
                self.tokenizer.bos_token + self.puzzle_context + c.sentence
                for c in candidates
            ],
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
            if self.c1663:
                text_sequence = text_sequence[
                    self.puzzle_context_token_count :
                ]  # trim off the puzzle_context
            batch.append(text_sequence)

        batch_scores = []
        for candidate, scored_tokens in zip(candidates, batch, strict=True):
            scored_words = []
            for word in candidate.words:
                accumulated_tokens = []
                while (
                    "".join([token.strip() for token, _ in accumulated_tokens]) != word
                ):
                    accumulated_tokens.append(scored_tokens.pop(0))
                accumulated_word = "".join(
                    [token.strip() for token, _ in accumulated_tokens]
                )
                # why fsum? https://huggingface.co/blog/how-to-generate
                # "auto-regressive language generation is based on the assumption that 
                # the probability distribution of a word sequence can be decomposed into
                # the product of conditional next word distributions"
                accumulated_score = fsum([score for _, score in accumulated_tokens])
                scored_words.append((accumulated_word, accumulated_score))
            batch_scores.append(scored_words)

        return batch_scores

    def score_candidate(self, candidate: Fragment) -> float:
        """Calculate the log scores of a single candidate sentence"""
        return self.score_candidates([candidate])[0]
