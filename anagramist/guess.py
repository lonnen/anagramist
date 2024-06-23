from dataclasses import dataclass
from typing import Self


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
