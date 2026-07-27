"""
Tests for per-stage tool sets and incremental state patches.

Two invariants carry most of the weight:

- A tool outside the current stage's set is refused. Prompting the model with a
  restricted list is a request; the dispatcher's refusal is the rule.
- A field disappearing from extraction is not a deletion. Extractors merge, so
  treating absence as removal would erase facts on every turn that happened not
  to mention them.
"""

import pytest

from src.agent.patches import (
    PatchLog,
    PatchOp,
    StatePatch,
    apply_patches,
    diff,
    format_for_prompt,
    invert,
    removal_patches,
    snapshot,
)
from src.agent.schemas import ExplicitNeeds, SessionState, Stage, VehicleNeeds
from src.agent.tools import (
    STAGE_TOOLS,
    TOOLS,
    dispatch,
    dispatch_all,
    is_allowed,
    render_catalog,
    tools_for,
)


def _state(stage=Stage.PROFILE_ANALYSIS, **kwargs):
    return SessionState(session_id="s", stage=stage, **kwargs)


# ── Tools ─────────────────────────────────────────────────────────────


class TestStageToolSets:
    def test_every_stage_declares_a_set(self):
        for stage in Stage:
            assert stage in STAGE_TOOLS

    def test_every_named_tool_exists(self):
        for stage, names in STAGE_TOOLS.items():
            for name in names:
                assert name in TOOLS, f"{stage.value} names unknown tool {name!r}"

    def test_farewell_is_terminal_and_toolless(self):
        assert STAGE_TOOLS[Stage.FAREWELL] == ()
        assert tools_for(Stage.FAREWELL) == []
        assert "没有可用工具" in render_catalog(Stage.FAREWELL)

    def test_transition_to_is_available_wherever_the_flow_continues(self):
        for stage in Stage:
            if stage is Stage.FAREWELL:
                continue
            assert is_allowed(stage, "transition_to"), stage.value

    def test_catalog_lists_only_this_stage_tools(self):
        catalog = render_catalog(Stage.PROFILE_ANALYSIS)

        assert "record_profile" in catalog
        assert "record_reservation" not in catalog

    def test_catalog_marks_optional_parameters(self):
        catalog = render_catalog(Stage.PROFILE_ANALYSIS)

        assert "field:" in catalog  # required
        assert "reason?:" in catalog  # optional


class TestDispatchEnforcement:
    def test_tool_outside_the_stage_set_is_refused(self):
        """
        The failure this prevents: a booking recorded while the conversation is
        still learning who the customer is, because they mentioned a weekday.
        """
        state = _state(Stage.PROFILE_ANALYSIS)

        result = dispatch(state, "record_reservation", {"fields": {"reservation_date": "周六"}})

        assert not result.ok
        assert "不允许" in result.message
        assert state.reservation.reservation_date == ""

    def test_refusal_lists_what_is_allowed(self):
        result = dispatch(_state(Stage.PROFILE_ANALYSIS), "select_vehicle", {"car_model": "X"})

        assert "record_profile" in result.message

    def test_unknown_tool_is_refused(self):
        assert not dispatch(_state(), "delete_everything", {}).ok

    def test_missing_required_parameter_is_refused(self):
        result = dispatch(_state(Stage.PROFILE_ANALYSIS), "record_profile", {})

        assert not result.ok
        assert "fields" in result.message

    def test_handler_exceptions_do_not_escape(self, monkeypatch):
        spec = TOOLS["record_profile"]

        def boom(state, args):
            raise RuntimeError("kaboom")

        # ToolSpec is frozen, so swap the registry entry rather than the field.
        monkeypatch.setitem(
            TOOLS,
            "record_profile",
            type(spec)(spec.name, spec.description, spec.parameters, boom, spec.required),
        )

        result = dispatch(
            _state(Stage.PROFILE_ANALYSIS), "record_profile", {"fields": {"name": "X"}}
        )

        assert not result.ok
        assert "kaboom" in result.message


class TestToolHandlers:
    def test_record_profile_writes_and_patches(self):
        state = _state(Stage.PROFILE_ANALYSIS)

        result = dispatch(state, "record_profile", {"fields": {"name": "张伟", "age": "35"}})

        assert result.ok
        assert state.profile.name == "张伟"
        assert {p.path for p in result.patches} == {"profile.name", "profile.age"}
        assert all(p.source == "record_profile" for p in result.patches)

    def test_unknown_field_is_dropped_not_fatal(self):
        state = _state(Stage.NEEDS_ANALYSIS)

        result = dispatch(state, "record_need", {"fields": {"budget": "30万", "prize": "30万"}})

        assert result.ok
        assert state.needs.explicit.prize == "30万"
        assert [p.path for p in result.patches] == ["needs.explicit.prize"]

    def test_rewriting_the_same_value_produces_no_patch(self):
        state = _state(
            Stage.NEEDS_ANALYSIS, needs=VehicleNeeds(explicit=ExplicitNeeds(prize="30万"))
        )

        result = dispatch(state, "record_need", {"fields": {"prize": "30万"}})

        assert result.ok
        assert result.patches == []

    def test_select_vehicle_promotes_the_choice(self):
        cars = [{"car_model": "A"}, {"car_model": "B"}, {"car_model": "C"}]
        state = _state(Stage.CAR_SELECTION, matched_cars=cars)

        result = dispatch(state, "select_vehicle", {"car_model": "B"})

        assert result.ok
        assert state.matched_cars[0]["car_model"] == "B"
        assert len(state.matched_cars) == 3, "runner-ups stay available"

    def test_select_vehicle_rejects_a_car_not_offered(self):
        state = _state(Stage.CAR_SELECTION, matched_cars=[{"car_model": "A"}])

        result = dispatch(state, "select_vehicle", {"car_model": "Z"})

        assert not result.ok
        assert "A" in result.message

    def test_confirm_reservation_names_missing_slots(self):
        state = _state(Stage.RESERVATION_CONFIRMATION)

        result = dispatch(state, "confirm_reservation", {})

        assert not result.ok
        assert "试驾人" in result.message and "门店" in result.message

    def test_transition_to_only_proposes(self):
        state = _state(Stage.PROFILE_ANALYSIS)

        result = dispatch(state, "transition_to", {"stage": "needs_analysis"})

        assert result.ok
        assert state.stage is Stage.PROFILE_ANALYSIS, "the tool must not move the stage itself"
        assert result.request == {"type": "transition", "stage": "needs_analysis", "reason": ""}

    def test_transition_to_rejects_an_unknown_stage(self):
        assert not dispatch(_state(), "transition_to", {"stage": "nirvana"}).ok

    def test_requests_are_surfaced_not_executed(self):
        state = _state(Stage.CAR_SELECTION, matched_cars=[{"car_model": "A"}])

        result = dispatch(state, "request_more_options", {"reason": "都太贵"})

        assert result.ok
        assert result.request["type"] == "retrieve"


class TestDispatchAll:
    def test_preserves_order(self):
        """A need recorded then a transition proposed must happen in that order."""
        state = _state(Stage.NEEDS_ANALYSIS)

        results = dispatch_all(
            state,
            [
                {"tool": "record_need", "args": {"fields": {"prize": "30万"}}},
                {"tool": "transition_to", "args": {"stage": "car_selection_confirmation"}},
            ],
        )

        assert [r.tool for r in results] == ["record_need", "transition_to"]
        assert state.needs.explicit.prize == "30万"

    def test_one_refusal_does_not_abort_the_batch(self):
        state = _state(Stage.NEEDS_ANALYSIS)

        results = dispatch_all(
            state,
            [
                {"tool": "select_vehicle", "args": {"car_model": "A"}},  # wrong stage
                {"tool": "record_need", "args": {"fields": {"prize": "30万"}}},
            ],
        )

        assert not results[0].ok and results[1].ok
        assert state.needs.explicit.prize == "30万"

    def test_non_dict_args_are_refused(self):
        results = dispatch_all(_state(), [{"tool": "record_profile", "args": "oops"}])

        assert not results[0].ok


# ── Patches ───────────────────────────────────────────────────────────


class TestSnapshotAndDiff:
    def test_snapshot_skips_empty_fields(self):
        state = _state()
        state.profile.name = "张伟"

        flat = snapshot(state)

        assert flat == {"profile.name": "张伟"}

    def test_diff_marks_new_fields_as_add(self):
        patches = diff({}, {"profile.name": "张伟"}, source="extractor")

        assert len(patches) == 1
        assert patches[0].op is PatchOp.ADD
        assert patches[0].source == "extractor"

    def test_diff_marks_changed_fields_as_update_with_previous(self):
        patches = diff({"needs.explicit.prize": "30万"}, {"needs.explicit.prize": "80万"})

        assert patches[0].op is PatchOp.UPDATE
        assert patches[0].previous == "30万"
        assert patches[0].value == "80万"

    def test_disappearing_fields_produce_no_patch(self):
        """
        Extractors merge, not replace. A field missing from this turn's output
        means the turn said nothing about it — treating that as a removal would
        erase facts every time the subject changed.
        """
        assert diff({"profile.name": "张伟"}, {}) == []

    def test_unchanged_fields_produce_no_patch(self):
        assert diff({"profile.name": "张伟"}, {"profile.name": "张伟"}) == []

    def test_removal_patches_are_explicit(self):
        patches = removal_patches(["profile.name"], {"profile.name": "张伟"}, source="rollback")

        assert patches[0].op is PatchOp.REMOVE
        assert patches[0].previous == "张伟"


class TestApplyAndInvert:
    def test_apply_writes_the_value(self):
        state = _state()

        applied = apply_patches(state, [StatePatch(PatchOp.ADD, "profile.name", "张伟")])

        assert applied == ["profile.name"]
        assert state.profile.name == "张伟"

    def test_apply_skips_unknown_paths(self):
        """A patch log from an older schema must not make a session unloadable."""
        state = _state()

        assert apply_patches(state, [StatePatch(PatchOp.ADD, "profile.zodiac", "龙")]) == []

    def test_remove_clears_the_field(self):
        state = _state()
        state.profile.name = "张伟"

        apply_patches(state, [StatePatch(PatchOp.REMOVE, "profile.name", previous="张伟")])

        assert state.profile.name == ""

    def test_invert_round_trips_a_change(self):
        state = _state()
        state.needs.explicit.prize = "30万"
        forward = [StatePatch(PatchOp.UPDATE, "needs.explicit.prize", "80万", previous="30万")]

        apply_patches(state, forward)
        assert state.needs.explicit.prize == "80万"

        apply_patches(state, invert(forward))
        assert state.needs.explicit.prize == "30万"

    def test_invert_of_an_add_removes(self):
        inverted = invert([StatePatch(PatchOp.ADD, "profile.name", "张伟")])

        assert inverted[0].op is PatchOp.REMOVE

    def test_invert_reverses_order(self):
        patches = [
            StatePatch(PatchOp.ADD, "profile.name", "A"),
            StatePatch(PatchOp.ADD, "profile.age", "35"),
        ]

        assert [p.path for p in invert(patches)] == ["profile.age", "profile.name"]


class TestPatchLog:
    def test_serialises_round_trip(self):
        log = PatchLog([StatePatch(PatchOp.ADD, "profile.name", "张伟", source="tool")])

        restored = PatchLog.from_json(log.to_json())

        assert len(restored) == 1
        assert restored.entries[0].path == "profile.name"
        assert restored.entries[0].source == "tool"

    def test_for_path_matches_a_subtree(self):
        log = PatchLog(
            [
                StatePatch(PatchOp.ADD, "needs.explicit.prize", "30万"),
                StatePatch(PatchOp.ADD, "profile.name", "张伟"),
            ]
        )

        assert [p.path for p in log.for_path("needs.explicit")] == ["needs.explicit.prize"]

    def test_recent_returns_the_tail(self):
        log = PatchLog([StatePatch(PatchOp.ADD, f"profile.f{i}", i) for i in range(10)])

        assert len(log.recent(3)) == 3
        assert log.recent(3)[-1].path == "profile.f9"


class TestPromptFormatting:
    def test_renders_changes_for_injection(self):
        text = format_for_prompt(
            [StatePatch(PatchOp.UPDATE, "needs.explicit.prize", "80万", previous="30万")]
        )

        assert "needs.explicit.prize" in text
        assert "30万" in text and "80万" in text

    def test_empty_input_renders_nothing(self):
        assert format_for_prompt([]) == ""

    def test_limits_how_many_appear(self):
        patches = [StatePatch(PatchOp.ADD, f"profile.f{i}", i) for i in range(20)]

        assert format_for_prompt(patches, limit=3).count("\n- ") == 3


class TestAgentIntegration:
    """The patch log must accumulate across turns, not reset each time."""

    def test_patches_accumulate_in_state(self):
        from src.agent.sales_agent import _record_patches

        state = _state()
        state.profile.name = "张伟"
        _record_patches(state, {}, source="extractor")

        state.needs.explicit.prize = "30万"
        _record_patches(state, snapshot(state) | {"needs.explicit.prize": None}, source="tool")

        paths = [p["path"] for p in state.patch_log]
        assert "profile.name" in paths
        assert "needs.explicit.prize" in paths

    def test_no_change_clears_last_patch_but_keeps_the_log(self):
        from src.agent.sales_agent import _record_patches

        state = _state()
        state.profile.name = "张伟"
        _record_patches(state, {}, source="extractor")
        assert state.last_patch

        _record_patches(state, snapshot(state), source="extractor")

        assert state.last_patch == {}
        assert len(state.patch_log) == 1, "history must survive a no-op turn"

    def test_tool_transition_request_is_arbitrated(self):
        from unittest.mock import MagicMock

        from src.agent.sales_agent import SalesAgent

        llm = MagicMock()
        llm.complete.return_value.text = "请告诉我您的预算。"
        state = _state(Stage.NEEDS_ANALYSIS)
        state.pending_requests = [
            {
                "type": "transition",
                "stage": Stage.CAR_SELECTION.value,
                "reason": "需求已经问完",
            }
        ]

        result = SalesAgent(llm).respond(state)

        assert result.session_state.stage == Stage.NEEDS_ANALYSIS
        assert result.session_state.pending_requests == []
        assert any("缺少预算" in note for note in llm.complete.call_args.args[0].splitlines())

    def test_dynamic_notes_are_appended_after_stable_stage_prompt(self):
        from unittest.mock import MagicMock

        from src.agent.response_generator import generate_response

        llm = MagicMock()
        llm.complete.return_value.text = "ok"

        generate_response(
            llm,
            Stage.NEEDS_ANALYSIS,
            "User: hello",
            _state().profile,
            _state().needs,
            [],
            _state().reservation,
            system_notes=["PATCH_SENTINEL"],
        )

        prompt = llm.complete.call_args.args[0]
        assert prompt.startswith("You are AutoVend")
        assert prompt.rfind("PATCH_SENTINEL") > prompt.rfind("Conversation so far")


@pytest.mark.parametrize("stage", list(Stage))
def test_render_catalog_never_raises(stage):
    assert isinstance(render_catalog(stage), str)
