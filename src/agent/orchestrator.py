"""
Sales Orchestrator — Central In-Cabin Sales & Tour Orchestrator for BYD 4S Showroom.

Owns:
- Showroom Anchor Vehicle Context (current vehicle customer is seated in)
- Sales Funnel FSM Arbitration & Rollback
- Structured State Compaction (StateCompact)
- Subagent Sandbox Task Dispatching (Model Comparison, Financial Calculation, Test Drive Scheduling)
- Dynamic Dialogue Flow Control
"""

import logging
from typing import Any, Dict, Iterator, List, Optional, Tuple

from llama_index.core.llms import LLM

from src.agent.sales_agent import SalesAgent
from src.agent.schemas import (
    AgentResult,
    AnchorVehicleContext,
    SessionState,
)
from src.agent.subagents.dispatcher import SubagentDispatcher
from src.governance.engine import get_governance_engine

logger = logging.getLogger(__name__)


class SalesOrchestrator(SalesAgent):
    """
    Dedicated Sales & In-Cabin Tour Orchestrator for BYD Offline Showroom.
    Manages anchor vehicle context, FSM funnel transitions, state compaction,
    and dispatches specialized sub-tasks to expert subagents.
    """

    def __init__(
        self,
        llm: LLM,
        generation_llm: Optional[LLM] = None,
        enable_tool_planning: bool = False,
        default_anchor_vehicle: Optional[AnchorVehicleContext] = None,
    ):
        super().__init__(
            llm=llm,
            generation_llm=generation_llm,
            enable_tool_planning=enable_tool_planning,
        )
        self.default_anchor_vehicle = default_anchor_vehicle or AnchorVehicleContext()
        self.subagent_dispatcher = SubagentDispatcher()

    def _ensure_anchor_context(self, state: SessionState) -> str:
        """Ensure state has anchor vehicle and build anchor system note idempotently."""
        if not getattr(state, "anchor_vehicle", None):
            state.anchor_vehicle = self.default_anchor_vehicle.model_copy(deep=True)

        anchor = state.anchor_vehicle
        anchor_note = (
            f"【当前座舱展车主锚点】: 顾客当前正坐在比亚迪 4S 旗舰店的实车座舱内！\n"
            f"展车车型: {anchor.model_name}（{anchor.series}系列，{anchor.trim}）\n"
            f"核心配置: 动力系统: {anchor.powertrain} | 智能座舱: {anchor.cockpit_system} | 底盘操控: {anchor.chassis}\n"
            f"售价指导: {anchor.price_guidance}\n"
            f"交互指引: 优先结合当前展车座舱实际感受展开销售导览，适时引导顾客体验自适应旋转大屏、云辇悬挂或预约实车道路试驾。"
        )

        # Avoid duplicate anchor notes in system_notes
        state.system_notes = [n for n in state.system_notes if "【当前座舱展车主锚点】" not in n]
        state.system_notes.insert(0, anchor_note)
        return anchor_note

    def compact_state(self, state: SessionState, threshold_turns: int = 6) -> SessionState:
        """
        Structured State Compaction (StateCompact).
        When the dialogue transcript grows long, summarizes older turns to retain
        contextual integrity within fixed token boundaries while keeping explicit/implicit
        needs and vehicle anchor context intact.
        """
        history = self.memory.get_history(state.session_id)
        if len(history) <= threshold_turns:
            return state

        uncompressed_turns = len(history) - state.last_compressed_turn
        if uncompressed_turns >= threshold_turns:
            logger.info(
                f"[{state.session_id}] StateCompact triggered: compacting {uncompressed_turns} turns."
            )
            summary_snippet = (
                f"顾客与销售顾问已在展车【{state.anchor_vehicle.model_name}】座舱内完成了初步需求沟通。"
                f"已提取核心偏好：预算 {state.needs.explicit.prize or '未指定'}，"
                f"意向车系 {state.needs.explicit.brand or '比亚迪'} "
                f"动力偏好 {state.needs.explicit.powertrain_type or '新能源'}。"
            )
            state.summary_history.append(
                {
                    "start_turn": state.last_compressed_turn,
                    "end_turn": len(history),
                    "summary": summary_snippet,
                }
            )
            state.last_compressed_turn = len(history)

        return state

    def remember(self, state: SessionState, user_message: str) -> SessionState:
        """Record utterance without extraction, keeping anchor vehicle and state compaction active."""
        if not getattr(state, "anchor_vehicle", None):
            state.anchor_vehicle = self.default_anchor_vehicle.model_copy(deep=True)
        updated = super().remember(state, user_message)
        return self.compact_state(updated)

    def observe(
        self,
        state: SessionState,
        user_message: str,
        use_tools: Optional[bool] = None,
    ) -> SessionState:
        """
        Observe user input, execute extraction, compact state if needed,
        and dispatch relevant domain expert subagents.
        """
        # Ensure anchor vehicle is present in state
        if not getattr(state, "anchor_vehicle", None):
            state.anchor_vehicle = self.default_anchor_vehicle.model_copy(deep=True)

        updated = super().observe(state, user_message, use_tools=use_tools)

        # Dispatch expert subagents in sandbox based on user utterance
        context = {
            "session_id": updated.session_id,
            "anchor_vehicle": updated.anchor_vehicle.model_dump(),
            "user_message": user_message,
            "stage": updated.stage.value,
            "needs": updated.needs.model_dump(),
            "profile": updated.profile.model_dump(),
        }

        subagent_results = self.subagent_dispatcher.auto_dispatch(user_message, context)
        for res in subagent_results:
            if res.conclusion:
                logger.info(
                    f"[{updated.session_id}] Subagent '{res.subagent_name}' yielded conclusion -> system_notes"
                )
                updated.system_notes.append(res.conclusion)

        # Run State Compaction
        updated = self.compact_state(updated)

        return updated

    def respond(
        self,
        state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        propose_with_llm: bool = False,
    ) -> AgentResult:
        """
        Arbitrate stage machine with anchor vehicle context, trigger stage governance,
        and generate customer-facing reply.
        """
        # Inject Anchor Vehicle Context Note idempotently
        self._ensure_anchor_context(state)

        result = super().respond(state, retrieved_cars=retrieved_cars, propose_with_llm=propose_with_llm)

        # Hook Governance: StageTransition
        gov = get_governance_engine()
        role_val = (
            result.session_state.user_role.value
            if hasattr(result.session_state.user_role, "value")
            else str(result.session_state.user_role)
        )
        gov.stage_transition(
            verdict=result.session_state,
            session_id=result.session_state.session_id,
            trace_id=result.session_state.trace_id,
            user_role=role_val,
        )

        return result

    def respond_stream(
        self,
        state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
    ) -> Iterator[Tuple[str, Any]]:
        """
        Stream customer-facing reply tokens with anchor vehicle grounding and stage governance.
        """
        self._ensure_anchor_context(state)

        for event_type, data in super().respond_stream(state, retrieved_cars):
            if event_type == "metadata":
                updated_state = data.get("session_state")
                if updated_state and data.get("stage_changed"):
                    gov = get_governance_engine()
                    role_val = (
                        updated_state.user_role.value
                        if hasattr(updated_state.user_role, "value")
                        else str(updated_state.user_role)
                    )
                    gov.stage_transition(
                        verdict=updated_state,
                        session_id=updated_state.session_id,
                        trace_id=updated_state.trace_id,
                        user_role=role_val,
                    )
            yield event_type, data
