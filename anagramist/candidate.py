from .vocab import vocab

from collections import Counter
from typing import List


class Candidate:
    def __init__(self, candidate_sentence: str):
        self.sentence = self.parse(candidate_sentence)
        self.letters = Counter(candidate_sentence)
        self.letters[" "] = 0

    def validate(self, letter_bank: str, c1663: bool = False) -> bool:
        """Answers whether the candidate_sentence satisfies the constraints of the Qwantzle puzzle. Not all constraints can be checked computationally, but
        the following are checked:

            * The candidate_sentence uses exactly all of the characters from the letter_bank, not counting whitespace
            * The characters are case-sensitive
            * All the words are vocabulary.txt dictionary included in this library (1-grams from qwantz comics up to c1663)

        Additional constraints that are checked iff c1663:

            * The solution starts with "I"
            * The punctuation appears in the order :,!!
            * The longest word is 11 characters long
            * The second longest word is 8 characters, and occurs adjacent to the longest word

        Constraints that are not validated:

            * The solution is a natural-sounding, reasonably-grammatical dialogue that T-rex would say
            * The solution does not refer to anagrams or puzzles or winning t-shirts
            * The solution is directly related to the content of the comic 1663 "The Qwantzle"
            * The solution "would make a good epitaph"

        Constraints collected from https://github.com/lonnen/cryptoanagram/blob/main/README.md. There are multiple anagrams of c1663
        that will pass this function, which satisfy several of the "Constraints that are not validated", but which are not the solution.

        Args:
            letter_bank (`String`) - the letters available for the anagram. Spaces are ignored, so sentences may be passed directly
            candidate_sentence (`String`) - a string to validate against the constraints of the Qwantzle
            c1663 (`bool`) - whether or not to apply special constraints that only apply to comic 1663 "The Qwantzle"

        return (`bool`) - does the candidate sentence satisfy the constraints of the Qwantzle puzzle
        """
        bank = Counter(letter_bank)
        bank[" "] = 0

        # first check - do they have the same numbers of specific letters?
        if not self.letters == bank:
            return False

        # check that every word appears in the vocab list
        for word in self.sentence:
            if word == "":
                continue
            if word not in vocab:
                return False

        if not c1663:
            return True

        # From here out, only rules specific to comic 1663

        if self.sentence[0] != "I":
            return False

        words_len = [len(w) for w in self.sentence]

        longest, second_longest = sorted(words_len)[:2]
        if longest != 11 or second_longest != 8:
            return False

        position_longest = words_len.index(11)
        if words_len[position_longest - 1] != 8 or words_len[position_longest + 1] != 8:
            return False

        return True

    @staticmethod
    def parse(candidate_sentence) -> List[str]:
        # partition out the candidate sentence into words with some punctuation treated as its own words
        words = [""]
        for char in candidate_sentence:
            if char in set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'-"):
                words[-1] += char
            elif char == " ":
                # on whitespace, ensure the next word is a fresh, empty string
                # this is necessary for longer stretches of whitespace, or the case
                # of no whitespace around punctuation-that-is-itself-a-word
                if words[-1] != "":
                    words.append("")
            else:
                # anything else is a word unto itself
                words.append(char)
                words.append("")
        return words
