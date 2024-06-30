import logging
from math import fsum
from random import choices
from os import PathLike

from .fragment import Fragment
from .oracles import TransformerOracle
from .puzzle import Puzzle, soft_validate
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
    faux_uct_search(letters, model_name_or_path, seed, use_gpu, fp16, c1663)
    # if c1663:
    #     logger.debug("c1663 is true - overriding provided letters")
    #     puzzle = Puzzle(
    #         "ttttttttttttooooooooooeeeeeeeeaaaaaaallllllnnnnnnuuuuuuiiiiisssssdddddhhhhhyyyyyIIrrrfffbbwwkcmvg:,!!",
    #         oracle=TransformerOracle(
    #             model_name_or_path, seed, (not use_gpu), fp16, c1663
    #         ),
    #         c1663=c1663,
    #     )
    #     return puzzle.search("I", strategy="strat_random_dfs")
    # else:
    #     puzzle = Puzzle(
    #         letters,
    #         oracle=TransformerOracle(
    #             model_name_or_path, seed, (not use_gpu), fp16, c1663
    #         ),
    #         c1663=c1663,
    #     )
    #     return puzzle.search("")


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
        # take a random weighted walk across the known world to an unexpanded node
        while True:
            cached = search_tree.get(node)
            if cached is None:
                # we have found an unexpanded node
                break

            p, r, score, _ = cached

            placed = Fragment(p)
            remaining = Fragment(r)

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
            # loop repeats, breaking when we reach an unexpanded node (no score)

        # expansion & simulation
        # take a deep, uniform, random walk until soft validation fails
        while True:
            placed = Fragment(node)
            remaining = puzzle.letter_bank.copy()
            remaining.subtract(placed.letters)

            if not soft_validate(placed, remaining, puzzle.vocabulary, c1663):
                break

            # recalculate all valid next words
            # pick one by uniform random sample
            next_words = [w for w in puzzle.vocabulary if Fragment(w).letters <= remaining]
            next = choices(next_words)[0]
            node = node + " " + next

        # preprocessing to get to word-level scores
        scored_tokens = oracle.calc_candidate_scores([placed.sentence,])[0]
        scored_words = []
        for w in placed.words:
            accumulated_tokens = []
            while "".join([token.strip() for token, _ in accumulated_tokens]) != w:
                accumulated_tokens.append(scored_tokens.pop(0))
            scored_words.append([
                "".join([token.strip() for token, _ in accumulated_tokens]),
                fsum([score for _, score in accumulated_tokens])]
            )

        # backpropogation
        # add the new random walk information to the known table
        sentence = ""
        for w, score in scored_words:
            parent = sentence
            if sentence == "":
                sentence = sentence + w
            else:
                sentence = sentence + " " + w
            remaining = puzzle.letter_bank.copy()
            remaining.subtract(sentence)
            # check for a winner
            if (
                sentence[-1] == "w"
                and remaining.total() == 2
                and remaining.get("!") == 2
            ):
                # we have a winner
                sentence += "!!"
                del remaining["!"]
                print("WINNER: {}".format(sentence))
                score = float("inf")
            search_tree.push(sentence, "".join(remaining.elements()), score, parent)
