"""
Production Observability, Metrics & Step-Level Error Tracing Engine for AutoVend Agent.

Tracks:
1. Success Rate & Step Completion Rate
2. Latency (p50, p95, mean latency per step type)
3. Tool Invocation Counts & Tool Failure Distribution
4. Step-Level Error Taxonomy (PLANNING_ERROR, EXTRACTION_ERROR, TOOL_EXECUTION_ERROR, RETRIEVAL_ERROR, GENERATION_ERROR)
5. Token Usage & Cost Attribution (Input/Output Tokens, Cost in USD)
"""

import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_METRICS_LOG_FILE = PROJECT_ROOT / "evaluation" / "results" / "production_observability.jsonl"


class StepType(str, Enum):
    """Categorization of agent processing steps."""

    PLANNING = "planning"  # SOP stage arbitration & transition
    EXTRACTION = "extraction"  # Profile & needs extraction
    TOOL_EXECUTION = "tool_execution"  # Tool dispatch & execution
    RETRIEVAL = "retrieval"  # RAG candidate search
    RESPONSE_GENERATION = "response_generation"  # LLM dialogue reply


class ErrorCategory(str, Enum):
    """Taxonomy of step-level errors."""

    PLANNING_ERROR = "planning_error"
    EXTRACTION_ERROR = "extraction_error"
    TOOL_EXECUTION_ERROR = "tool_execution_error"
    RETRIEVAL_ERROR = "retrieval_error"
    GENERATION_ERROR = "generation_error"
    TIMEOUT_ERROR = "timeout_error"
    SECURITY_REJECTION = "security_rejection"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class StepTraceRecord:
    """Detailed trace record for one step execution."""

    trace_id: str
    session_id: str
    step_type: StepType
    step_name: str
    success: bool
    latency_s: float
    error_category: Optional[ErrorCategory] = None
    error_message: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "step_type": self.step_type.value,
            "step_name": self.step_name,
            "success": self.success,
            "latency_s": round(self.latency_s, 4),
            "error_category": self.error_category.value if self.error_category else None,
            "error_message": self.error_message,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "details": self.details,
            "timestamp": self.timestamp,
        }


class ProductionObservabilityCollector:
    """
    In-memory and JSONL-persisted Observability Collector for production metrics.
    """

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = Path(log_path) if log_path else DEFAULT_METRICS_LOG_FILE
        self.records: List[StepTraceRecord] = []

    def record_step(
        self,
        trace_id: str,
        session_id: str,
        step_type: StepType,
        step_name: str,
        success: bool,
        latency_s: float,
        error_category: Optional[ErrorCategory] = None,
        error_message: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
    ) -> StepTraceRecord:
        """Record and log one step execution trace."""
        record = StepTraceRecord(
            trace_id=trace_id,
            session_id=session_id,
            step_type=step_type,
            step_name=step_name,
            success=success,
            latency_s=latency_s,
            error_category=error_category,
            error_message=error_message,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=cost_usd,
            details=details or {},
            timestamp=time.time(),
        )
        self.records.append(record)

        if not success:
            logger.warning(
                f"[OBSERVABILITY] [{step_type.value.upper()} FAILED] session={session_id} trace={trace_id} "
                f"step={step_name} category={error_category}: {error_message}"
            )

        self._persist_record(record)
        return record

    def _persist_record(self, record: StepTraceRecord) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.error(f"Failed to write observability record: {exc}")

    def compute_summary_metrics(self) -> Dict[str, Any]:
        """Compute aggregated production metrics across all recorded traces."""
        if not self.records:
            return {"sample_size": 0, "overall_success_rate": 1.0}

        total_steps = len(self.records)
        successful_steps = sum(1 for r in self.records if r.success)
        overall_success_rate = successful_steps / total_steps

        latencies = [r.latency_s for r in self.records]
        mean_latency = statistics.mean(latencies)
        sorted_latencies = sorted(latencies)
        p50_latency = sorted_latencies[int(total_steps * 0.50)]
        p95_latency = sorted_latencies[int(total_steps * 0.95)] if total_steps >= 20 else max(latencies)

        # Tool invocation metrics
        tool_records = [r for r in self.records if r.step_type == StepType.TOOL_EXECUTION]
        tool_counts: Dict[str, int] = {}
        tool_success: Dict[str, int] = {}

        for tr in tool_records:
            tool_name = tr.details.get("tool", tr.step_name)
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
            if tr.success:
                tool_success[tool_name] = tool_success.get(tool_name, 0) + 1

        tool_stats = {
            name: {
                "count": count,
                "success_rate": round(tool_success.get(name, 0) / count, 4),
            }
            for name, count in tool_counts.items()
        }

        # Step error distribution
        error_records = [r for r in self.records if not r.success]
        error_distribution: Dict[str, int] = {}
        for er in error_records:
            cat = er.error_category.value if er.error_category else "unknown_error"
            error_distribution[cat] = error_distribution.get(cat, 0) + 1

        # Token & cost attribution
        total_prompt_tokens = sum(r.prompt_tokens for r in self.records)
        total_completion_tokens = sum(r.completion_tokens for r in self.records)
        total_cost_usd = sum(r.estimated_cost_usd for r in self.records)

        return {
            "sample_size": total_steps,
            "overall_success_rate": round(overall_success_rate, 4),
            "latency_seconds": {
                "mean": round(mean_latency, 4),
                "p50": round(p50_latency, 4),
                "p95": round(p95_latency, 4),
            },
            "tool_metrics": {
                "total_tool_calls": len(tool_records),
                "by_tool": tool_stats,
            },
            "error_taxonomy_counts": error_distribution,
            "cost_and_tokens": {
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "estimated_cost_usd": round(total_cost_usd, 6),
            },
        }

    def generate_markdown_dashboard(self) -> str:
        """Format metrics into a production observability dashboard report."""
        metrics = self.compute_summary_metrics()
        if metrics["sample_size"] == 0:
            return "# 生产环境 Agent 可观测性指标报告\n*尚无可用的步骤追踪记录*"

        lat = metrics["latency_seconds"]
        cost = metrics["cost_and_tokens"]

        lines = [
            "# 生产环境 Agent 可观测性指标面板 (Production Observability Dashboard)",
            f"*分析样本数: {metrics['sample_size']} 条步骤追踪日志*",
            "",
            "## 1. 核心 SLA 与成功率指标",
            "| 监控维度 | 统计数值 | 目标 SLA / 说明 |",
            "|---|---|---|",
            f"| **步骤总体成功率** | **{metrics['overall_success_rate'] * 100:.2f}%** | 目标 ≥ 99.0% |",
            f"| **平均端到端延迟 (Mean)** | **{lat['mean']:.4f} s** | P50 耗时参考 |",
            f"| **P50 延迟** | **{lat['p50']:.4f} s** | 正常中位数开销 |",
            f"| **P95 尾部延迟** | **{lat['p95']:.4f} s** | 目标 ≤ 3.5s |",
            "",
            "## 2. 工具调用与成功率统计 (Tool Invocation Stats)",
            "| 工具名称 | 调用总次数 | 成功率 | 状态 |",
            "|---|---|---|---|",
        ]

        tool_metrics = metrics["tool_metrics"]
        if tool_metrics["by_tool"]:
            for name, stats in tool_metrics["by_tool"].items():
                lines.append(
                    f"| `{name}` | {stats['count']} | **{stats['success_rate'] * 100:.1f}%** | {'🟢 正常' if stats['success_rate'] >= 0.9 else '⚠️ 告警'} |"
                )
        else:
            lines.append("| (无工具调用记录) | 0 | N/A | N/A |")

        lines.extend(
            [
                "",
                "## 3. 步骤级故障归因分类 (Step-Level Error Taxonomy)",
                "| 故障归因分类 (Error Category) | 出现频次 | 说明 / 告警处理 |",
                "|---|---|---|",
            ]
        )

        errors = metrics["error_taxonomy_counts"]
        if errors:
            for cat, count in errors.items():
                lines.append(f"| `{cat}` | {count} 次 | 精准定位到步骤节点 |")
        else:
            lines.append("| `无运行异常` | 0 次 | 运行环境 100% 健康 |")

        lines.extend(
            [
                "",
                "## 4. Token 消费与成本归因 (Cost & Token Attribution)",
                "| 资源指标 | 统计用量 |",
                "|---|---|",
                f"| **输入 Prompt Tokens** | {cost['total_prompt_tokens']:,} |",
                f"| **输出 Completion Tokens** | {cost['total_completion_tokens']:,} |",
                f"| **总 Token 消耗** | {cost['total_tokens']:,} |",
                f"| **估算 API 成本 (USD)** | **${cost['estimated_cost_usd']:.6f}** |",
            ]
        )

        return "\n".join(lines)


# Global singleton instance
observability_collector = ProductionObservabilityCollector()
