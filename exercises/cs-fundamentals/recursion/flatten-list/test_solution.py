from solution import flatten


def test_flattens_any_depth():
    assert flatten([1, [2, [3, [4]], 5]]) == [1, 2, 3, 4, 5]


def test_flat_and_empty_lists():
    assert flatten([1, 2, 3]) == [1, 2, 3]
    assert flatten([]) == []
    assert flatten([[], [[]]]) == []


def test_keeps_non_list_values_as_they_are():
    assert flatten(["ab", ["cd"], (1, 2)]) == ["ab", "cd", (1, 2)]


def test_does_not_modify_the_input():
    nested = [1, [2, [3]]]
    flatten(nested)
    assert nested == [1, [2, [3]]]
