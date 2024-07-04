import sqlite3
from contextlib import closing
from typing import Tuple


class PersistentSearchTree:
    """A persistence structure for storing the tree-search-space in a SQL lite db.
    Absolutely not thread-safe, nor any other kind of safe. It will delete all your data
    and physically deform your storage devices. It is literally powered by injustice.

    Attributes:
        __TABLE_SCHEMA_VISITED (str): (class attribute) The database schema to be
        created if the connection is successful and the necessary tables don't exist yet
        __TABLE_SCHEMA_FRONTIER (str): (class attribute) The database schema to be
        created if the connection is successful and the necessary tables don't exist yet
    """

    __TABLE_SCHEMA_VISITED = """
    CREATE TABLE IF NOT EXISTS visited (
        placed TEXT NOT NULL,
        remaining TEXT NOT NULL,
        parent TEXT NOT NULL,
        score REAL,
        cumulative_score REAL,

        PRIMARY KEY(placed, remaining)
    );
    """

    def __init__(self, db_name="anagramist.db"):
        self.__db_name = db_name
        con = sqlite3.connect(self.__db_name)
        with con:
            cursor = con.cursor()
            cursor.execute(self.__TABLE_SCHEMA_VISITED)
        con.close()

    def __len__(self):
        with closing(sqlite3.connect(self.__db_name)) as conn:  # auto-closes
            with conn:  # auto-commits
                with closing(conn.cursor()) as cursor:  # auto-closes
                    return cursor.execute("SELECT COUNT(*) FROM visited").fetchone()[0]

    def get(self, placed: str, default=None) -> Tuple[str, str, str, float, float]:
        with closing(sqlite3.connect(self.__db_name)) as conn:  # auto-closes
            with conn:  # auto-commits
                with closing(conn.cursor()) as cursor:  # auto-closes
                    fetch = cursor.execute(
                        """
                        SELECT *
                        FROM visited
                        WHERE placed = ?
                        LIMIT 1
                    """,
                        (placed,),
                    ).fetchone()
                    if fetch is None:
                        if default is not None:
                            return default
                    return fetch

    def get_children(self, parent: str):
        with closing(sqlite3.connect(self.__db_name)) as conn:  # auto-closes
            with conn:  # auto-commits
                with closing(conn.cursor()) as cursor:  # auto-closes
                    fetch = cursor.execute(
                        """
                        SELECT *
                        FROM visited
                        WHERE parent = ?
                    """,
                        (parent,),
                    ).fetchall()
                    return fetch

    def push(
        self,
        placed: str,
        remaining: str,
        parent: str,
        score: float | None,
        cumulative_score: float | None,
    ):
        con = sqlite3.connect(self.__db_name)
        cur = con.cursor()
        cur.execute(
            """INSERT INTO visited 
                VALUES (?, ?, ?, ?, ?) 
            ON CONFLICT (placed, remaining) 
            DO UPDATE SET 
                score = excluded.score, 
                cumulative_score = excluded.cumulative_score
            """,
            (placed, remaining, parent, score, cumulative_score),
        )
        con.commit()
