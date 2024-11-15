import logging
from math import fsum
from random import choices
from statistics import geometric_mean
from typing import Counter, Generator, List, Optional, Set, Tuple, Union

import cProfile
from pstats import Stats

from .fragment import Fragment
from .oracles import TransformerOracle
from .persistentsearchtree import PersistentSearchTree
from .vocab import corpus

logging.basicConfig(
    format="[%(asctime)s] %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


CANDIDATE_STATUS_CODES = {
    0: "OK",  # or None
    1: "Fails Validation",
    5: "Fully Explored",
    7: "Manual Intervention",
}

PROFILING_ITERATIONS = 10
"""how many iterations of search to do while profiling"""

MAX_NUM_OF_SIMULATIONS = 100
"""maximum number of simulations for each selection"""

EXPLORATION_SCORE = float(-40)
"""a score used for as-yet unscored candidates"""


def search(
    letters: str,
    search_tree: PersistentSearchTree,
    oracle: TransformerOracle,
    c1663: bool = False,
    do_profiling: bool = True,
):
    if do_profiling:
        with cProfile.Profile() as pr:
            faux_uct_search(
                letters,
                search_tree,
                oracle,
                c1663=c1663,
                max_iterations=PROFILING_ITERATIONS,
            )
        with open("profiling_stats.txt", "w") as stream:
            stats = Stats(pr, stream=stream)
            stats.strip_dirs()
            stats.sort_stats("time")
            stats.dump_stats(".prof_stats")
            stats.print_stats()
        return
    faux_uct_search(letters, search_tree, oracle, c1663=c1663)


def faux_uct_search(
    letters: str,
    search_tree: PersistentSearchTree,
    oracle: TransformerOracle,
    vocabulary: Optional[Set[str]] = None,
    c1663: bool = False,
    max_iterations: Optional[int] = None,
):
    # setup
    letter_bank = Fragment(letters).letters
    root = ""

    if c1663:
        logger.info("using special constraints for comic 1663")
        root = "I"

    vocabulary = corpus(c1663)
    logger.info(f"loaded vocab ({len(vocabulary)} items)")

    loop_count = 0
    while True:
        if max_iterations is not None:
            if loop_count == max_iterations:
                break
            loop_count += 1
        node = root
        # selection
        node, prune = selection(node, letter_bank, search_tree, vocabulary)

        logger.info(f"selected: {node}")
        if prune:
            logger.info(f"{node} is fully explored. pruning...")
            search_tree.trim(node, status=5)
            continue

        simulation_id = 0
        while simulation_id < MAX_NUM_OF_SIMULATIONS:
            simulation_id += 1
            # expansion & simulation
            # take a deep, uniform, random walk until soft validation fails
            placed = simulation(node, letter_bank, vocabulary, c1663)

            # get word-level scores from score_fragment
            scored_words = score_fragment(placed, oracle)

            # construct every stop on a walk out to the candidate node c, with scores
            entries = backpropogation(node, letter_bank, scored_words, c1663)
            for (
                sentence,
                remaining,
                parent,
                score,
                cumulative_score,
                mean_score,
                status,
            ) in entries:
                search_tree.push(
                    sentence,
                    remaining,
                    parent,
                    score,
                    cumulative_score,
                    mean_score,
                    status,
                )
                logger.info(
                    f"recorded simulation ({mean_score:2.2f}, {status}): {sentence}"
                )
                if score == float("inf"):
                    exit()


def selection(
    root: str,
    letter_bank: Counter,
    search_tree: PersistentSearchTree,
    vocabulary: Set[str],
) -> Union[str, bool]:
    """Take a random walk across a given `PersistentSearchTree` starting from a given
    root node. Each step of the walk is determined by a weighted random choice from the
    set of valid next steps, using Oracle scores as weights, a default score for
    unexplored nodes, and ignoring nodes already marked as known losers.

    This method is guaranteed to return an unexplored node or return a node that roots a
    fully explored subtree that can be trimmed.

    Args:
        root (`str`) - A sentence fragment corresponding to the placed letters of a
            puzzle candidate. This is the first half of a position in the search_tree.
        letter_bank (`Counter`) - The total characters to be placed. This is the
            second half of a position in the search tree.
        search_tree (`PersistentSearchTree`) - A tree containing all explored fragments
            of the puzzle.
        vocabulary (`Set[str]`) - The set known to contain at least all the words that
            appear in the solution.

    Returns (`str`) - A string containing an unexplored node chosen by the random walk
            (`bool`) - `True` if the returned node has no unexplored children
    """
    node = root
    # selection
    # take a random weighted walk across the known world to an unexpanded node
    while True:
        cached = search_tree.get(node)
        if cached is None:
            # we have found an unexpanded node
            break

        placed_letters, _, _, _, _, _, _ = cached

        valid_vocab = [w for w in compute_valid_vocab(vocabulary, letter_bank)]
        explored_vocab = {
            entry[0]: entry for entry in search_tree.get_children(placed_letters)
        }

        words = []
        for word in valid_vocab:
            new_sentence = placed_letters + " " + word
            w = explored_vocab.get(
                new_sentence,
                (new_sentence, "", "", EXPLORATION_SCORE, None, None, 0),
            )
            if w[6] == 0:  # see CANDIDATE_STATUS_CODES for details
                words.append(w)
        if len(words) == 0:
            # all legal child nodes have non-zero status, so we're in a dead end
            return placed_letters, True
        # weighted random sample based on score, or EXPLORATION_SCORE if unvisited
        weight_offset = (
            abs(min([w[3] for w in words])) + 1
        )  # weights must sum positive, but all scores are negative
        node = choices(
            [w[0] for w in words], weights=[w[3] + weight_offset for w in words]
        )[0]
        # loop repeats, breaking when we reach an unexpanded node (no score)
    return node, False


def simulation(
    node: str, letter_bank: Counter, vocabulary: Set[str], c1663: bool = False
) -> Fragment:
    """Simulates a deep, uniform, random walk down the branch until soft validation
    fails and no possible arrangement of additional letters could result in a winning
    answer.

    Critically, this leaf node could itself be a winner, because placing any
    additional letters to the winner will never result in a winning answer.

    Returns (`str`) - the leaf node discovered at the end of the random walk
    """
    # expansion & simulation
    # take a deep, uniform, random walk until soft validation fails
    while True:
        placed = Fragment(node)
        remaining = letter_bank.copy()
        remaining.subtract(placed.letters)

        if not soft_validate(placed, remaining, vocabulary, c1663):
            break

        # recalculate all valid next words
        # pick one by uniform random sample
        next_words = [w for w in compute_valid_vocab(vocabulary, remaining)]

        if len(next_words) == 0:
            break

        next = choices(next_words)[0]
        node = node + " " + next
    return placed


def score_fragment(
    placed: Fragment, oracle: TransformerOracle
) -> List[Tuple[str, float]]:
    """Passes a sentence to the provided oracle for scoring, and then post-processes
    the resulting value to combine token-level log-scores from the oracle into a list of
    aligned word-level log-scores

    Args:
        placed: (`Fragment`) - A fragment containing the `str` sentence and `List[str]`
            of words parsed out of that sentence for alignment
        oracle: (`TransformerOracle`) - A wrapper around a transformer model that will
            accept the `str` sentence and return token-level scores for each token given
            the previously examined tokens

    Returns (`List[Tuple[str, float]]`) A list of 2-item tuples containing the
        accumulated words and their combined score
    """
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
        accumulated_word = "".join([token.strip() for token, _ in accumulated_tokens])
        accumulated_score = fsum([score for _, score in accumulated_tokens])
        scored_words.append((accumulated_word, accumulated_score))
    return scored_words


def backpropogation(
    node: str,
    letter_bank: Counter[str],
    scored_words: List[Tuple[str, float]],
    c1663: bool,
) -> List[Tuple[str, str, str, float, float, float, int]]:
    # backpropogation
    # calculate new table entries
    entries = []
    sentence = ""
    cumulative_score = 0
    scores = []
    for w, score in scored_words:
        parent = sentence
        if sentence == "":
            sentence = sentence + w
        else:
            sentence = sentence + " " + w

        scores.append(score)

        if node.startswith(sentence):
            # scored_words has the whole sentence, some of which is already in the db
            # so we build up the scores array for calculating mean_score later and
            # skip everything else to avoid rewriting entries with the same data
            continue

        remaining = letter_bank.copy()
        remaining.subtract(sentence)

        # check for a winner
        if hard_validate(Fragment(sentence), remaining, letter_bank, c1663=c1663):
            # we have a winner
            sentence += "!!"
            del remaining["!"]
            logger.critical("WINNER: {}".format(sentence))
            score = float("inf")
        elif w == scored_words[-1][0]:
            # if the final word doesn't hard validate it must have failed,
            # but we must write down the failure to avoid exploring it further
            score = float("-inf")

        cumulative_score = fsum(scores)
        offset = abs(min(scores)) + 1
        status = 0
        if score == float("-inf") or cumulative_score == float("-inf"):
            mean_score = float("-inf")
            status = 1
        else:
            mean_score = geometric_mean([s + offset for s in scores]) - offset
        entries.append(
            [
                sentence,
                "".join(remaining.elements()),
                parent,
                score,
                cumulative_score,
                mean_score,
                status,
            ]
        )
        if (
            score == float("inf")
            or score == float("-inf")
            or cumulative_score == float("-inf")
            or mean_score == float("-inf")
        ):
            break  # we don't need to continue, infinity means this is a terminal node
    return entries


def compute_valid_vocab(
    vocabulary: List[str], remaining: Counter
) -> Generator[str, None, None]:
    """Filters the vocab list to return only know-valid words that can be placed next.

    Args:
        vocab (`List[str]`) - the list containing the words that are legal to use in
            this puzzle
        remaining (`Counter`) - the letters remaining to be placed
        c1163 (`bool`) - whether or not to leverage comic 1663 specific hints

    Returns (`generator[str, None, None]`) - a generator that yields vocabular words
        that can be spelled with the remaining letters
    """
    for word in vocabulary:
        next_word = Fragment(word)
        if not next_word.letters <= remaining:
            continue
        yield next_word.sentence


def soft_validate(
    placed: Fragment,
    remaining: Counter,
    vocabulary: Set[str],
    c1663: bool = False,
) -> bool:
    """Soft validation answers whether the candidate conforms to the problem
    constraints given the placement of letters so far.

    All incomplete solutions will violate at least some of the problem constraints
    as the space is explored, by virtue of having some unplaced letters. Soft
    validation will only fail if some placement of the current letters guarantees
    that no possible placement of remaining letters could make the guess valid.

    Critically, passing soft validation does not necessarily guarantee there exists
    a solution in an arrangement of remaining letters, only that the current
    placement does not preclude one existing.

    Examples of states that would return false include placements using words
    outside of the vocab list, or characters outside of the letter bank. For c1663,
    additional constraints are applied, collected from Ryan North's hints about that
    specific puzzle. For example, the final letter of the puzzle is "w". This means
    that if all the "w"s are used before the final word is placed, the guess fails
    soft validation. It also means when there are no remaining values, the final
    placed letter should be "w".

    Returns (`bool`) - indicating if the provided fragment `placed` conforms to the
        problem constraits given the letters placed so far
    """
    # the sentence uses only characters from the provided bank
    if any([v < 0 for v in remaining.values()]):
        return False  # candidate uses letters not in the bank

    if any([w not in vocabulary for w in placed.words]):
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
        if len(w) == 1 and w not in set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        ):
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


def hard_validate(
    placed: Fragment,
    remaining: Counter,
    original_letter_bank: Counter,
    vocabulary: Optional[Set[str]] = None,
    c1663: bool = False,
) -> bool:
    """Hard validation andswers whether this passes all the constraints that can be
    verified computationally. In an effort to return quickly it starts with the broadest
    and easiest to check constraints, saving expensive ones for later in the check.

    Returns (`bool`) - whether the provided Fragment `placed` conforms to all
        constraints that can be verified computationally
    """

    if placed.letters != original_letter_bank:
        return False  # placed must use exactly all the letters of the bank

    if any([w not in vocabulary for w in placed.words]):
        return False  # candidate uses words not in the bank

    if not c1663:
        return True

    # from here on out, the constraints are derived from hints about comic 1663

    # the first word is "I"
    if placed.words[0] != "I":
        return False

    # the final three characters are "w!!"
    if placed.sentence[-3:] != "w!!":
        return False

    # punctuation is in the solution in the order :,!!
    expected_punctuation = [":", ",", "!", "!"]
    punctuation_position = 0
    for w in placed.words:
        if len(w) == 1 and w not in set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        ):
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

    return True


def show_candidate(
    root: str,
    pst: PersistentSearchTree,
    limit: int = 5,
    vocabulary: Optional[Set[str]] = None,
    c1663: bool = True,
):
    """Retrieves the node `root` and calculates some statistics about it and its child
    nodes, including how much of the next layer of search has been explored, the most
    promising child nodes, and the most promising nodes that have been discovered in
    this branch of the tree.
    """
    cached = pst.get(root)
    if cached is None:
        return {}, {}, {}
    _, remaining, _, _, _, _, _ = cached
    children = pst.get_children(root)

    vocabulary = corpus(c1663)
    valid_vocab = [w for w in compute_valid_vocab(vocabulary, Counter(remaining))]
    explored_vocab = {entry[0]: entry for entry in children}

    status_codes = {0: 0, 7: 0}
    children = []
    for word in valid_vocab:
        new_sentence = root + " " + word
        w = explored_vocab.get(
            new_sentence,
            (new_sentence, "", "", None, None, None, "Unexplored"),
        )
        sc = w[6]
        if status_codes.get(sc) is None:
            status_codes[sc] = 0
        status_codes[sc] += 1
        if sc == 0:  # see CANDIDATE_STATUS_CODES for details
            children.append(w)
    total = float(sum(status_codes.values()))

    stats = {}
    for sc, v in sorted(status_codes.items(), key=lambda x: str(x)):
        s = str(sc)[0]
        percentage = float(v) / total
        stats[str(s)] = {"status_code": s, "count": v, "percentage": percentage}

    top_children = {}
    for entry in sorted(
        children,
        key=lambda x: x[5] if x[5] is not None else EXPLORATION_SCORE,
        reverse=True,
    )[:limit]:
        top_children[entry[0]] = entry

    descendents = pst.get_descendents(root)
    top_descendents = {}
    for entry in sorted(
        descendents,
        key=lambda x: x[5] if x[5] is not None else EXPLORATION_SCORE,
        reverse=True,
    )[:limit]:
        top_descendents[entry[0]] = entry

    return stats, top_children, top_descendents


def score_one(root, letter_bank, oracle, search_tree, c1663):
    placed = Fragment(root)
    remaining = Fragment(letter_bank)
    remaining.subtract(placed.letters)

    valid_vocab = [w for w in compute_valid_vocab(corpus(c1663), remaining.letters)]
    if not soft_validate(placed, remaining, valid_vocab, c1663):
        return None
    scored_words = score_fragment(placed, oracle)
    entry = backpropogation(placed, remaining, scored_words, c1663)
    if len(entry) > 0:
        search_tree.push(*entry)
        search_tree.push(*entry[-1])
    return entry
