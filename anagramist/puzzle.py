import logging
import random
from typing import Counter, Iterator, List

from . import soft_validate
from .fragment import Fragment
from .guess import Guess
from .oracles import Oracle, UniversalOracle
from .searchqueue import PersistentSearchQueue
from .vocab import vocab

logger = logging.getLogger(__name__)


class Puzzle:
    """A cryptoanagram puzzle consisting of a bank of letters to be formed into a
    sentence.

    Attributes:
        magic_score_threshhold: (`float`) - ignore logprobs below this threshold as if
        they didn't pass soft-validation

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

    MAGIC_SCORE_THRESHOLD = float(-50)

    def __init__(
        self,
        letter_bank: str,
        vocabulary: List[str] = vocab,
        oracle: Oracle = None,  # default: Universal
        max_candidates: int = 10000,
        c1663: bool = False,
    ) -> None:
        self.letter_bank = Fragment(letter_bank).letters
        # first pass restriction of the vocabulary based on the initial letter_bank
        self.vocabulary = set(
            w for w in vocabulary if Fragment(w).letters <= self.letter_bank
        )
        if c1663:
            # longest word is 11 chars, second longest is 8 chars
            self.vocabulary = set(
                w for w in self.vocabulary if (len(w) == 11 or len(w) <= 8)
            )
        if oracle is None:
            self.oracle = UniversalOracle()
        else:
            self.oracle = oracle
        self.candidates = PersistentSearchQueue(max_size=max_candidates)
        self.c1663 = c1663

    def search(self, sentence_start: str, strategy="strat_weighted_bfs"):
        if strategy == "strat_weighted_bfs":
            self.strat_weighted_bfs(sentence_start)
        elif strategy == "strat_random_dfs":
            self.strat_random_dfs(sentence_start)

    def strat_random_dfs(self, sentence_start: str):
        if len(self.candidates) < 1:
            remaining = self.letter_bank.copy()
            remaining.subtract(Fragment(sentence_start).letters)
            self.candidates.push(
                Guess(
                    sentence_start,
                    "".join(remaining.elements()),
                    self.score_candidate(sentence_start, remaining),
                )
            )
        while len(self.candidates) > 0:
            g = self.candidates.weighted_random_sample()
            next_candidate = Fragment(g[0])

            vocab = set(
                w
                for w in self.vocabulary
                if Fragment(g[0] + " " + w).letters <= self.letter_bank
            )

            while len(vocab) > 0:
                word = random.choice(list(vocab))

                # compute child candidate and remaining letters
                next_candidate = Fragment(next_candidate.sentence + " " + word)
                next_remaining = self.letter_bank.copy()
                next_remaining.subtract(next_candidate.sentence)
                del next_remaining[" "]

                if not soft_validate(next_candidate, next_remaining, c1663=self.c1663):
                    # there is no hope for this candidate
                    # delete the word and retry until we're out of words
                    vocab = vocab - set(word)
                    next_candidate = Fragment(" ".join(next_candidate.words[:-1]))
                    # reuse vocab, no need to recalc
                    continue

                # ok this isn't yet a loser, so let's check for a winner
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
                    # neither doomed nor annointed? Dunno. Feed it to some ML heuristic?
                    score = self.score_candidate(
                        next_candidate.sentence, next_remaining
                    )

                if score < self.MAGIC_SCORE_THRESHOLD:
                    # there is no hope for this candidate
                    # delete the word and retry until we're out of words
                    vocab = vocab - set(word)
                    next_candidate = Fragment(" ".join(next_candidate.words[:-1]))
                    # reuse vocab, no need to recalc
                    continue

                self.candidates.push(
                    Guess(
                        next_candidate.sentence,
                        "".join(next_remaining.elements()),
                        score,
                    )
                )
                vocab = set(
                    w for w in self.vocabulary if Fragment(w).letters <= next_remaining
                )

    def strat_weighted_bfs(self, sentence_start: str):
        if len(self.candidates) < 1:
            remaining = self.letter_bank.copy()
            remaining.subtract(Fragment(sentence_start).letters)
            self.candidates.push(
                Guess(
                    sentence_start,
                    "".join(remaining.elements()),
                    self.score_candidate(sentence_start, remaining),
                )
            )
        while len(self.candidates) > 0:
            g = self.candidates.weighted_random_sample()
            c = Guess(g[0], g[1], g[2])
            for child in self.evaluate_one(c):
                self.candidates.push(child)

    def evaluate_one(self, candidate_guess: Guess) -> Iterator[Guess]:
        """Starting from the provided Guess, iterate through the vocabulary to
        produce all possible child guesses.

        Args:
            candidate_guess(`Guess`) - a root Guess within the context of the Puzzle

        Returns:
            A List of Guesses representing all possible children of the candidate_guess
        """
        # calculate new letter pool
        remaining = self.letter_bank.copy()
        remaining.subtract(candidate_guess.placed)
        del remaining[" "]

        if any([v < 0 for v in remaining.values()]):
            # the submitted guess uses letters not in the bank
            # no placement of additional letters can save it
            raise StopIteration

        # restrict vocab to what can be spelled given the remaining letters
        # after removing letters used by the guess
        vocab = set(w for w in self.vocabulary if Fragment(w).letters <= remaining)

        if self.c1663:
            candidate_words = Fragment(candidate_guess.placed).words
            if len(candidate_words[-1]) == 11 and len(candidate_words[-2]) != 8:
                # len 11 and len 8 are adjacent
                # if len 11 has appeared, and len 8 has not, it must be next
                vocab = set(w for w in vocab if len(w) == 8)

        for word in vocab:
            # compute child candidate and remaining letters
            next_candidate = Fragment(candidate_guess.placed + " " + word)
            next_remaining = self.letter_bank.copy()
            next_remaining.subtract(next_candidate.sentence)
            del next_remaining[" "]

            if not soft_validate(next_candidate, next_remaining, c1663=self.c1663):
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
                score = self.score_candidate(next_candidate.sentence, next_remaining)

            g = Guess(
                next_candidate.sentence, "".join(next_remaining.elements()), score
            )
            yield g

    def score_candidate(self, candidate: str, remaining: Counter):
        oracle = self.oracle.score_candidate(candidate)

        # used_letter_count = Fragment(candidate).letters.total()
        # letter_usage = math.log(
        #     used_letter_count / (used_letter_count + remaining.total())
        # )
        # return math.fsum((oracle, letter_usage))
        return oracle
