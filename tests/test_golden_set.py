"""
Tests for the golden set.

The golden set is what every quoted retrieval number rests on, so these assert
its *integrity* — unique ids, resolvable predicates, no accidental empties —
rather than any particular score.
"""

import sqlite3

import pytest

from src.eval.golden_set import (
    ALL_SPECS,
    GoldenQuery,
    load_golden_set,
    resolve_specs,
    write_golden_set,
)


@pytest.fixture(scope="module")
def catalogue_path(tmp_path_factory):
    """A miniature catalogue, so these tests never depend on the real index."""
    path = tmp_path_factory.mktemp("golden") / "vehicles.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE vehicles ("
        "car_model TEXT, vehicle_category_bottom TEXT, brand TEXT, prize TEXT, "
        "powertrain_type TEXT, seat_layout TEXT, drive_type TEXT, design_style TEXT, "
        "driving_range TEXT, autonomous_driving_level TEXT, trunk_volume TEXT, "
        "city_commuting TEXT, highway_long_distance TEXT, cargo_capability TEXT, "
        "off_road_capability TEXT, size TEXT, family_friendliness TEXT, "
        "comfort_level TEXT, smartness TEXT, energy_consumption_level TEXT)"
    )
    conn.execute(
        "INSERT INTO vehicles VALUES "
        "('BMW-X3', 'mid-size suv', 'bmw', '40,000 ~ 60,000', 'gasoline engine', "
        "'5-seat', 'all-wheel drive', 'sporty', '400-800km', 'l2', '400~500l', "
        "'yes', 'yes', 'yes', 'low', 'medium', 'high', 'high', 'high', 'medium')"
    )
    conn.commit()
    conn.close()
    return str(path)


class TestSpecs:
    def test_ids_are_unique(self):
        ids = [s.id for s in ALL_SPECS]

        assert len(ids) == len(set(ids)), "duplicate ids would silently overwrite results"

    def test_queries_are_unique(self):
        queries = [s.query for s in ALL_SPECS]

        assert len(queries) == len(set(queries))

    def test_every_spec_has_a_predicate_and_tags(self):
        for spec in ALL_SPECS:
            assert spec.where.strip(), f"{spec.id} has no ground-truth predicate"
            assert spec.tags, f"{spec.id} has no tags — it cannot appear in any breakdown"

    def test_predicates_never_reference_the_system_under_test(self):
        """
        Ground truth must come from the catalogue, not from QueryParser or
        FilterEngine. A predicate mentioning either would grade the system
        against its own output.
        """
        for spec in ALL_SPECS:
            lowered = spec.where.lower()
            assert "parser" not in lowered
            assert "filter" not in lowered

    def test_covers_the_major_label_families(self):
        tags = {tag for spec in ALL_SPECS for tag in spec.tags}

        assert {"category", "brand", "powertrain", "price", "ambiguous", "zh"} <= tags

    def test_marks_known_gaps_explicitly(self):
        """
        Queries needing knowledge the vocabulary lacks (country of origin,
        'affordable') are kept on purpose — they are the headroom, and tagging
        them keeps that visible in the per-tag breakdown.
        """
        gaps = [s for s in ALL_SPECS if "known-gap" in s.tags]

        assert len(gaps) >= 5
        assert all(s.note or "world-knowledge" in s.tags or "paraphrase" in s.tags for s in gaps)


class TestResolveSpecs:
    def test_resolves_matching_predicates_against_the_catalogue(self, catalogue_path):
        resolved = resolve_specs(catalogue_path)

        by_id = {q.id: q for q in resolved}
        assert by_id["cat02"].relevant_car_models == ["BMW-X3"]  # Mid-Size SUV
        assert by_id["brd02"].relevant_car_models == ["BMW-X3"]  # BMW

    def test_drops_specs_that_match_nothing(self, catalogue_path):
        """An empty relevant set makes recall undefined, so it must not survive."""
        resolved = resolve_specs(catalogue_path)

        assert all(q.relevant_car_models for q in resolved)
        assert len(resolved) < len(ALL_SPECS)

    def test_results_are_sorted_for_stable_diffs(self, catalogue_path):
        for query in resolve_specs(catalogue_path):
            assert query.relevant_car_models == sorted(query.relevant_car_models)


class TestPersistence:
    def test_round_trips_through_jsonl(self, tmp_path, catalogue_path):
        target = tmp_path / "golden_set.jsonl"

        write_golden_set(target, catalogue_path)
        loaded = load_golden_set(target)

        assert loaded
        assert all(isinstance(q, GoldenQuery) for q in loaded)
        assert {q.id for q in loaded} == {q.id for q in resolve_specs(catalogue_path)}

    def test_relevant_set_is_a_set(self):
        query = GoldenQuery(id="q", query="x", relevant_car_models=["a", "a", "b"], tags=[])

        assert query.relevant_set == {"a", "b"}
