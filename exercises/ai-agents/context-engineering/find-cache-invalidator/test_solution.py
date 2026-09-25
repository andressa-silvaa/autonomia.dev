from solution import build_system

MANUAL = "Manual estável."
PROFILE_A = {"name": "Ana", "plan": "pro", "region": "BR"}
PROFILE_B = {"region": "BR", "plan": "pro", "name": "Ana"}


def test_same_profile_in_any_key_order_gives_the_same_text():
    first = build_system(MANUAL, PROFILE_A)
    second = build_system(MANUAL, PROFILE_B)
    assert first[0]["text"] == second[0]["text"]


def test_profile_is_still_in_the_prompt():
    text = build_system(MANUAL, PROFILE_A)[0]["text"]
    assert "Ana" in text and "pro" in text and "BR" in text


def test_manual_comes_first():
    text = build_system(MANUAL, PROFILE_A)[0]["text"]
    assert text.startswith(MANUAL)


def test_block_is_still_cached():
    assert build_system(MANUAL, PROFILE_A)[0]["cache_control"] == {"type": "ephemeral"}


def test_different_profiles_still_differ():
    other = {"name": "Bia", "plan": "free", "region": "PT"}
    assert build_system(MANUAL, PROFILE_A)[0]["text"] != build_system(MANUAL, other)[0]["text"]
