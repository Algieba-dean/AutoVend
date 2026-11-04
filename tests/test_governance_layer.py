"""
Unit tests for Hook & Governance Layer (src/governance/).
"""

from unittest.mock import MagicMock

from src.agent.schemas import SessionState, Stage
from src.governance.engine import GovernanceEngine


def test_session_lifecycle_hooks():
    engine = GovernanceEngine()
    start_ctx = engine.on_session_start(session_id="test_sess_001", user_role="customer")
    assert start_ctx.session_id == "test_sess_001"
    assert start_ctx.user_role == "customer"

    end_ctx = engine.on_session_end(session_id="test_sess_001")
    assert end_ctx.session_id == "test_sess_001"


def test_pre_observe_short_circuit_and_pii():
    mock_pii = MagicMock()
    mock_pii.mask.return_value = ("你好，我是<CN_PERSON_1>", [("PERSON", "张伟")])

    mock_router = MagicMock()
    decision = MagicMock()
    decision.matched = True
    decision.intent = "smalltalk"
    mock_router.classify.return_value = decision

    engine = GovernanceEngine(pii_interceptor=mock_pii, semantic_router=mock_router)

    # When PII is found, short-circuit must NOT skip extraction
    ctx = engine.pre_observe(user_message="你好，我是张伟", session_id="s1")
    assert ctx.pii_found is True
    assert ctx.safe_message == "你好，我是<CN_PERSON_1>"
    assert ctx.skip_extraction is False

    # When no PII and intent is smalltalk -> skip extraction
    mock_pii.mask.return_value = ("你好呀", [])
    ctx2 = engine.pre_observe(user_message="你好呀", session_id="s1")
    assert ctx2.pii_found is False
    assert ctx2.skip_extraction is True


def test_pre_observe_interrupt_detection():
    mock_router = MagicMock()
    decision = MagicMock()
    decision.matched = True
    decision.intent = "update_constraint"
    mock_router.classify.return_value = decision

    engine = GovernanceEngine(semantic_router=mock_router)
    ctx = engine.pre_observe(user_message="我想修改一下预算", session_id="s1")
    assert ctx.interrupt_detected is True


def test_pre_tool_use_rbac_and_sanitization():
    engine = GovernanceEngine()

    # Customer allowed to query store inventory
    args, allowed = engine.pre_tool_use(
        tool_name="query_store_inventory",
        tool_args={"car_model": "汉 EV<script>alert(1)</script>"},
        session_id="s1",
        user_role="customer",
    )
    assert allowed is True
    assert "<script>" not in args["car_model"]
    assert "汉 EV" in args["car_model"]

    # Customer NOT allowed to rollback tool transaction directly
    args_admin, allowed_admin = engine.pre_tool_use(
        tool_name="rollback_tool_transaction",
        tool_args={},
        session_id="s1",
        user_role="customer",
    )
    assert allowed_admin is False

    # Customer NOT allowed to confirm reservation directly (salesperson/admin privilege)
    _, allowed_confirm = engine.pre_tool_use(
        tool_name="confirm_reservation",
        tool_args={},
        session_id="s1",
        user_role="customer",
    )
    assert allowed_confirm is False


def test_post_tool_use_audit():
    engine = GovernanceEngine()
    ctx = engine.post_tool_use(
        tool_name="query_store_inventory",
        tool_result={"ok": True, "message": "Success"},
        transaction_id="tx_123",
        session_id="s1",
    )
    assert ctx.tool_name == "query_store_inventory"
    assert ctx.transaction_id == "tx_123"


def test_stage_transition_governance():
    engine = GovernanceEngine()
    verdict = MagicMock()
    verdict.stage = Stage.CAR_SELECTION
    verdict.rejection = None

    ctx = engine.stage_transition(verdict=verdict, session_id="s1")
    assert ctx.stage_verdict.stage == Stage.CAR_SELECTION


def test_post_generate_compliance_and_restitution():
    mock_pii = MagicMock()
    mock_pii.unmask.side_effect = lambda text, sid: text.replace("<CN_PERSON_1>", "王先生")

    engine = GovernanceEngine(pii_interceptor=mock_pii)

    state = SessionState(session_id="s1")
    state.profile.name = "<CN_PERSON_1>"
    state.reservation.test_driver = "<CN_PERSON_1>"

    raw_response = "<CN_PERSON_1>，我们保证全网最低价，为您推荐汉EV"
    final_text, warnings = engine.post_generate(
        response_text=raw_response,
        state=state,
        session_id="s1",
    )

    # 1. PII restored
    assert "王先生" in final_text
    assert "<CN_PERSON_1>" not in final_text
    assert state.profile.name == "王先生"
    assert state.reservation.test_driver == "王先生"

    # 2. Compliance: prohibited promise redacted
    assert "保证全网最低价" not in final_text
    assert len(warnings) > 0
