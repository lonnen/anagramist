import logging
import math
from dataclasses import dataclass
from typing import Counter, List, Self

from .fragment import Fragment
from .oracles import Oracle, UniversalOracle
from .searchqueue import SearchQueue
from .vocab import vocab

logger = logging.getLogger(__name__)


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


class Puzzle:
    """A cryptoanagram puzzle consisting of a bank of letters to be formed into a
    sentence.

    Args:
        letter_bank: (`String`) - a string containing all the characters to be used in
            the solution. Spaces will be ignored. This may be a sentence, or a simple
            sequence of letters
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
        max_candidates: int = 1000,
        c1663: bool = False,
    ) -> None:
        self.letter_bank = Fragment(letter_bank).letters
        # first pass restriction of the vocabulary based on the initial letter_bank
        self.vocabulary = set(
            w for w in vocabulary if Fragment(w).letters <= self.letter_bank
        )
        if oracle is None:
            self.oracle = UniversalOracle()
        else:
            self.oracle = oracle
        self.candidates = SearchQueue(max_size=max_candidates)
        self.c1663 = c1663

    def search(self, sentence_start: str):
        remaining = self.letter_bank.copy()
        remaining.subtract(Fragment(sentence_start).letters)
        self.candidates.push(
            Guess(
                sentence_start,
                remaining,
                math.exp(self.oracle.score_candidate(sentence_start)),
            )
        )
        while len(self.candidates) > 0:
            c = self.candidates.weighted_random_sample(key=lambda x: x.score)
            for child in self.evaluate_one(c):
                self.candidates.push(child)

    def evaluate_one(self, candidate_guess: Guess) -> List[Guess]:
        """Starting from the provided Guess, iterate through the vocabulary to
        produce all possible child guesses.

        Args:
            candidate_guess(`Guess`) - a root Guess within the context of the Puzzle

        Returns:
            A List of Guesses representing all possible children of the candidate_guess
        """
        candidates = []  # a place to store child-guesses calculations

        # calculate new letter pool
        remaining = self.letter_bank.copy()
        remaining.subtract(candidate_guess.placed)
        del remaining[" "]

        if any([v < 0 for v in remaining.values()]):
            # the submitted guess uses letters not in the bank
            # no placement of additional letters can save it
            return []

        # restrict vocab to what can be spelled given the remaining letters
        # after removing letters used by the guess
        vocab = set(w for w in self.vocabulary if Fragment(w).letters <= remaining)

        for word in vocab:
            # compute child candidate and remaining letters
            next_candidate = Fragment(candidate_guess.placed + " " + word)
            next_remaining = self.letter_bank.copy()
            next_remaining.subtract(next_candidate.sentence)
            del next_remaining[" "]

            if not self.soft_validate(next_candidate, next_remaining):
                # do not record candidates that cannot be winners because of
                # words that have already been placed.
                continue

            if (
                next_candidate.sentence[-1] == "w"
                and next_remaining.total() == 2
                and next_remaining.get("!") == 2
            ):
                # we have a winner
                next_candidate.sentence += "!!"
                del next_remaining["!"]
                print("WINNER: {}".format(next_candidate))
                score = float("inf")
            else:
                # calculate a heuristic score
                score = math.exp(self.oracle.score_candidate(next_candidate.sentence))

            g = Guess(
                next_candidate.sentence, "".join(next_remaining.elements()), score
            )
            candidates.append(g)
        return candidates

    def soft_validate(self, placed: Fragment, remaining: Counter) -> bool:
        """Soft validation answers whether the candidate conforms to the problem
        constraints given the placement of letters so far.

        All incomplete solutions will violate at least some of the problem constraints
        as the space is explored, by virtue of having some unplaced letters. Soft
        validation will only fail if some placement of the current letters guarantees
        that no possible placement of remaining letters could make the guess valid.

        Critically passing soft validation does not necessarily guarantee there exists
        a solution in an arrangement of remaining letters, only that the current
        placement does not preclude one existing.

        Examples of states that would return false include placements using words
        outside of the vocab list, or characters outside of the letter bank. For c1663,
        additional constraints are applied, collected from Ryan North's hints about that
        specific puzzle. For example, the final letter of the puzzle is "w". This means
        that if all the "w"s are used before the final word is placed, the guess fails
        soft validation. It also means when there are no remaining values, the final
        placed letter should be "w".
        """
        # the sentence uses only characters from the provided bank
        if any([v < 0 for v in remaining.values()]):
            return False  # candidate uses letters not in the bank

        if any([w not in vocab for w in placed.words]):
            return False  # candidate uses words not in the bank

        if remaining.total() > 0:
            for w in self.vocabulary:
                if Fragment(w).letters <= remaining:
                    # at least one valid word can be spelled with the remaining letters
                    break
            else:
                return False  # candidate can't make a valid word with remaining letters

        # constraints that only apply to c1663
        if self.c1663:
            # the first word is "I"
            if placed.words[0] != "I":
                return False

            # punctuation is in the solution in the order :,!!
            punctuation = [":", ",", "!", "!"]
            pos = 0
            while pos < len(placed.words):
                cha = placed.words[pos]
                if len(cha) == 1 and cha not in set(
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                ):
                    if len(punctuation) < 1 or cha != punctuation.pop():
                        return False
                pos += 1

            # longest word is 11 characters long
            # second longest word is 8 characters long
            # the words are side by side in the solution
            word_lengths = [len(w) for w in placed.words]
            for length, pos in enumerate(word_lengths):
                if length <= 8:
                    continue
                if length != 11:
                    # we have a word longer than 8 chars that is not 11 letters
                    return False
                # now we have our 11 letter word
                # if it is the most recently placed, the next word could be length 8
                if pos == len(word_lengths):
                    continue
                if word_lengths[length - 1] != 8 and word_lengths[length + 1] != 8:
                    # either the word before or after must be 8
                    return False

            # the final letter is "w"
            # so the final three characters must be "w!!"
            if remaining.total() == 2:
                if placed.sentence[-1] != "w" or remaining["!"] != 2:
                    return False

            # so word bank must contain a "w!!" until the end
            if remaining.total() > 3:
                if remaining["w"] == 0 or remaining["!"] < 2:
                    return False

            # so there must be a word in the vocab ending in "w" until the last
            if remaining.total() > 2:
                for w in self.vocabulary:
                    if Fragment(w).letters <= remaining and w[-1] == "w":
                        # at least one valid word ending in "w" remains
                        break
                else:
                    # remaining letters do not allow for a word ending in "w"
                    return False

            return True
