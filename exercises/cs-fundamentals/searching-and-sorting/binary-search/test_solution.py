import time

from solution import binary_search

LARGE_SIZE = 200_000
SEARCHES = 2000
TIME_LIMIT_SECONDS = 0.15


def test_finds_every_position():
    items = [1, 3, 5, 7, 9]
    for index, value in enumerate(items):
        assert binary_search(items, value) == index


def test_missing_values():
    assert binary_search([1, 3, 5, 7], 4) == -1
    assert binary_search([1, 3, 5, 7], 0) == -1
    assert binary_search([1, 3, 5, 7], 8) == -1
    assert binary_search([], 1) == -1


def test_single_item():
    assert binary_search([42], 42) == 0
    assert binary_search([42], 7) == -1


def test_is_fast_on_large_input():
    items = list(range(0, LARGE_SIZE * 2, 2))
    targets = [items[-1 - index] for index in range(SEARCHES)]
    started = time.perf_counter()
    for target in targets:
        binary_search(items, target)
    elapsed = time.perf_counter() - started
    assert elapsed < TIME_LIMIT_SECONDS, f"Levou {elapsed:.2f}s: parece uma busca linear"
