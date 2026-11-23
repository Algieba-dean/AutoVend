"""
Vehicle retrieval, CRAG grading, and query-rewrite graph nodes (`src/agent/graph/retrieval_nodes.py`).
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Literal, Optional, Tuple

from src.agent.events import AnyDialogueEvent, MatchedCarsUpdated, SystemNoteAdded
from src.agent.evidence_ledger import VerificationEvidenceLedger
from src.agent.execution_guard import check_step_budget
from src.agent.graph.state import MAX_CRAG_RETRIES, AgentGraphState
from src.agent.preference_model import PreferenceEngine
from src.agent.schemas import SessionState, Stage
from src.agent.topic_manager import UserDialogueIntent
from src.core.agentops import enqueue_agent_dlq, record_compliance_audit
from src.core.container import ServiceContainer
from src.core.interfaces import RAGQueryRequest
from src.core.tiered_engine import TieredRetrievalEngine
from src.core.truth_engine import TruthEngineFacade
from src.llm.cost_ledger import AgentNodeRole, node_cost_context
from src.privacy.prompt_sanitizer import PromptSanitizer

logger = logging.getLogger(__name__)


def extract_comparison_models(query: str, sess: SessionState) -> List[str]:
    """Extract >= 2 distinct vehicle models for parallel comparison retrieval."""
    if not query:
        return []
    found: List[str] = []
    try:
        known_models = TruthEngineFacade.get_instance().get_known_models()
    except Exception:
        known_models = []

    q_lower = query.lower()
    for model in sorted(known_models, key=len, reverse=True):
        if model.lower() in q_lower and model not in found:
            found.append(model)

    for car in sess.matched_cars or []:
        cm = str(car.get("car_model") or "").strip()
        if cm and cm.lower() in q_lower and cm not in found:
            found.append(cm)

    if len(found) >= 2:
        return found[:4]

    parts = [
        p.strip()
        for p in re.split(r"(?:\bvs\.?\b|对比|还是|以及|和|跟|与)", query, flags=re.IGNORECASE)
        if p and len(p.strip()) >= 2
    ]
    if len(parts) >= 2 and any(k in query for k in ("对比", "vs", "VS", "区别", "哪个好", "选谁")):
        return parts[:3]
    return []


def retrieve_single_query(
    agent: Any,
    retrieval_query: str,
    explicit_dict: Dict[str, Any],
    implicit_dict: Dict[str, Any],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Execute one retrieval call against `agent.retriever` or `ServiceContainer.get_rag_service()`."""
    if agent.retriever is not None:
        try:
            from src.retrieval.langchain_retriever import documents_to_car_dicts

            if hasattr(agent.retriever, "retrieve_with_slots"):
                docs = agent.retriever.retrieve_with_slots(
                    retrieval_query,
                    explicit_conditions=explicit_dict,
                    implicit_needs=implicit_dict,
                )
            else:
                docs = agent.retriever.invoke(retrieval_query)
            cars = documents_to_car_dicts(docs, limit=top_k)
            if cars:
                try:
                    from src.retrieval.compression import ContextCompressor

                    cars = ContextCompressor.compress_matched_cars(
                        cars,
                        query_text=retrieval_query,
                        active_constraints=explicit_dict,
                    )
                except Exception:
                    pass
            return cars
        except Exception as exc:
            logger.warning(f"LangChain retriever failed for '{retrieval_query}': {exc}")

    if ServiceContainer.has_rag_service():
        rag_service = ServiceContainer.get_rag_service()
        try:
            resp = rag_service.search_vehicles(
                RAGQueryRequest(
                    query_text=retrieval_query,
                    explicit_conditions=explicit_dict,
                    implicit_needs=implicit_dict,
                    top_k=top_k,
                )
            )
            return list(resp.results or [])
        except Exception as exc:
            logger.warning(f"RAGService retrieval failed for '{retrieval_query}': {exc}")
    return []


def finalize_retrieved_cars(
    state: AgentGraphState,
    sess: SessionState,
    ledger: VerificationEvidenceLedger,
    raw_cars: List[Dict[str, Any]],
    source: str,
) -> Dict[str, Any]:
    sanitized_cars, inj_patterns = PromptSanitizer.sanitize_matched_cars(raw_cars)
    if inj_patterns:
        record_compliance_audit(
            event_type="INDIRECT_PROMPT_INJECTION",
            session_id=sess.session_id,
            trace_id=sess.trace_id,
            checkpoint_id=sess.session_id,
            severity="CRITICAL",
            details={"source": source, "detected_patterns": inj_patterns},
        )
    filtered_cars = PreferenceEngine.filter_excluded_vehicles(sanitized_cars, sess.preferences)
    if filtered_cars:
        enriched = ledger.record_retrieved_vehicles(filtered_cars, source=source)
        sess.matched_cars = enriched
    else:
        sess.matched_cars = []
    car_event = MatchedCarsUpdated(
        turn_id=int(getattr(sess, "turn_count", 0)),
        source=f"retrieve:{source}",
        matched_cars=list(sess.matched_cars),
    )
    trace = [*list(state.get("execution_trace") or []), "retrieve_vehicles"]
    return {
        "events": [car_event],
        "session_state": sess,
        "evidence_anchors": ledger.get_anchors_summary(),
        "step_count": int(state.get("step_count", 0)) + 1,
        "execution_trace": trace,
    }


def node_retrieve_vehicles(agent: Any, state: AgentGraphState) -> Dict[str, Any]:
    sess = state["session_state"].model_copy(deep=True)
    ledger = VerificationEvidenceLedger()

    pre_retrieved = state.get("retrieved_cars")
    if pre_retrieved:
        return finalize_retrieved_cars(state, sess, ledger, pre_retrieved, source="pre_retrieved")

    query = state.get("safe_message") or state.get("user_message", "")
    retries = int(state.get("retrieval_retries", 0))
    override_query = state.get("retrieval_query_override")
    relaxed_explicit = state.get("retrieval_relaxed_constraints")

    is_compare = state.get("topic_intent") == UserDialogueIntent.SPEC_COMPARISON.value
    compare_models = extract_comparison_models(query, sess) if (is_compare or query) else []
    if (is_compare or len(compare_models) >= 2) and len(compare_models) >= 2 and retries == 0:
        explicit_dict = sess.needs.explicit.model_dump(exclude_none=True)
        implicit_dict = sess.needs.implicit.model_dump(exclude_none=True)

        def _fetch_model(model_name: str) -> List[Dict[str, Any]]:
            t0_cars: List[Dict[str, Any]] = []
            try:
                t0 = TieredRetrievalEngine.get_instance().search_tier0(
                    model_name, car_model_hint=model_name
                )
                if t0 is not None and t0.results:
                    for r in t0.results[:2]:
                        meta = dict(r.metadata) if r.metadata else {}
                        cm = r.car_model or meta.get("car_model", "")
                        if cm:
                            t0_cars.append(
                                {
                                    **meta,
                                    "car_model": cm,
                                    "score": getattr(r, "score", 1.0),
                                    "metadata": meta,
                                    "text_snippet": r.text_snippet or t0.facts_summary or "",
                                }
                            )
            except Exception:
                pass
            rag_cars = (
                retrieve_single_query(
                    agent,
                    model_name,
                    {k: v for k, v in explicit_dict.items() if k != "brand"},
                    implicit_dict,
                    top_k=3,
                )
                if (agent.retriever is not None or ServiceContainer.has_rag_service())
                else []
            )
            return t0_cars + rag_cars

        with ThreadPoolExecutor(max_workers=min(4, len(compare_models))) as pool:
            per_model_results = list(pool.map(_fetch_model, compare_models))

        merged: List[Dict[str, Any]] = []
        seen_models: set[str] = set()
        max_len = max((len(lst) for lst in per_model_results), default=0)
        for idx in range(max_len):
            for lst in per_model_results:
                if idx < len(lst):
                    car = lst[idx]
                    cm = str(car.get("car_model") or "").strip()
                    if cm and cm not in seen_models:
                        seen_models.add(cm)
                        merged.append(car)
        if merged:
            return finalize_retrieved_cars(
                state, sess, ledger, merged[:6], source="parallel_comparison"
            )

    if query and retries == 0:
        try:
            t0 = TieredRetrievalEngine.get_instance().search_tier0(query)
            if t0 is not None and t0.results:
                fast_cars = []
                for r in t0.results:
                    meta = dict(r.metadata) if r.metadata else {}
                    car_entry = {
                        **meta,
                        "car_model": r.car_model or meta.get("car_model", ""),
                        "score": getattr(r, "score", 1.0),
                        "metadata": meta,
                        "text_snippet": r.text_snippet or t0.facts_summary or "",
                    }
                    if car_entry["car_model"]:
                        fast_cars.append(car_entry)
                if fast_cars:
                    return finalize_retrieved_cars(
                        state, sess, ledger, fast_cars, source="tier0_fastpath"
                    )
        except Exception as te:
            logger.debug(f"[{sess.session_id}] Tier 0 lookup skipped: {te}")

    if not state.get("voice_mode") and sess.stage not in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
        trace = [*list(state.get("execution_trace") or []), "retrieve_vehicles"]
        return {
            "session_state": sess,
            "step_count": int(state.get("step_count", 0)) + 1,
            "execution_trace": trace,
        }

    from src.retrieval.adapters import needs_to_query_text

    explicit_dict = (
        dict(relaxed_explicit)
        if relaxed_explicit is not None
        else sess.needs.explicit.model_dump(exclude_none=True)
    )
    implicit_dict = sess.needs.implicit.model_dump(exclude_none=True)

    if override_query:
        retrieval_query = override_query
    else:
        needs_query = needs_to_query_text(sess.needs.explicit, sess.needs.implicit)
        if needs_query and needs_query != "recommend a good vehicle":
            retrieval_query = needs_query
        else:
            retrieval_query = query or needs_query or "recommend a vehicle"

    cars = retrieve_single_query(agent, retrieval_query, explicit_dict, implicit_dict, top_k=5)
    if not cars and state.get("voice_mode") and explicit_dict:
        # Voice-First millisecond FilterEngine relaxation (single-pass, no CRAG LLM rewrite loop)
        relaxed_dict = {
            k: v
            for k, v in explicit_dict.items()
            if k not in ("brand", "seat_layout", "design_style", "drive_type")
        }
        cars = retrieve_single_query(agent, retrieval_query, relaxed_dict, implicit_dict, top_k=5)
    return finalize_retrieved_cars(state, sess, ledger, cars or [], source="hybrid_rag")


def extract_budget_bounds(sess: SessionState) -> Tuple[Optional[float], Optional[float]]:
    b_min = sess.needs.explicit.budget_min
    b_max = sess.needs.explicit.budget_max
    if b_max is None and sess.needs.explicit.price:
        nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", sess.needs.explicit.price)]
        if len(nums) >= 2:
            b_min = b_min if b_min is not None else min(nums[0], nums[1])
            b_max = max(nums[0], nums[1])
        elif len(nums) == 1:
            b_max = nums[0]
    return b_min, b_max


def car_matches_powertrain(car: Dict[str, Any], target_power: str) -> bool:
    meta = car.get("metadata") if isinstance(car.get("metadata"), dict) else {}
    car_power = str(
        car.get("powertrain_type") or car.get("power_type") or meta.get("powertrain_type") or ""
    ).lower()
    if not car_power:
        return True
    t = target_power.lower()
    if any(k in t for k in ("纯电", "bev", "ev")):
        return any(k in car_power for k in ("纯电", "bev", "ev"))
    if any(k in t for k in ("增程", "reev")):
        return any(k in car_power for k in ("增程", "reev"))
    if any(k in t for k in ("插混", "phev", "混动")):
        return any(k in car_power for k in ("插混", "phev", "混动", "dm-i"))
    if any(k in t for k in ("燃油", "汽油", "ice")):
        return any(k in car_power for k in ("燃油", "汽油", "ice"))
    return t in car_power


def node_grade_retrieval(agent: Any, state: AgentGraphState) -> Dict[str, Any]:
    """CRAG Grader: verify retrieved cars are non-empty and respect hard constraints."""
    if state.get("voice_mode"):
        return {"retrieval_grade_passed": True, "retrieval_grade_reason": "voice_hotpath_bypass"}
    sess = state["session_state"].model_copy(deep=True)
    retries = int(state.get("retrieval_retries", 0))

    with node_cost_context(sess.session_id, AgentNodeRole.GRADER):
        if state.get("retrieved_cars"):
            return {"retrieval_grade_passed": True, "retrieval_grade_reason": "pre_retrieved"}
        if sess.stage not in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
            return {"retrieval_grade_passed": True, "retrieval_grade_reason": "non_selection_stage"}

        backend_available = (agent.retriever is not None) or ServiceContainer.has_rag_service()
        cars = sess.matched_cars or []

        if not cars:
            if not backend_available:
                return {"retrieval_grade_passed": True, "retrieval_grade_reason": "no_backend_configured"}
            if retries < MAX_CRAG_RETRIES:
                return {"retrieval_grade_passed": False, "retrieval_grade_reason": "召回结果为空"}
            note = "[CRAG检索提示] 放宽次要条件后仍未命中精确车型，请礼貌引导客户适当放宽预算或车型条件。"
            grade_events: List[AnyDialogueEvent] = []
            if note not in sess.system_notes:
                sess.system_notes.append(note)
                grade_events.append(
                    SystemNoteAdded(
                        turn_id=int(getattr(sess, "turn_count", 0)),
                        source="crag_grader",
                        note=note,
                    )
                )
            enqueue_agent_dlq(
                task_type="zero_hit",
                session_id=sess.session_id,
                checkpoint_id=sess.session_id,
                trace_id=sess.trace_id,
                user_message=state.get("safe_message") or state.get("user_message", ""),
                stage=sess.stage.value,
                error_message="CRAG retrieval exhausted with 0 matched vehicles",
                error_category="rag_zero_hit",
                context_snapshot={"explicit_needs": sess.needs.explicit.model_dump(exclude_none=True)},
            )
            return {
                "events": grade_events,
                "session_state": sess,
                "retrieval_grade_passed": True,
                "retrieval_grade_reason": "exhausted_empty",
            }

        b_min, b_max = extract_budget_bounds(sess)
        target_power = (sess.needs.explicit.powertrain_type or "").strip()
        target_brand = (sess.needs.explicit.brand or "").strip()

        reasons: List[str] = []
        if b_max is not None:
            budget_ok = False
            has_any_price = False
            for car in cars:
                meta = car.get("metadata") if isinstance(car.get("metadata"), dict) else {}
                p_raw = (
                    car.get("price_wan")
                    or car.get("msrp_wan")
                    or car.get("price")
                    or meta.get("price")
                )
                if p_raw is not None:
                    m = re.search(r"(\d+(?:\.\d+)?)", str(p_raw))
                    if m:
                        has_any_price = True
                        p_val = float(m.group(1))
                        if p_val > 1000:
                            p_val /= 10000.0
                        low_ok = (b_min is None) or (p_val >= b_min * 0.8)
                        high_ok = p_val <= b_max * 1.2
                        if low_ok and high_ok:
                            budget_ok = True
                            break
            if has_any_price and not budget_ok:
                reasons.append(f"召回车型价格均超出预算约束 ({b_max}万)")

        if target_power and not any(car_matches_powertrain(c, target_power) for c in cars):
            reasons.append(f"召回车型动力类型均不符合 '{target_power}'")

        if target_brand and state.get("topic_intent") != UserDialogueIntent.SPEC_COMPARISON.value:
            brand_ok = any(
                target_brand.lower() in str(c.get("brand") or c.get("car_model") or "").lower()
                for c in cars
            )
            if not brand_ok:
                reasons.append(f"召回车型品牌均不符合 '{target_brand}'")

        if reasons and retries < MAX_CRAG_RETRIES and backend_available:
            return {
                "retrieval_grade_passed": False,
                "retrieval_grade_reason": "; ".join(reasons),
            }

        grade_events = []
        if reasons and retries >= MAX_CRAG_RETRIES:
            note = f"[CRAG检索提示] 已尝试放宽次要条件重搜，但仍存在约束偏差（{'; '.join(reasons)}），请如实向客户说明并给出最接近的备选。"
            if note not in sess.system_notes:
                sess.system_notes.append(note)
                grade_events.append(
                    SystemNoteAdded(
                        turn_id=int(getattr(sess, "turn_count", 0)),
                        source="crag_grader",
                        note=note,
                    )
                )

        return {
            "events": grade_events,
            "session_state": sess,
            "retrieval_grade_passed": True,
            "retrieval_grade_reason": "passed" if not reasons else "exhausted_with_partial_match",
        }


def route_after_grade(
    agent: Any, state: AgentGraphState
) -> Literal["rewrite_query", "run_plugins_and_subdag", "safe_degrade"]:
    within_budget, _ = check_step_budget(int(state.get("step_count", 0)), agent.budget_config)
    if not within_budget:
        return "safe_degrade"
    if (
        not state.get("retrieval_grade_passed", True)
        and int(state.get("retrieval_retries", 0)) < agent.budget_config.max_crag_retries
    ):
        return "rewrite_query"
    return "run_plugins_and_subdag"


def node_rewrite_query(state: AgentGraphState) -> Dict[str, Any]:
    """Relax secondary constraints and rewrite retrieval query for CRAG retry."""
    sess = state["session_state"]
    retries = int(state.get("retrieval_retries", 0)) + 1
    explicit_dict = sess.needs.explicit.model_dump(exclude_none=True)

    relaxed = {
        k: v
        for k, v in explicit_dict.items()
        if v and k not in ("design_style", "seat_layout", "autonomous_driving_level", "drive_type")
    }
    if retries == 1:
        relaxed.pop("brand", None)
        parts = [
            str(relaxed.get(k))
            for k in ("price", "powertrain_type", "vehicle_category_bottom")
            if relaxed.get(k)
        ]
        new_query = " ".join(parts) or state.get("safe_message") or "推荐新能源或家用车型"
    else:
        relaxed.pop("brand", None)
        relaxed.pop("powertrain_type", None)
        if "budget_max" in relaxed and isinstance(relaxed["budget_max"], (int, float)):
            relaxed["budget_max"] = round(float(relaxed["budget_max"]) * 1.2, 1)
        new_query = (
            f"{relaxed.get('vehicle_category_bottom', '')} {relaxed.get('price', '')}".strip()
            or "高性价比热门车型推荐"
        )

    logger.info(
        f"[{sess.session_id}] CRAG rewrite #{retries} (reason: {state.get('retrieval_grade_reason')}) -> '{new_query}'"
    )
    trace = [*list(state.get("execution_trace") or []), "rewrite_query"]
    return {
        "retrieval_retries": retries,
        "retrieval_query_override": new_query,
        "retrieval_relaxed_constraints": relaxed,
        "step_count": int(state.get("step_count", 0)) + 1,
        "execution_trace": trace,
    }
