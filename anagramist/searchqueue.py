import random
from collections import UserList
from typing import Iterable, List, Optional, TypeVar


T = TypeVar("T")


class SearchQueue(UserList):

    data: List[T] = []

    def __init__[T](self, iterable: Optional[Iterable[T]] = None, max_size: int = None):
        if iterable is not None:
            self.data: List[T] = list(iterable)
        self.max_size: int = max_size

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
