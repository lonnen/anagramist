from .logits import LetterBankLogitsProcessor
from .solvers import GenerativeSolver

import logging
from os import PathLike

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


def generate_text(
    letters: str,
    model_name_or_path: str | PathLike[str],
    seed: int,
    use_gpu: bool = False,
    fp16: bool = False,
    c1663: bool = False,
):
    solver = GenerativeSolver(model_name_or_path, seed, (not use_gpu), fp16, c1663)
    solver.generate_solutions(letters)
