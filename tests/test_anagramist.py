import pytest

from anagramist.candidate import Candidate

from collections import Counter


def test_generate_text():
    pass


class TestCandidate:
    def test_init(self):
        c = Candidate("a")
        assert c.sentence == ["a"]
        assert c.letters == Counter("a")

    def test_sentence(self):
        c = Candidate("but they were also concerned about people")
        assert c.sentence == [
            "but",
            "they",
            "were",
            "also",
            "concerned",
            "about",
            "people",
        ]
        assert c.letters == Counter(
            {
                "e": 7,
                "o": 4,
                "t": 3,
                "b": 2,
                "u": 2,
                "r": 2,
                "a": 2,
                "l": 2,
                "c": 2,
                "n": 2,
                "p": 2,
                "h": 1,
                "y": 1,
                "w": 1,
                "s": 1,
                "d": 1,
                " ": 0,
            }
        )

    def test_punctuation(self):
        c = Candidate("behold! a dragon")
        assert c.sentence == [
            "behold",
            "!",
            "a",
            "dragon",
        ]
        assert c.letters == Counter(
            {
                "o": 2,
                "d": 2,
                "a": 2,
                "b": 1,
                "e": 1,
                "h": 1,
                "l": 1,
                "!": 1,
                "r": 1,
                "g": 1,
                "n": 1,
                " ": 0,
            }
        )

    def test_capitalization(self):
        c = Candidate("CAPS MATTER")
        assert c.sentence == [
            "CAPS",
            "MATTER",
        ]
        assert not c.sentence == ["caps", "matter"]

    def test_validation(self):
        c = Candidate("okay wait suddenly I see your point")
        assert c.validate("Ioaaddeeeiiklnnooprssttuuwyyy")


# def test_validate_solution():
#     assert validate_solution("a", "a")
#     assert not validate_solution("b", "a")

#     assert validate_solution(
#         "abeeefgiklnorrssttt",
#         "letter bank goes first"
#     )
#     assert not validate_solution(
#         "letter bank goes first",
#         "abeeefgiklnorrssttt"
#     )

#     assert not validate_solution("CAPS MATTER", "caps matter")
#     assert not validate_solution("aaa!!!", "aaa")


#     assert validate_solution(
#         "eeeeeeeeeetttttaaaaoooorrrlllsssnnniiiuuhhccddppywbbg!",
#         "but they were also concerned about people stealing their ideas!",
#     )
