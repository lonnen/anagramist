import heapq
from collections import UserList
from typing import Iterable


class HeapQueue(UserList):
    """A class wrapper around the heapq library.

    Heaps are binary trees for which every parent node has a value less than or equal
    to any of its children.

    This module follows the python convention of both zero-indexing and pop returning
    the smallest item, not the largest (called a "min heap").

    By wrapping UserList this integrates the methods of heapq, preserves the invariants,
    and presents a more typical data structure interface. `heap[0]` is the smallest
    item, and `heap.sort()` maintains the heap invariant! Not that iterating over the
    `heap` directly, say, in a list comprehension, will not return items in a sorted
    order. Repeatedly popping the heap to exhaustion will, however.

    Complex records may be wrapped in a tuple (with careful though given to ties), or in
    a custom object. See the heapq library documentation on Priority Queue
    implementation for more.
    """

    def __init__(self, iterable: Iterable = []) -> None:
        self.data = [i for i in iterable]
        heapq.heapify(self.data)

    def push(self, item):
        heapq.heappush(self.data, item)

    def pop(self):
        return heapq.heappop(self.data)

    def pushpop(self, item):
        return heapq.heappushpop(self.data, item)

    def replace(self, item):
        return heapq.heapreplace(self.data, item)

    def nsmallest(self, n):
        return heapq.nsmallest(n, self.data)

    def nlargest(self, n):
        return heapq.nlargest(n, self.data)
