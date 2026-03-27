"""
Tests for the TOML vehicle data parser.
"""

from pathlib import Path

import pytest
import toml

from app.ingestion.toml_parser import (
    METADATA_FIELDS,
    _build_text_from_toml,
    _extract_metadata,
    parse_all_vehicles,
    parse_vehicle_toml,
)

# --- Sample TOML data ---

SAMPLE_VEHICLE_DATA = {
    "title": "CarLabels",
    "car_model": "Tesla-Model Y Compact Electric SUV",
    "PriciseLabels": {
        "prize": "40,000~60,000",
        "prize_comments": "Priced between $43,990 and $52,490 USD.",
        "vehicle_category_bottom": "Compact SUV",
        "vehicle_category_bottom_comments": "Classified as a compact electric crossover SUV.",
        "brand": "Tesla",
        "brand_comments": "American electric vehicle company.",
        "powertrain_type": "Battery Electric Vehicle",
        "powertrain_type_comments": "Pure electric vehicle with no ICE.",
        "design_style": "Sporty",
        "design_style_comments": "Minimalist design with aerodynamic lines.",
        "drive_type": "All-Wheel Drive",
        "drive_type_comments": "Standard dual motor setup.",
        "seat_layout": "5-seat",
        "seat_layout_comments": "Standard config with optional 7-seat.",
        "autonomous_driving_level": "L2",
        "autonomous_driving_level_comments": "Tesla Autopilot provides L2.",
        "ABS": "Yes",
        "ABS_comments": "Standard ABS with EBD.",
    },
    "AmbiguousLabels": {
        "size": "Medium",
        "size_comments": "Compact SUV dimensions.",
        "family_friendliness": "High",
        "family_friendliness_comments": "Excellent safety ratings for families.",
        "comfort_level": "High",
        "comfort_level_comments": "Premium interior materials.",
        "smartness": "High",
        "smartness_comments": "Industry-leading tech features.",
        "energy_consumption_level": "Low",
        "energy_consumption_level_comments": "Very efficient for its size.",
    },
    "KeyDetails": {
        "key_details": "The Tesla Model Y is an all-electric compact SUV.",
        "key_details_comments": "Best-selling model globally with impressive range.",
    },
}

MINIMAL_VEHICLE_DATA = {
    "title": "CarLabels",
    "car_model": "TestBrand-TestModel",
    "PriciseLabels": {
        "brand": "TestBrand",
    },
    "AmbiguousLabels": {},
    "KeyDetails": {},
}


def _write_toml(dir_path: Path, filename: str, data: dict) -> Path:
    """Helper to write a TOML file."""
    file_path = dir_path / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        toml.dump(data, f)
    return file_path


class TestBuildTextFromToml:
    """Tests for _build_text_from_toml."""

    def test_full_vehicle(self):
        text = _build_text_from_toml(SAMPLE_VEHICLE_DATA)
        assert "Tesla-Model Y Compact Electric SUV" in text
        assert "all-electric compact SUV" in text
        assert "Best-selling model globally" in text
        assert "American electric vehicle company" in text
        assert "Minimalist design" in text

    def test_minimal_vehicle(self):
        text = _build_text_from_toml(MINIMAL_VEHICLE_DATA)
        assert "TestBrand-TestModel" in text

    def test_empty_data(self):
        text = _build_text_from_toml({})
        assert "Unknown Vehicle" in text

    def test_comments_included(self):
        text = _build_text_from_toml(SAMPLE_VEHICLE_DATA)
        # All comments should be in the text
        assert "Priced between" in text
        assert "Compact SUV dimensions" in text
        assert "Excellent safety ratings" in text

    def test_no_duplicate_text(self):
        text = _build_text_from_toml(SAMPLE_VEHICLE_DATA)
        lines = text.split("\n")
        # Each line should be unique
        assert len(lines) == len(set(lines))


class TestExtractMetadata:
    """Tests for _extract_metadata."""

    def test_full_metadata(self):
        meta = _extract_metadata(SAMPLE_VEHICLE_DATA)
        assert meta["car_model"] == "Tesla-Model Y Compact Electric SUV"
        assert meta["brand"] == "Tesla"
        assert meta["prize"] == "40,000~60,000"
        assert meta["powertrain_type"] == "Battery Electric Vehicle"
        assert meta["vehicle_category_bottom"] == "Compact SUV"
        assert meta["design_style"] == "Sporty"
        assert meta["drive_type"] == "All-Wheel Drive"
        assert meta["seat_layout"] == "5-seat"
        assert meta["autonomous_driving_level"] == "L2"
        assert meta["size"] == "Medium"
        assert meta["family_friendliness"] == "High"
        assert meta["comfort_level"] == "High"
        assert meta["smartness"] == "High"
        assert meta["energy_consumption_level"] == "Low"

    def test_minimal_metadata(self):
        meta = _extract_metadata(MINIMAL_VEHICLE_DATA)
        assert meta["car_model"] == "TestBrand-TestModel"
        assert meta["brand"] == "TestBrand"
        # Empty fields should not be present
        assert "prize" not in meta
        assert "powertrain_type" not in meta

    def test_empty_data(self):
        meta = _extract_metadata({})
        assert len(meta) == 0

    def test_only_metadata_fields_included(self):
        meta = _extract_metadata(SAMPLE_VEHICLE_DATA)
        # Should not contain comment fields or non-metadata fields
        for key in meta:
            assert not key.endswith("_comments")
            assert key == "car_model" or key in METADATA_FIELDS


class TestParseVehicleToml:
    """Tests for parse_vehicle_toml."""

    def test_valid_file(self, tmp_path):
        file_path = _write_toml(tmp_path, "test.toml", SAMPLE_VEHICLE_DATA)
        doc = parse_vehicle_toml(file_path)
        assert doc is not None
        assert "Tesla-Model Y" in doc.text
        assert doc.metadata["brand"] == "Tesla"
        assert doc.metadata["source_file"] == "test.toml"

    def test_minimal_file(self, tmp_path):
        file_path = _write_toml(tmp_path, "minimal.toml", MINIMAL_VEHICLE_DATA)
        doc = parse_vehicle_toml(file_path)
        assert doc is not None
        assert doc.metadata["car_model"] == "TestBrand-TestModel"

    def test_missing_car_model(self, tmp_path):
        data = {"title": "CarLabels", "PriciseLabels": {"brand": "Test"}}
        file_path = _write_toml(tmp_path, "no_model.toml", data)
        doc = parse_vehicle_toml(file_path)
        assert doc is None

    def test_invalid_toml(self, tmp_path):
        file_path = tmp_path / "invalid.toml"
        file_path.write_text("this is not valid {{{ toml")
        doc = parse_vehicle_toml(file_path)
        assert doc is None

    def test_source_file_excluded_from_embedding(self, tmp_path):
        file_path = _write_toml(tmp_path, "test.toml", SAMPLE_VEHICLE_DATA)
        doc = parse_vehicle_toml(file_path)
        assert "source_file" in doc.excluded_embed_metadata_keys
        assert "source_file" in doc.excluded_llm_metadata_keys


class TestParseAllVehicles:
    """Tests for parse_all_vehicles."""

    def test_multiple_brands(self, tmp_path):
        # Create brand directories with vehicle files
        _write_toml(tmp_path / "Tesla", "Tesla-Model Y.toml", SAMPLE_VEHICLE_DATA)

        data2 = {**MINIMAL_VEHICLE_DATA, "car_model": "BYD-Seal EV"}
        data2["PriciseLabels"] = {"brand": "BYD"}
        _write_toml(tmp_path / "BYD", "BYD-Seal EV.toml", data2)

        docs = parse_all_vehicles(str(tmp_path))
        assert len(docs) == 2
        brands = {doc.metadata.get("brand") for doc in docs}
        assert brands == {"Tesla", "BYD"}

    def test_skips_car_labels(self, tmp_path):
        _write_toml(tmp_path, "CarLabels.toml", {"title": "CarLabels"})
        _write_toml(tmp_path / "Tesla", "Tesla-Model Y.toml", SAMPLE_VEHICLE_DATA)
        docs = parse_all_vehicles(str(tmp_path))
        assert len(docs) == 1

    def test_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        docs = parse_all_vehicles(str(empty_dir))
        assert len(docs) == 0

    def test_nonexistent_directory(self):
        docs = parse_all_vehicles("/nonexistent/path")
        assert len(docs) == 0

    def test_skips_invalid_files(self, tmp_path):
        _write_toml(tmp_path / "Good", "good.toml", SAMPLE_VEHICLE_DATA)
        # Invalid file
        bad_path = tmp_path / "Bad" / "bad.toml"
        bad_path.parent.mkdir(parents=True)
        bad_path.write_text("not valid toml {{{")
        docs = parse_all_vehicles(str(tmp_path))
        assert len(docs) == 1

    def test_real_data_directory(self):
        """Integration test: parse actual vehicle data if available."""
        real_dir = Path(__file__).resolve().parent.parent.parent / "DataInUse" / "VehicleData"
        if not real_dir.exists():
            pytest.skip("Real vehicle data not available")

        docs = parse_all_vehicles(str(real_dir))
        assert len(docs) > 100  # Should have many vehicles
        # Verify all docs have required metadata
        for doc in docs:
            assert "car_model" in doc.metadata
            assert doc.text  # Non-empty text
