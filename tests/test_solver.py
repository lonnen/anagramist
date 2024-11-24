from collections import Counter
import os
import sqlite3

import pytest
from anagramist.oracles import TransformerOracle
from anagramist.persistentsearchtree import PersistentSearchTree
from anagramist.solver import Solver

@pytest.fixture
def temp_database():
    db_name = "test_anagramist.db"
    sqlite3.connect(db_name)
    yield db_name
    os.remove(db_name)

TRANSFOMER_MODEL = "microsoft/phi-1_5"
TRANSFORMER_SEED = 42
SHARED_ORACLE = TransformerOracle(TRANSFOMER_MODEL, TRANSFORMER_SEED)


class TestSolver:
    def test_init(self, temp_database):
        solver = Solver(
            "dromiceiomimus is a dinosaur",
            PersistentSearchTree(db_name=temp_database),
            SHARED_ORACLE,
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
