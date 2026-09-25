import pytest
from solution import is_balanced


@pytest.mark.parametrize(
    "text", ["", "()", "([]{})", "(a[b]{c})", "def f(x): return [x, {1: (2)}]"]
)
def test_balanced_texts(text):
    assert is_balanced(text)


@pytest.mark.parametrize("text", ["(", ")", "((", "([)]", "{[}", "())(", "]["])
def test_unbalanced_texts(text):
    assert not is_balanced(text)
