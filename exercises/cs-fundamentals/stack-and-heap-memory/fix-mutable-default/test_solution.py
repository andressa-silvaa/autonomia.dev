from solution import add_item


def test_each_call_without_list_starts_empty():
    assert add_item("a") == ["a"]
    assert add_item("b") == ["b"]


def test_given_list_is_extended_in_place():
    shopping = ["café"]
    result = add_item("pão", shopping)
    assert result is shopping
    assert shopping == ["café", "pão"]
