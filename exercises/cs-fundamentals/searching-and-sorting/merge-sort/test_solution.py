import random
from pathlib import Path

import solution
from solution import merge_sort


def test_sorts_numbers():
    assert merge_sort([5, 2, 9, 1, 5, 6]) == [1, 2, 5, 5, 6, 9]


def test_edge_cases():
    assert merge_sort([]) == []
    assert merge_sort([1]) == [1]
    assert merge_sort([3, 2, 1]) == [1, 2, 3]


def test_matches_python_on_random_data():
    generator = random.Random(7)
    items = [generator.randint(-1000, 1000) for _ in range(500)]
    assert merge_sort(items) == sorted(items)


def test_does_not_modify_the_input():
    items = [3, 1, 2]
    merge_sort(items)
    assert items == [3, 1, 2]


def test_does_not_use_builtin_sorting():
    source = Path(solution.__file__).read_text(encoding="utf-8")
    assert "sorted(" not in source and ".sort(" not in source, "Sem sorted() nem .sort()"
