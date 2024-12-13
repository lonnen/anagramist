from collections import Counter
from dataclasses import dataclass
from typing import Union
from anagramist.fragment import Fragment


CANDIDATE_STATUS_CODES = {
    0: "OK",  # or None
    1: "Fails Validation",
    5: "Fully Explored",
    6: "Unexplored",
    7: "Manual Intervention",
}


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
    status: Union[float, int]
