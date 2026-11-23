"""
Unified Structured-Output Turn Intent & Interruption Classifier (`src/agent/turn_classifier.py`).

Replaces hardcoded Chinese keyword lists in `langgraph_agent.py` and `sales_agent.py`
with a unified `with_structured_output` lightweight classifier (local 8B / extraction model)
combined with `SemanticRouter` signals.
"""

import logging
from typing import Any, List, Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agent.schemas import SessionState, Stage
from src.agent.topic_manager import TopicAnalysisResult, TopicManager, UserDialogueIntent

logger = logging.getLogger(__name__)


class TurnIntentClassification(BaseModel):
    """Structured output schema for user turn intent, interruption, and constraint-change detection."""

    intent: Literal[
        "normal",
        "side_question",
        "spec_comparison",
        "constraint_update",
        "multi_intent",
    ] = Field(default="normal", description="Primary dialogue intent for this turn.")
    is_interrupt: bool = Field(
        default=False,
        description="True if the user is interrupting the current stage flow (side question, comparison, or constraint change).",
    )
    is_constraint_change: bool = Field(
        default=False,
        description="True if the user is modifying, relaxing, or retracting a previously stated car preference/budget/reservation.",
    )
    should_push_goal: bool = Field(
        default=False,
        description="True if the current stage goal should be pushed onto the goal stack while answering a side question.",
    )
    topic_label: str = Field(
        default="",
        description="Short topic label when interrupting (e.g. '车辆参数与技术咨询').",
    )
    retracted_constraints: List[str] = Field(
        default_factory=list,
        description="Constraint fields retracted or modified by the user (e.g. ['budget', 'car_type']).",
    )
    extracted_slots_hint: List[str] = Field(
        default_factory=list,
        description="Optional slot names hinted by the utterance.",
    )
    suggested_directive: str = Field(
        default="",
        description="Optional system directive for the response generator.",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @property
    def is_multi_intent(self) -> bool:
        return self.intent == "multi_intent"


_CLASSIFIER_SYSTEM_PROMPT = """You are a fast, precise automotive sales dialogue intent classifier.
Given the current sales stage and the customer's latest message, classify:
1. `intent`: one of "normal", "side_question", "spec_comparison", "constraint_update", "multi_intent".
2. `is_interrupt`: true if the customer is asking a side question, comparing specs, or changing/retracting constraints (budget, body style, powertrain, delaying reservation).
3. `is_constraint_change`: true if the customer wants to alter, lower, raise, or retract any constraint or hold off on booking a test drive — even if phrased colloquially (e.g., "刚才那个预算不太行，咱往下降点", "先不急着去店里").
4. `should_push_goal`: true for side questions / spec comparisons where we should return to the current stage afterward, false if it's a constraint_update.
5. `topic_label`: concise Chinese topic label if interrupting.
"""


def _from_topic_analysis(res: TopicAnalysisResult) -> TurnIntentClassification:
    intent_map = {
        UserDialogueIntent.SALES_PROGRESSION: "normal",
        UserDialogueIntent.SIDE_QUESTION: "side_question",
        UserDialogueIntent.SPEC_COMPARISON: "spec_comparison",
        UserDialogueIntent.CONSTRAINT_UPDATE: "constraint_update",
        UserDialogueIntent.MULTI_INTENT: "multi_intent",
    }
    intent_str = intent_map.get(res.intent, "normal")
    is_constraint = res.intent == UserDialogueIntent.CONSTRAINT_UPDATE
    should_push = res.is_interrupt and not is_constraint and (
        res.intent in (UserDialogueIntent.SIDE_QUESTION, UserDialogueIntent.SPEC_COMPARISON)
        or (
            res.intent == UserDialogueIntent.MULTI_INTENT
            and bool(res.topic_label)
            and res.topic_label != "车辆参数与技术咨询"
        )
    )
    return TurnIntentClassification(
        intent=intent_str,  # type: ignore[arg-type]
        is_interrupt=res.is_interrupt,
        is_constraint_change=is_constraint,
        should_push_goal=should_push,
        topic_label=res.topic_label or "",
        extracted_slots_hint=list(getattr(res, "extracted_slots_hint", []) or []),
        suggested_directive=res.suggested_directive or "",
        confidence=0.85,
    )


def classify_turn_intent(
    chat_model: Optional[Any],
    user_message: str,
    current_stage: Stage,
    session_state: SessionState,
    semantic_decision: Optional[Any] = None,
) -> TurnIntentClassification:
    """
    Classify turn intent & interruption using SemanticRouter + `with_structured_output`
    lightweight classifier, with deterministic TopicManager fallback for MockLLM/offline tests.
    """
    if not user_message or not user_message.strip():
        return TurnIntentClassification()

    # Use lightweight structured-output LLM when a real chat model is available
    is_mock = chat_model is None or "Mock" in type(chat_model).__name__
    if not is_mock and hasattr(chat_model, "with_structured_output"):
        try:
            structured_llm = chat_model.with_structured_output(TurnIntentClassification)
            router_hint = ""
            if semantic_decision is not None and getattr(semantic_decision, "matched", False):
                router_hint = (
                    f"\n[SemanticRouter hint: intent={semantic_decision.intent}, "
                    f"score={semantic_decision.score:.3f}]"
                )
            prompt = (
                f"Current stage: {current_stage.value}\n"
                f"User message: {user_message}{router_hint}"
            )
            result = structured_llm.invoke(
                [SystemMessage(content=_CLASSIFIER_SYSTEM_PROMPT), HumanMessage(content=prompt)]
            )
            if isinstance(result, TurnIntentClassification):
                return result
        except Exception as exc:
            logger.debug(f"Structured turn classifier fallback to TopicManager: {exc}")

    # Deterministic fallback (MockLLM / offline unit tests)
    topic_res = TopicManager.analyze_user_turn(user_message, current_stage, session_state)
    cls = _from_topic_analysis(topic_res)
    if (
        semantic_decision is not None
        and getattr(semantic_decision, "matched", False)
        and getattr(semantic_decision, "intent", None) in ("change_budget", "reject_recommendation")
    ):
        cls.intent = "constraint_update"
        cls.is_interrupt = True
        cls.is_constraint_change = True
        cls.should_push_goal = False
    return cls
