import heapq
from typing import Optional


class Heap[T]:
    """A min-heap capped at a maximum size. Once the size has been reached the smallest
    item is removed whenever a new item is item is added. This wraps a list and the
    heapq api in order to maintain some invariants when modifying the list. To access
    the data contained in the *Heap*, consider performing read-only operations on the
    instance property *H*, the internal list.

    Args:
        iterable (`list[T]`) - a list to use as the heap
        max_size (`int`) - the maximum number of items to hold in the heap

    derived from: https://stackoverflow.com/posts/56630485/revisions
    """

    h: list[T]

    def __init__(self, iterable: list[T], max_size: int = None):
        self.h = iterable
        heapq.heapify(self.h)
        if max_size is not None:
            self.max_size = max_size

    def push(self, item: T) -> Optional[T]:
        """Push the value *item* onto the *Heap*. If this will exceed the maximum heap
        size, drop the smallest item.

        Args:
            item (`T`) - an item to add to the Heap

        Returns:
            The smallest item in the Heap, iff adding the item exceeds the maximum heap
            size. Otherwise None.
        """
        if (self.max_size is None) or (len(self.h) < self.max_size):
            heapq.heappush(self.h, item)
            return
        else:
            if item > self.h[0]:
                return heapq.heapreplace(self.h, item)
            # the new item would be the smallest thing, so skip adding it
            return item

    def pop(self) -> T:
        """Pop and return the smallest item form the *Heap*, maintaining the Heap
        invariant.

        Returns:
            The smallest item from the *Heap*

        Raises:
            IndexError: If Heap is empty
        """
        return heapq.heappop(self.h)

    def pushpop(self, item: T) -> T:
        """Push *item* on the *Heap*, then pop and return the smallest item from the
        *Heap*. This combined action is runs more efficiently than push() followed by a
        separate call to pop().

        If the Heap is already at maximum size, and the item would become the smallest
        item in the heap, the item is returned without modifying the heap.

        Args:
            item (`T`) - an item to add to the Heap

        Returns:
            The smallest item from the *Heap* after the new *item* is added
        """
        if (self.max_size is None) or (len(self.h) < self.max_size):
            return heapq.heappushpop(self.h, item)
        else:
            if item > self.h[0]:
                return heapq.heapreplace(self.h, item)
            # the new item would be the smallest thing, so skip adding it
            return item

    def replace(self, item: T) -> T:
        """Pop the smallest item from the *Heap*, push the new *item*, then return the
        popped item.The *Heap* size doesn't change. This action is more efficient than a
        pop() followed by a push(). Note that the value returned by be larger than
        *item*!

        Args:
            item (`T`) - an item to add to the Heap

        Returns:
            The smallest item on the Heap before *item* is added

        Raises:
            IndexError: If Heap is empty
        """
        return heapq.heapreplace(self.h, item)

    def nlargest(self, n: int, key=None) -> list[T]:
        """Return a list with the *n* largest items from the *Heap*. This works
        best for smaller values of *n*. For larger values it may be more
        efficient to use the built-in `sorted()` function.

        Args:
            n (`int`) - the maximum size of the returned list
            key - optional function of one argument that is used to extract a
                comparison key from each element in the *Heap*
        """
        return heapq.nlargest(n, self.h, key)

    def nsmallest(self, n: int, key=None) -> list[T]:
        """Return a list with the *n* smallest items from the *Heap*. This works
        best for smaller values of *n*. For larger values it may be more
        efficient to use the built-in `sorted()` function.

        Args:
            n (`int`) - the maximum size of the returned list
            key - optional function of one argument that is used to extract a
                comparison key from each element in the *Heap*
        """
        return heapq.nsmallest(n, self.h, key)
