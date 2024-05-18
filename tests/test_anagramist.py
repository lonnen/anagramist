import pytest

from anagramist import validate_solution


def test_generate_text():
    pass


def test_validate_solution():
    assert validate_solution("a", "a")
    assert validate_solution(
        "But they were also concerned about people stealing their ideas!",
        "eeeeeeeeeetttttaaaaoooorrrlllsssnnniiiuuhhccddppBywbg!",
    )
    assert not validate_solution("b", "a")
    assert not validate_solution("CAPS MATTER", "caps matter")
