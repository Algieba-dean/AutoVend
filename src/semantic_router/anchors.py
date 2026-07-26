"""
Anchor vectors: the offline half of the semantic router.

Pipeline: seed utterances -> BGE-M3 embeddings -> K-means per intent ->
centroids -> `.npz` artifact. At startup the artifact loads into a single FP32
tensor and classification becomes one matrix multiply.

**Why cluster instead of keeping every seed vector.** A dozen seeds per intent
would work as a nearest-neighbour index, but centroids are better on both axes
that matter here. They denoise — an idiosyncratic seed stops being its own
attractor — and they shrink the online comparison from O(seeds) to O(clusters),
which keeps the whole matrix in L2 cache. K > 1 per intent because intents are
genuinely multi-modal: "太贵了" and "有没有便宜点的" are both budget objections
but sit in different regions, and forcing one centroid puts it between them,
close to neither.

**Why cosine similarity is a dot product here.** `BGEEmbeddingModel` L2-normalises
by default, so normalised vectors make cosine and inner product identical. The
build asserts this rather than assuming it — a future change to the embedding
config would otherwise silently turn every score into an unnormalised dot
product and shift all thresholds.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from src.semantic_router.seeds import all_seeds, family_of
from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

ANCHOR_PATH = PROJECT_ROOT / "data" / "anchors.npz"

#: Clusters per intent. Chosen relative to seed count: with ~10 seeds per
#: intent, 3 centroids capture the main phrasings without splitting into
#: singletons that would just be the seeds again.
DEFAULT_K = 3

#: Below this many seeds, clustering is meaningless — use the mean instead.
MIN_SEEDS_FOR_CLUSTERING = 6


@dataclass
class AnchorSet:
    """
    Anchor vectors plus their labels.

    `vectors` is (n_anchors, dim) float32, L2-normalised. Row i is described by
    `intents[i]` and `families[i]`.
    """

    vectors: np.ndarray
    intents: List[str]
    families: List[str]
    model_name: str
    dim: int

    def __post_init__(self):
        if self.vectors.dtype != np.float32:
            self.vectors = self.vectors.astype(np.float32)
        if len(self.intents) != len(self.vectors) or len(self.families) != len(self.vectors):
            raise ValueError(
                f"Label count mismatch: {len(self.vectors)} vectors, "
                f"{len(self.intents)} intents, {len(self.families)} families"
            )

    def __len__(self) -> int:
        return len(self.vectors)

    @property
    def intent_names(self) -> List[str]:
        seen: List[str] = []
        for intent in self.intents:
            if intent not in seen:
                seen.append(intent)
        return seen

    def save(self, path: Optional[Path] = None) -> Path:
        target = Path(path or ANCHOR_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            target,
            vectors=self.vectors,
            intents=np.array(self.intents, dtype=object),
            families=np.array(self.families, dtype=object),
            meta=np.array(
                [json.dumps({"model_name": self.model_name, "dim": self.dim})],
                dtype=object,
            ),
        )
        logger.info(f"锚点已保存: {target} ({len(self)} 个锚点, {self.dim} 维)")
        return target

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AnchorSet":
        target = Path(path or ANCHOR_PATH)
        with np.load(target, allow_pickle=True) as payload:
            meta = json.loads(payload["meta"][0])
            return cls(
                vectors=payload["vectors"],
                intents=[str(x) for x in payload["intents"]],
                families=[str(x) for x in payload["families"]],
                model_name=meta["model_name"],
                dim=meta["dim"],
            )

    def summary(self) -> Dict:
        counts: Dict[str, int] = {}
        for intent in self.intents:
            counts[intent] = counts.get(intent, 0) + 1
        return {
            "n_anchors": len(self),
            "dim": self.dim,
            "model": self.model_name,
            "intents": counts,
        }


def _kmeans(
    vectors: np.ndarray,
    k: int,
    seed: int = 42,
    iterations: int = 50,
) -> np.ndarray:
    """
    Spherical K-means (cosine) over L2-normalised vectors.

    Deterministic by construction: initial centroids are the k seeds furthest
    apart rather than random picks, so rebuilding the artifact from the same
    seeds reproduces it byte for byte. That matters because the anchors are a
    committed artifact — a nondeterministic build would show up as a spurious
    diff on every rebuild and make regressions impossible to spot.
    """
    n = len(vectors)
    if k >= n:
        return vectors.copy()

    # k-means++-style init, but argmax instead of sampling for determinism.
    rng = np.random.default_rng(seed)
    centroids = [vectors[rng.integers(n)]]
    for _ in range(k - 1):
        similarity = vectors @ np.array(centroids).T  # (n, chosen)
        closest = similarity.max(axis=1)
        centroids.append(vectors[int(np.argmin(closest))])
    centers = np.array(centroids, dtype=np.float32)

    for _ in range(iterations):
        assignments = np.argmax(vectors @ centers.T, axis=1)
        moved = False
        for index in range(k):
            members = vectors[assignments == index]
            if len(members) == 0:
                continue
            updated = members.mean(axis=0)
            norm = np.linalg.norm(updated)
            if norm > 0:
                updated = updated / norm
            if not np.allclose(updated, centers[index]):
                centers[index] = updated
                moved = True
        if not moved:
            break

    # Drop centroids that ended up with no members.
    assignments = np.argmax(vectors @ centers.T, axis=1)
    populated = [i for i in range(k) if np.any(assignments == i)]
    return centers[populated]


def build_anchor_set(
    embedder=None,
    k: int = DEFAULT_K,
    seeds: Optional[Dict[str, Dict[str, Sequence[str]]]] = None,
) -> AnchorSet:
    """
    Embed the seed corpus and cluster it into anchors.

    Args:
        embedder: Anything with `_get_text_embeddings(List[str])`. Defaults to
            the same BGE-M3 instance the retrieval stack uses — reusing it is
            the point: the router costs no extra model in memory.
        k: Clusters per intent.
        seeds: Override corpus, for tests.
    """
    if embedder is None:
        from src.rag.embeddings import BGEEmbeddingModel

        embedder = BGEEmbeddingModel()

    corpus = seeds if seeds is not None else all_seeds()

    vectors: List[np.ndarray] = []
    intents: List[str] = []
    families: List[str] = []

    for family, intent_map in corpus.items():
        for intent, utterances in intent_map.items():
            if not utterances:
                continue
            embedded = np.array(embedder._get_text_embeddings(list(utterances)), dtype=np.float32)
            embedded = _normalise(embedded)

            if len(utterances) < MIN_SEEDS_FOR_CLUSTERING:
                centroids = _normalise(embedded.mean(axis=0, keepdims=True))
            else:
                centroids = _kmeans(embedded, k)

            vectors.append(centroids)
            intents.extend([intent] * len(centroids))
            families.extend([family] * len(centroids))
            logger.info(f"  {family}/{intent}: {len(utterances)} 条 → {len(centroids)} 个锚点")

    stacked = np.vstack(vectors).astype(np.float32)
    dim = stacked.shape[1]

    anchor_set = AnchorSet(
        vectors=stacked,
        intents=intents,
        families=families,
        model_name=_embedder_name(embedder),
        dim=dim,
    )
    logger.info(f"锚点构建完成: {len(anchor_set)} 个锚点 / {len(anchor_set.intent_names)} 个意图")
    return anchor_set


def _embedder_name(embedder) -> str:
    """
    Read the embedding model's name.

    `BGEEmbeddingModel.model_name` is a property, but the class inherits from a
    Pydantic v2 BaseEmbedding and `model_` is Pydantic's protected namespace —
    `getattr(e, "model_name")` hands back the property object rather than its
    value, which then fails to serialise. The private attribute is the one that
    actually holds the string.
    """
    for attribute in ("_model_name", "model_name"):
        value = getattr(embedder, attribute, None)
        if isinstance(value, str):
            return value
    return "unknown"


def _normalise(matrix: np.ndarray) -> np.ndarray:
    """
    L2-normalise rows, so an inner product is a cosine.

    Applied even though BGE-M3 normalises already: it is cheap, and it makes
    the invariant hold regardless of the embedder's configuration rather than
    depending on a setting elsewhere.
    """
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)


def _family_for(intent: str) -> str:
    return family_of(intent)
