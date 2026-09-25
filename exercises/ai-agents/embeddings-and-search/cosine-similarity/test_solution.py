import math
from pathlib import Path

import pytest
import solution
from solution import cosine_similarity


def test_identical_direction():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([2, 4], [1, 2]) == pytest.approx(1.0)


def test_orthogonal_and_opposite():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)


def test_known_value():
    assert cosine_similarity([1, 1], [1, 0]) == pytest.approx(1 / math.sqrt(2))


def test_zero_vector_returns_zero():
    assert cosine_similarity([0, 0], [1, 2]) == 0.0
    assert cosine_similarity([1, 2], [0, 0]) == 0.0


def test_different_lengths_raise():
    with pytest.raises(ValueError):
        cosine_similarity([1, 2], [1, 2, 3])


def test_does_not_use_numpy():
    source = Path(solution.__file__).read_text(encoding="utf-8")
    assert "numpy" not in source and "scipy" not in source
