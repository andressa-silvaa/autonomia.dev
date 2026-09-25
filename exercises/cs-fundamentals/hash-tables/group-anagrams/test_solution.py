from solution import group_anagrams


def test_groups_in_order_of_first_appearance():
    words = ["roma", "sal", "amor", "las", "mora"]
    assert group_anagrams(words) == [["roma", "amor", "mora"], ["sal", "las"]]


def test_words_without_partner_stay_alone():
    assert group_anagrams(["abc", "xyz"]) == [["abc"], ["xyz"]]


def test_empty_input():
    assert group_anagrams([]) == []
