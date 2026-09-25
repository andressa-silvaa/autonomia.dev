import pytest
from solution import Queue


def test_first_in_first_out():
    queue = Queue()
    for item in "abc":
        queue.enqueue(item)
    assert [queue.dequeue(), queue.dequeue(), queue.dequeue()] == ["a", "b", "c"]


def test_interleaved_operations_keep_order():
    queue = Queue()
    queue.enqueue(1)
    queue.enqueue(2)
    assert queue.dequeue() == 1
    queue.enqueue(3)
    assert queue.dequeue() == 2
    assert queue.dequeue() == 3


def test_length_follows_operations():
    queue = Queue()
    assert len(queue) == 0
    queue.enqueue("x")
    queue.enqueue("y")
    queue.dequeue()
    assert len(queue) == 1


def test_empty_queue_raises_index_error():
    with pytest.raises(IndexError):
        Queue().dequeue()
