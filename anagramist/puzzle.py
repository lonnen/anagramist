import logging
from dataclasses import dataclass
from functools import cached_property
from typing import List

from sortedcontainers import SortedKeyList

from .fragment import Fragment
from .oracles import Oracle, TransformerOracle, UniversalOracle
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
        oracle: Oracle = None,
        c1663: bool = False,
    ) -> None:
        self.letter_bank = Fragment(letter_bank)
        if oracle is None:
            self.oracle = UniversalOracle()
        else:
            self.oracle = oracle
        self.vocabulary = vocabulary
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
        g = Guess(sentence_start, remaining, self.oracle.score_candidate())
        self.max_candidates = max_candidates
        candidates = [g]
        while candidates.pop():
            self.oracle.score_candidate
            # calculate valid next words
            # score valid next words
            # push new candidates
            pass

    def create_guess(self, candidate: str):
        remaining = self.letter_bank.letters.copy()
        remaining.subtract(Fragment(candidate).letters)        
        
        score = self.oracle.score_candidate(candidate)

        return(candidate, remaining, score)
        

@dataclass(frozen=True)
class Guess:
    """A guess at the solution"""
    placed: str
    remaining: str
    score: float   

    def __lt__(self, other):
        return self.score < other.score     

    # @cached_property
    # def children(self) -> dict:
    #     bank = self.letter_bank.letters.copy()
    #     for w in self.words:
    #         bank.subtract(w)
    #     return {
    #         w.sentence[0]: Guess(self.words + w.sentence)
    #         for w in self.vocabulary
    #         if w.sentence < bank
    #     }
