"""
Tests for Production Observability Collector, Step-level Error Tracing and Agent Evaluator.
"""

import pytest
from pathlib import Path

from src.eval.agent_evaluator import AgentEvaluator
from src.eval.golden_agent_dataset import load_golden_agent_dataset
from src.utils.observability import ErrorCategory, ProductionObservabilityCollector, StepType


class TestObservabilityAndAgentEval:
    def test_production_observability_collector(self, tmp_path):
        """Test recording step traces, latencies, tool counts, error taxonomy and cost."""
        log_file = tmp_path / "obs.jsonl"
        collector = ProductionObservabilityCollector(log_path=log_file)

        collector.record_step(
            trace_id="t1",
            session_id="s1",
            step_type=StepType.PLANNING,
            step_name="advance_stage",
            success=True,
            latency_s=0.15,
            prompt_tokens=500,
            completion_tokens=50,
            cost_usd=0.001,
        )

        collector.record_step(
            trace_id="t1",
            session_id="s1",
            step_type=StepType.TOOL_EXECUTION,
            step_name="record_profile",
            success=False,
            latency_s=0.08,
            error_category=ErrorCategory.TOOL_EXECUTION_ERROR,
            error_message="Missing required field",
            details={"tool": "record_profile"},
        )

        summary = collector.compute_summary_metrics()
        assert summary["sample_size"] == 2
        assert summary["overall_success_rate"] == 0.5
        assert summary["tool_metrics"]["total_tool_calls"] == 1
        assert summary["error_taxonomy_counts"]["tool_execution_error"] == 1

        md_report = collector.generate_markdown_dashboard()
        assert "# 生产环境 Agent 可观测性指标面板" in md_report
        assert "record_profile" in md_report

    def test_golden_dataset_loading(self):
        """Test loading Agent Golden Dataset."""
        cases = load_golden_agent_dataset()
        assert len(cases) >= 10
        typical_cases = [c for c in cases if c.category == "typical"]
        edge_cases = [c for c in cases if c.category == "edge_case"]
        assert len(typical_cases) >= 4
        assert len(edge_cases) >= 6

    def test_agent_evaluator_benchmark(self):
        """Test running multi-dimensional Agent benchmark."""
        evaluator = AgentEvaluator()
        summary = evaluator.run_benchmark()

        assert summary.sample_size >= 10
        assert summary.overall_pass_rate >= 0.9
        assert summary.mean_planning_accuracy >= 0.9
        assert summary.mean_tool_accuracy >= 0.9
        assert summary.mean_security_gate_accuracy >= 0.9

        md_report = summary.to_markdown_table()
        assert "# AutoVend Agent 多维能力评估基准报告" in md_report
        assert "TYP_01_WELCOME_PROFILE" in md_report
        assert "EDGE_01_BUDGET_BRAND_CONFLICT" in md_report
