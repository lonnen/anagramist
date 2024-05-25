from typing import List

from .fragment import Fragment
from .vocab import vocab


class Puzzle:
    """A cryptoanagram puzzle consisting of a bank of letters to be formed into a
    sentence and an optional partial solution.

    Args:
        letter_bank: (`String`) - a string containing all the characters to be used in
        the solution. Spaces will be ignored. This may be a sentence, or a simple
        sequence of letters
        candidate: (`String`) or (`Fragment`) - a possible, possibly partial, solution
        to the puzzle
        vocabulary: (`List[String]`) - a list of words that may be used in valid answers
        c1663: (`bool`) - whether or not to apply special constraints that only apply
        to comic 1663 "The Qwantzle"
    """

    def __init__(
        self,
        letter_bank: str,
        candidate: str | Fragment = "",
        vocabulary: List[str] = vocab,
        c1663: bool = False,
    ) -> None:
        self.letter_bank = Fragment(letter_bank)
        if isinstance(candidate, str):
            self.candidate = Fragment(candidate)
        else:
            self.candidate = candidate
        self.vocabulary = vocabulary
        self.c1663 = c1663
