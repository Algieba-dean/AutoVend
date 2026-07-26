"""
Deterministic retrieval metrics.

No LLM calls, no randomness — the same index and golden set always produce the
same numbers, which is what makes these safe to gate CI on.

All functions take `retrieved` as a *ranked* list of car_model strings (best
first) and `relevant` as the ground-truth set.

A note on which metric to read:

- `recall@k` answers "did we surface the right cars at all". It is bounded by
  `k / |relevant|`, so for a query with 900 relevant cars, recall@3 can never
  exceed 0.003 — meaningless. Use it on narrow queries.
- `precision@k` answers "is what we showed correct". It stays meaningful for
  broad queries where recall@k is structurally capped.
- `hit_rate@k` ("was at least one of the top-k relevant") is the closest proxy
  for the user-visible question: did this recommendation make sense?
- `MRR` rewards putting a relevant car first, which is what the UI shows.

The aggregate report carries all of them precisely because no single one is
honest across the whole query mix.
"""

import math
from typing import Dict, Iterable, List, Sequence, Set


def _top_k(retrieved: Sequence[str], k: int) -> List[str]:
    return list(retrieved[:k])


def recall_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    """Fraction of relevant items that appear in the top k."""
    if not relevant:
        return 0.0
    hits = sum(1 for item in _top_k(retrieved, k) if item in relevant)
    return hits / len(relevant)


def capped_recall_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    """
    Recall normalised by the best score reachable at this k.

    With |relevant| > k, plain recall@k cannot reach 1.0 no matter how perfect
    the ranking, so averaging it across queries with wildly different relevant-set
    sizes mixes two different scales. Dividing by min(k, |relevant|) puts every
    query back on a 0-1 scale where 1.0 means "as good as possible at this k".
    """
    if not relevant:
        return 0.0
    hits = sum(1 for item in _top_k(retrieved, k) if item in relevant)
    return hits / min(k, len(relevant))


def precision_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    """Fraction of the top k that is relevant."""
    top = _top_k(retrieved, k)
    if not top:
        return 0.0
    return sum(1 for item in top if item in relevant) / len(top)


def hit_rate_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    """1.0 if any of the top k is relevant, else 0.0."""
    return 1.0 if any(item in relevant for item in _top_k(retrieved, k)) else 0.0


def mrr(retrieved: Sequence[str], relevant: Set[str]) -> float:
    """Reciprocal rank of the first relevant item (0.0 if none)."""
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    """
    Binary-relevance NDCG@k.

    Ideal DCG assumes the top min(k, |relevant|) positions are all relevant.
    """
    if not relevant:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, item in enumerate(_top_k(retrieved, k), start=1)
        if item in relevant
    )
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(k, len(relevant)) + 1))
    return dcg / ideal if ideal else 0.0


#: Cut-offs reported for every run. 3 is the headline (the UI shows a handful of
#: cards); 1 and 5/10 bracket it.
DEFAULT_KS = (1, 3, 5, 10)


def evaluate_one(
    retrieved: Sequence[str],
    relevant: Set[str],
    ks: Iterable[int] = DEFAULT_KS,
) -> Dict[str, float]:
    """All metrics for a single query."""
    scores: Dict[str, float] = {"mrr": mrr(retrieved, relevant)}
    for k in ks:
        scores[f"recall@{k}"] = recall_at_k(retrieved, relevant, k)
        scores[f"capped_recall@{k}"] = capped_recall_at_k(retrieved, relevant, k)
        scores[f"precision@{k}"] = precision_at_k(retrieved, relevant, k)
        scores[f"hit_rate@{k}"] = hit_rate_at_k(retrieved, relevant, k)
        scores[f"ndcg@{k}"] = ndcg_at_k(retrieved, relevant, k)
    return scores


def aggregate(per_query: Sequence[Dict[str, float]]) -> Dict[str, float]:
    """Macro-average each metric across queries (every query weighs the same)."""
    if not per_query:
        return {}
    keys = per_query[0].keys()
    return {key: sum(q[key] for q in per_query) / len(per_query) for key in keys}
