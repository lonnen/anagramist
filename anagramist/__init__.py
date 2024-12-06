import logging

import cProfile
from pstats import Stats

from .fragment import Fragment as Fragment
from .oracles import TransformerOracle as TransformerOracle
from .persistentsearchtree import PersistentSearchTree as PersistentSearchTree
from .solver import Solver as Solver

logging.basicConfig(
    format="[%(asctime)s] %(message)s",
    level=logging.DEBUG,
)
logging.captureWarnings(capture=True)
logger = logging.getLogger(__name__)

PROFILING_ITERATIONS = 10
"""how many iterations of search to do while profiling"""


def search(
    letters: str,
    search_tree: PersistentSearchTree,
    oracle: TransformerOracle,
    c1663: bool = False,
    do_profiling: bool = True,
):
    if do_profiling:
        with cProfile.Profile() as pr:
            s = Solver(
                letters,
                search_tree,
                oracle,
                c1663=c1663,
                max_iterations=PROFILING_ITERATIONS,
            )
            s.solve()
        with open("profiling_stats.txt", "w") as stream:
            stats = Stats(pr, stream=stream)
            stats.strip_dirs()
            stats.sort_stats("time")
            stats.dump_stats(".prof_stats")
            stats.print_stats()
        return
    s = Solver(
        letters, search_tree, oracle, c1663=c1663, max_iterations=PROFILING_ITERATIONS
    )
    s.solve()
