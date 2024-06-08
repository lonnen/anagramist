from anagramist import PriorityQueue

from random import shuffle


class TestParseSentence:
    def test_empty(self):
        pq = PriorityQueue()

    def test_empty(self):
        data = [1, 2, 3, 4, 5]
        assert data == sorted(data)
        shuffle(data)
        assert data != sorted(data)
        pq = PriorityQueue(data)
        sorted_data = []
        while len(pq):
            sorted_data.append(pq.pop())
        assert sorted_data == sorted(data)
