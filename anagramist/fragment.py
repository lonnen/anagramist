from collections import Counter

from . import parse_sentence
from .vocab import vocab


class Fragment:
    """A fragment of the puzzle, consisting of the ordered string and the letters that
    make up that sentence (ignoring spaces, per the rules of the puzzle)

    Args:
        candidate_sentence (`String`) - a single string containing a sentence fragment
            that could have come from Dinosaur Comics
    """

    def __init__(self, candidate_sentence: str):
        self.sentence = parse_sentence(candidate_sentence)
        self.letters = Counter(candidate_sentence)
        self.letters[" "] = 0