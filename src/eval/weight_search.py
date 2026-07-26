"""
Grid search over RRF fusion weights.

Sweeps the dense/sparse split from 0.0 to 1.0 against the golden set and
reports `capped_recall@3` and `MRR` at each point, then evaluates the
intent-routed policy on the same data so the two are directly comparable.

Only the weights vary. Retrieval, the golden set and the scoring code are
identical across every point in the sweep, so a difference in the numbers is a
difference in the weights and not in anything else.

**Why the search runs on cached rankings.** Re-running retrieval for all eleven
weight settings would embed the same 116 queries eleven times for no reason —
the rankings do not depend on the fusion weights, only the *combination* does.
Each query is retrieved once, both channel rankings are cached, and the sweep
is pure arithmetic over them. That turns a ~20 minute search into seconds and,
more usefully, guarantees every point sees byte-identical inputs.

Usage:
    python -m src.eval.weight_search
    python -m src.eval.weight_search --step 0.05 --top-k 10
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from src.eval.golden_set import GoldenQuery, load_golden_set
from src.eval.metrics import capped_recall_at_k, mrr
from src.eval.runner import RESULTS_DIR
from src.retrieval.fusion import (
    FusionWeights,
    reciprocal_rank_fusion,
    weights_for_query,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Retrieval depth per channel while collecting rankings. Deeper than the
#: reported k so a document the fusion would promote is actually present.
CHANNEL_DEPTH = 40


@dataclass
class QueryRankings:
    """Both channels' rankings for one query, plus its routing signal."""

    query: GoldenQuery
    dense: List[str]
    sparse: List[str]
    matched_keywords: List[str]


def collect_rankings(
    queries: Sequence[GoldenQuery], depth: int = CHANNEL_DEPTH
) -> List[QueryRankings]:
    """
    Retrieve each query once, keeping both channel rankings.

    Applies the same structured pre-filter the pipeline applies, so the sweep
    scores the fusion the production path actually performs rather than a
    fusion over unfiltered channels.
    """
    from src.filter.filter_engine import FilterEngine
    from src.filter.label_registry import LabelRegistry
    from src.filter.query_parser import QueryParser
    from src.filter.vehicle_db import VehicleDB
    from src.models.query import Query
    from src.rag.embeddings import BGEEmbeddingModel
    from src.rag.retriever import VehicleRetriever
    from src.rag.vector_store import ChromaVectorStore
    from src.retrieval.bm25_index import BM25Index

    registry = LabelRegistry()
    db = VehicleDB(registry=registry)
    engine = FilterEngine(db=db, registry=registry)
    parser = QueryParser(registry=registry)
    retriever = VehicleRetriever(BGEEmbeddingModel(), ChromaVectorStore(), similarity_threshold=0.0)
    sparse = BM25Index.load_or_build()

    collected: List[QueryRankings] = []
    for index, query in enumerate(queries, start=1):
        parsed = parser.parse(query.query)
        filtered = engine.filter(parsed.conditions)
        allowed = set(filtered.car_models) if filtered.car_models else None

        vector_query = Query(text=query.query, top_k=depth)
        if filtered.car_models:
            vector_query.filters = {"car_model_candidates": filtered.car_models}
        dense_ranking = [r.vehicle.car_model for r in retriever.search(vector_query).results]

        sparse_ranking = [m for m, _ in sparse.search(query.query, top_k=depth)]
        if allowed:
            sparse_ranking = [m for m in sparse_ranking if m in allowed]

        collected.append(
            QueryRankings(
                query=query,
                dense=dense_ranking,
                sparse=sparse_ranking,
                matched_keywords=list(parsed.matched_keywords),
            )
        )
        if index % 25 == 0:
            logger.info(f"[weight-search] collected {index}/{len(queries)}")

    return collected


def score(
    rankings: Sequence[QueryRankings],
    weight_of: "callable",
    k: int,
    top_k: int,
) -> Dict[str, float]:
    """
    Score one weighting policy over the cached rankings.

    `weight_of` maps a QueryRankings to FusionWeights, which is what lets the
    same function evaluate a fixed split and the intent-routed policy.
    """
    recalls: List[float] = []
    reciprocal_ranks: List[float] = []

    for item in rankings:
        weights = weight_of(item)
        fused = reciprocal_rank_fusion(
            [item.dense, item.sparse], k=k, weights=weights.as_list(), top_k=top_k
        )
        order = [model for model, _ in fused]
        relevant = item.query.relevant_set
        recalls.append(capped_recall_at_k(order, relevant, 3))
        reciprocal_ranks.append(mrr(order, relevant))

    n = len(rankings) or 1
    return {
        "capped_recall@3": round(sum(recalls) / n, 4),
        "mrr": round(sum(reciprocal_ranks) / n, 4),
    }


def sweep(
    rankings: Sequence[QueryRankings],
    step: float = 0.1,
    k: int = 60,
    top_k: int = 10,
) -> List[Dict]:
    """Score every dense/sparse split from 0.0 to 1.0."""
    results: List[Dict] = []
    steps = int(round(1.0 / step)) + 1
    for i in range(steps):
        dense = round(i * step, 4)
        sparse = round(1.0 - dense, 4)
        weights = FusionWeights(dense=dense, sparse=sparse, reason="grid")
        metrics = score(rankings, lambda _item, w=weights: w, k, top_k)
        results.append({"dense": dense, "sparse": sparse, **metrics})
    return results


def score_dynamic(rankings: Sequence[QueryRankings], k: int, top_k: int) -> Dict:
    """Score the intent-routed policy, and report how the queries split."""
    metrics = score(
        rankings,
        lambda item: weights_for_query(item.matched_keywords, dynamic=True),
        k,
        top_k,
    )
    lexical = sum(1 for item in rankings if item.matched_keywords)
    return {
        **metrics,
        "n_lexical": lexical,
        "n_semantic": len(rankings) - lexical,
    }


def sweep_k(rankings: Sequence[QueryRankings], ks: Sequence[int], top_k: int) -> List[Dict]:
    """
    Score the damping constant at a fixed 0.5/0.5 split.

    k=60 is inherited from the literature; this checks whether it is defensible
    on *this* data rather than merely conventional.
    """
    equal = FusionWeights(0.5, 0.5, reason="k-sweep")
    return [{"k": k, **score(rankings, lambda _item, w=equal: w, k, top_k)} for k in ks]


def sweep_by_subset(
    rankings: Sequence[QueryRankings],
    step: float,
    k: int,
    top_k: int,
) -> Dict[str, Dict]:
    """
    Find the optimal split *within* each routing subset.

    This is the experiment that decides whether routing can help at all. If the
    lexical and semantic subsets peak at the same weights, no per-query policy
    can beat the single static split — routing would only add variance. If they
    peak apart, the gap is the headroom routing has to capture.
    """
    subsets = {
        "lexical": [item for item in rankings if item.matched_keywords],
        "semantic": [item for item in rankings if not item.matched_keywords],
    }

    analysis: Dict[str, Dict] = {}
    for name, items in subsets.items():
        if not items:
            continue
        grid = sweep(items, step=step, k=k, top_k=top_k)
        best = _best(grid, "capped_recall@3")
        analysis[name] = {"n": len(items), "grid": grid, "best": best}
    return analysis


def _best(results: Sequence[Dict], metric: str) -> Dict:
    return max(results, key=lambda r: r[metric])


def resolution(n_queries: int) -> float:
    """
    How much one query is worth. The floor on what this golden set can resolve.

    A "peak" smaller than this is one query flipping, not a better weighting.
    Reported next to every optimum because a grid search always returns a
    maximum — whether that maximum means anything is a separate question, and
    reading it off the table is how you end up shipping noise as a feature.
    """
    return 1.0 / n_queries if n_queries else 0.0


def plateau(results: Sequence[Dict], metric: str, tolerance: float) -> Tuple[float, float]:
    """
    The contiguous range of `dense` whose score is within `tolerance` of the best.

    A wide plateau means the parameter does not matter over that range, which
    is more useful to know than where the arg-max happens to land.
    """
    best = _best(results, metric)[metric]
    within = [r["dense"] for r in results if best - r[metric] <= tolerance]
    return (min(within), max(within)) if within else (0.0, 0.0)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=float, default=0.1, help="Weight increment")
    parser.add_argument("--k", type=int, default=60, help="RRF damping constant")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--sweep-k",
        action="store_true",
        help="Also sweep the damping constant at an equal split.",
    )
    args = parser.parse_args(argv)

    queries = load_golden_set()
    print(f"Collecting rankings for {len(queries)} golden queries...")
    rankings = collect_rankings(queries)

    grid = sweep(rankings, step=args.step, k=args.k, top_k=args.top_k)
    dynamic = score_dynamic(rankings, k=args.k, top_k=args.top_k)

    print(f"\nWeight sweep (k={args.k}, step={args.step}):")
    print(f"{'dense':>7} {'sparse':>7} {'capped_recall@3':>17} {'MRR':>8}")
    best_recall = _best(grid, "capped_recall@3")
    for row in grid:
        marker = " ←" if row is best_recall else ""
        print(
            f"{row['dense']:>7.2f} {row['sparse']:>7.2f} "
            f"{row['capped_recall@3']:>17.4f} {row['mrr']:>8.4f}{marker}"
        )

    grain = resolution(len(queries))
    low, high = plateau(grid, "capped_recall@3", grain)
    print(
        f"\nBest static: dense={best_recall['dense']:.2f} sparse={best_recall['sparse']:.2f} "
        f"→ capped_recall@3 {best_recall['capped_recall@3']:.4f}, MRR {best_recall['mrr']:.4f}"
    )
    print(
        f"Resolution: one query = {grain:.4f}. Everything within that of the best "
        f"is indistinguishable — here dense ∈ [{low:.2f}, {high:.2f}]."
    )
    print(
        f"Intent-routed: capped_recall@3 {dynamic['capped_recall@3']:.4f}, "
        f"MRR {dynamic['mrr']:.4f} "
        f"({dynamic['n_lexical']} lexical / {dynamic['n_semantic']} semantic queries)"
    )

    delta = dynamic["capped_recall@3"] - best_recall["capped_recall@3"]
    verdict = "beats" if delta > 0 else ("ties" if delta == 0 else "loses to")
    print(f"Dynamic routing {verdict} the best static split by {delta:+.4f} capped_recall@3.")

    # Whether routing *can* help: do the two subsets want different weights?
    subsets = sweep_by_subset(rankings, args.step, args.k, args.top_k)
    print("\nPer-subset optimum (does routing have anything to capture?):")
    for name, data in subsets.items():
        best = data["best"]
        print(
            f"  {name:<9} n={data['n']:<4} best dense={best['dense']:.2f} "
            f"sparse={best['sparse']:.2f} → {best['capped_recall@3']:.4f}"
        )
    if len(subsets) == 2:
        # A peak is only evidence if it clears the subset's own noise floor.
        # With 33 semantic queries one flip moves the score by 0.03, so a 0.01
        # "improvement" is not an improvement.
        separated = True
        for name, data in subsets.items():
            grain_s = resolution(data["n"])
            low_s, high_s = plateau(data["grid"], "capped_recall@3", grain_s)
            data["plateau"] = [low_s, high_s]
            data["resolution"] = round(grain_s, 4)
            print(
                f"  {name:<9} plateau dense ∈ [{low_s:.2f}, {high_s:.2f}] "
                f"(one query = {grain_s:.4f})"
            )
        lex, sem = subsets["lexical"], subsets["semantic"]
        overlap = (
            max(lex["plateau"][0], sem["plateau"][0]),
            min(lex["plateau"][1], sem["plateau"][1]),
        )
        separated = overlap[0] > overlap[1]

        if separated:
            print("  → Plateaus do not overlap. Routing has real headroom.")
        else:
            print(
                f"  → Plateaus overlap on dense ∈ [{overlap[0]:.2f}, {overlap[1]:.2f}]. "
                "The subsets' optima are indistinguishable at this sample size, so "
                "routing would be fitting noise, not signal. Use a single static "
                "split from the overlap."
            )

    report: Dict = {
        "n_queries": len(queries),
        "k": args.k,
        "step": args.step,
        "grid": grid,
        "best_static": best_recall,
        "dynamic": dynamic,
        "subsets": subsets,
        "resolution": round(grain, 4),
        "plateau": [low, high],
    }

    if args.sweep_k:
        k_rows = sweep_k(rankings, [1, 5, 10, 20, 60, 100, 300], args.top_k)
        report["k_sweep"] = k_rows
        print(
            f"\nDamping constant sweep (equal split):\n{'k':>5} {'capped_recall@3':>17} {'MRR':>8}"
        )
        for row in k_rows:
            print(f"{row['k']:>5} {row['capped_recall@3']:>17.4f} {row['mrr']:>8.4f}")

    out = args.out or (RESULTS_DIR / "fusion_weight_search.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
