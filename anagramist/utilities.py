import heapq


# https://stackoverflow.com/posts/56630485/revisions
class MaxHeap:
    def __init__(self, top_n):
        self.h = []
        self.length = top_n
        heapq.heapify(self.h)

    def add(self, element):
        if len(self.h) < self.length:
            heapq.heappush(self.h, element)
        else:
            heapq.heappushpop(self.h, element)

    def getTop(self):
        return heapq.nlargest(self.length, self.h)
