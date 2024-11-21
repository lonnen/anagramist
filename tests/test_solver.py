from collections import Counter
from anagramist.oracles import TransformerOracle
from anagramist.persistentsearchtree import PersistentSearchTree
from anagramist.solver import Solver

PST_DATABASE = "file::memory:?cache=shared"
TRANSFOMER_MODEL = "microsoft/phi-1_5"
TRANSFORMER_SEED = 42


class TestSolver:
    def test_init(self):
        solver = Solver(
            "dromiceiomimus is a dinosaur",
            PersistentSearchTree(PST_DATABASE),
            TransformerOracle(TRANSFOMER_MODEL, TRANSFORMER_SEED),
            c1663=True,
        )
        assert solver.root == "I"
        assert solver.letter_bank == Counter(
            {
                "a": 2,
                "c": 1,
                "d": 2,
                "e": 1,
                "i": 5,
                "m": 3,
                "n": 1,
                "o": 3,
                "r": 2,
                "s": 3,
                "u": 2,
                " ": 0,
            }
        )
