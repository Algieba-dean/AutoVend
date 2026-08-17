"""
Stage-specific Sub-DAG workflow definitions.

Implements complex local stage DAG topologies for:
- Stage.CAR_SELECTION: Multi-car comparison, spec API lookup, feature matrix decision.
- Stage.RESERVATION_4S: Preliminary qualification verification, 4S dealer inventory API, slot check decision.
"""

from typing import Any, Dict, Optional
from src.agent.schemas import Stage
from src.agent.subdag.executor import SubDAGExecutor


def create_car_selection_dag() -> SubDAGExecutor:
    """
    Sub-DAG definition for Stage.CAR_SELECTION (Multi-car contrast & selection).
    """
    definition = {
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "data": {"description": "Start CAR_SELECTION Sub-DAG"},
            },
            {
                "id": "fetch_specs",
                "type": "api",
                "data": {
                    "api_name": "car_specs_comparison",
                    "url": "https://api.autovend.internal/vehicles/specs",
                },
            },
            {
                "id": "check_matched_cars",
                "type": "condition",
                "data": {
                    "condition_type": "variable",
                    "variable": "matched_cars",
                    "operator": "isNotEmpty",
                },
            },
            {
                "id": "generate_comparison_matrix",
                "type": "decision",
                "data": {
                    "action": "add_comparison_note",
                    "note": (
                        "[Sub-DAG: 多车对比分析] 已从 API 调取候选车型的详细技术参数。"
                        "请在回复中为客户提供直观的多车对比（包含续航、零百加速、智能驾舱与售价），"
                        "并突出最符合客户需求的推荐车型。"
                    ),
                },
            },
            {
                "id": "recommendation_fallback",
                "type": "decision",
                "data": {
                    "action": "add_fallback_note",
                    "note": "[Sub-DAG: 车型推荐提示] 尚未检索到符合条件的具体车型，请先向客户核实续航或预算要求。",
                },
            },
            {
                "id": "end",
                "type": "end",
                "data": {"description": "End CAR_SELECTION Sub-DAG"},
            },
        ],
        "edges": [
            {"source": "start", "target": "fetch_specs"},
            {"source": "fetch_specs", "target": "check_matched_cars"},
            {
                "source": "check_matched_cars",
                "target": "generate_comparison_matrix",
                "sourceHandle": "true",
            },
            {
                "source": "check_matched_cars",
                "target": "recommendation_fallback",
                "sourceHandle": "false",
            },
            {"source": "generate_comparison_matrix", "target": "end"},
            {"source": "recommendation_fallback", "target": "end"},
        ],
    }
    return SubDAGExecutor(stage=Stage.CAR_SELECTION, definition=definition)


def create_reservation_4s_dag() -> SubDAGExecutor:
    """
    Sub-DAG definition for Stage.RESERVATION_4S (Qualification preliminary check & 4S stock check).
    """
    definition = {
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "data": {"description": "Start RESERVATION_4S Sub-DAG"},
            },
            {
                "id": "verify_qualification",
                "type": "api",
                "data": {
                    "api_name": "qualification_check",
                    "url": "https://api.autovend.internal/customer/qualification",
                },
            },
            {
                "id": "check_qual_result",
                "type": "condition",
                "data": {
                    "condition_type": "variable",
                    "variable": "verify_qualification.body.eligible",
                    "operator": "equals",
                    "compare_value": "True",
                },
            },
            {
                "id": "check_dealer_stock",
                "type": "api",
                "data": {
                    "api_name": "dealer_inventory_check",
                    "url": "https://api.autovend.internal/dealer/inventory",
                },
            },
            {
                "id": "finalize_reservation_prep",
                "type": "decision",
                "data": {
                    "action": "prefill_and_note",
                    "note": (
                        "[Sub-DAG: 4S资质初审与库存查询] 客户试驾资质初审通过，4S店现车及试驾时段已确认。"
                        "请向客户确认具体的试驾时间、地点及联系电话。"
                    ),
                    "updates": {
                        "reservation_location": "AutoVend 旗舰 4S 体验中心",
                        "salesman": "高级销售顾问 Alex",
                    },
                },
            },
            {
                "id": "qualification_pending_note",
                "type": "decision",
                "data": {
                    "action": "add_pending_note",
                    "note": "[Sub-DAG: 资质初审提示] 资质初审缺少必要的联系人或试驾人信息，请提示客户提供姓名和手机号。",
                },
            },
            {
                "id": "end",
                "type": "end",
                "data": {"description": "End RESERVATION_4S Sub-DAG"},
            },
        ],
        "edges": [
            {"source": "start", "target": "verify_qualification"},
            {"source": "verify_qualification", "target": "check_qual_result"},
            {
                "source": "check_qual_result",
                "target": "check_dealer_stock",
                "sourceHandle": "true",
            },
            {
                "source": "check_qual_result",
                "target": "qualification_pending_note",
                "sourceHandle": "false",
            },
            {"source": "check_dealer_stock", "target": "finalize_reservation_prep"},
            {"source": "finalize_reservation_prep", "target": "end"},
            {"source": "qualification_pending_note", "target": "end"},
        ],
    }
    return SubDAGExecutor(stage=Stage.RESERVATION_4S, definition=definition)


_STAGE_DAG_MAP: Dict[Stage, SubDAGExecutor] = {}


def get_stage_subdag(stage: Stage) -> Optional[SubDAGExecutor]:
    """Get the registered Sub-DAG executor for a given stage, if any."""
    if stage not in _STAGE_DAG_MAP:
        if stage == Stage.CAR_SELECTION:
            _STAGE_DAG_MAP[stage] = create_car_selection_dag()
        elif stage == Stage.RESERVATION_4S:
            _STAGE_DAG_MAP[stage] = create_reservation_4s_dag()

    return _STAGE_DAG_MAP.get(stage)
