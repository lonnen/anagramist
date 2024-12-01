from statistics import geometric_mean
from typing import Iterable, SupportsFloat


def geometricish_mean(data: Iterable[SupportsFloat]) -> float:
    offset = abs(min(data)) + 1
    return geometric_mean([s + offset for s in data]) - offset
