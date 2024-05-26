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
        bank = self.letter_bank.letters

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
    