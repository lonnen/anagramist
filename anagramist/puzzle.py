import logging
from dataclasses import dataclass
from typing import List, Self

from .fragment import Fragment
from .heapqueue import HeapQueue
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

    @property
    def validates(self) -> bool:
        """Answers whether the candidate_sentence satisfies the constraints of the
        Qwantzle puzzle. Not all constraints can be checked computationally, but the
        following are checked:

            * The candidate_sentence uses exactly all of the characters from the
              letter_bank, not counting whitespace
            * The characters are case-sensitive
            * All the words are vocabulary.txt dictionary included in this library
              (1-grams from qwantz comics up to c1663)

        Additional constraints that are checked iff c1663:

            * The solution starts with "I"
            * The punctuation appears in the order :,!!
            * The longest word is 11 characters long
            * The second longest word is 8 characters, and occurs adjacent to the
              longest word

        Constraints that are not validated:

            * The solution is a natural-sounding, reasonably-grammatical dialogue that
              T-rex would say
            * The solution does not refer to anagrams or puzzles or winning t-shirts
            * The solution is directly related to the content of the comic 1663 "The
              Qwantzle"
            * The solution "would make a good epitaph"

        Constraints collected from https://github.com/lonnen/cryptoanagram/blob/main/README.md.
        There are multiple anagrams of c1663 that will pass this function, which
        satisfy several of the "Constraints that are not validated", but which are not
        the solution.

        return (`bool`) - does the candidate sentence satisfy the constraints of the
        Qwantzle puzzle
        """
        bank = Fragment(self.letter_bank.letters)

        # first check - do they have the same numbers of specific letters?
        if not self.candidate.letters == bank:
            return False

        # check that every word appears in the vocab list
        for word in self.candidate.sentence:
            if word == "":
                continue
            if word not in self.vocab:
                return False

        if not self.c1663:
            return True

        # From here out, only rules specific to comic 1663

        if self.candidate.sentence[0] != "I":
            return False

        words_len = [len(w) for w in self.candidate.sentence]

        longest, second_longest = sorted(words_len)[:2]
        if longest != 11 or second_longest != 8:
            return False

        position_longest = words_len.index(11)
        if words_len[position_longest - 1] != 8 or words_len[position_longest + 1] != 8:
            return False

        return True

    def search(self, sentence_start: str, max_candidates: int = 1000):
        remaining = self.letter_bank.letters.copy()
        remaining.subtract(Fragment(sentence_start).letters)
        self.max_candidates = max_candidates
        candidates = HeapQueue(
            [
                Guess(
                    sentence_start,
                    remaining,
                    self.oracle.score_candidate(sentence_start),
                )
            ]
        )
        while len(candidates) > 0:
            c = candidates.pop()
            candidate = c.placed
            remaining = c.remaining

            # calculate valid next words

            for word in self.vocabulary:
                # score valid next words
                next_candidate = candidate + " " + word

                # constraints indicate we should throw out a candidate
                constraint_violations = 0

                if Fragment(next_candidate).letters >= remaining:
                    constraint_violations += 1

                # constraints that only apply to c1663
                if self.c1663:
                    # the first word is "I"
                    if next_candidate[0] != "I":
                        constraint_violations += 1

                    # punctuation is in the solution in the order :,!!
                    punctuation = [":", ",", "!", "!"]
                    pos = 0
                    while pos < len(next_candidate):
                        cha = next_candidate[pos]
                        if cha not in {
                            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "
                        }:
                            if len(punctuation) == 0 or cha != punctuation.pop(0):
                                constraint_violations += 1
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
                                    constraint_violations += 1
                            else:
                                constraint_violations += 1

                # initial oracle score
                # oracles are expensive, don't bother if this candidate cannot win
                if constraint_violations != 0:
                    score = float("-inf")
                else:
                    score = self.oracle.score_candidate(next_candidate)

                # finally, HeapQueue is a min-queue, so better candidates should have
                # a smaller value.
                score *= -1
                g = Guess(next_candidate, remaining - Fragment(word).letters, score)
                if len(candidates) >= max_candidates:
                    candidates.replace(g)
                else:
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
