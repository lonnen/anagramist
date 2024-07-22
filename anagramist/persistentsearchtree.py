import sqlite3
from contextlib import closing
from typing import List, Optional, Tuple

from .fragment import Fragment


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
        mean_score REAL,
        status INTEGER,

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

    def __len__(self) -> int:
        with closing(sqlite3.connect(self.__db_name)) as conn:  # auto-closes
            with conn:  # auto-commits
                with closing(conn.cursor()) as cursor:  # auto-closes
                    return cursor.execute("SELECT COUNT(*) FROM visited").fetchone()[0]

    def contains(
        self, word: str, limit: Optional[int] = None, status: Optional[int] = None
    ):
        with closing(sqlite3.connect(self.__db_name)) as conn:  # auto-closes
            with conn:  # auto-commits
                with closing(conn.cursor()) as cursor:  # auto-closes
                    if status is None:
                        status = "*"
                    if limit is None:
                        fetch = cursor.execute(
                            """
                            SELECT *
                            FROM visited
                            WHERE 
                                status = ?
                            AND (placed LIKE ? OR placed LIKE ?)
                            ORDER BY placed
                        """,
                            (status, "% " + word + " %", "% " + word),
                        ).fetchall()
                    else:
                        fetch = cursor.execute(
                            """
                            SELECT *
                            FROM visited
                            WHERE 
                                 status = ?
                            AND (placed LIKE ? OR placed LIKE ?)
                            ORDER BY placed
                            LIMIT ?
                        """,
                            (status, "% " + word + " %", "% " + word, int(limit)),
                        ).fetchall()
                    return fetch

    def get(
        self, placed: str, default=None
    ) -> Tuple[str, str, str, float, float, float, int]:
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

    def get_children(
        self, parent: str
    ) -> List[Tuple[str, str, str, float, float, float, int]]:
        with closing(sqlite3.connect(self.__db_name)) as conn:  # auto-closes
            with conn:  # auto-commits
                with closing(conn.cursor()) as cursor:  # auto-closes
                    return cursor.execute(
                        """
                        SELECT *
                        FROM visited
                        WHERE parent = ?
                    """,
                        (parent,),
                    ).fetchall()

    def push(
        self,
        placed: str,
        remaining: str,
        parent: str,
        score: float | None,
        cumulative_score: float | None,
        mean_score: float | None,
        status: int | None,
    ) -> None:
        con = sqlite3.connect(self.__db_name)
        cur = con.cursor()
        cur.execute(
            """INSERT INTO visited 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (placed, remaining) 
            DO UPDATE SET 
                score = excluded.score, 
                cumulative_score = excluded.cumulative_score,
                mean_score = excluded.mean_score,
                status = excluded.status
            """,
            (placed, remaining, parent, score, cumulative_score, mean_score, status),
        )
        con.commit()

    def trim(self, placed: str, status: int = 7) -> Tuple[int, int]:
        """Changes a root node to the provided status code and deleted all descendents.

        Args:
            placed (`str`) - The string indicating the root node to mark
            status (`int`) - The status code to use per CANDIDATE_STATUS_CODES

        Returns:
            Tuple[int, int] - two integers indicating how many records were deleted and
                modified, respectively. If (0, 0) is returned the root was not found.
                If negative numbers are returned, it indicates that no modifications
                were necessary. Repeated issuing of a command should indicate (-1, -1).
                If the root's status was somehow modified to match the status already,
                but descendents needed to be cleaned up the response would be
                (-1, {:num_descendents}).
        """
        con = sqlite3.connect(self.__db_name)
        cur = con.cursor()
        rows = cur.execute(
            """ 
            WITH RECURSIVE descends_from(x) AS (
                VALUES(?)
                UNION
                SELECT placed FROM visited, descends_from
                WHERE visited.parent=descends_from.x
            )
            SELECT * FROM visited WHERE visited.placed IN descends_from
            """,
            (placed,),
        ).fetchall()
        con.commit()

        if len(rows) == 0:
            # root not found
            return (0, 0)

        if len(rows) == 1 and rows[0][-1] == status:
            # no modifications are necessary, operations skipped
            return (-1, -1)

        modified = 0
        if rows[0][-1] == status:
            # status is set correctly at root but there are rows to trim
            modified = -1
        else:
            # mark the root
            cur = con.cursor()
            cur.execute(
                """
                UPDATE visited
                SET status = ?
                WHERE placed = ? AND remaining = ?
                """,
                [(status, chld[0], chld[1]) for chld in rows if chld[0] == placed][0],
            )
            modified = cur.rowcount
            con.commit()

        # discard the rest
        children = [(chld[0], chld[1]) for chld in rows if chld[0] != placed]
        cur = con.cursor()
        rows = cur.executemany(
            """
            DELETE FROM visited
            WHERE placed = ? AND remaining = ?
            """,
            children,
        )
        deleted = cur.rowcount
        con.commit()
        return (modified, deleted)
