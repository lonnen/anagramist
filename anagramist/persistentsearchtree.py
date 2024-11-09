from collections import Counter
import sqlite3
from contextlib import closing, contextmanager
from typing import List, Optional, Tuple

from .fragment import Fragment


@contextmanager
def db_connection_manager(path: str):
    """A context manager for the sqlite db at `path`

    This is necessary because the connect method operates over db transactions, not over
    database connections. This wrapper ensures the connection closes.
    """
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()


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
        with db_connection_manager(self.__db_name) as con:
            con.cursor().execute(self.__TABLE_SCHEMA_VISITED)

    def __len__(self) -> int:
        with db_connection_manager(self.__db_name) as con:
            return con.cursor().execute("SELECT COUNT(*) FROM visited").fetchone()[0]

    def contains(
        self, word: str, limit: Optional[int] = None, status: Optional[int] = None
    ):
        with db_connection_manager(self.__db_name) as con:
            cursor = con.cursor()
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
            # because of post-fetch filtering we cannot apply the limit until after
            if limit is None:
                limit = len(rows)
            return rows[:limit]

    def get(
        self, placed: str, default=None
    ) -> Tuple[str, str, str, float, float, float, int]:
        with db_connection_manager(self.__db_name) as con:
            cursor = con.cursor()
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
        with db_connection_manager(self.__db_name) as con:
            cursor = con.cursor()
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
        with db_connection_manager(self.__db_name) as con:
            cursor = con.cursor()
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
        with db_connection_manager(self.__db_name) as con:
            cursor = con.cursor()
            cursor.execute(
                """INSERT INTO visited 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (placed, remaining) 
                DO UPDATE SET 
                    score = excluded.score, 
                    cumulative_score = excluded.cumulative_score,
                    mean_score = excluded.mean_score,
                    status = excluded.status
                """,
                (
                    placed,
                    remaining,
                    parent,
                    score,
                    cumulative_score,
                    mean_score,
                    status,
                ),
            )
            con.commit()

    def status(self, placed: str, status: int) -> int:
        """Change the status of entry `placed` to `status`

        Args:
            placed (`str`) - The string indicating the node to change
            status (`int`) - The status code from CANDIDATE_STATUS_CODES in the module

        Returns:
            int - an integer code indicating how many rows have changed. -1 indicates
            that the status was already set to `status`, 0 indicates no entry found for
            `placed`, 1 indicates the entry was found and status set.
        """
        with db_connection_manager(self.__db_name) as con:
            cursor = con.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM visited
                WHERE
                    placed = ?
                """,
                (placed,),
            )

            entry = cursor.fetchone()

            if not entry:
                # nothing found
                return 0

            if entry[-1] == status:
                # status is already correctly set
                return -1
            else:
                # mark the root with the appropriate status
                cursor.execute(
                    """
                    UPDATE visited
                    SET status = ?
                    WHERE placed = ?
                    """,
                    (status, placed),
                )
                con.commit()

            return cursor.rowcount

    def trim(self, placed: str) -> int:
        """Deleted all descendents of a given root node `placed`

        Args:
            placed (`str`) - The string indicating the root node

        Returns:
            int - an integer indicating how many records were deleted. Negative numbers
            indicate that the root node was not found.
        """
        with db_connection_manager(self.__db_name) as con:
            cursor = con.cursor()
            rows = cursor.execute(
                """
                SELECT *
                FROM visited
                WHERE
                    placed LIKE ? OR placed = ?
                ORDER BY placed
                """,
                (placed + " %", placed),
            ).fetchall()

            deleted = 0

            if len(rows) == 0:
                # nothing found
                return -1

            if rows[0][0] == placed:
                # ignore the entry itself
                rows = rows[1:]
            else:
                # invalid state?
                # some node is prefixed with `placed`, but not rooted at ''. It could be
                # that the search was initiated after `placed` as an optimization
                # e.g. c1663 does not start with the empty string since the first word
                # is given
                pass

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
            return deleted

    def verify_integrity(self) -> Tuple[bool, Counter[str, int]]:
        """Verify that the database exists, the program can connect to it, and answer
        whether each row has the same set of letters (placed and unplaced).

        WARNING: this is quite expensive, proportional to the size of the database

        Returns:
            (`bool`) - true if all the rows in the database are made from the same set
                of letters, or if there are no rows in the database
            (`Counter[str, int]`) - a counter containing buckets of each unique set of
                letters and their counts. If the database is empty this will be 0. If
                this is a single entry the database integrity is intact. If this has
                more than one try the database integity is *not* intact but the details
                of the entries may be useful in remediating or recovering the db.
        """
        with db_connection_manager(self.__db_name) as con:
            cursor = con.cursor()
            cursor.execute(
                """
                SELECT placed, remaining
                FROM visited
                """,
            )
            bins = Counter()
            rowcount = 0
            for placed, remaining in cursor:
                combined = Fragment(placed) + Fragment(remaining)
                bins.update(("".join(sorted(combined.letters.elements())),))
                rowcount += 1
            con.commit()
            if rowcount < 1:
                return (True, bins)
            return (len(bins) == 1, bins)

    # def sample(self):
    #     # https://blog.moertel.com/posts/2024-08-23-sampling-with-sql.html
    #     """
    #     SELECT *
    #         FROM visited
    #         WHERE status is 0
    #     ORDER BY -ln(1.0 - RANDOM()) / exp(mean_score)
    #         LIMIT 100
    #     """
