from collections import Counter
from random import shuffle

from anagramist import compute_valid_vocab
from anagramist.fragment import Fragment, parse_sentence
from anagramist.vocab import vocab


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
        assert c.sentence == "a"
        assert c.words == ["a"]
        assert c.letters == Counter("a")

    def test_sentence(self):
        c = Fragment("but they were also concerned about people")
        assert c.words == [
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
        assert c.words == [
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
        assert c.words == [
            "CAPS",
            "MATTER",
        ]
        assert not c.sentence == ["caps", "matter"]

    def test_merged_punctuation(self):
        c = Fragment("""I rem needs laan hah toot du tony ,""")
        assert c.words == [
            "I",
            "rem",
            "needs",
            "laan",
            "hah",
            "toot",
            "du",
            "tony",
            ",",
        ]
