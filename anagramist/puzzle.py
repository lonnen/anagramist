import logging
import math
import random
from collections import UserList
from dataclasses import dataclass
from typing import Iterable, List, Self

from .fragment import Fragment
from .oracles import Oracle, UniversalOracle
from .vocab import vocab

logger = logging.getLogger(__name__)


class Puzzle:
    """A cryptoanagram puzzle consisting of a bank of letters to be formed into a
    sentence.

    Args:
        letter_bank: (`String`) - a string containing all the characters to be used in
            the solution. Spaces will be ignored. This may be a sentence, or a simple
            sequence of letters
        candidate: (`String`) or (`Fragment`) - a possible, possibly partial, solution
            to the puzzle
        vocabulary: (`List[String]`) - a list of words that may be used in valid answers
        oracle: (`Oracle`) - a heuristic strategy for evaluating candidates during
            search. If `None` the `UniversalOracle` will be used, which evaluates every
            candidate as having the same, universal score.
        c1663: (`bool`) - whether or not to apply special constraints that only apply
            to comic 1663 "The Qwantzle"
    """

    def __init__(
        self,
        letter_bank: str,
        vocabulary: List[str] = vocab,
        oracle: Oracle = None,  # default: Universal
        c1663: bool = False,
    ) -> None:
        self.letter_bank = Fragment(letter_bank)
        self.vocabulary = vocabulary
        if oracle is None:
            self.oracle = UniversalOracle()
        else:
            self.oracle = oracle
        self.c1663 = c1663

    def search(self, sentence_start: str, max_candidates: int = 1000):
        remaining = self.letter_bank.letters.copy()
        remaining.subtract(Fragment(sentence_start).letters)
        self.max_candidates = max_candidates
        candidates = SearchQueue(
            [
                Guess(
                    sentence_start,
                    remaining,
                    math.exp(self.oracle.score_candidate(sentence_start)),
                )
            ],
            max_size=max_candidates,
        )
        while len(candidates) > 0:
            c = candidates.weighted_random_sample(key=lambda x: x.score)

            candidate = c.placed
            remaining = Fragment(c.remaining).letters

            # calculate valid next words
            for word in self.vocabulary:
                # score valid next words
                next_candidate = candidate + " " + word

                next_remaining = remaining.copy()
                next_remaining.subtract(word)

                # A lot of constraints will be soft-violated while the solution is
                # being assembled -- reject them only when the candidate has crossed
                # the point where it could no longer become a valid answer with some
                # hypothetical arragnement of remaining letters

                violations = 0
                # the sentence uses only characters from the provided bank
                if any([v < 0 for v in next_remaining.values()]):
                    violations += 1  # candidate uses letters not in the bank

                # constraints that only apply to c1663
                if self.c1663:
                    # the first word is "I"
                    if next_candidate[0] != "I":
                        violations += 1

                    # punctuation is in the solution in the order :,!!
                    punctuation = [":", ",", "!", "!"]
                    pos = 0
                    while pos < len(next_candidate):
                        cha = next_candidate[pos]
                        if cha not in {
                            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "
                        }:
                            if len(punctuation) == 0 or cha != punctuation.pop(0):
                                violations += 1
                        pos += 1

                    # longest word is 11 characters long
                    # second longest word is 8 characters long
                    # the words are side by side in the solution
                    word_lengths = [len(w) for w in next_candidate.split()]
                    for length, pos in enumerate(word_lengths):
                        if length > 8:
                            if length == 11:
                                if (
                                    word_lengths[length - 1] == 8
                                    or word_lengths[length + 1] == 8
                                    or pos == len(word_lengths)
                                ):
                                    pass
                                else:
                                    violations += 1
                            else:
                                violations += 1

                    # the final letter is "w"
                    # so the final three characters must be "w!!"
                    if next_remaining.total() > 3:
                        if next_remaining["w"] == 0:
                            violations += 1

                    if next_remaining.total() == 2:
                        if next_candidate[-1] != "w":
                            violations += 1
                        else:
                            next_candidate += "!!"
                            next_remaining = next_remaining.subtract("!!")
                            print("winner: {}".format(next_candidate))

                if violations > 0:
                    score = 0
                else:
                    # calculate a heuristic score
                    score = math.exp(self.oracle.score_candidate(next_candidate))

                g = Guess(next_candidate, remaining - Fragment(word).letters, score)
                candidates.push(g)


@dataclass()
class Guess:
    """A guess at the solution.

    Wraps the placed and remaining letters up with a score.

    The score is used for comparing guesses. As a perf optimization, these comparisons
    do not check that `Fragment(placed + remaining).letters` are the same in both before
    comparing scores. Technically guesses with different total letters are from
    different puzzles and should raise a ValueError or similar. This optimization works
    only when a guess exists solely in the context of a single Puzzle context.

    Implementors handling guesses from multiple puzzles should implement their own
    checks to ensures guesses being compared are from the same puzzle.
    """

    placed: str
    remaining: str
    score: float

    def __lt__(self, other: Self):
        return self.score < other.score

    def __le__(self, other: Self):
        return self.score <= other.score

    def __eq__(self, other: Self):
        return self.score == other.score

    def __ne__(self, other: Self):
        return self.score != other.score

    def __gt__(self, other: Self):
        return self.score > other.score

    def __ge__(self, other: Self):
        return self.score >= other.score


class SearchQueue(UserList):
    def __init__(self, iterable: Iterable, max_size: int = None):
        self.data = list(iterable)
        self.max_size = max_size

    def weighted_random_sample(self, key=lambda x: x):
        pos = random.choices(
            [p for p, _ in enumerate(self.data)],
            weights=[key(d) for d in self.data],
        )[0]
        return self.data.pop(pos)

    def push(self, element, key=lambda x: x):
        if self.max_size is not None:
            if len(self.data) >= self.max_size:
                index, _ = min(
                    enumerate([key(i) for i in self.data]),
                    key=lambda e: e[1],
                )
                self.data.pop(index)
        self.data.append(element)
