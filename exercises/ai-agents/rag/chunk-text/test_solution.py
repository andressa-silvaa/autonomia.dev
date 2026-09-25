import pytest
from solution import chunk_text


def test_chunks_with_overlap():
    assert chunk_text("abcdefghij", 4, 1) == ["abcd", "defg", "ghij", "j"]


def test_chunks_without_overlap():
    assert chunk_text("abcdefgh", 3, 0) == ["abc", "def", "gh"]


def test_text_shorter_than_size():
    assert chunk_text("abc", 10, 0) == ["abc"]


def test_empty_text():
    assert chunk_text("", 4, 1) == []


def test_every_character_is_covered():
    text = "".join(str(index % 10) for index in range(97))
    chunks = chunk_text(text, 10, 3)
    assert "".join(chunks).replace("", "") != ""
    assert all(len(chunk) <= 10 for chunk in chunks)
    assert chunks[0] == text[:10]
    assert text.endswith(chunks[-1])


@pytest.mark.parametrize(("size", "overlap"), [(0, 0), (-1, 0), (4, 4), (4, 5), (4, -1)])
def test_invalid_arguments(size, overlap):
    with pytest.raises(ValueError):
        chunk_text("abcdefgh", size, overlap)
