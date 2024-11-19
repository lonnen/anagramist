import logging
import time
from typing import Optional

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
        max_iterations: Optional[int] = None,
        max_time: Optional[int] = None,
    ):
        self.letter_bank = Fragment(letters).letters
        self.search_tree = search_tree
        self.oracle = oracle

        self.root = ""
        if c1663:
            logger.info("using special constraints for comic 1663")
            self.root = "I"
        self.vocabulary = corpus(c1663)
        logger.info(f"loaded vocab ({len(self.vocabulary)} items)")
        self.max_iterations = max_iterations

        self.current_iteration = 0

    def solve(self) -> None:
        start_time = time.time()

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
                self._max_time is not None
                and (time.time() - start_time) > self._max_time
            ):
                logging.info(
                    "Timeout after %d seconds, stopping.",
                    self._max_time,
                )
                break

            candidate = self.root

            # selection
            candidate = self.select(candidate)
            # expansion
            candidate = self.expansion(candidate)
            # assessment
            candidate = self.assessment(candidate)
            # backpropogation
            self.backpropogation(candidate)

            self.current_iteration += 1
