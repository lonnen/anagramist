from math import fsum
import pytest
from anagramist.fragment import Fragment
from anagramist.oracles import TransformerOracle

TRANSFOMER_MODEL = "microsoft/phi-1_5"
TRANSFORMER_SEED = 42


class TestOracle:
    def test_init(self):
        oracle = TransformerOracle(TRANSFOMER_MODEL, TRANSFORMER_SEED, c1663=True)

        assert oracle.puzzle_context.startswith("In comparison, being an anagramist")
        assert oracle.puzzle_context_token_count == 33

        with pytest.raises(RuntimeError):
            # cannot provide context AND c1663 flag, which implicitly sets context
            TransformerOracle(
                TRANSFOMER_MODEL,
                TRANSFORMER_SEED,
                puzzle_context="This should fail",
                c1663=True,
            )

    def test_score_candidate(self):
        expected = Fragment("I cannot believe")
        oracle = TransformerOracle(TRANSFOMER_MODEL, TRANSFORMER_SEED, c1663=True)
        word_scores = oracle.score_candidate(expected)
        assert expected.words == [w for w, _ in word_scores]
        # even with a fixed seed this value varies with changes to certain code paths
        # manually verify the result before adjusting this number
        assert -33 == round(fsum([s for _, s in word_scores]), 0)
