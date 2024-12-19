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
