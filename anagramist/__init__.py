import logging
from os import PathLike

from typing import List

from .oracles import TransformerOracle
from .puzzle import Puzzle

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


def search(
    candidate_sentence: str,
    model_name_or_path: str | PathLike[str],
    seed: int,
    use_gpu: bool = False,
    fp16: bool = False,
    c1663: bool = False,
):
    puzzle = Puzzle(
        oracle=TransformerOracle(model_name_or_path, seed, (not use_gpu), fp16, c1663),
    )
    return puzzle.search()


def calculate_scores(
    candidate_sentence: str,
    model_name_or_path: str | PathLike[str],
    seed: int,
    use_gpu: bool = False,
    fp16: bool = False,
    c1663: bool = False,
):
    """Calculate the log scores of a candidate_sentence being generated by the given
    model
    """
    solver = TransformerOracle(model_name_or_path, seed, (not use_gpu), fp16, c1663)
    return solver.score_candidates(candidate_sentence)


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
            words.append(char)
            words.append("")
    if words[-1] != "":
        return words
    return words[:-1]
