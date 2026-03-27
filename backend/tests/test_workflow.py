"""
Tests for the stage workflow engine, stages, memory, and response generator.
"""

import json
from unittest.mock import MagicMock

from agent.memory import ChatMemoryManager
from app.models.schemas import (
    ExplicitNeeds,
    ReservationInfo,
    Stage,
    UserProfile,
    VehicleNeeds,
)
from agent.response_generator import (
    _format_matched_cars,
    _get_missing_needs_fields,
    _get_missing_profile_fields,
    _get_missing_reservation_fields,
    generate_response,
)
from app.workflow.stage_workflow import SessionState, StageWorkflow
from agent.stages import (
    STAGE_ORDER,
    STAGE_TRANSITIONS,
    can_transition,
    determine_next_stage,
    should_advance_to_car_selection,
    should_advance_to_confirmation,
    should_advance_to_farewell,
    should_advance_to_needs,
    should_advance_to_reservation,
)

# ============================================================
# Stage transition tests
# ============================================================


class TestCanTransition:
    def test_valid_transitions(self):
        assert can_transition(Stage.WELCOME, Stage.PROFILE_ANALYSIS)
        assert can_transition(Stage.PROFILE_ANALYSIS, Stage.NEEDS_ANALYSIS)
        assert can_transition(Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION)
        assert can_transition(Stage.CAR_SELECTION, Stage.RESERVATION_4S)
        assert can_transition(Stage.RESERVATION_4S, Stage.RESERVATION_CONFIRMATION)
        assert can_transition(Stage.RESERVATION_CONFIRMATION, Stage.FAREWELL)

    def test_invalid_transitions(self):
        assert not can_transition(Stage.WELCOME, Stage.FAREWELL)
        assert not can_transition(Stage.PROFILE_ANALYSIS, Stage.CAR_SELECTION)
        assert not can_transition(Stage.FAREWELL, Stage.WELCOME)

    def test_backwards_allowed_for_car_selection(self):
        assert can_transition(Stage.CAR_SELECTION, Stage.NEEDS_ANALYSIS)

    def test_backwards_allowed_for_reservation_confirmation(self):
        assert can_transition(Stage.RESERVATION_CONFIRMATION, Stage.RESERVATION_4S)

    def test_farewell_has_no_transitions(self):
        assert STAGE_TRANSITIONS[Stage.FAREWELL] == set()


class TestStageOrder:
    def test_has_all_stages(self):
        assert len(STAGE_ORDER) == 7
        assert STAGE_ORDER[0] == Stage.WELCOME
        assert STAGE_ORDER[-1] == Stage.FAREWELL


class TestShouldAdvanceFunctions:
    def test_advance_to_needs_with_info(self):
        profile = UserProfile(name="John")
        assert should_advance_to_needs(profile)

    def test_advance_to_needs_without_info(self):
        profile = UserProfile()
        assert not should_advance_to_needs(profile)

    def test_advance_to_car_selection_enough_fields(self):
        needs = VehicleNeeds(explicit=ExplicitNeeds(brand="Tesla", prize="40,000~60,000"))
        assert should_advance_to_car_selection(needs)

    def test_advance_to_car_selection_not_enough(self):
        needs = VehicleNeeds(explicit=ExplicitNeeds(brand="Tesla"))
        assert not should_advance_to_car_selection(needs)

    def test_advance_to_reservation_with_cars(self):
        assert should_advance_to_reservation([{"car_model": "Tesla-Model Y"}])

    def test_advance_to_reservation_no_cars(self):
        assert not should_advance_to_reservation([])

    def test_advance_to_confirmation(self):
        res = ReservationInfo(
            reservation_date="2024-03-15",
            reservation_time="14:00",
            reservation_location="Downtown",
        )
        assert should_advance_to_confirmation(res)

    def test_advance_to_confirmation_incomplete(self):
        res = ReservationInfo(reservation_date="2024-03-15")
        assert not should_advance_to_confirmation(res)

    def test_advance_to_farewell(self):
        res = ReservationInfo(
            test_driver="John",
            reservation_date="2024-03-15",
            reservation_time="14:00",
            reservation_location="Downtown",
            reservation_phone_number="13888888888",
        )
        assert should_advance_to_farewell(res)

    def test_advance_to_farewell_incomplete(self):
        res = ReservationInfo(test_driver="John")
        assert not should_advance_to_farewell(res)


class TestDetermineNextStage:
    def test_welcome_always_advances(self):
        result = determine_next_stage(
            Stage.WELCOME, UserProfile(), VehicleNeeds(), [], ReservationInfo()
        )
        assert result == Stage.PROFILE_ANALYSIS

    def test_profile_stays_without_info(self):
        result = determine_next_stage(
            Stage.PROFILE_ANALYSIS, UserProfile(), VehicleNeeds(), [], ReservationInfo()
        )
        assert result == Stage.PROFILE_ANALYSIS

    def test_profile_advances_with_name(self):
        result = determine_next_stage(
            Stage.PROFILE_ANALYSIS,
            UserProfile(name="John"),
            VehicleNeeds(),
            [],
            ReservationInfo(),
        )
        assert result == Stage.NEEDS_ANALYSIS

    def test_needs_advances_with_enough_info(self):
        needs = VehicleNeeds(explicit=ExplicitNeeds(brand="Tesla", powertrain_type="BEV"))
        result = determine_next_stage(
            Stage.NEEDS_ANALYSIS, UserProfile(), needs, [], ReservationInfo()
        )
        assert result == Stage.CAR_SELECTION


# ============================================================
# Chat memory tests
# ============================================================


class TestChatMemoryManager:
    def test_create_and_get(self):
        mgr = ChatMemoryManager()
        buf = mgr.get_or_create("s1")
        assert buf is not None
        assert mgr.has_session("s1")

    def test_add_messages(self):
        mgr = ChatMemoryManager()
        mgr.add_user_message("s1", "Hello")
        mgr.add_assistant_message("s1", "Hi there!")
        history = mgr.get_history("s1")
        assert len(history) == 2

    def test_get_history_as_text(self):
        mgr = ChatMemoryManager()
        mgr.add_user_message("s1", "Hello")
        mgr.add_assistant_message("s1", "Hi!")
        text = mgr.get_history_as_text("s1")
        assert "User: Hello" in text
        assert "Assistant: Hi!" in text

    def test_clear_session(self):
        mgr = ChatMemoryManager()
        mgr.add_user_message("s1", "Hello")
        mgr.clear_session("s1")
        assert not mgr.has_session("s1")

    def test_active_sessions(self):
        mgr = ChatMemoryManager()
        mgr.get_or_create("s1")
        mgr.get_or_create("s2")
        assert set(mgr.active_sessions) == {"s1", "s2"}

    def test_clear_nonexistent_session(self):
        mgr = ChatMemoryManager()
        mgr.clear_session("nonexistent")  # Should not raise


# ============================================================
# Response generator helper tests
# ============================================================


class TestResponseGeneratorHelpers:
    def test_missing_profile_fields(self):
        profile = UserProfile(name="John")
        missing = _get_missing_profile_fields(profile)
        assert "name" not in missing
        assert "age" in missing

    def test_complete_profile(self):
        profile = UserProfile(
            phone_number="123",
            name="John",
            title="Mr.",
            age="35",
            target_driver="self",
            expertise="beginner",
            family_size="4",
            price_sensitivity="medium",
            residence="Beijing",
            parking_conditions="garage",
        )
        missing = _get_missing_profile_fields(profile)
        assert "None" in missing

    def test_missing_needs_fields(self):
        needs = VehicleNeeds(explicit=ExplicitNeeds(brand="Tesla"))
        missing = _get_missing_needs_fields(needs)
        assert "brand" not in missing
        assert "prize" in missing

    def test_missing_reservation_fields(self):
        res = ReservationInfo(test_driver="John")
        missing = _get_missing_reservation_fields(res)
        assert "test_driver" not in missing
        assert "reservation_date" in missing

    def test_format_matched_cars_empty(self):
        result = _format_matched_cars([])
        assert "No vehicles" in result

    def test_format_matched_cars_with_data(self):
        cars = [
            {"car_model": "Tesla-Model Y", "score": 0.95, "text_snippet": "Electric SUV"},
            {"car_model": "BYD-Seal", "score": 0.88, "text_snippet": "EV sedan"},
        ]
        result = _format_matched_cars(cars)
        assert "Tesla-Model Y" in result
        assert "BYD-Seal" in result

    def test_generate_response_success(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Welcome! How can I help you today?"
        mock_llm.complete.return_value = mock_response

        result = generate_response(
            mock_llm,
            Stage.WELCOME,
            "",
            UserProfile(),
            VehicleNeeds(),
            [],
            ReservationInfo(),
        )
        assert "Welcome" in result

    def test_generate_response_error_fallback(self):
        mock_llm = MagicMock()
        mock_llm.complete.side_effect = Exception("API error")

        result = generate_response(
            mock_llm,
            Stage.WELCOME,
            "",
            UserProfile(),
            VehicleNeeds(),
            [],
            ReservationInfo(),
        )
        assert "apologize" in result


# ============================================================
# Session state tests
# ============================================================


class TestSessionState:
    def test_default_state(self):
        state = SessionState("s1")
        assert state.session_id == "s1"
        assert state.stage == Stage.WELCOME
        assert state.profile.name == ""
        assert state.matched_cars == []

    def test_with_profile(self):
        profile = UserProfile(name="John")
        state = SessionState("s1", profile)
        assert state.profile.name == "John"

    def test_to_dict(self):
        state = SessionState("s1")
        d = state.to_dict()
        assert d["session_id"] == "s1"
        assert d["stage"] == "welcome"
        assert "profile" in d
        assert "needs" in d


# ============================================================
# StageWorkflow integration tests (mock LLM)
# ============================================================


def _mock_llm_for_workflow() -> MagicMock:
    """Create a mock LLM that returns appropriate JSON for each extractor call."""
    mock = MagicMock()

    def side_effect(prompt):
        resp = MagicMock()
        if "profile" in prompt.lower() and "extract" in prompt.lower():
            resp.text = json.dumps({"name": "John", "age": "35"})
        elif "explicit" in prompt.lower() or "vehicle requirements" in prompt.lower():
            resp.text = json.dumps({"brand": "Tesla", "prize": "40,000~60,000"})
        elif "implicit" in prompt.lower() or "deduce" in prompt.lower():
            resp.text = json.dumps({"comfort_level": "High"})
        elif "reservation" in prompt.lower() and "extract" in prompt.lower():
            resp.text = json.dumps({"reservation_date": "2024-03-15"})
        else:
            resp.text = "Hello! Welcome to AutoVend. How can I help you today?"
        return resp

    mock.complete.side_effect = side_effect
    return mock


class TestStageWorkflow:
    def test_create_session(self):
        llm = MagicMock()
        wf = StageWorkflow(llm)
        state = wf.create_session("s1")
        assert state.session_id == "s1"
        assert state.stage == Stage.WELCOME

    def test_get_session(self):
        llm = MagicMock()
        wf = StageWorkflow(llm)
        wf.create_session("s1")
        assert wf.get_session("s1") is not None
        assert wf.get_session("nonexistent") is None

    def test_end_session(self):
        llm = MagicMock()
        wf = StageWorkflow(llm)
        wf.create_session("s1")
        wf.end_session("s1")
        assert wf.get_session("s1") is None

    def test_process_message_creates_session(self):
        llm = _mock_llm_for_workflow()
        wf = StageWorkflow(llm)
        response = wf.process_message("s1", "Hello")
        assert response.message.content == "Hello"
        assert response.response.content  # Non-empty response
        assert response.stage.current_stage  # Has a stage

    def test_process_message_advances_from_welcome(self):
        llm = _mock_llm_for_workflow()
        wf = StageWorkflow(llm)
        response = wf.process_message("s1", "Hi, I'm looking for a car")
        # Should advance from WELCOME to PROFILE_ANALYSIS
        assert response.stage.current_stage == Stage.PROFILE_ANALYSIS.value

    def test_process_message_returns_valid_chat_response(self):
        llm = _mock_llm_for_workflow()
        wf = StageWorkflow(llm)
        response = wf.process_message("s1", "Hello")
        assert response.message.sender_type == "user"
        assert response.response.sender_type == "system"
        assert response.response.sender_id == "AutoVend"
        assert response.profile is not None
        assert response.needs is not None
