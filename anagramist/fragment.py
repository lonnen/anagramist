from collections import Counter
from dataclasses import dataclass
from typing import List


@dataclass()
class Fragment:
    """A fragment of the puzzle, consisting of the ordered string and the letters that
    make up that sentence (ignoring spaces, per the rules of the puzzle)

    Args:
        candidate_sentence (`String`) - a single string containing a sentence fragment
            that could have come from Dinosaur Comics
    """

    def __init__(self, candidate_sentence: str, word: bool = False):
        self.sentence = candidate_sentence
        self.letters = Counter(candidate_sentence)
        self.letters[" "] = 0
        if word:
            self.words = parse_sentence(candidate_sentence)
        else:
            self.words = [candidate_sentence]


def parse_sentence(candidate_sentence: str) -> List[str]:
    """partition a candidate sentence string into a list of words.

    Characters ' and - are treated as letters in a larger word, but any other
    punctuation is split out as an independent word.

    Args:
        candidate_sentence (`String`) - a single string containing a sentence fragment
        that could have come from Dinosaur Comics
    """
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
            if words[-1] != "":
                # move to a new word as in the case of comma without preceeding space
                # but check first so sequential punctuation don't leave empty words
                words.append("")
            words[-1] += char
            words.append("")
    if words[-1] != "":
        return words
    return words[:-1]
