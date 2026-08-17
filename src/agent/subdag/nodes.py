"""
Node Definitions for Sub-DAG Workflow Engine.

Implements Start, End, Condition, API, LLM, and Decision nodes.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple

from src.agent.subdag.context import SubDAGContext

logger = logging.getLogger(__name__)


class BaseSubDAGNode(ABC):
    """Abstract base class for all Sub-DAG node executors."""

    def __init__(self, node_id: str, node_type: str, config: Optional[Dict[str, Any]] = None):
        self.node_id = node_id
        self.node_type = node_type
        self.config = config or {}

    @abstractmethod
    def execute(self, context: SubDAGContext) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Execute the node logic.
        Returns: (output_dict, next_handle_id)
        """
        pass


class StartNode(BaseSubDAGNode):
    """Entry node of a Sub-DAG."""

    def execute(self, context: SubDAGContext) -> Tuple[Dict[str, Any], Optional[str]]:
        return {"status": "started", "stage": context.session_state.stage.value}, None


class EndNode(BaseSubDAGNode):
    """Terminal node of a Sub-DAG."""

    def execute(self, context: SubDAGContext) -> Tuple[Dict[str, Any], Optional[str]]:
        return {"status": "completed"}, None


class ConditionNode(BaseSubDAGNode):
    """
    Condition evaluation node supporting variable comparison, operators, or expressions.
    Returns handle_id: "true" or "false".
    """

    def execute(self, context: SubDAGContext) -> Tuple[Dict[str, Any], Optional[str]]:
        condition_type = self.config.get("condition_type", "variable")
        result = False

        if condition_type == "variable":
            var_path = self.config.get("variable", "")
            operator = self.config.get("operator", "equals")
            compare_val = context.resolve_template(str(self.config.get("compare_value", "")))
            var_val = context.get_variable(var_path)

            if operator == "equals":
                result = str(var_val).strip().lower() == str(compare_val).strip().lower()
            elif operator == "notEquals":
                result = str(var_val).strip().lower() != str(compare_val).strip().lower()
            elif operator == "contains":
                result = str(compare_val).lower() in str(var_val).lower()
            elif operator == "greaterThan":
                try:
                    result = float(var_val) > float(compare_val)
                except (ValueError, TypeError):
                    result = False
            elif operator == "lessThan":
                try:
                    result = float(var_val) < float(compare_val)
                except (ValueError, TypeError):
                    result = False
            elif operator == "isEmpty":
                result = not var_val
            elif operator == "isNotEmpty":
                result = bool(var_val)
            elif operator == "is_true":
                result = bool(var_val)

        elif condition_type == "custom":
            fn = self.config.get("custom_fn")
            if callable(fn):
                result = bool(fn(context))

        handle_id = "true" if result else "false"
        return {"result": result, "operator": self.config.get("operator"), "handle": handle_id}, handle_id


class APINode(BaseSubDAGNode):
    """
    API execution node.
    Simulates or performs external/internal API calls for vehicle specs, dealer inventory,
    or qualification verification.
    """

    def execute(self, context: SubDAGContext) -> Tuple[Dict[str, Any], Optional[str]]:
        api_name = self.config.get("api_name", "generic_api")
        url = context.resolve_template(self.config.get("url", ""))
        params = self.config.get("params", {})

        # Custom handler override if provided in config
        custom_handler = self.config.get("handler")
        if callable(custom_handler):
            res = custom_handler(context)
            return {"status_code": 200, "body": res, "api_name": api_name}, None

        # Standard built-in API handlers for AutoVend sales workflows
        if api_name == "car_specs_comparison" or "specs" in url:
            # Query vehicle technical specs & comparison matrix
            cars = context.session_state.matched_cars
            spec_data = []
            for car in cars:
                spec_data.append({
                    "model_name": car.get("model_name", "Standard Model"),
                    "brand": car.get("brand", "AutoVend"),
                    "price_range": car.get("price_range", car.get("price", "N/A")),
                    "powertrain": car.get("powertrain", car.get("engine", "Pure Electric / Hybrid")),
                    "range_km": car.get("electric_range", "600 km"),
                    "acceleration_0_100": car.get("acceleration", "4.5s"),
                    "autonomous_level": car.get("autonomous_level", "L2+ High-Speed NOA"),
                    "key_features": car.get("features", ["Smart Cockpit", "HUD", "Zero Gravity Seats"]),
                })
            return {
                "status_code": 200,
                "body": {"specs": spec_data, "count": len(spec_data)},
                "api_name": api_name,
            }, None

        elif api_name == "dealer_inventory_check" or "inventory" in url:
            # Query 4S dealer inventory & test drive slot availability
            cars = context.session_state.matched_cars
            target_car = cars[0].get("model_name", "Focus Vehicle") if cars else "Standard SUV"
            inventory_res = {
                "dealer_name": "AutoVend Flagship 4S Experience Center",
                "target_car": target_car,
                "in_stock": True,
                "available_colors": ["Pearl White", "Obsidian Black", "Cosmic Gray"],
                "test_drive_available": True,
                "available_time_slots": ["10:00 AM", "02:00 PM", "04:30 PM"],
                "assigned_salesman": "Senior Advisor - Alex",
            }
            return {
                "status_code": 200,
                "body": inventory_res,
                "api_name": api_name,
            }, None

        elif api_name == "qualification_check" or "qualification" in url:
            # Preliminary qualification & driver license verification
            user_profile = context.session_state.profile
            user_phone = user_profile.phone_number or context.session_state.reservation.reservation_phone_number
            user_name = user_profile.name or context.session_state.reservation.test_driver

            # Rules: Needs valid name or phone, or valid dialogue intent
            is_eligible = bool(user_name or user_phone or "试驾" in context.user_message or "预约" in context.user_message)
            qual_res = {
                "eligible": is_eligible,
                "driver_license_required": True,
                "age_limit_passed": True,
                "credit_pre_approval": "APPROVED",
                "notes": "Qualification verification passed. Ready for 4S appointment." if is_eligible else "Contact info needed.",
            }
            return {
                "status_code": 200,
                "body": qual_res,
                "api_name": api_name,
            }, None

        # Generic default response
        return {
            "status_code": 200,
            "body": {"message": f"API {api_name} executed successfully", "url": url},
            "api_name": api_name,
        }, None


class LLMNode(BaseSubDAGNode):
    """
    LLM reasoning or content generation node within Sub-DAG.
    """

    def execute(self, context: SubDAGContext) -> Tuple[Dict[str, Any], Optional[str]]:
        prompt = context.resolve_template(self.config.get("prompt", ""))
        llm = self.config.get("llm")

        response_text = ""
        if llm and hasattr(llm, "complete"):
            try:
                res = llm.complete(prompt)
                response_text = str(res.text if hasattr(res, "text") else res)
            except Exception as e:
                logger.error(f"Error executing LLMNode {self.node_id}: {e}")
                response_text = f"[LLM Evaluation]: Prompt processed for {self.node_id}"
        else:
            response_text = f"[Sub-DAG LLM Step]: Evaluated {self.node_id}"

        return {"llm_output": response_text}, None


class DecisionNode(BaseSubDAGNode):
    """
    Decision node that updates SessionState or adds system notes.
    """

    def execute(self, context: SubDAGContext) -> Tuple[Dict[str, Any], Optional[str]]:
        action = self.config.get("action", "add_note")
        note_template = self.config.get("note", "")

        if note_template:
            resolved_note = context.resolve_template(note_template)
            if resolved_note not in context.system_notes:
                context.system_notes.append(resolved_note)

        # Optional state field update
        updates = self.config.get("updates", {})
        for key, val in updates.items():
            resolved_val = context.resolve_template(str(val)) if isinstance(val, str) else val
            if key == "reservation_location" and not context.session_state.reservation.reservation_location:
                context.session_state.reservation.reservation_location = str(resolved_val)
            elif key == "salesman" and not context.session_state.reservation.salesman:
                context.session_state.reservation.salesman = str(resolved_val)

        return {"decision": action, "note_injected": bool(note_template)}, None
