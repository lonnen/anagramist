import pytest
from random import shuffle

from anagramist.heapqueue import HeapQueue
from anagramist.puzzle import Guess


class TestParseSentence:
    def test_empty(self):
        pq = HeapQueue()
        assert len(pq) == 0

    def test_existing(self):
        pq = HeapQueue(range(5))
        assert len(pq) == 5

    def test_push(self):
        data = [1, 2, 3, 4, 5]
        pq = HeapQueue()
        for i in data:
            pq.push(i)
        assert len(pq) == 5
        assert set(pq) == set(data)

    def test_pop(self):
        pq = HeapQueue([1, 2, 3, 4, 5])
        expected = 1
        while len(pq):
            assert expected == pq.pop()
            expected += 1
        with pytest.raises(IndexError):
            pq.pop()

    def test_pushpop(self):
        pq = HeapQueue([1, 2, 3, 4, 5])
        popped = []
        for i in [5, 4, 3, 2, 1]:
            popped.append(pq.pushpop(i))
            assert len(pq) == 5
        assert popped == [1, 2, 3, 2, 1]

    def test_replace(self):
        pq = HeapQueue([3, 3, 3, 3, 3])
        assert pq.replace(2) == 3
        assert pq.replace(5) == 2
        assert pq.replace(5) == 3
        assert pq.replace(5) == 3
        assert len(pq) == 5
        assert sorted(pq[:]) == [3, 3, 5, 5, 5]

    def test_nsmallest(self):
        data = [1, 2, 3, 4, 5]
        assert data == sorted(data)
        shuffle(data)
        assert data != sorted(data)
        pq = HeapQueue(data)
        assert pq.nsmallest(3) == [1, 2, 3]
        assert pq.nsmallest(10) == [1, 2, 3, 4, 5]

    def test_nlargest(self):
        data = [1, 2, 3, 4, 5]
        assert data == sorted(data)
        shuffle(data)
        assert data != sorted(data)
        pq = HeapQueue(data)
        assert pq.nlargest(3) == [5, 4, 3]
        assert pq.nlargest(10) == [5, 4, 3, 2, 1]

    def test_sorted_order(self):
        data = [1, 2, 3, 4, 5]
        assert data == sorted(data)
        shuffle(data)
        assert data != sorted(data)
        pq = HeapQueue(data)
        sorted_data = []
        while len(pq):
            sorted_data.append(pq.pop())
        assert sorted_data == sorted(data)

    def test_tuple(self):
        data = list(zip(range(5), 'abcde'))
        shuffle(data)
        assert data != sorted(data, key=lambda d: d[0])
        pq = HeapQueue(data)
        sorted_data = []
        while len(pq):
            sorted_data.append(pq.pop())
        assert sorted_data == sorted(data)

    def test_complex_object(self):
        guesses = []
        expected = [float(x) for x in range(10)]
        for x in expected:
            guesses.append(Guess("some", "other", x))
        shuffle(guesses)
        assert [g.score for g in guesses] != [g.score for g in sorted(guesses)]
        # data is now shuffled
        pq = HeapQueue(guesses)
        hq_sorted = []
        while len(pq):
            hq_sorted.append(pq.pop().score)
        assert hq_sorted == expected
