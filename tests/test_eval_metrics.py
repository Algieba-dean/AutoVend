"""Tests for the deterministic retrieval metrics."""

import math

import pytest

from src.eval.metrics import (
    aggregate,
    capped_recall_at_k,
    evaluate_one,
    hit_rate_at_k,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


class TestRecall:
    def test_counts_relevant_items_in_the_top_k(self):
        assert recall_at_k(["a", "b", "c"], {"a", "c", "z"}, 3) == pytest.approx(2 / 3)

    def test_ignores_items_past_k(self):
        assert recall_at_k(["x", "y", "a"], {"a"}, 2) == 0.0

    def test_empty_relevant_set_is_zero(self):
        assert recall_at_k(["a"], set(), 3) == 0.0


class TestCappedRecall:
    def test_reaches_one_when_the_top_k_is_all_relevant(self):
        """
        The reason capped_recall exists: plain recall@3 here is 3/900 ≈ 0.003
        even though the ranking is perfect.
        """
        relevant = {f"car-{i}" for i in range(900)}
        retrieved = ["car-0", "car-1", "car-2"]

        assert capped_recall_at_k(retrieved, relevant, 3) == 1.0
        assert recall_at_k(retrieved, relevant, 3) < 0.01

    def test_matches_plain_recall_when_relevant_fits_in_k(self):
        relevant = {"a", "b"}
        retrieved = ["a", "z", "b"]

        assert capped_recall_at_k(retrieved, relevant, 3) == recall_at_k(retrieved, relevant, 3)

    def test_empty_relevant_set_is_zero(self):
        assert capped_recall_at_k(["a"], set(), 3) == 0.0


class TestPrecision:
    def test_fraction_of_top_k_that_is_relevant(self):
        assert precision_at_k(["a", "x", "b"], {"a", "b"}, 3) == pytest.approx(2 / 3)

    def test_divides_by_the_actual_result_count(self):
        """A system returning 1 result must not be scored as if it returned k."""
        assert precision_at_k(["a"], {"a"}, 5) == 1.0

    def test_empty_retrieval_is_zero(self):
        assert precision_at_k([], {"a"}, 3) == 0.0


class TestHitRate:
    def test_one_when_any_top_k_item_is_relevant(self):
        assert hit_rate_at_k(["x", "y", "a"], {"a"}, 3) == 1.0

    def test_zero_when_the_relevant_item_falls_outside_k(self):
        assert hit_rate_at_k(["x", "y", "a"], {"a"}, 2) == 0.0


class TestMRR:
    @pytest.mark.parametrize(
        "retrieved,expected",
        [
            (["a", "x", "y"], 1.0),
            (["x", "a", "y"], 0.5),
            (["x", "y", "a"], 1 / 3),
            (["x", "y", "z"], 0.0),
        ],
    )
    def test_reciprocal_of_the_first_relevant_rank(self, retrieved, expected):
        assert mrr(retrieved, {"a"}) == pytest.approx(expected)


class TestNDCG:
    def test_perfect_ranking_scores_one(self):
        assert ndcg_at_k(["a", "b"], {"a", "b"}, 2) == pytest.approx(1.0)

    def test_penalises_burying_the_relevant_item(self):
        top = ndcg_at_k(["a", "x"], {"a"}, 2)
        buried = ndcg_at_k(["x", "a"], {"a"}, 2)

        assert top > buried
        assert buried == pytest.approx(1 / math.log2(3))

    def test_no_relevant_hits_scores_zero(self):
        assert ndcg_at_k(["x", "y"], {"a"}, 2) == 0.0


class TestEvaluateOne:
    def test_reports_every_metric_at_every_k(self):
        scores = evaluate_one(["a", "b"], {"a"}, ks=(1, 3))

        assert set(scores) == {
            "mrr",
            "recall@1",
            "capped_recall@1",
            "precision@1",
            "hit_rate@1",
            "ndcg@1",
            "recall@3",
            "capped_recall@3",
            "precision@3",
            "hit_rate@3",
            "ndcg@3",
        }


class TestAggregate:
    def test_macro_averages_each_metric(self):
        result = aggregate([{"m": 1.0}, {"m": 0.0}, {"m": 0.5}])

        assert result["m"] == pytest.approx(0.5)

    def test_weighs_every_query_equally(self):
        """Macro, not micro: a query with 900 relevant cars must not dominate."""
        assert aggregate([{"m": 1.0}, {"m": 0.0}])["m"] == pytest.approx(0.5)

    def test_empty_input_is_empty_output(self):
        assert aggregate([]) == {}
