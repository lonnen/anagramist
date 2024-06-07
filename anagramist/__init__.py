import heapq
import logging
from os import PathLike
from typing import Iterable

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
    letters: str,
    model_name_or_path: str | PathLike[str],
    seed: int,
    use_gpu: bool = False,
    fp16: bool = False,
    c1663: bool = False,
):
    puzzle = Puzzle(
        letters,
        oracle=TransformerOracle(model_name_or_path, seed, (not use_gpu), fp16, c1663),
    )
    return puzzle.search()


class PriorityQueue:
    def __init__(self, iterable: Iterable = []) -> None:
        self.pq = heapq.heapify(iterable)

    def push(self, item):
        heapq.heappush(self.pq, item)

    def pop(self):
        return heapq.heappop(self.pq)

    def pushpop(self, item):
        return heapq.heappushpop(self.pq, item)

    def replace(self, item):
        return heapq.heapreplace(self.pq, item)
