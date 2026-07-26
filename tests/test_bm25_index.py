"""Tests for the BM25 lexical index."""

import pytest

from src.retrieval.bm25_index import BM25Index, _document_text, tokenize


class TestTokenize:
    def test_splits_latin_on_non_alphanumerics(self):
        assert tokenize("BMW-X3 40 TFSI") == ["bmw", "x3", "40", "tfsi"]

    def test_lowercases(self):
        assert tokenize("Mercedes-Benz") == ["mercedes", "benz"]

    def test_handles_mixed_chinese_and_latin(self):
        tokens = tokenize("中型纯电SUV")

        assert "suv" in tokens
        assert any("一" <= ch <= "鿿" for token in tokens for ch in token)

    def test_empty_text_yields_no_tokens(self):
        assert tokenize("") == []
        assert tokenize("   !!!  ") == []


class TestDocumentText:
    def test_repeats_the_car_model(self):
        """
        Exact-match weighting: a query naming a model should outrank cars that
        merely share its labels, which is the case BM25 exists to cover.
        """
        text = _document_text({"car_model": "BMW-X3", "brand": "bmw"})

        assert text.split().count("BMW-X3") == 2

    def test_drops_low_signal_columns(self):
        text = _document_text({"car_model": "X", "abs": "yes", "esp": "yes", "brand": "bmw"})

        assert "yes" not in text
        assert "bmw" in text

    def test_drops_empty_and_placeholder_values(self):
        text = _document_text(
            {"car_model": "X", "brand": "", "color": "none", "seat_layout": "5-seat"}
        )

        assert "none" not in text
        assert "5-seat" in text


def _build(car_models):
    corpus = [
        tokenize(_document_text({"car_model": m, "brand": m.split("-")[0].lower()}))
        for m in car_models
    ]
    return BM25Index(car_models, corpus)


@pytest.fixture
def index():
    """
    A corpus large enough for BM25's IDF to stay positive.

    BM25 assigns idf = log((N - df + 0.5) / (df + 0.5)), which hits zero at
    df/N = 0.5 and goes negative beyond it. Two BMWs out of four documents
    lands exactly on that boundary and scores every result at 0 — an artifact
    of a toy corpus, not of the index. See test_common_term_in_a_tiny_corpus.
    """
    return _build(
        ["BMW-X3", "BMW-i7"] + [f"Toyota-Model{i}" for i in range(8)] + ["NIO-ES6", "Audi-Q5"]
    )


class TestBM25Index:
    def test_ranks_exact_model_matches_first(self, index):
        assert index.search("Q5", top_k=1)[0][0] == "Audi-Q5"

    def test_brand_query_returns_that_brand(self, index):
        models = [m for m, _ in index.search("BMW", top_k=4)]

        assert set(models) == {"BMW-X3", "BMW-i7"}

    def test_common_term_in_a_tiny_corpus_scores_zero(self):
        """
        Documents BM25's IDF floor rather than guarding against it.

        At df/N >= 0.5 the IDF collapses to zero, so every document scores 0 and
        the >0 filter drops them all. This only bites on toy corpora: in the
        1281-vehicle catalogue even 'suv' (~800 docs) keeps idf ≈ 1.25 because
        the document text carries many other terms.
        """
        tiny = _build(["BMW-X3", "BMW-i7", "Toyota-Corolla", "NIO-ES6"])

        assert tiny.search("BMW", top_k=4) == []

    def test_drops_zero_score_results(self, index):
        """
        A zero score means no query term occurred in the document — keeping
        those would pad the result list with arbitrary cars.
        """
        assert index.search("submarine", top_k=4) == []

    def test_respects_top_k(self, index):
        assert len(index.search("BMW", top_k=1)) == 1

    def test_empty_query_returns_nothing(self, index):
        assert index.search("", top_k=4) == []

    def test_scores_are_descending(self, index):
        scores = [score for _, score in index.search("BMW X3", top_k=4)]

        assert scores == sorted(scores, reverse=True)

    def test_round_trips_through_disk(self, index, tmp_path):
        path = tmp_path / "bm25.pkl"
        index.save(path)

        reloaded = BM25Index.load(path)

        assert reloaded.car_models == index.car_models
        assert reloaded.search("BMW", top_k=2) == index.search("BMW", top_k=2)

    def test_rebuilds_when_the_cached_index_is_corrupt(self, tmp_path, monkeypatch):
        path = tmp_path / "bm25.pkl"
        path.write_bytes(b"not a pickle")

        built = BM25Index(["X"], [["x"]])
        monkeypatch.setattr(BM25Index, "build", classmethod(lambda cls: built))

        assert BM25Index.load_or_build(path).car_models == ["X"]
