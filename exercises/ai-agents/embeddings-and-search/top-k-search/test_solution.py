import pytest
from solution import top_k

DOCUMENTS = [
    [1.0, 0.0],
    [0.0, 1.0],
    [0.9, 0.1],
    [-1.0, 0.0],
]


def test_returns_most_similar_first():
    result = top_k([1.0, 0.0], DOCUMENTS, 2)
    assert [index for index, _ in result] == [0, 2]
    assert result[0][1] == pytest.approx(1.0)


def test_respects_k():
    assert len(top_k([1.0, 0.0], DOCUMENTS, 1)) == 1
    assert len(top_k([1.0, 0.0], DOCUMENTS, 3)) == 3


def test_k_larger_than_corpus_returns_everything():
    assert len(top_k([1.0, 0.0], DOCUMENTS, 99)) == len(DOCUMENTS)


def test_ties_are_broken_by_index():
    documents = [[1.0, 0.0], [2.0, 0.0], [0.0, 1.0]]
    result = top_k([5.0, 0.0], documents, 2)
    assert [index for index, _ in result] == [0, 1]


def test_empty_corpus():
    assert top_k([1.0, 0.0], [], 3) == []
