import time

from solution import two_sum

LARGE_SIZE = 6000
TIME_LIMIT_SECONDS = 0.3


def test_finds_the_pair():
    assert two_sum([2, 7, 11, 15], 9) == (0, 1)
    assert two_sum([3, 2, 4], 6) == (1, 2)


def test_same_value_twice():
    assert two_sum([3, 3], 6) == (0, 1)


def test_returns_pair_that_ends_first():
    assert two_sum([1, 4, 2, 3], 5) == (0, 1)


def test_returns_none_without_pair():
    assert two_sum([1, 2], 10) is None
    assert two_sum([], 0) is None


def test_is_fast_on_large_input():
    numbers = list(range(LARGE_SIZE))
    target = numbers[-1] + numbers[-2]
    started = time.perf_counter()
    assert two_sum(numbers, target) == (LARGE_SIZE - 2, LARGE_SIZE - 1)
    elapsed = time.perf_counter() - started
    assert elapsed < TIME_LIMIT_SECONDS, f"Levou {elapsed:.2f}s: ainda parece O(n²)"
