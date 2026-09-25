import time

from solution import has_duplicates

LARGE_SIZE = 4000
TIME_LIMIT_SECONDS = 0.25


def test_finds_duplicates():
    assert has_duplicates([3, 1, 4, 1, 5])
    assert has_duplicates(["a", "b", "a"])


def test_accepts_lists_without_duplicates():
    assert not has_duplicates([])
    assert not has_duplicates([7])
    assert not has_duplicates([1, 2, 3, 4])


def test_is_fast_on_large_input():
    items = list(range(LARGE_SIZE))
    started = time.perf_counter()
    assert not has_duplicates(items)
    elapsed = time.perf_counter() - started
    assert elapsed < TIME_LIMIT_SECONDS, f"Levou {elapsed:.2f}s: ainda parece O(n²)"
