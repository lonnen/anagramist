from collections import Counter
import logging
from random import choices
import time
from typing import Generator, Union

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

            if self.max_time is not None and (time.time() - start_time) > self.max_time:
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

    def select(self, candidate: str = None) -> str:
        """Select a random starting node from the tree by considering all nodes prefixed
        with `candidate` and weighing the selection by the score of each node.

        Args:
            candidate (str): a candidate node from which to search. Only the candidate
                and its child nodes will be considered. If no candidate is provided the
                entire database will be considered.
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

        Args:
            candidate (str): a canddiate node from which to start expansion

        Returns:
            The candidate discovered at the end of the random walk
        """
        while True:
            placed = Fragment(candidate)
            remaining = self.letter_bank.copy()
            remaining.subtract(placed.letters)

            if not self.soft_validate(placed, remaining):
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
            remaining_letters (Counter): the letters available for making new words

        Returns:
            a generator of valid words from the Solver's vocabulary
        """
        for word in self.vocabulary:
            next_word = Fragment(word)
            if not next_word.letters <= remaining_letters:
                continue
            yield next_word.sentence

    def soft_validate(self, candidate: str, remaining_letters: Counter) -> bool:
        """Answers whether the words placed conform to the problem constraints and that
        the letters remaining allow for at least one more valid word to be placed.

        Soft validation will fail if the current placement violates a constraint that
        cannot be remedied with the placement of additional words (e.g. placing letters
        that are not in the original letter bank), but will pass if there are
        constraints that have not yet been satisfied if there is some arrangement of the
        remaining letters that could possible satisfy it (e.g. there are enough letters
        to form more words from the vocab list). 

        The function does not produce false negatives, but it's predictive power over
        future states is limited and it may produce false positives. For example, 
        because it only looks one word ahead it may be that each next word would leave
        behind a handful of letters that cannot form a second word. soft_validate would
        return True, unable to see far enough to know the candidate is already doomed.

        Args:
            candidate (str): a partial arrangement of letters
            remaining_letters (Counter): the letters available for maiking new words

        Returns:
            a boolean indicating whether the candidate passed soft validation
        """
        candidate = Fragment(candidate)
        # the sentence uses only characters from the provided bank
        if any([v < 0 for v in remaining_letters.values()]):
            return False  # candidate uses letters not in the bank

        if any([w not in self.vocabulary for w in candidate.words]):
            return False  # candidate uses words not in the bank

        if remaining_letters.total() > 0:
            for w in self.vocabulary:
                if Fragment(w).letters <= remaining_letters:
                    # at least one valid word can be spelled with the remaining letters
                    break
            else:
                return False  # candidate can't make a valid word with remaining letters

        if not self.c1663:
            return True

        # from here on out, the constraints are derived from hints about comic 1663

        # the first word is "I"
        if candidate.words[0] != "I":
            return False

        # punctuation is in the solution in the order :,!!
        expected_punctuation = [":", ",", "!", "!"]
        punctuation_position = 0
        for w in candidate.words:
            if len(w) == 1 and w not in set(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            ):
                if expected_punctuation[punctuation_position] != w:
                    return False
                punctuation_position += 1

        # longest word is 11 characters long
        # second longest word is 8 characters long
        # the words are side by side in the solution
        word_lengths = [len(w) for w in candidate.words]
        for pos, length in enumerate(word_lengths):
            if length <= 8:
                continue
            if length != 11:
                # we have a word longer than 8 chars that is not 11 letters
                return False
            # now we have our 11 letter word
            # if it is the most recently placed, the next word could be length 8
            if pos == len(word_lengths) - 1:
                continue
            if word_lengths[pos - 1] != 8 and word_lengths[pos + 1] != 8:
                # either the word before or after must be 8
                return False

        # the final letter is "w"
        # so the final three characters must be "w!!"
        if remaining_letters.total() == 2:
            if candidate.sentence[-1] != "w" or remaining_letters["!"] != 2:
                return False

        # so word bank must contain a "w!!" until the end
        if remaining_letters.total() > 3:
            if remaining_letters["w"] == 0 or remaining_letters["!"] < 2:
                return False

        # so there must be a word in the vocab ending in "w" until the last
        if remaining_letters.total() > 2:
            for w in self.vocabulary:
                if Fragment(w).letters <= remaining_letters and w[-1] == "w":
                    # at least one valid word ending in "w" remains
                    break
            else:
                # remaining letters do not allow for a word ending in "w"
                return False

        return True
