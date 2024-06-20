import random
import sqlite3
from contextlib import closing
from typing import Iterable, List, TypeVar


T = TypeVar("T")


class SearchQueue:
    def __init__[T](self, iterable: Iterable[T] = [], max_size: int = None):
        if iterable is not None:
            self.data: List[T] = list(iterable)
        self.max_size: int = max_size

    def __len__(self):
        return len(self.data)

    def weighted_random_sample(self, key=lambda x: x) -> T:
        pos = random.choices(
            [p for p, _ in enumerate(self.data)],
            weights=[key(d) for d in self.data],
        )[0]
        return self.data.pop(pos)

    def push(self, element: T, key=lambda x: x):
        if self.max_size is not None:
            if len(self.data) >= self.max_size:
                index, _ = min(
                    enumerate([key(i) for i in self.data]),
                    key=lambda e: e[1],
                )
                self.data.pop(index)
        self.data.append(element)


class PersistentSearchQueue:
    """A search queue that persists entries to a SQL lite db. Absolutely not
    thread-safe, nor any other kind of safe. It will delete all your data and physically
    deform your storage devices. It is literally powered by injustice.

    Attributes:
        __TABLE_SCHEMA_VISITED (str): (class attribute) The database schema to be
        created if the connection is successful and the necessary tables don't exist yet
        __TABLE_SCHEMA_FRONTIER (str): (class attribute) The database schema to be
        created if the connection is successful and the necessary tables don't exist yet
    """

    __TABLE_SCHEMA_FRONTIER = """
    CREATE TABLE IF NOT EXISTS frontier (
        placed TEXT NOT NULL,
        remaining TEXT NOT NULL,
        score REAL NOT NULL,

        PRIMARY KEY(placed, remaining)
    );
    """
    __TABLE_SCHEMA_VISITED = """
    CREATE TABLE IF NOT EXISTS visited (
        placed TEXT NOT NULL,
        remaining TEXT NOT NULL,
        score REAL NOT NULL,

        PRIMARY KEY(placed, remaining)
    );
    """

    def __init__(self, max_size: int = None, db_name="anagramist.db"):
        self.max_size = max_size
        self.__db_name = db_name
        con = sqlite3.connect(self.__db_name)
        with con:
            cursor = con.cursor()
            cursor.execute(self.__TABLE_SCHEMA_FRONTIER)
            cursor.execute(self.__TABLE_SCHEMA_VISITED)
        con.close()

    def __len__(self):
        with closing(sqlite3.connect(self.__db_name)) as conn:  # auto-closes
            with conn:  # auto-commits
                with closing(conn.cursor()) as cursor:  # auto-closes
                    return cursor.execute("SELECT COUNT(*) FROM frontier").fetchone()[0]

    def weighted_random_sample(
        self,
    ) -> T:
        con = sqlite3.connect(self.__db_name)
        cur = con.cursor()
        rows = cur.execute("""SELECT * FROM frontier""").fetchall()
        sampled = random.choices(rows, weights=[d[2] for d in rows])[0]
        sql = "DELETE FROM frontier WHERE placed = '{}'".format(sampled[0])
        cur.execute(sql)
        con.commit()
        cur.close()
        return sampled

    def push(self, element: T):
        if self.max_size is not None:
            if len(self) >= self.max_size:
                con = sqlite3.connect(self.__db_name)
                cur = con.cursor()
                cur.execute("DELETE FROM frontier ORDER BY score ASC LIMIT 1")
                cur.close()
        con = sqlite3.connect(self.__db_name)
        cur = con.cursor()
        cur.execute(
            """INSERT INTO frontier 
                VALUES (?, ?, ?) 
            ON CONFLICT(placed, remaining) 
            DO UPDATE SET score = excluded.score;
            """,
            (element.placed, element.remaining, element.score),
        )
        cur.execute(
            """INSERT INTO visited 
                VALUES (?, ?, ?) 
            ON CONFLICT(placed, remaining) 
            DO UPDATE SET score = excluded.score
            """,
            (element.placed, element.remaining, element.score),
        )
        con.commit()
