"""Tests for Reciprocal Rank Fusion."""

import pytest

from src.retrieval.fusion import DEFAULT_K, reciprocal_rank_fusion


class TestReciprocalRankFusion:
    def test_agreement_beats_a_single_top_hit(self):
        """
        The property RRF exists for: broad agreement outranks one strong vote.

        'b' is 2nd and 2nd; 'a' is 1st and absent. With k=60 the rank-1 bonus is
        1/61 while two rank-2 votes are 2/62, so 'b' wins.
        """
        fused = reciprocal_rank_fusion([["a", "b", "c"], ["d", "b", "e"]])

        assert fused[0][0] == "b"

    def test_single_ranking_preserves_order(self):
        fused = reciprocal_rank_fusion([["a", "b", "c"]])

        assert [item for item, _ in fused] == ["a", "b", "c"]

    def test_scores_follow_the_rrf_formula(self):
        fused = dict(reciprocal_rank_fusion([["a", "b"], ["b", "a"]], k=DEFAULT_K))

        expected = 1 / (DEFAULT_K + 1) + 1 / (DEFAULT_K + 2)
        assert fused["a"] == pytest.approx(expected)
        assert fused["b"] == pytest.approx(expected)

    def test_ties_break_deterministically(self):
        """Feeding a CI gate means the same input must always give the same order."""
        first = reciprocal_rank_fusion([["b", "a"], ["a", "b"]])
        second = reciprocal_rank_fusion([["b", "a"], ["a", "b"]])

        assert first == second
        # Equal scores, so the tie-break is the id itself.
        assert [item for item, _ in first] == ["a", "b"]

    def test_weights_shift_the_ranking(self):
        unweighted = reciprocal_rank_fusion([["a", "x"], ["b", "y"]])
        weighted = reciprocal_rank_fusion([["a", "x"], ["b", "y"]], weights=[0.1, 1.0])

        assert unweighted[0][0] == "a"  # tie broken on id
        assert weighted[0][0] == "b"  # second ranking now dominates

    def test_rejects_mismatched_weights(self):
        with pytest.raises(ValueError, match="2 weights for 1 rankings"):
            reciprocal_rank_fusion([["a"]], weights=[1.0, 1.0])

    def test_truncates_to_top_k(self):
        fused = reciprocal_rank_fusion([["a", "b", "c", "d"]], top_k=2)

        assert len(fused) == 2

    def test_empty_input_is_empty_output(self):
        assert reciprocal_rank_fusion([]) == []
        assert reciprocal_rank_fusion([[], []]) == []

    def test_smaller_k_sharpens_the_top_rank(self):
        """Low k weights position 1 heavily; high k flattens the curve."""
        sharp = dict(reciprocal_rank_fusion([["a", "b", "c"], ["z"]], k=1))
        flat = dict(reciprocal_rank_fusion([["a", "b", "c"], ["z"]], k=1000))

        assert sharp["a"] / sharp["c"] > flat["a"] / flat["c"]


class TestFusionWeights:
    """
    Weighting policy. The shipped answer is "equal weights, routing off" — see
    the module docstring for the measurement that produced it. These pin the
    mechanism so the decision can be revisited from data rather than reverted
    by accident.
    """

    def test_static_is_the_default(self):
        from src.retrieval.fusion import STATIC_WEIGHTS, weights_for_query

        assert weights_for_query(["BMW"]) is STATIC_WEIGHTS
        assert weights_for_query(None) is STATIC_WEIGHTS

    def test_dynamic_routes_on_parser_hits(self):
        from src.retrieval.fusion import (
            LEXICAL_WEIGHTS,
            SEMANTIC_WEIGHTS,
            weights_for_query,
        )

        assert weights_for_query(["BMW"], dynamic=True) is LEXICAL_WEIGHTS
        assert weights_for_query([], dynamic=True) is SEMANTIC_WEIGHTS
        assert weights_for_query(None, dynamic=True) is SEMANTIC_WEIGHTS

    def test_weights_are_normalised_to_one(self):
        """Not required by RRF, but keeps the numbers comparable across policies."""
        from src.retrieval.fusion import (
            LEXICAL_WEIGHTS,
            SEMANTIC_WEIGHTS,
            STATIC_WEIGHTS,
        )

        for weights in (STATIC_WEIGHTS, LEXICAL_WEIGHTS, SEMANTIC_WEIGHTS):
            assert weights.dense + weights.sparse == pytest.approx(1.0)

    def test_as_list_orders_dense_then_sparse(self):
        from src.retrieval.fusion import FusionWeights

        assert FusionWeights(0.3, 0.7).as_list() == [0.3, 0.7]

    def test_sparse_weight_promotes_the_sparse_ranking(self):
        """The mechanism the search relies on: weights actually change order."""
        dense = ["a", "b"]
        sparse = ["b", "a"]

        dense_heavy = reciprocal_rank_fusion([dense, sparse], weights=[0.9, 0.1])
        sparse_heavy = reciprocal_rank_fusion([dense, sparse], weights=[0.1, 0.9])

        assert dense_heavy[0][0] == "a"
        assert sparse_heavy[0][0] == "b"

    def test_zero_weight_silences_a_channel(self):
        fused = reciprocal_rank_fusion([["a"], ["z"]], weights=[1.0, 0.0])

        assert fused[0][0] == "a"
        assert dict(fused)["z"] == 0.0
