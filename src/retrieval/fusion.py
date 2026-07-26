"""
Reciprocal Rank Fusion (RRF), weighted and intent-routed.

Combines rankings from retrievers whose scores are not comparable — cosine
similarity and BM25 live on different scales, so averaging or normalising them
introduces an arbitrary weighting. RRF only reads *ranks*, which sidesteps the
problem entirely:

    score(d) = w_dense · 1/(k + rank_dense(d)) + w_sparse · 1/(k + rank_sparse(d))

## On k

`k` damps the top positions. Without it, rank 1 scores 1.0 and rank 2 scores
0.5 — a document that one channel happened to put first, for reasons unrelated
to the query, would outscore a document both channels ranked 2nd-3rd. With
k=60 those become 1/61 and 1/62: still ordered, but close enough that agreement
across channels beats a single confident vote. That noise-damping is the whole
job of the constant, and 60 is the value from Cormack et al. (2009).

## On weights — and why routing is off by default

Both channels get equal weight, and that is a measured decision rather than a
default nobody questioned. `src.eval.weight_search` sweeps the split from 0.0
to 1.0 over the 116-query golden set:

    dense 0.00 → 0.7069     dense 0.40 → 0.7557 (arg-max)
    dense 0.50 → 0.7529     dense 1.00 → 0.6810

The ends are clearly worse — fusion beats either channel alone by 5-7 points.
The middle is flat: every split from dense 0.20 to 0.70 lands within one
query's worth of the maximum (1/116 = 0.0086). The arg-max at 0.40 is not a
finding, it is where the noise happened to peak.

**Intent routing was implemented, measured, and left disabled.** The hypothesis
was that queries naming catalogue vocabulary ("BMW", "Mid-Size SUV") should
lean lexical, while paraphrases ("适合家用的车") should lean semantic. Splitting
the golden set that way and searching each subset separately:

    lexical  (n=83)  plateau dense ∈ [0.20, 0.80]
    semantic (n=33)  plateau dense ∈ [0.10, 0.70]

The plateaus overlap on [0.20, 0.70]. The subsets do not want measurably
different weights at this sample size, and the routed policy duly scored
*below* the best static split (0.7500 vs 0.7557). Shipping it on would have
been fitting noise.

The machinery stays because the question is worth re-asking on a larger golden
set — pass `dynamic_fusion_weights=True` to enable it, and re-run the search
first. A second finding worth keeping: the semantic subset preferred *more*
sparse weight, the opposite of the hypothesis. A query the rule parser misses
is not a query BM25 misses; the parser only knows the label vocabulary, while
BM25 indexes the full catalogue text.

Reference: Cormack, Clarke & Buettcher, "Reciprocal Rank Fusion outperforms
Condorcet and individual Rank Learning Methods", SIGIR 2009.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_K = 60


@dataclass(frozen=True)
class FusionWeights:
    """Per-channel weights for one fused query."""

    dense: float = 1.0
    sparse: float = 1.0
    #: Why these weights were chosen, for logging and telemetry.
    reason: str = "static"

    def as_list(self) -> List[float]:
        """In the order `[dense, sparse]` that the pipeline passes rankings."""
        return [self.dense, self.sparse]


#: The shipped weights. Equal, and sitting in the middle of the measured
#: plateau [0.20, 0.70] rather than on the arg-max, because the arg-max is
#: within single-query noise and chasing it would be overfitting the golden set.
STATIC_WEIGHTS = FusionWeights(dense=0.5, sparse=0.5, reason="static")

#: Weights for the intent-routed policy. Disabled by default — measured below
#: the static split; see the module docstring. Kept for re-evaluation on a
#: larger golden set.
LEXICAL_WEIGHTS = FusionWeights(dense=0.5, sparse=0.5, reason="lexical-intent")
SEMANTIC_WEIGHTS = FusionWeights(dense=0.4, sparse=0.6, reason="semantic-intent")

#: At or above this many matched keywords the query counts as lexical.
LEXICAL_KEYWORD_THRESHOLD = 1


def weights_for_query(
    matched_keywords: Optional[Sequence[str]] = None,
    dynamic: bool = False,
) -> FusionWeights:
    """
    Pick channel weights for one query.

    Args:
        matched_keywords: What the rule parser matched. Empty or None means the
            query used no catalogue vocabulary.
        dynamic: Enable intent routing. Off by default because it measured
            *worse* than the static split on the current golden set — the two
            subsets' optimal weights are indistinguishable at n=116. Re-run
            `python -m src.eval.weight_search` before turning it on.
    """
    if not dynamic:
        return STATIC_WEIGHTS
    if matched_keywords and len(matched_keywords) >= LEXICAL_KEYWORD_THRESHOLD:
        return LEXICAL_WEIGHTS
    return SEMANTIC_WEIGHTS


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
