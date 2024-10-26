from collections import Counter
import sqlite3
from contextlib import closing
from typing import Dict, List, Optional, Tuple

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
                    # SQLite is case insensitive, so double filter for case issues
                    rows = []
                    for row in fetch:
                        placed = row[0]
                        if f" {word} " in placed or placed.endswith(f" {word}"):
                            rows.append(row)
                        else:
                            pass
                    # because of post-fetch filtering we cannot apply the limit until
                    # after
                    if limit is None:
                        limit = len(rows)
                    return rows[:limit]

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

    def get_descendents(
        self, parent: str
    ) -> List[Tuple[str, str, str, float, float, float, int]]:
        with closing(sqlite3.connect(self.__db_name)) as conn:  # auto-closes
            with conn:  # auto-commits
                with closing(conn.cursor()) as cursor:  # auto-closes
                    return cursor.execute(
                        """
                        SELECT *
                        FROM visited
                        WHERE placed LIKE ?
                    """,
                        (parent + " %",),
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
            SELECT *
            FROM visited
            WHERE
                placed LIKE ? OR placed = ?
            ORDER BY placed
            """,
            (placed + " %", placed),
        ).fetchall()
        con.commit()

        modified = 0
        deleted = 0

        if len(rows) < 1:
            # nothing found
            return modified, deleted

        if rows[0][0] == placed:
            if rows[0][-1] == status:
                # root found but status is already set correctly
                modified = -1
            else:
                # mark the root with the appropriate status
                cur = con.cursor()
                cur.execute(
                    """
                    UPDATE visited
                    SET status = ?
                    WHERE placed = ?
                    """,
                    (status, placed),
                )
                modified = cur.rowcount
                con.commit()
            rows = rows[1:]

        if len(rows) == 0:
            return (modified, deleted)

        # discard the rest
        cur = con.cursor()
        rows = cur.executemany(
            """
            DELETE FROM visited
            WHERE placed = ? AND remaining = ?
            """,
            [(r[0], r[1]) for r in rows],
        )
        deleted = cur.rowcount
        con.commit()
        return (modified, deleted)

    def trim_containing(self, word: str, status: int = 7) -> Tuple[int, int]:
        total_modified, total_deleted = 0, 0
        while True:
            rows = self.contains(word, limit=1, status=0)
            entry = rows[0][0] if len(rows) > 0 else None
            if entry is None:
                return total_modified, total_deleted
            frag = Fragment(entry).words
            truncated = frag[: frag.index(word) + 1]
            modified, deleted = self.trim(" ".join(truncated), status)
            total_modified += max(modified, 0)
            total_deleted += max(deleted, 0)

    def verify(self) -> Tuple[bool, Counter[str, int]]:
        """Verify that the database exists, the program can connect to it, and answer
        whether each row has the same set of letters (placed and unplaced).

        Returns:
            (`bool`) - true if all the rows in the database are made from the same set
                of letters
            (`Counter[str, int]`) - a counter containing buckets of each unique set of
                letters and their counts. If the earlier value is true, this will be a 
                single entry, but if it is false this may be useful in remediating or
                reporting problems.
        """
        con = sqlite3.connect(self.__db_name)
        cur = con.cursor()
        cur.execute(
            """
            SELECT placed, remaining
            FROM visited
            LIMIT 10
            """,
        )
        bins = Counter()
        for placed, remaining in cur:
            combined = Fragment(placed) + Fragment(remaining)
            bins.update((sorted("".join(combined.letters.elements())),))
        con.commit()
        return (len(bins) == 0, bins)
