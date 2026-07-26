"""
Semantic router: the online half.

Anchors load once at startup into a resident FP32 tensor. Classification is one
`(1, dim) @ (dim, n_anchors)` matmul plus an argmax — microseconds, no LLM, no
network. That is the whole point: an utterance like "行，听你的" carries no
vehicle attribute, and discovering that with a 70B model costs a second and a
cloud call. The router answers it before the model is ever consulted.

This sits *below* the hybrid inference router in cost, forming a third tier:

    semantic router (µs, no model)  →  local 8B (~65 ms TTFT)  →  cloud 70B

**On thresholds.** A single global cut-off would be wrong: BGE-M3 packs short
Chinese utterances densely, so an unrelated sentence still scores ~0.5 against
some anchor. The router therefore requires both an absolute floor and a margin
over the runner-up from a *different* intent. Without the margin, turns that
sit between two intents get assigned confidently to whichever wins by 0.001.

**On what a hit is allowed to do.** Control-flow hits may skip extraction.
Needs-flow hits may *not* skip anything — they hint which slot the extractor
should focus on, and the extractor still runs. A router that decided needs on
its own would replace a model that reads the whole sentence with one that
matches its vibe.
"""

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from src.semantic_router.anchors import ANCHOR_PATH, AnchorSet
from src.semantic_router.seeds import CONTROL_FLOW, NEEDS_FLOW
from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Minimum cosine similarity for a match to be considered at all.
DEFAULT_THRESHOLD = 0.62

#: Required lead over the best anchor from a different intent. Guards against
#: confident assignment of genuinely ambiguous turns.
DEFAULT_MARGIN = 0.03


@dataclass(frozen=True)
class RouteDecision:
    """Outcome of classifying one utterance."""

    intent: Optional[str]
    family: Optional[str]
    score: float
    margin: float
    matched: bool
    runner_up: Optional[str] = None

    @property
    def is_control_flow(self) -> bool:
        return self.matched and self.family == CONTROL_FLOW

    @property
    def is_needs_flow(self) -> bool:
        return self.matched and self.family == NEEDS_FLOW

    def as_dict(self) -> dict:
        return {
            "intent": self.intent,
            "family": self.family,
            "score": round(self.score, 4),
            "margin": round(self.margin, 4),
            "matched": self.matched,
            "runner_up": self.runner_up,
        }


class SemanticRouter:
    """
    Classifies utterances against resident anchor vectors.

    Thread-safe and stateless per call. The anchor tensor is read-only after
    load, so concurrent requests share it without locking.
    """

    def __init__(
        self,
        anchors: AnchorSet,
        embedder=None,
        threshold: float = DEFAULT_THRESHOLD,
        margin: float = DEFAULT_MARGIN,
    ):
        self.anchors = anchors
        self.threshold = threshold
        self.margin = margin
        self._embedder = embedder

        # Transposed once at load so the hot path is a plain matmul with no
        # per-call transpose or copy.
        self._matrix = np.ascontiguousarray(anchors.vectors.T, dtype=np.float32)
        self._intents = list(anchors.intents)
        self._families = list(anchors.families)

    @property
    def embedder(self):
        """The shared BGE-M3 instance — the router adds no model of its own."""
        if self._embedder is None:
            from src.rag.embeddings import BGEEmbeddingModel

            self._embedder = BGEEmbeddingModel()
        return self._embedder

    # ── classification ────────────────────────────────────────────────

    def classify(self, text: str) -> RouteDecision:
        """Route one utterance."""
        if not text or not text.strip():
            return RouteDecision(None, None, 0.0, 0.0, matched=False)

        vector = self._embed(text)
        scores = vector @ self._matrix  # (n_anchors,)

        best_index = int(np.argmax(scores))
        best_score = float(scores[best_index])
        best_intent = self._intents[best_index]

        runner_up, runner_score = self._best_other_intent(scores, best_intent)
        margin = best_score - runner_score

        matched = best_score >= self.threshold and margin >= self.margin
        return RouteDecision(
            intent=best_intent if matched else None,
            family=self._families[best_index] if matched else None,
            score=best_score,
            margin=margin,
            matched=matched,
            runner_up=runner_up,
        )

    def explain(self, text: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """Top-N (intent, score) pairs — for tuning thresholds and debugging."""
        if not text or not text.strip():
            return []
        scores = self._embed(text) @ self._matrix
        order = np.argsort(-scores)[: top_n * 3]

        seen: List[Tuple[str, float]] = []
        for index in order:
            intent = self._intents[int(index)]
            if any(intent == existing for existing, _ in seen):
                continue
            seen.append((intent, float(scores[int(index)])))
            if len(seen) >= top_n:
                break
        return seen

    def _embed(self, text: str) -> np.ndarray:
        raw = np.array(self.embedder._get_text_embedding(text), dtype=np.float32)
        norm = np.linalg.norm(raw)
        return raw / norm if norm > 0 else raw

    def _best_other_intent(self, scores: np.ndarray, exclude: str) -> Tuple[Optional[str], float]:
        """Highest-scoring anchor whose intent differs from `exclude`."""
        best_intent: Optional[str] = None
        best_score = -1.0
        for index, intent in enumerate(self._intents):
            if intent == exclude:
                continue
            value = float(scores[index])
            if value > best_score:
                best_score = value
                best_intent = intent
        return best_intent, max(best_score, 0.0)

    def summary(self) -> dict:
        return {
            **self.anchors.summary(),
            "threshold": self.threshold,
            "margin": self.margin,
            "resident_bytes": int(self._matrix.nbytes),
            "dtype": str(self._matrix.dtype),
        }


_default_router: Optional[SemanticRouter] = None
_lock = threading.Lock()


def get_router(
    path: Optional[Path] = None,
    embedder=None,
    required: bool = False,
) -> Optional[SemanticRouter]:
    """
    Load the process-wide router, or None when no anchors are built.

    Returning None rather than raising keeps the router optional: a deployment
    without the artifact simply routes everything the long way, which is the
    behaviour that existed before this layer.
    """
    global _default_router
    if _default_router is not None:
        return _default_router

    with _lock:
        if _default_router is not None:
            return _default_router
        target = Path(path or ANCHOR_PATH)
        if not target.exists():
            message = (
                f"Anchor artifact not found at {target}. "
                "Build it with: python -m src.semantic_router.build"
            )
            if required:
                raise FileNotFoundError(message)
            logger.warning(message)
            return None
        anchors = AnchorSet.load(target)
        _default_router = SemanticRouter(anchors, embedder=embedder)
        logger.info(
            f"语义路由就绪: {len(anchors)} 个锚点常驻内存 "
            f"({_default_router._matrix.nbytes / 1024:.1f} KB, FP32)"
        )
        return _default_router


def reset_router() -> None:
    """Drop the cached router. For tests and after rebuilding anchors."""
    global _default_router
    with _lock:
        _default_router = None


__all__ = [
    "SemanticRouter",
    "RouteDecision",
    "get_router",
    "reset_router",
    "CONTROL_FLOW",
    "NEEDS_FLOW",
]
