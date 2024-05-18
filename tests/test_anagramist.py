import pytest

from anagramist import validate_solution


def test_generate_text():
    pass


def test_validate_solution():
    assert validate_solution("a", "a")
    assert not validate_solution("b", "a")

    assert validate_solution(
        "abeeefgiklnorrssttt",
        "letter bank goes first"
    )
    assert not validate_solution(
        "letter bank goes first",
        "abeeefgiklnorrssttt"
    )

    assert not validate_solution("CAPS MATTER", "caps matter")
    assert not validate_solution("aaa!!!", "aaa")
    
    assert validate_solution("!acinnopttuu", "punctuation!")
    assert validate_solution("!acinnopttuu", "!punctuation")
    assert not validate_solution("!acinnopttuu", "punct!uation")
    
    assert validate_solution(
        "eeeeeeeeeetttttaaaaoooorrrlllsssnnniiiuuhhccddppywbbg!",
        "but they were also concerned about people stealing their ideas!",
    )