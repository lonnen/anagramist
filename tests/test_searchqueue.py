import os
import pytest
import sqlite3
from anagramist.puzzle import Guess
from anagramist.searchqueue import PersistentSearchQueue


@pytest.fixture
def temp_database():
    db_name = "test_anagramist.db"
    sqlite3.connect(db_name)
    yield db_name
    os.remove(db_name)


class TestSearchQueue:
    def test_database_creation(self, temp_database):
        PersistentSearchQueue(db_name=temp_database)
        con = sqlite3.connect(temp_database)
        cur = con.cursor()
        cur.execute("""
            SELECT name
            FROM sqlite_schema
            WHERE type='table';
        """)
        assert [x[0] for x in cur.fetchall()] == ["frontier", "visited"]
        con.commit()
        cur.close()

    def test_database_push(self, temp_database):
        psq = PersistentSearchQueue(db_name=temp_database)
        psq.push(Guess("placed letters", "remaining letters", float(0)))

        con = sqlite3.connect(temp_database)
        cur = con.cursor()
        cur.execute("""
            SELECT *
            FROM frontier;
        """)
        assert cur.fetchone() == ("placed letters", "remaining letters", float(0))
        cur.execute("""
            SELECT *
            FROM visited;
        """)
        assert cur.fetchone() == ("placed letters", "remaining letters", float(0))
        con.commit()
        cur.close()

    def test_database_len(self, temp_database):
        psq = PersistentSearchQueue(db_name=temp_database)
        psq.push(Guess("placed letters", "remaining letters", float(0)))
        psq.push(Guess("other letters", "other remaining letters", float(1)))
        psq.push(Guess("even more letters", "some letters", float(2)))

        assert len(psq) == 3