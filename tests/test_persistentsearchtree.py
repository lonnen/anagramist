import os
import pytest
import sqlite3
from anagramist import PersistentSearchTree


@pytest.fixture
def temp_database():
    db_name = "test_anagramist.db"
    sqlite3.connect(db_name)
    yield db_name
    os.remove(db_name)


class TestPersistentSearchTree:
    def test_database_creation(self, temp_database):
        PersistentSearchTree(db_name=temp_database)
        con = sqlite3.connect(temp_database)
        cur = con.cursor()
        cur.execute("""
            SELECT name
            FROM sqlite_schema
            WHERE type='table';
        """)
        assert [x[0] for x in cur.fetchall()] == ["visited"]
        con.commit()
        cur.close()

    def test_database_push(self, temp_database):
        psq = PersistentSearchTree(db_name=temp_database)
        psq.push(
            "placed letters",
            "remaining letters",
            "placed",
            float(0),
            float(0),
            float(0),
            0,
        )

        con = sqlite3.connect(temp_database)
        cur = con.cursor()
        cur.execute("""
            SELECT *
            FROM visited;
        """)
        assert cur.fetchone() == (
            "placed letters",
            "remaining letters",
            "placed",
            0.0,
            0.0,
            0.0,
            0,
        )
        con.commit()
        cur.close()

    def test_database_verify_integrity(self, temp_database):
        pst = PersistentSearchTree(db_name=temp_database)
        pst.push("", "placedletters", "", None, None, None, None)
        pst.push("placed", "letters", "", None, None, None, None)
        pst.push("placed letters", "", "placed", None, None, None, None)
        pst.push("letters", "placed", "", None, None, None, None)
        pst.push("letters placed", "", "letters", None, None, None, None)

        integrity, pools = pst.verify_integrity()
        assert integrity
        assert len(pools.items()) == 1

    def test_database_verify_empty(self, temp_database):
        pst = PersistentSearchTree(db_name=temp_database)

        integrity, pools = pst.verify_integrity()
        assert integrity
        assert len(pools.items()) == 0

    def test_database_verify_integrity_failure(self, temp_database):
        pst = PersistentSearchTree(db_name=temp_database)
        pst.push("", "placedletters", "", None, None, None, None)
        pst.push("p", "placedletters", "", None, None, None, None)
        pst.push("pl", "placedletters", "", None, None, None, None)
        pst.push("pl ace d", "placedletters", "pl ace", None, None, None, None)
        pst.push("pl ace d l", "pleacedletters", "pl ace d", None, None, None, None)

        integrity, pools = pst.verify_integrity()
        assert not integrity
        assert len(pools.items()) == 5
