from anagramist import parse_sentence
from anagramist.fragment import Fragment

from collections import Counter


def test_generate_text():
    pass


class TestParseSentence:
    def test_parse_sentence(self):
        assert parse_sentence("I") == ["I"]
        assert parse_sentence("This is a six word fragment") == [
            "This",
            "is",
            "a",
            "six",
            "word",
            "fragment",
        ]
        assert parse_sentence("This is a seven word fragment.") == [
            "This",
            "is",
            "a",
            "seven",
            "word",
            "fragment",
            ".",
        ]
        assert parse_sentence("This fragment's count is six words") == [
            "This",
            "fragment's",
            "count",
            "is",
            "six",
            "words",
        ]
        assert parse_sentence("This fragment-count is five words") == [
            "This",
            "fragment-count",
            "is",
            "five",
            "words",
        ]


class TestFragment:
    def test_init(self):
        c = Fragment("a")
        assert c.sentence == ["a"]
        assert c.letters == Counter("a")

    def test_sentence(self):
        c = Fragment("but they were also concerned about people")
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
        c = Fragment("behold! a dragon")
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
        c = Fragment("CAPS MATTER")
        assert c.sentence == [
            "CAPS",
            "MATTER",
        ]
        assert not c.sentence == ["caps", "matter"]

    def test_validation(self):
        c = Fragment("okay wait suddenly I see your point")
        assert c.validate("Ioaaddeeeiiklnnooprssttuuwyyy")

    def test_invalid_solution(self):
        c = Fragment("a")
        assert c.validate("a")
        assert not c.validate("b")

    def test_caps_matter(self):
        c = Fragment("CAPS MATTER")
        assert not c.validate("caps matter")

    def test_punctuation_matters(self):
        c = Fragment("aaa!!!")
        assert not c.validate("aaa")
        assert not c.validate("a!aa!!")
