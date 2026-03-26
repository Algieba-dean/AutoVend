"""
Tests for structured information extractors.

Uses mock LLM responses to test extraction logic without actual API calls.
"""

import json
from unittest.mock import MagicMock

from app.extractors.implicit_deductor import deduce_implicit_needs
from app.extractors.needs_extractor import extract_explicit_needs
from app.extractors.profile_extractor import extract_profile
from app.extractors.reservation_extractor import extract_reservation
from app.models.schemas import (
    ExplicitNeeds,
    ImplicitNeeds,
    ReservationInfo,
    UserProfile,
)


def _mock_llm(response_json: dict) -> MagicMock:
    """Create a mock LLM that returns a JSON string."""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(response_json)
    mock.complete.return_value = mock_response
    return mock


def _mock_llm_markdown(response_json: dict) -> MagicMock:
    """Create a mock LLM that returns JSON wrapped in markdown code block."""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.text = f"```json\n{json.dumps(response_json)}\n```"
    mock.complete.return_value = mock_response
    return mock


def _mock_llm_error() -> MagicMock:
    """Create a mock LLM that returns invalid JSON."""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is not valid JSON at all"
    mock.complete.return_value = mock_response
    return mock


# --- Profile Extractor Tests ---

class TestProfileExtractor:
    def test_extract_new_profile(self):
        llm = _mock_llm({
            "name": "John",
            "age": "35",
            "family_size": "4",
            "expertise": "beginner",
        })
        profile = extract_profile(llm, "My name is John, I'm 35 and have a family of 4.")
        assert profile.name == "John"
        assert profile.age == "35"
        assert profile.family_size == "4"
        assert profile.expertise == "beginner"

    def test_merge_with_existing(self):
        existing = UserProfile(name="John", phone_number="123456")
        llm = _mock_llm({"age": "35", "residence": "Beijing"})

        profile = extract_profile(llm, "I'm 35, living in Beijing", existing)
        assert profile.name == "John"  # Preserved
        assert profile.phone_number == "123456"  # Preserved
        assert profile.age == "35"  # New
        assert profile.residence == "Beijing"  # New

    def test_does_not_overwrite_with_empty(self):
        existing = UserProfile(name="John", age="35")
        llm = _mock_llm({"name": "", "age": ""})

        profile = extract_profile(llm, "Some conversation", existing)
        assert profile.name == "John"  # Not overwritten by empty
        assert profile.age == "35"

    def test_handles_markdown_response(self):
        llm = _mock_llm_markdown({"name": "Alice", "title": "Ms."})
        profile = extract_profile(llm, "I'm Ms. Alice")
        assert profile.name == "Alice"
        assert profile.title == "Ms."

    def test_handles_invalid_json(self):
        llm = _mock_llm_error()
        existing = UserProfile(name="John")
        profile = extract_profile(llm, "gibberish", existing)
        assert profile.name == "John"  # Falls back to existing

    def test_handles_none_current(self):
        llm = _mock_llm({"name": "Bob"})
        profile = extract_profile(llm, "I'm Bob", None)
        assert profile.name == "Bob"

    def test_ignores_unknown_fields(self):
        llm = _mock_llm({"name": "John", "favorite_color": "blue"})
        profile = extract_profile(llm, "I'm John, I like blue")
        assert profile.name == "John"


# --- Needs Extractor Tests ---

class TestNeedsExtractor:
    def test_extract_basic_needs(self):
        llm = _mock_llm({
            "brand": "Tesla",
            "prize": "40,000~60,000",
            "powertrain_type": "Battery Electric Vehicle",
        })
        needs = extract_explicit_needs(llm, "I want a Tesla EV around $50k")
        assert needs.brand == "Tesla"
        assert needs.prize == "40,000~60,000"
        assert needs.powertrain_type == "Battery Electric Vehicle"

    def test_merge_with_existing(self):
        existing = ExplicitNeeds(brand="Tesla", seat_layout="5-seat")
        llm = _mock_llm({"prize": "40,000~60,000"})

        needs = extract_explicit_needs(llm, "Budget around 50k", existing)
        assert needs.brand == "Tesla"  # Preserved
        assert needs.seat_layout == "5-seat"  # Preserved
        assert needs.prize == "40,000~60,000"  # New

    def test_handles_error_gracefully(self):
        llm = _mock_llm_error()
        existing = ExplicitNeeds(brand="BMW")
        needs = extract_explicit_needs(llm, "gibberish", existing)
        assert needs.brand == "BMW"  # Falls back

    def test_empty_conversation(self):
        llm = _mock_llm({})
        needs = extract_explicit_needs(llm, "")
        assert needs.brand == ""
        assert needs.prize == ""


# --- Implicit Deductor Tests ---

class TestImplicitDeductor:
    def test_deduce_from_profile(self):
        llm = _mock_llm({
            "family_friendliness": "High",
            "space": "Large",
            "safety": "High",
            "comfort_level": "High",
        })
        profile = UserProfile(family_size="5", expertise="beginner")
        explicit = ExplicitNeeds()

        implicit = deduce_implicit_needs(llm, profile, explicit)
        assert implicit.family_friendliness == "High"
        assert implicit.space == "Large"
        assert implicit.safety == "High"

    def test_merge_with_existing(self):
        existing = ImplicitNeeds(size="Medium", comfort_level="High")
        llm = _mock_llm({"safety": "High"})

        implicit = deduce_implicit_needs(
            llm, UserProfile(), ExplicitNeeds(), existing
        )
        assert implicit.size == "Medium"  # Preserved
        assert implicit.comfort_level == "High"  # Preserved
        assert implicit.safety == "High"  # New

    def test_handles_error_gracefully(self):
        llm = _mock_llm_error()
        existing = ImplicitNeeds(size="Large")
        implicit = deduce_implicit_needs(
            llm, UserProfile(), ExplicitNeeds(), existing
        )
        assert implicit.size == "Large"  # Falls back


# --- Reservation Extractor Tests ---

class TestReservationExtractor:
    def test_extract_reservation(self):
        llm = _mock_llm({
            "test_driver": "John",
            "reservation_date": "2024-03-15",
            "reservation_time": "14:00",
            "reservation_location": "Downtown Tesla Center",
            "reservation_phone_number": "13888888888",
        })
        res = extract_reservation(llm, "I'd like to test drive on March 15th at 2pm")
        assert res.test_driver == "John"
        assert res.reservation_date == "2024-03-15"
        assert res.reservation_time == "14:00"
        assert res.reservation_location == "Downtown Tesla Center"
        assert res.reservation_phone_number == "13888888888"

    def test_merge_with_existing(self):
        existing = ReservationInfo(
            test_driver="John", reservation_phone_number="13888888888"
        )
        llm = _mock_llm({
            "reservation_date": "2024-03-15",
            "reservation_time": "10:00",
        })

        res = extract_reservation(llm, "Let's do March 15 at 10am", existing)
        assert res.test_driver == "John"  # Preserved
        assert res.reservation_phone_number == "13888888888"  # Preserved
        assert res.reservation_date == "2024-03-15"  # New
        assert res.reservation_time == "10:00"  # New

    def test_handles_error_gracefully(self):
        llm = _mock_llm_error()
        existing = ReservationInfo(test_driver="John")
        res = extract_reservation(llm, "gibberish", existing)
        assert res.test_driver == "John"  # Falls back

    def test_handles_markdown_response(self):
        llm = _mock_llm_markdown({
            "test_driver": "Alice",
            "reservation_location": "BMW Center",
        })
        res = extract_reservation(llm, "I'm Alice, at BMW center")
        assert res.test_driver == "Alice"
        assert res.reservation_location == "BMW Center"
