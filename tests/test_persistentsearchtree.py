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
