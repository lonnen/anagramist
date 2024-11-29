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
        oracle = TransformerOracle(TRANSFOMER_MODEL, TRANSFORMER_SEED, c1663=True)
        oracle.score_candidate(Fragment("I cannot believe"))