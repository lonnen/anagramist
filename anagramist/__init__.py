import logging
from random import choices
from os import PathLike

from .fragment import Fragment
from .oracles import TransformerOracle
from .puzzle import Puzzle
from .searchqueue import PersistentSearchTree

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


def search(
    letters: str,
    model_name_or_path: str | PathLike[str],
    seed: int,
    use_gpu: bool = False,
    fp16: bool = False,
    c1663: bool = False,
):
    if c1663:
        logger.debug("c1663 is true - overriding provided letters")
        puzzle = Puzzle(
            "ttttttttttttooooooooooeeeeeeeeaaaaaaallllllnnnnnnuuuuuuiiiiisssssdddddhhhhhyyyyyIIrrrfffbbwwkcmvg:,!!",
            oracle=TransformerOracle(
                model_name_or_path, seed, (not use_gpu), fp16, c1663
            ),
            c1663=c1663,
        )
        return puzzle.search("I", strategy="strat_random_dfs")
    else:
        puzzle = Puzzle(
            letters,
            oracle=TransformerOracle(
                model_name_or_path, seed, (not use_gpu), fp16, c1663
            ),
            c1663=c1663,
        )
        return puzzle.search("")


# the exploration constant is the stand in score for unscored candidates
EXPLORATION_SCORE = float(-40)


def faux_uct_search(
    letters: str,
    model_name_or_path: str | PathLike[str],
    seed: int,
    use_gpu: bool = False,
    fp16: bool = False,
    c1663: bool = False,
):
    # setup
    oracle = TransformerOracle(model_name_or_path, seed, (not use_gpu), fp16, c1663)
    search_tree = PersistentSearchTree()
    puzzle = Puzzle(letters, c1663=c1663)
    root = "I" if c1663 else ""

    node = root
    while True:
        # selection
        p, r, score, parent = search_tree.get(node)
        placed = Fragment(placed)
        remaining = Fragment(remaining)

        if score is None:
            # we have found an unexpanded node
            break

        words = []
        for word in puzzle.vocabulary:
            if not Fragment(word).letters <= remaining:
                # word cannot be spelled with remaining characters
                continue
            words.append(
                search_tree.get(placed.sentence + " " + word, EXPLORATION_SCORE)
            )
        # weighted random sample based on score, or EXPLORATION_SCORE if unvisited
        node = choices([w[0] for w in words], weights=[w[1] for w in words])[0]
        # keep looping until we reach an unexpanded node (no score)

    # expansion
    node 

    # simulation

    # backpropogation
