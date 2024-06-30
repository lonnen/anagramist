import logging
from math import fsum
from random import choices
from os import PathLike
from typing import Counter, List, Set

from .fragment import Fragment
from .oracles import TransformerOracle
from .puzzle import Puzzle
from .searchqueue import PersistentSearchTree
from .vocab import vocab

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
    #         """ttttttttttttooooooooooeeeeeeeeaaaaaaallllllnnnnnnuuuuuuiiiiisssss
    #            dddddhhhhhyyyyyIIrrrfffbbwwkcmvg:,!!""",
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

    while True:
        node = root
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
            for word in compute_valid_vocab(
                puzzle.vocabulary, puzzle.letter_bank, c1663
            ):
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
            next_words = [
                w for w in compute_valid_vocab(puzzle.vocabulary, remaining, c1663)
            ]

            next = choices(next_words)[0]
            node = node + " " + next

        # preprocessing to get to word-level scores
        scored_tokens = oracle.calc_candidate_scores(
            [
                placed.sentence,
            ]
        )[0]
        scored_words = []
        for w in placed.words:
            accumulated_tokens = []
            while "".join([token.strip() for token, _ in accumulated_tokens]) != w:
                accumulated_tokens.append(scored_tokens.pop(0))
            scored_words.append(
                [
                    "".join([token.strip() for token, _ in accumulated_tokens]),
                    fsum([score for _, score in accumulated_tokens]),
                ]
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
            search_tree.push(sentence, "".join(remaining.elements()), parent, score)


def compute_valid_vocab(vocab: List[str], remaining: Counter, c1163: bool):
    """Filters the vocab list to return only know-valid words that can be placed next.

    Args:
        vocab (`List[str]`) - the list containing the words that are legal to use in
            this puzzle
        remaining (`Counter`) - the letters remaining to be placed
        c1163 (`bool`) - whether or not to leverage comic 1663 specific hints
    """
    for word in vocab:
        next_word = Fragment(word)
        if not next_word.letters <= remaining:
            continue
        if not c1163:
            yield next_word.sentence
        else:
            if remaining.get("w", 0) == next_word.letters.get("w", 0):
                if next_word.sentence[-1] != "w":
                    # last word must end in "w"
                    continue
                if remaining != next_word.letters + +Counter("!!"):
                    # the last w must be used in the final word
                    continue
            yield next_word.sentence


def soft_validate(
    placed: Fragment,
    remaining: Counter,
    vocabulary: Set[str] = vocab,
    c1663: bool = False,
) -> bool:
    """Soft validation answers whether the candidate conforms to the problem
    constraints given the placement of letters so far.

    All incomplete solutions will violate at least some of the problem constraints
    as the space is explored, by virtue of having some unplaced letters. Soft
    validation will only fail if some placement of the current letters guarantees
    that no possible placement of remaining letters could make the guess valid.

    Critically passing soft validation does not necessarily guarantee there exists
    a solution in an arrangement of remaining letters, only that the current
    placement does not preclude one existing.

    Examples of states that would return false include placements using words
    outside of the vocab list, or characters outside of the letter bank. For c1663,
    additional constraints are applied, collected from Ryan North's hints about that
    specific puzzle. For example, the final letter of the puzzle is "w". This means
    that if all the "w"s are used before the final word is placed, the guess fails
    soft validation. It also means when there are no remaining values, the final
    placed letter should be "w".
    """
    # the sentence uses only characters from the provided bank
    if any([v < 0 for v in remaining.values()]):
        return False  # candidate uses letters not in the bank

    if any([w not in vocab for w in placed.words]):
        return False  # candidate uses words not in the bank

    if remaining.total() > 0:
        for w in vocabulary:
            if Fragment(w).letters <= remaining:
                # at least one valid word can be spelled with the remaining letters
                break
        else:
            return False  # candidate can't make a valid word with remaining letters

    if not c1663:
        return True

    # from here on out, the constraints are derived from hints about comic 1663

    # the first word is "I"
    if placed.words[0] != "I":
        return False

    # punctuation is in the solution in the order :,!!
    expected_punctuation = [":", ",", "!", "!"]
    punctuation_position = 0
    for w in placed.words:
        if len(w) == 1 and w not in set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"):
            if expected_punctuation[punctuation_position] != w:
                return False
            punctuation_position += 1

    # longest word is 11 characters long
    # second longest word is 8 characters long
    # the words are side by side in the solution
    word_lengths = [len(w) for w in placed.words]
    for pos, length in enumerate(word_lengths):
        if length <= 8:
            continue
        if length != 11:
            # we have a word longer than 8 chars that is not 11 letters
            return False
        # now we have our 11 letter word
        # if it is the most recently placed, the next word could be length 8
        if pos == len(word_lengths) - 1:
            continue
        if word_lengths[pos - 1] != 8 and word_lengths[pos + 1] != 8:
            # either the word before or after must be 8
            return False

    # the final letter is "w"
    # so the final three characters must be "w!!"
    if remaining.total() == 2:
        if placed.sentence[-1] != "w" or remaining["!"] != 2:
            return False

    # so word bank must contain a "w!!" until the end
    if remaining.total() > 3:
        if remaining["w"] == 0 or remaining["!"] < 2:
            return False

    # so there must be a word in the vocab ending in "w" until the last
    if remaining.total() > 2:
        for w in vocabulary:
            if Fragment(w).letters <= remaining and w[-1] == "w":
                # at least one valid word ending in "w" remains
                break
        else:
            # remaining letters do not allow for a word ending in "w"
            return False

    return True
