"""
Reciprocal Rank Fusion (RRF).

Combines rankings from retrievers whose scores are not comparable — cosine
similarity and BM25 live on different scales, so averaging or normalising them
introduces an arbitrary weighting. RRF only reads *ranks*, which sidesteps the
problem entirely:

    score(d) = Σ_r  1 / (k + rank_r(d))

`k` damps the top positions: a document ranked 1st by one retriever and absent
from the other should not automatically beat a document ranked 2nd-3rd by both.
k=60 is the value from Cormack et al. (2009) and is the usual default.

Reference: Cormack, Clarke & Buettcher, "Reciprocal Rank Fusion outperforms
Condorcet and individual Rank Learning Methods", SIGIR 2009.
"""

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_K = 60


def reciprocal_rank_fusion(
    rankings: Iterable[Sequence[str]],
    k: int = DEFAULT_K,
    weights: Optional[Sequence[float]] = None,
    top_k: Optional[int] = None,
) -> List[Tuple[str, float]]:
    """
    Fuse ranked id lists into one ranking.

    Args:
        rankings: One ranked list of ids per retriever, best first.
        k: Rank damping constant.
        weights: Optional per-retriever weight, same order as `rankings`.
        top_k: Truncate the fused ranking.

    Returns:
        (id, fused_score) pairs, best first. Ties break on the id so the output
        is deterministic — which matters when this feeds a CI gate.
    """
    ranking_list = [list(r) for r in rankings]
    if weights is None:
        weights = [1.0] * len(ranking_list)
    elif len(weights) != len(ranking_list):
        raise ValueError(f"Got {len(weights)} weights for {len(ranking_list)} rankings.")

    scores: Dict[str, float] = {}
    for ranking, weight in zip(ranking_list, weights):
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + weight / (k + rank)

    fused = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    return fused[:top_k] if top_k else fused
