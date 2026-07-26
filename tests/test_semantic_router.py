"""
Tests for the semantic router.

Split in two: everything that can run against a synthetic embedder runs fast
and unmarked; the handful that need real BGE-M3 vectors are `slow`.

The property that matters most is the negative one — an off-domain sentence
must come back unmatched. A router that always picks its nearest intent would
route "今天天气真不错" to small talk and skip an extraction it should not have.
"""

import zlib

import numpy as np
import pytest

from src.semantic_router.anchors import AnchorSet, _kmeans, build_anchor_set
from src.semantic_router.router import (
    DEFAULT_MARGIN,
    DEFAULT_THRESHOLD,
    SemanticRouter,
)
from src.semantic_router.seeds import (
    CONTROL_FLOW,
    CONTROL_SEEDS,
    NEEDS_FLOW,
    NEEDS_SEEDS,
    family_of,
    seed_count,
)


class _StubEmbedder:
    """
    Maps text to a deterministic unit vector.

    Sentences sharing a keyword land in the same direction, which is enough to
    exercise clustering and routing without loading a 2GB model.
    """

    dim = 8

    #: Axes 0-3 belong to keywords (and therefore to anchors); unknown text is
    #: confined to 4-7 so it is guaranteed orthogonal to every anchor.
    #:
    #: The first version scattered unknown text across all 8 axes using
    #: `hash(text)`. Python randomises string hashing per process, so the
    #: "unrelated text does not match" case landed on an anchor's axis in
    #: roughly a quarter of runs — a flaky test masquerading as a routing bug.
    UNKNOWN_AXIS_BASE = 4
    _model_name = "stub"

    def __init__(self, keyword_axes=None):
        self.keyword_axes = keyword_axes or {}
        assert all(axis < self.UNKNOWN_AXIS_BASE for axis in (keyword_axes or {}).values()), (
            "keyword axes must stay below UNKNOWN_AXIS_BASE or unknown text "
            "can collide with an anchor"
        )

    def _get_text_embedding(self, text: str):
        vector = np.zeros(self.dim, dtype=np.float32)
        for keyword, axis in self.keyword_axes.items():
            if keyword in text:
                vector[axis] += 1.0
        if not vector.any():
            span = self.dim - self.UNKNOWN_AXIS_BASE
            offset = zlib.crc32(text.encode("utf-8")) % span
            vector[self.UNKNOWN_AXIS_BASE + offset] = 1.0
        return (vector / np.linalg.norm(vector)).tolist()

    def _get_text_embeddings(self, texts):
        return [self._get_text_embedding(t) for t in texts]


def _anchor_set(rows):
    """Build an AnchorSet from (intent, family, axis) triples."""
    vectors = []
    intents = []
    families = []
    for intent, family, axis in rows:
        vector = np.zeros(8, dtype=np.float32)
        vector[axis] = 1.0
        vectors.append(vector)
        intents.append(intent)
        families.append(family)
    return AnchorSet(np.array(vectors), intents, families, "stub", 8)


class TestSeeds:
    def test_families_do_not_share_intents(self):
        assert not set(CONTROL_SEEDS) & set(NEEDS_SEEDS)

    def test_every_intent_resolves_to_a_family(self):
        for intent in list(CONTROL_SEEDS) + list(NEEDS_SEEDS):
            assert family_of(intent) in (CONTROL_FLOW, NEEDS_FLOW)

    def test_unknown_intent_raises(self):
        with pytest.raises(KeyError):
            family_of("nonexistent")

    def test_each_intent_has_enough_variety_to_cluster(self):
        """K-means over three near-identical seeds finds modes that aren't there."""
        for group in (CONTROL_SEEDS, NEEDS_SEEDS):
            for intent, utterances in group.items():
                assert len(utterances) >= 7, f"{intent} has only {len(utterances)} seeds"
                assert len(set(utterances)) == len(utterances), f"{intent} has duplicates"

    def test_corpus_is_large_enough_to_be_meaningful(self):
        assert seed_count() >= 100


class TestKMeans:
    def test_is_deterministic(self):
        """The artifact is committed; a nondeterministic build makes diffs noise."""
        vectors = np.eye(6, dtype=np.float32)

        first = _kmeans(vectors, 3)
        second = _kmeans(vectors, 3)

        assert np.allclose(first, second)

    def test_returns_unit_vectors(self):
        rng = np.random.default_rng(0)
        raw = rng.normal(size=(20, 8)).astype(np.float32)
        vectors = raw / np.linalg.norm(raw, axis=1, keepdims=True)

        centroids = _kmeans(vectors, 3)

        assert np.allclose(np.linalg.norm(centroids, axis=1), 1.0, atol=1e-5)

    def test_k_larger_than_the_sample_returns_the_sample(self):
        vectors = np.eye(3, dtype=np.float32)

        assert len(_kmeans(vectors, 10)) == 3

    def test_separates_distinct_groups(self):
        group_a = np.tile(np.array([1.0, 0, 0, 0], dtype=np.float32), (5, 1))
        group_b = np.tile(np.array([0, 1.0, 0, 0], dtype=np.float32), (5, 1))

        centroids = _kmeans(np.vstack([group_a, group_b]), 2)

        assert len(centroids) == 2
        assert np.allclose(sorted(np.argmax(centroids, axis=1)), [0, 1])


class TestBuildAnchorSet:
    def test_labels_line_up_with_vectors(self):
        embedder = _StubEmbedder({"budget": 0, "yes": 1})
        seeds = {
            CONTROL_FLOW: {"affirm": ["yes " + str(i) for i in range(8)]},
            NEEDS_FLOW: {"budget": ["budget " + str(i) for i in range(8)]},
        }

        anchors = build_anchor_set(embedder=embedder, k=2, seeds=seeds)

        assert len(anchors.intents) == len(anchors.vectors)
        assert set(anchors.intents) == {"affirm", "budget"}
        assert set(anchors.families) == {CONTROL_FLOW, NEEDS_FLOW}

    def test_vectors_are_float32(self):
        """The artifact is loaded straight into a resident FP32 tensor."""
        embedder = _StubEmbedder({"yes": 1})
        seeds = {CONTROL_FLOW: {"affirm": ["yes " + str(i) for i in range(8)]}}

        anchors = build_anchor_set(embedder=embedder, k=2, seeds=seeds)

        assert anchors.vectors.dtype == np.float32

    def test_small_intents_collapse_to_a_single_mean(self):
        embedder = _StubEmbedder({"yes": 1})
        seeds = {CONTROL_FLOW: {"affirm": ["yes a", "yes b"]}}

        anchors = build_anchor_set(embedder=embedder, k=3, seeds=seeds)

        assert len(anchors) == 1

    def test_round_trips_through_disk(self, tmp_path):
        embedder = _StubEmbedder({"yes": 1, "budget": 0})
        seeds = {
            CONTROL_FLOW: {"affirm": ["yes " + str(i) for i in range(8)]},
            NEEDS_FLOW: {"budget": ["budget " + str(i) for i in range(8)]},
        }
        anchors = build_anchor_set(embedder=embedder, k=2, seeds=seeds)
        path = anchors.save(tmp_path / "anchors.npz")

        loaded = AnchorSet.load(path)

        assert np.allclose(loaded.vectors, anchors.vectors)
        assert loaded.intents == anchors.intents
        assert loaded.families == anchors.families
        assert loaded.model_name == "stub"

    def test_mismatched_labels_are_rejected(self):
        with pytest.raises(ValueError, match="Label count mismatch"):
            AnchorSet(np.zeros((2, 4), dtype=np.float32), ["a"], ["control"], "stub", 4)


class TestRouting:
    @pytest.fixture
    def router(self):
        anchors = _anchor_set([("affirm", CONTROL_FLOW, 0), ("budget", NEEDS_FLOW, 1)])
        embedder = _StubEmbedder({"yes": 0, "budget": 1})
        return SemanticRouter(anchors, embedder=embedder, threshold=0.6, margin=0.03)

    def test_routes_to_the_nearest_intent(self, router):
        decision = router.classify("yes please")

        assert decision.matched
        assert decision.intent == "affirm"
        assert decision.is_control_flow
        assert not decision.is_needs_flow

    def test_reports_the_family(self, router):
        assert router.classify("budget is 30").family == NEEDS_FLOW

    def test_unrelated_text_does_not_match(self, router):
        """The negative case the whole design turns on."""
        decision = router.classify("completely unrelated sentence")

        assert not decision.matched
        assert decision.intent is None

    def test_margin_rejects_an_ambiguous_hit(self):
        """
        A turn equidistant from two intents must not be assigned to whichever
        wins by a hair. Score alone would accept this; the margin is what
        rejects it.
        """
        anchors = _anchor_set([("affirm", CONTROL_FLOW, 0), ("budget", NEEDS_FLOW, 1)])
        embedder = _StubEmbedder({"yes": 0, "budget": 1})
        router = SemanticRouter(anchors, embedder=embedder, threshold=0.5, margin=0.2)

        decision = router.classify("yes budget")  # lands between both anchors

        assert decision.score >= router.threshold, "score alone would have accepted"
        assert not decision.matched, "margin should have rejected it"

    def test_empty_input_is_unmatched(self, router):
        assert not router.classify("").matched
        assert not router.classify("   ").matched

    def test_explain_lists_distinct_intents(self, router):
        explained = router.explain("yes please", top_n=2)

        assert [intent for intent, _ in explained] == ["affirm", "budget"]
        assert explained[0][1] >= explained[1][1]

    def test_summary_reports_the_resident_footprint(self, router):
        summary = router.summary()

        assert summary["dtype"] == "float32"
        assert summary["resident_bytes"] == router.anchors.vectors.nbytes
        assert summary["threshold"] == 0.6


class TestDefaults:
    def test_threshold_and_margin_are_both_engaged(self):
        """
        Documented behaviour: real off-domain probes score *above* the
        threshold and are rejected on margin alone. A margin of 0 would
        silently disable that guard.
        """
        assert 0.0 < DEFAULT_THRESHOLD < 1.0
        assert DEFAULT_MARGIN > 0.0


@pytest.mark.slow
class TestWithRealEmbeddings:
    """Against actual BGE-M3 vectors, using the committed anchor artifact."""

    @pytest.fixture(scope="class")
    def router(self):
        from src.semantic_router.router import get_router

        instance = get_router()
        if instance is None:
            pytest.skip("anchors not built — run: python -m src.semantic_router.build")
        return instance

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("行，听你的", "affirm"),
            ("我再想想吧", "defer"),
            ("太贵了，超预算", "budget_objection"),
            ("我有35万的预算", "budget"),
            ("我要油车，不要电车", "powertrain"),
            ("平时就是上下班代步", "usage"),
        ],
    )
    def test_paraphrases_route_correctly(self, router, text, expected):
        assert router.classify(text).intent == expected

    @pytest.mark.parametrize("text", ["今天天气真不错", "这个螺丝刀多少钱"])
    def test_off_domain_text_is_rejected(self, router, text):
        decision = router.classify(text)

        assert not decision.matched, (
            f"{text!r} matched {decision.intent} "
            f"(score={decision.score:.3f}, margin={decision.margin:.3f})"
        )

    def test_control_and_needs_are_distinguished(self, router):
        assert router.classify("行，听你的").is_control_flow
        assert router.classify("我有35万的预算").is_needs_flow


class TestBuildCLI:
    """
    The probe gate must be able to fail.

    CI runs `build --probe`; if that always exited 0, a seed or threshold change
    that broke routing would land silently — an unbuilt or mis-tuned router does
    not error, it just sends every turn the long way.
    """

    def _stub_router(self, monkeypatch, verdicts):
        """Patch SemanticRouter so classify() returns scripted intents."""
        from src.semantic_router import build as build_module

        class _Scripted:
            threshold = 0.6
            margin = 0.03

            def __init__(self, *args, **kwargs):
                pass

            def classify(self, text):
                from src.semantic_router.router import RouteDecision

                intent = verdicts.get(text, "wrong_intent")
                return RouteDecision(intent, "control", 0.9, 0.1, matched=intent is not None)

        monkeypatch.setattr(
            build_module, "build_anchor_set", lambda **kw: _DummyAnchors(), raising=True
        )
        monkeypatch.setattr("src.semantic_router.router.SemanticRouter", _Scripted)

    def test_exits_non_zero_when_probes_disagree(self, monkeypatch, tmp_path, capsys):
        from src.semantic_router import build as build_module

        self._stub_router(monkeypatch, verdicts={})

        exit_code = build_module.main(["--probe", "--out", str(tmp_path / "a.npz")])

        assert exit_code == 1
        assert "probes disagree" in capsys.readouterr().err

    def test_exits_zero_when_every_probe_agrees(self, monkeypatch, tmp_path):
        from src.semantic_router import build as build_module

        expected = {text: intent for text, intent in build_module.PROBE_UTTERANCES}
        self._stub_router(monkeypatch, verdicts=expected)

        assert build_module.main(["--probe", "--out", str(tmp_path / "a.npz")]) == 0


class _DummyAnchors:
    """Minimal stand-in so the CLI can save and summarise without embedding."""

    def save(self, path=None):
        from pathlib import Path

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"stub")
        return target

    def summary(self):
        return {"n_anchors": 1, "dim": 8, "model": "stub", "intents": {"affirm": 1}}
