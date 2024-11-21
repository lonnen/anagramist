from collections import Counter
import logging
from random import choices
import time
from typing import Generator, Union

from anagramist import soft_validate
from anagramist.fragment import Fragment
from anagramist.oracles import TransformerOracle
from anagramist.persistentsearchtree import PersistentSearchTree
from anagramist.vocab import corpus

logger = logging.getLogger(__name__)


class Solver:
    def __init__(
        self,
        letters: str,
        search_tree: PersistentSearchTree,
        oracle: TransformerOracle,
        c1663: bool = False,
        max_iterations: Union[int, None] = None,
        max_time: Union[int, None] = None,
    ):
        self.letter_bank = Fragment(letters).letters
        self.search_tree = search_tree
        self.oracle = oracle
        self.c1663 = c1663

        self.root = ""
        if c1663:
            logger.info("using special constraints for comic 1663")
            self.root = "I"
        self.vocabulary = corpus(c1663)
        logger.info(f"loaded vocab ({len(self.vocabulary)} items)")
        self.max_iterations = max_iterations
        self.max_time = max_time

        self.current_iteration = 0

    def solve(self, root_candidate: Union[str, None] = None) -> None:
        """Compute candidate solutions to the cryptoanagram.

        Args:
            root_candidate (Union[str, None]): The candidate prefix to explore from. If
                this is not provided the solver will begin from an empty solution, or
                start from a known hint in the case of Comic 1663
        """
        start_time = time.time()

        if root_candidate is None:
            root_candidate = self.root

        while True:
            if (
                self.max_iterations is not None
                and self.current_iteration >= self.max_iterations
            ):
                logging.info(
                    "Performed %d runs (%d/s), stopping.",
                    self.max_iterations,
                    self.max_iterations / (time.time() - start_time),
                )
                break

            if (
                self.max_time is not None
                and (time.time() - start_time) > self.max_time
            ):
                logging.info(
                    "Timeout after %d seconds, stopping.",
                    self.max_time,
                )
                break

            candidate = root_candidate

            # selection
            candidate = self.select(candidate)
            # expansion
            candidate = self.expansion(candidate)
            # assessment
            candidate = self.assessment(candidate)
            # backpropogation
            self.backpropogation(candidate)

            self.current_iteration += 1

    def select(self, candidate: str) -> str:
        """Select a random starting node from the tree by considering all nodes prefixed
        with `candidate` and weighing the selection by the score of each node.

        Args:
            candidate (str): a candidate node from which to search. Only the candidate
                and its child nodes will be considered.
        Raises:
            ValueError: If no nodes exist prefixed by `candidate`
        """
        record = self.search_tree.sample(candidate=candidate)
        if record is None:
            raise ValueError("No records found prefixed by 'f{candidate}'")
        else:
            record[0]

    def expansion(self, candidate: str) -> str:
        """Take a deep, uniform, random walk adding words until soft validation fails
        and there are no words in the vocabulary that can be placed with the remaining
        letters.

        Critically, this will occur when the leaf node itself is a winning candidate.

        Returns:
            The candidate discovered at the end of the random walk
        """
        while True:
            placed = Fragment(candidate)
            remaining = self.letter_bank.copy()
            remaining.subtract(placed.letters)

            if not soft_validate(placed, remaining, self.vocabulary, self.c1663):
                break

            next_words = [w for w in self.compute_valid_vocab(remaining)]

            if len(next_words) == 0:
                break

            next = choices(next_words)[0]
            candidate = " ".join(candidate, next)

        return placed

    def compute_valid_vocab(
        self, remaining_letters: Counter
    ) -> Generator[str, None, None]:
        """Lazily compute the vocabulary words that can be placed with the remaining
        letters.

        Args:
            remaining_letters (Counter): the letters remaining to be placed

        Returns:
            a generator of valid words from the Solver's vocabulary
        """
        for word in self.vocabulary:
            next_word = Fragment(word)
            if not next_word.letters <= remaining_letters:
                continue
            yield next_word.sentence
