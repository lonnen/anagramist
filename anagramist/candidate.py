from collections import Counter
from dataclasses import dataclass
from enum import IntEnum
from typing import Union
from anagramist.fragment import Fragment


class Status(IntEnum):
    """Candidate Status Codes"""
    OK = 0  # or None
    INVALID = 1
    VALID = 2
    FULLY_EXPLORED = 5
    UNEXPLORED = 6
    MANUAL_INVALIDATION = 7

@dataclass()
class Candidate:
    """A candidate solution model, complete with all the fields necessary to record
    this entry in a database.
    """

    placed: Fragment
    remaining: Counter
    parent: Fragment
    score: Union[float, None]
    cumulative_score: Union[float, None]
    mean_score: Union[float, None]
    status: Status
