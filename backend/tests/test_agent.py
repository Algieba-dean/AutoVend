"""
Comprehensive unit tests for the Agent package.

Tests SalesAgent, extractors, stages, memory, and response generator
using mock LLM — no actual LLM calls or backend dependencies.
"""

import json
from unittest.mock import MagicMock

import pytest

from agent.extractors.base import extract_with_llm, merge_model, parse_llm_json
from agent.extractors.implicit_deductor import deduce_implicit_needs
from agent.extractors.needs_extractor import extract_explicit_needs
from agent.extractors.profile_extractor import extract_profile
from agent.extractors.reservation_extractor import extract_reservation
from agent.memory import ChatMemoryManager
from agent.response_generator import (
    _format_matched_cars,
    _get_missing_needs_fields,
    _get_missing_profile_fields,
    _get_missing_reservation_fields,
    generate_response,
)
from agent.sales_agent import SalesAgent
from agent.schemas import (
    AgentInput,
    AgentResult,
    ExplicitNeeds,
    ImplicitNeeds,
    ReservationInfo,
    SessionState,
    Stage,
    UserProfile,
    VehicleNeeds,
)
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

# ── Helpers ────────────────────────────────────────────────────


def _mock_llm(response_text: str = "{}") -> MagicMock:
    """Create a mock LLM that returns the given JSON text."""
    mock = MagicMock()
    resp = MagicMock()
    resp.text = response_text
    mock.complete.return_value = resp
    return mock


def _mock_llm_dynamic() -> MagicMock:
    """Create a mock LLM that returns context-appropriate responses."""
    mock = MagicMock()

    def side_effect(prompt):
        resp = MagicMock()
        p = prompt.lower()
        # Global extraction prompt (all four categories in one call)
        if "category 1" in p and "category 2" in p and "category 4" in p:
            resp.text = json.dumps({
                "profile": {"name": "TestUser", "age": "30"},
                "explicit": {"brand": "Tesla", "powertrain_type": "EV"},
                "implicit": {"comfort_level": "High", "safety": "High"},
                "reservation": {
                    "reservation_date": "2024-06-01",
                    "reservation_time": "10:00",
                    "reservation_location": "East Store"
                },
            })
        elif "profile" in p and "extract" in p:
            resp.text = json.dumps({"name": "TestUser", "age": "30"})
        elif "needs" in p or "vehicle" in p:
            resp.text = json.dumps({"brand": "Tesla", "powertrain_type": "EV"})
        elif "implicit" in p or "deduce" in p:
            resp.text = json.dumps({"comfort_level": "High", "safety": "High"})
        elif "reservation" in p:
            resp.text = json.dumps({
                "reservation_date": "2024-06-01",
                "reservation_time": "10:00",
                "reservation_location": "East Store"
            })
        else:
            resp.text = "Hello! Welcome to AutoVend."
        return resp

    mock.complete.side_effect = side_effect
    return mock


# ── Schema Tests ───────────────────────────────────────────────


class TestSchemas:
    def test_session_state_defaults(self):
        s = SessionState(session_id="test-1")
        assert s.stage == Stage.WELCOME
        assert s.profile.name == ""
        assert s.matched_cars == []

    def test_session_state_with_profile(self):
        p = UserProfile(name="Alice", phone_number="123")
        s = SessionState(session_id="test-2", profile=p)
        assert s.profile.name == "Alice"

    def test_agent_input(self):
        ai = AgentInput(
            session_state=SessionState(session_id="s1"),
            user_message="Hello",
            retrieved_cars=[{"car_model": "Tesla"}],
        )
        assert ai.user_message == "Hello"
        assert len(ai.retrieved_cars) == 1

    def test_agent_result(self):
        ar = AgentResult(
            session_state=SessionState(session_id="s1"),
            response_text="Hi there!",
            stage_changed=True,
        )
        assert ar.response_text == "Hi there!"
        assert ar.stage_changed is True

    def test_stage_enum_values(self):
        assert Stage.WELCOME.value == "welcome"
        assert Stage.FAREWELL.value == "farewell"


# ── Extractor Base Tests ──────────────────────────────────────


class TestExtractorBase:
    def test_parse_raw_json(self):
        assert parse_llm_json('{"name": "John"}') == {"name": "John"}

    def test_parse_markdown_json(self):
        assert parse_llm_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_parse_plain_code_block(self):
        assert parse_llm_json('```\n{"a": 1}\n```') == {"a": 1}

    def test_parse_invalid_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json("not json")

    def test_merge_model_adds_new(self):
        p = UserProfile(name="John")
        result = merge_model(p, {"age": "35"})
        assert result.name == "John"
        assert result.age == "35"

    def test_merge_model_ignores_empty(self):
        p = UserProfile(name="John")
        result = merge_model(p, {"name": "", "age": ""})
        assert result.name == "John"

    def test_merge_model_overwrites(self):
        p = UserProfile(name="John")
        result = merge_model(p, {"name": "Jane"})
        assert result.name == "Jane"

    def test_merge_model_ignores_unknown_keys(self):
        p = UserProfile(name="John")
        result = merge_model(p, {"unknown_key": "value"})
        assert result.name == "John"

    def test_extract_with_llm_success(self):
        llm = _mock_llm('{"name": "Alice"}')
        result = extract_with_llm(llm, "prompt", UserProfile())
        assert result.name == "Alice"

    def test_extract_with_llm_failure_returns_current(self):
        llm = _mock_llm("not json")
        current = UserProfile(name="Safe")
        result = extract_with_llm(llm, "prompt", current)
        assert result.name == "Safe"

    def test_extract_with_llm_exception_returns_current(self):
        llm = MagicMock()
        llm.complete.side_effect = RuntimeError("LLM down")
        current = UserProfile(name="Safe")
        result = extract_with_llm(llm, "prompt", current)
        assert result.name == "Safe"


# ── Individual Extractor Tests ─────────────────────────────────


class TestProfileExtractor:
    def test_extract_from_empty(self):
        llm = _mock_llm('{"name": "Bob", "age": "25"}')
        result = extract_profile(llm, "conversation text")
        assert result.name == "Bob"
        assert result.age == "25"

    def test_extract_merge_existing(self):
        llm = _mock_llm('{"age": "30"}')
        existing = UserProfile(name="Alice")
        result = extract_profile(llm, "text", existing)
        assert result.name == "Alice"
        assert result.age == "30"

    def test_extract_default_on_none(self):
        llm = _mock_llm("{}")
        result = extract_profile(llm, "text", None)
        assert result.name == ""


class TestNeedsExtractor:
    def test_extract_needs(self):
        llm = _mock_llm('{"brand": "BMW", "powertrain_type": "EV"}')
        result = extract_explicit_needs(llm, "text")
        assert result.brand == "BMW"
        assert result.powertrain_type == "EV"

    def test_extract_merge_existing(self):
        llm = _mock_llm('{"prize": "200000"}')
        existing = ExplicitNeeds(brand="Tesla")
        result = extract_explicit_needs(llm, "text", existing)
        assert result.brand == "Tesla"
        assert result.prize == "200000"


class TestImplicitDeductor:
    def test_deduce(self):
        llm = _mock_llm('{"comfort_level": "High", "safety": "High"}')
        result = deduce_implicit_needs(
            llm, UserProfile(family_size="5"), ExplicitNeeds(powertrain_type="EV")
        )
        assert result.comfort_level == "High"
        assert result.safety == "High"

    def test_deduce_merge(self):
        llm = _mock_llm('{"safety": "Medium"}')
        existing = ImplicitNeeds(comfort_level="High")
        result = deduce_implicit_needs(llm, UserProfile(), ExplicitNeeds(), existing)
        assert result.comfort_level == "High"
        assert result.safety == "Medium"


class TestReservationExtractor:
    def test_extract_reservation(self):
        llm = _mock_llm('{"reservation_date": "2024-06-01", "reservation_time": "10:00"}')
        result = extract_reservation(llm, "text")
        assert result.reservation_date == "2024-06-01"

    def test_extract_merge(self):
        llm = _mock_llm('{"reservation_location": "East Store"}')
        existing = ReservationInfo(reservation_date="2024-06-01")
        result = extract_reservation(llm, "text", existing)
        assert result.reservation_date == "2024-06-01"
        assert result.reservation_location == "East Store"


# ── Stage Tests ────────────────────────────────────────────────


class TestStages:
    def test_stage_order_has_all(self):
        assert len(STAGE_ORDER) == len(Stage)

    def test_valid_transitions(self):
        assert can_transition(Stage.WELCOME, Stage.PROFILE_ANALYSIS)
        assert can_transition(Stage.PROFILE_ANALYSIS, Stage.NEEDS_ANALYSIS)
        assert not can_transition(Stage.WELCOME, Stage.FAREWELL)

    def test_farewell_has_no_transitions(self):
        assert STAGE_TRANSITIONS[Stage.FAREWELL] == set()

    def test_backward_allowed(self):
        assert can_transition(Stage.CAR_SELECTION, Stage.NEEDS_ANALYSIS)
        assert can_transition(Stage.RESERVATION_CONFIRMATION, Stage.RESERVATION_4S)

    def test_should_advance_to_needs_with_info(self):
        assert should_advance_to_needs(UserProfile(name="Alice"))

    def test_should_advance_to_needs_without_info(self):
        assert not should_advance_to_needs(UserProfile())

    def test_should_advance_to_car_selection_enough(self):
        needs = VehicleNeeds(explicit=ExplicitNeeds(brand="Tesla", powertrain_type="EV"))
        assert should_advance_to_car_selection(needs)

    def test_should_advance_to_car_selection_not_enough(self):
        needs = VehicleNeeds(explicit=ExplicitNeeds(brand="Tesla"))
        assert not should_advance_to_car_selection(needs)

    def test_should_advance_to_reservation(self):
        assert should_advance_to_reservation([{"car_model": "X"}])
        assert not should_advance_to_reservation([])

    def test_should_advance_to_confirmation(self):
        r = ReservationInfo(
            reservation_date="2024-06-01",
            reservation_time="10:00",
            reservation_location="Store A",
        )
        assert should_advance_to_confirmation(r)

    def test_should_advance_to_confirmation_incomplete(self):
        r = ReservationInfo(reservation_date="2024-06-01")
        assert not should_advance_to_confirmation(r)

    def test_should_advance_to_farewell(self):
        r = ReservationInfo(
            test_driver="Alice",
            reservation_date="2024-06-01",
            reservation_time="10:00",
            reservation_location="Store A",
            reservation_phone_number="123",
        )
        assert should_advance_to_farewell(r)

    def test_should_advance_to_farewell_incomplete(self):
        r = ReservationInfo(test_driver="Alice", reservation_date="2024-06-01")
        assert not should_advance_to_farewell(r)


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
            Stage.PROFILE_ANALYSIS, UserProfile(name="Alice"), VehicleNeeds(), [], ReservationInfo()
        )
        assert result == Stage.NEEDS_ANALYSIS

    def test_needs_advances_with_enough_fields(self):
        needs = VehicleNeeds(explicit=ExplicitNeeds(brand="BMW", prize="200000"))
        result = determine_next_stage(
            Stage.NEEDS_ANALYSIS, UserProfile(), needs, [], ReservationInfo()
        )
        assert result == Stage.CAR_SELECTION

    def test_needs_stays_without_enough_fields(self):
        needs = VehicleNeeds(explicit=ExplicitNeeds(brand="BMW"))
        result = determine_next_stage(
            Stage.NEEDS_ANALYSIS, UserProfile(), needs, [], ReservationInfo()
        )
        assert result == Stage.NEEDS_ANALYSIS

    def test_car_selection_advances_with_cars(self):
        result = determine_next_stage(
            Stage.CAR_SELECTION,
            UserProfile(),
            VehicleNeeds(),
            [{"car_model": "X"}],
            ReservationInfo(),
        )
        assert result == Stage.RESERVATION_4S

    def test_car_selection_stays_without_cars(self):
        result = determine_next_stage(
            Stage.CAR_SELECTION, UserProfile(), VehicleNeeds(), [], ReservationInfo()
        )
        assert result == Stage.CAR_SELECTION

    def test_reservation_advances_with_info(self):
        r = ReservationInfo(
            reservation_date="2024-06-01",
            reservation_time="10:00",
            reservation_location="Store",
        )
        result = determine_next_stage(Stage.RESERVATION_4S, UserProfile(), VehicleNeeds(), [], r)
        assert result == Stage.RESERVATION_CONFIRMATION

    def test_confirmation_advances_to_farewell(self):
        r = ReservationInfo(
            test_driver="A",
            reservation_date="2024-06-01",
            reservation_time="10:00",
            reservation_location="Store",
            reservation_phone_number="123",
        )
        result = determine_next_stage(
            Stage.RESERVATION_CONFIRMATION, UserProfile(), VehicleNeeds(), [], r
        )
        assert result == Stage.FAREWELL

    def test_farewell_stays(self):
        result = determine_next_stage(
            Stage.FAREWELL, UserProfile(), VehicleNeeds(), [], ReservationInfo()
        )
        assert result == Stage.FAREWELL


# ── Memory Tests ───────────────────────────────────────────────


class TestChatMemory:
    def test_create_and_get(self):
        mgr = ChatMemoryManager()
        buf = mgr.get_or_create("s1")
        assert buf is not None

    def test_add_messages(self):
        mgr = ChatMemoryManager()
        mgr.add_user_message("s1", "Hello")
        mgr.add_assistant_message("s1", "Hi!")
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
        mgr.add_user_message("s1", "a")
        mgr.add_user_message("s2", "b")
        assert set(mgr.active_sessions) == {"s1", "s2"}

    def test_clear_nonexistent(self):
        mgr = ChatMemoryManager()
        mgr.clear_session("nonexistent")  # should not raise


# ── Response Generator Tests ──────────────────────────────────


class TestResponseGenerator:
    def test_missing_profile_fields(self):
        result = _get_missing_profile_fields(UserProfile())
        assert "name" in result

    def test_complete_profile(self):
        p = UserProfile(
            phone_number="1",
            name="A",
            title="Mr",
            age="30",
            target_driver="self",
            expertise="beginner",
            family_size="3",
            price_sensitivity="medium",
            residence="Beijing",
            parking_conditions="garage",
        )
        assert "None" in _get_missing_profile_fields(p)

    def test_missing_needs_fields(self):
        result = _get_missing_needs_fields(VehicleNeeds())
        assert "prize" in result

    def test_missing_reservation_fields(self):
        result = _get_missing_reservation_fields(ReservationInfo())
        assert "reservation_date" in result

    def test_format_matched_cars_empty(self):
        assert "No vehicles" in _format_matched_cars([])

    def test_format_matched_cars_with_data(self):
        result = _format_matched_cars(
            [{"car_model": "Tesla Model 3", "score": 0.9, "text_snippet": "Great EV"}]
        )
        assert "Tesla Model 3" in result

    def test_generate_response_success(self):
        llm = _mock_llm("Welcome to AutoVend!")
        result = generate_response(
            llm, Stage.WELCOME, "User: Hi", UserProfile(), VehicleNeeds(), [], ReservationInfo()
        )
        assert "Welcome to AutoVend!" in result

    def test_generate_response_error_fallback(self):
        llm = MagicMock()
        llm.complete.side_effect = RuntimeError("fail")
        result = generate_response(
            llm, Stage.WELCOME, "", UserProfile(), VehicleNeeds(), [], ReservationInfo()
        )
        assert "apologize" in result.lower()


# ── SalesAgent Integration Tests ──────────────────────────────


class TestSalesAgent:
    def test_process_welcome(self):
        llm = _mock_llm_dynamic()
        agent = SalesAgent(llm=llm)
        state = SessionState(session_id="s1")
        inp = AgentInput(session_state=state, user_message="Hello")
        result = agent.process(inp)

        assert isinstance(result, AgentResult)
        assert result.session_state.stage == Stage.CAR_SELECTION  # global extraction jumps
        # to car selection
        assert result.stage_changed is True
        assert result.response_text  # has some response

    def test_process_profile_extraction(self):
        llm = _mock_llm_dynamic()
        agent = SalesAgent(llm=llm)
        state = SessionState(session_id="s2", stage=Stage.PROFILE_ANALYSIS)
        inp = AgentInput(session_state=state, user_message="My name is Alice, I'm 30")
        result = agent.process(inp)

        # Profile should be extracted
        assert result.session_state.profile.name == "TestUser"
        assert result.session_state.profile.age == "30"

    def test_process_injects_retrieved_cars(self):
        llm = _mock_llm_dynamic()
        agent = SalesAgent(llm=llm)
        state = SessionState(session_id="s3", stage=Stage.NEEDS_ANALYSIS)
        cars = [{"car_model": "Tesla Model 3", "score": 0.95}]
        inp = AgentInput(
            session_state=state,
            user_message="I want an EV",
            retrieved_cars=cars,
        )
        result = agent.process(inp)
        assert result.session_state.matched_cars == cars

    def test_process_without_retrieved_cars(self):
        llm = _mock_llm_dynamic()
        agent = SalesAgent(llm=llm)
        state = SessionState(session_id="s4", stage=Stage.WELCOME)
        inp = AgentInput(session_state=state, user_message="Hi")
        result = agent.process(inp)
        assert result.session_state.matched_cars == []

    def test_clear_session(self):
        llm = _mock_llm_dynamic()
        agent = SalesAgent(llm=llm)
        agent.memory.add_user_message("s5", "test")
        assert agent.memory.has_session("s5")
        agent.clear_session("s5")
        assert not agent.memory.has_session("s5")

    def test_get_history_text(self):
        llm = _mock_llm_dynamic()
        agent = SalesAgent(llm=llm)
        state = SessionState(session_id="s6")
        inp = AgentInput(session_state=state, user_message="Hello")
        agent.process(inp)
        text = agent.get_history_text("s6")
        assert "Hello" in text

    def test_process_preserves_session_id(self):
        llm = _mock_llm_dynamic()
        agent = SalesAgent(llm=llm)
        state = SessionState(session_id="unique-123")
        inp = AgentInput(session_state=state, user_message="test")
        result = agent.process(inp)
        assert result.session_state.session_id == "unique-123"

    def test_process_does_not_mutate_input(self):
        llm = _mock_llm_dynamic()
        agent = SalesAgent(llm=llm)
        state = SessionState(session_id="s7")
        inp = AgentInput(session_state=state, user_message="test")
        original_stage = inp.session_state.stage
        agent.process(inp)
        assert inp.session_state.stage == original_stage  # input unchanged
