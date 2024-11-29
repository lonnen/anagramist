from collections import Counter
import itertools
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
C1663_LETTERS = "ttttttttttttooooooooooeeeeeeeeaaaaaaallllllnnnnnnuuuuuuiiiiisssssdddddhhhhhyyyyyIIrrrfffbbwwkcmvg:,!!" #noqa

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

    def test_select(self, temp_database):
        expected = "no"
        solver = Solver(
            "",
            PersistentSearchTree(db_name=temp_database),
            SHARED_ORACLE,
            vocabulary=['no', 'problems'],
            c1663=False,
        )
        solver.search_tree.push(expected, "", "", 0, 0, 0, 0)
        # only one entry should always return that entry
        assert expected == solver.select()
        # it can be repeatedly sampled
        assert expected == solver.select()
        #when called with a prefix, it should return iff the prefix matches
        assert expected == solver.select("n")
        # when called with a prefix that doesn't match, it should fall over
        with pytest.raises(ValueError):
            solver.select("problems")
        # when called with a prefix that exactly matches, it should return
        assert expected == solver.select("no")

    def test_expansion(self, temp_database):
        vocab = ['bish', 'bash', 'bosh']
        solver = Solver(
            "bishbashbosh",
            PersistentSearchTree(db_name=temp_database),
            SHARED_ORACLE,
            vocabulary=vocab,
            c1663=False,
        )
        actual = solver.expansion("bish")
        assert "bish bash bosh" == actual or "bish bosh bash" == actual
        # immediate soft validation fail will return the candidate
        assert "Richmond" == solver.expansion("Richmond")
        # verify an empty string arg comes back as a space separated sentence
        expected = set(" ".join(v) for v in itertools.combinations(vocab, 3))
        assert solver.expansion("") in expected

    def test_assessment(self, temp_database):
        vocab = ['bish', 'bash', 'bosh']
        solver = Solver(
            "bishbashbosh",
            PersistentSearchTree(db_name=temp_database),
            SHARED_ORACLE,
            vocabulary=vocab,
            c1663=False,
        )
        actual = solver.assessment("bish bash bosh")
        # a hard validating winners score is infinite
        assert float("inf") == actual[-1][3]
        # one response per word
        assert len(actual) == 3
        # responses should build up towards the provided sentence
        # '!!' is appended after hard validation
        expected = ["bish", "bish bash", "bish bash bosh!!"]
        for e, a in zip(expected, [a[0] for a in actual]):
            assert e == a
        # remaining letters should diminish as words are added
        for e, a in zip(['bbsshhao', 'bsho', ''], [a[1] for a in actual]):
            assert e == a

    def test_compute_valid_vocab(self, temp_database):
        vocab = ['bish', 'bash', 'bosh']
        solver = Solver(
            "bishbash",
            PersistentSearchTree(db_name=temp_database),
            SHARED_ORACLE,
            vocabulary=vocab,
            c1663=False,
        )
        actual = solver.compute_valid_vocab(solver.letter_bank)
        expected = ["bish", "bash"]
        for e, a in zip(expected, actual):
            assert e == a
        
        # this puzzle is insolvable given the mix of letters and vocab words but
        # the compute_valid_vocab method should still work
        solver = Solver(
            "bishbshbsh",
            PersistentSearchTree(db_name=temp_database),
            SHARED_ORACLE,
            vocabulary=vocab,
            c1663=False,
        )
        actual = solver.compute_valid_vocab(solver.letter_bank)
        expected = ["bish"]
        assert expected == [a for a in actual]

    def test_soft_validate(self, temp_database):
        vocab = ['bish', 'bash', 'bosh']
        solver = Solver(
            "bishbash",
            PersistentSearchTree(db_name=temp_database),
            SHARED_ORACLE,
            vocabulary=vocab,
            c1663=False,
        )
        # a perfect answer should return true
        assert solver.soft_validate("bish bash")
        # a partial answer that breaks no rules should return true
        assert solver.soft_validate("bish")
        assert solver.soft_validate("bash")
        # cannot use letters not in the bank
        assert not solver.soft_validate("pete")
        # cannot use words not in the bank, even though the letters are there
        assert not solver.soft_validate("shabba")

    def test_soft_validate_c1663(self, temp_database):
        """It is difficult to propery test all the validation criteria without having a
        solution. This draws a candidate from the database that excercises most of the
        rules, but which is comically low scoring because it makes no sense.
        """
        solver = Solver(
            C1663_LETTERS,
            PersistentSearchTree(db_name=temp_database),
            SHARED_ORACLE,
            c1663=True,
        )
        assert solver.soft_validate(
            ("I behave rate outdone instinctual throttle honking serum lean stout "
             "ball hush id leds duty fyi I fo : tada yo , toy of")
        )
        # must start with "I"
        assert not solver.soft_validate(
            ("behave rate outdone instinctual throttle honking serum lean stout "
             "ball hush id leds duty fyi I fo : tada yo , toy of")
        )
        # punctuation must appear in order :,!!
        assert not solver.soft_validate(
            ("I behave rate outdone instinctual throttle honking serum lean stout "
             "ball hush id leds duty fyi I fo , tada yo : toy of")
        )
        # longest word must be 11 letters, and it must occur next to an 8 letter word
        assert not solver.soft_validate(
            ("I behave rate outdone instinctual honking serum throttle lean stout "
             "ball hush id leds duty fyi I fo : tada yo , toy of")
        )
        # There must be a w remaining if any characters are remaining
        assert not solver.soft_validate(
            ("I behave rate outdone instinctual throttle honking serum lean stout "
             "ball hush id leds duty fyi I fo : tada yow , toy of")
        )

    def test_hard_validate(self, temp_database):
        """Hard validation will only pass when theres an exact solution, which is
        unknown for c1663. We can only test it for non-c1663 puzzles, which will not
        excercise the full set of constraints
        """
        vocab = ['bish', 'bash', 'bosh']
        solver = Solver(
            "bishbash",
            PersistentSearchTree(db_name=temp_database),
            SHARED_ORACLE,
            vocabulary=vocab,
            c1663=False,
        )
        # a perfect answer should return true
        assert solver.hard_validate("bish bash")
        # a partial answer that with letters remaining should return false
        assert not solver.hard_validate("bish")
        assert not solver.hard_validate("bash")
        # cannot use letters not in the bank
        assert not solver.hard_validate("pete")
        # cannot use words not in the bank, even though the letters are there
        assert not solver.hard_validate("shabba")

    def test_solve(self, temp_database):
        """this depends on the exact seed. In order for it to complete in a reasonable
        time it has to be short, which blunts the ability of the oracle to converge
        search towards the highest scoring outcome. At best, this is a barely convincing
        test of the happy path through the wiring of the solver task.
        """
        expected = "bash bish bosh"
        solver = Solver(
            expected, # the letter bank
            PersistentSearchTree(db_name=temp_database),
            SHARED_ORACLE,
            vocabulary=['bish', 'bash', 'bosh'],
            c1663=False,
        )
        assert expected == solver.solve()

    def test_retrieve_candidate(self, temp_database):
        pst = PersistentSearchTree(db_name=temp_database)
        # insert rows taken from the solved prior test
        pst.push("", "bbbassshhhio", "", -40, -40, -40, 0)
        pst.push("bash", "bbsshhio", "", -21.8, -21.8, -21.8, 0)
        pst.push("bash bish", "bsho", "bash", -29.7, -51, -27.7, 0)
        solver = Solver(
            "bish bash bosh",
            pst,
            SHARED_ORACLE,
            vocabulary=["bish", "bash", "bosh"],
            c1663=False,
        )
        stats, top_children, top_descendents = solver.retrieve_candidate("bash")

        assert len(stats.items()) == 2
        assert sum([v["count"] for v in stats.values()]) == 2
        assert stats["0"]["percentage"] == 0.5

        assert len(top_children) == 1
        assert top_children["bash bish"] == (
            "bash bish",
            "bsho",
            "bash",
            -29.7,
            -51.0,
            -27.7,
            0,
        )
        assert top_descendents["bash bish"] == (
            "bash bish",
            "bsho",
            "bash",
            -29.7,
            -51.0,
            -27.7,
            0,
        )
