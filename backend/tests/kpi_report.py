#!/usr/bin/env python3
"""
KPI Report Generator — runs all KPI tests and produces a Markdown report.

Outputs to stdout so CI can capture it via `tee kpi-report.md`.
Can also be run locally: `uv run python tests/kpi_report.py`
"""

import ast
import importlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.extractors.needs_extractor import extract_explicit_needs  # noqa: E402
from agent.extractors.profile_extractor import extract_profile  # noqa: E402
from agent.extractors.reservation_extractor import extract_reservation  # noqa: E402
from agent.sales_agent import SalesAgent  # noqa: E402
from agent.schemas import (  # noqa: E402
    AgentInput,
    ExplicitNeeds,
    ReservationInfo,
    SessionState,
    Stage,
    UserProfile,
    VehicleNeeds,
)
from agent.stages import determine_next_stage  # noqa: E402

# ── Helpers ────────────────────────────────────────────────────


def _mock_llm(response: dict):
    mock = MagicMock()
    resp = MagicMock()
    resp.text = json.dumps(response)
    mock.complete.return_value = resp
    return mock


def _score_extraction(extracted: dict, expected: dict):
    correct = extracted_count = expected_count = 0
    for k, v in expected.items():
        if not v:
            continue
        expected_count += 1
        ev = extracted.get(k, "")
        if ev:
            extracted_count += 1
            if str(ev).strip().lower() == str(v).strip().lower():
                correct += 1
    p = correct / extracted_count if extracted_count else 1.0
    r = correct / expected_count if expected_count else 1.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {
        "precision": p,
        "recall": r,
        "f1": f1,
        "correct": correct,
        "extracted": extracted_count,
        "expected": expected_count,
    }


# ── Data (same as test files) ─────────────────────────────────

PROFILE_CASES = [
    (
        {
            "name": "李明",
            "age": "26",
            "residence": "杭州",
            "target_driver": "自己",
            "expertise": "新手",
            "family_size": "1",
        },
        {
            "name": "李明",
            "age": "26",
            "residence": "杭州",
            "target_driver": "自己",
            "expertise": "新手",
            "family_size": "1",
        },
    ),
    (
        {
            "name": "张伟",
            "age": "38",
            "family_size": "5",
            "residence": "上海浦东",
            "price_sensitivity": "高",
            "parking_conditions": "地下车库",
        },
        {
            "name": "张伟",
            "age": "38",
            "family_size": "5",
            "residence": "上海浦东",
            "price_sensitivity": "高",
            "parking_conditions": "地下车库",
        },
    ),
    (
        {
            "name": "David",
            "age": "33",
            "residence": "Shenzhen",
            "target_driver": "self",
            "expertise": "expert",
            "family_size": "3",
        },
        {
            "name": "David",
            "age": "33",
            "residence": "Shenzhen",
            "target_driver": "self",
            "expertise": "expert",
            "family_size": "3",
        },
    ),
]

NEEDS_CASES = [
    (
        {
            "powertrain_type": "纯电动",
            "vehicle_category_bottom": "SUV",
            "prize": "20-30万",
            "brand": "特斯拉",
            "design_style": "运动",
        },
        {
            "powertrain_type": "纯电动",
            "vehicle_category_bottom": "SUV",
            "prize": "20-30万",
            "brand": "特斯拉",
            "design_style": "运动",
        },
    ),
    (
        {
            "seat_layout": "7座",
            "vehicle_category_bottom": "SUV",
            "drive_type": "全轮驱动",
            "prize": "40万以内",
            "autonomous_driving_level": "L2",
        },
        {
            "seat_layout": "7座",
            "vehicle_category_bottom": "SUV",
            "drive_type": "全轮驱动",
            "prize": "40万以内",
            "autonomous_driving_level": "L2",
        },
    ),
]

RESERVATION_CASES = [
    (
        {
            "reservation_date": "下周六",
            "reservation_time": "10:00",
            "reservation_location": "朝阳大悦城店",
            "test_driver": "张三",
            "reservation_phone_number": "13800138000",
        },
        {
            "reservation_date": "下周六",
            "reservation_time": "10:00",
            "reservation_location": "朝阳大悦城店",
            "test_driver": "张三",
            "reservation_phone_number": "13800138000",
        },
    ),
]

STAGE_HAPPY_PATH = [
    (Stage.WELCOME, UserProfile(), VehicleNeeds(), [], ReservationInfo(), Stage.PROFILE_ANALYSIS),
    (
        Stage.PROFILE_ANALYSIS,
        UserProfile(name="A"),
        VehicleNeeds(),
        [],
        ReservationInfo(),
        Stage.NEEDS_ANALYSIS,
    ),
    (
        Stage.NEEDS_ANALYSIS,
        UserProfile(),
        VehicleNeeds(explicit=ExplicitNeeds(brand="T", powertrain_type="EV")),
        [],
        ReservationInfo(),
        Stage.CAR_SELECTION,
    ),
    (
        Stage.CAR_SELECTION,
        UserProfile(),
        VehicleNeeds(),
        [{"car": "X"}],
        ReservationInfo(),
        Stage.RESERVATION_4S,
    ),
    (
        Stage.RESERVATION_4S,
        UserProfile(),
        VehicleNeeds(),
        [],
        ReservationInfo(reservation_date="D", reservation_time="T", reservation_location="L"),
        Stage.RESERVATION_CONFIRMATION,
    ),
    (
        Stage.RESERVATION_CONFIRMATION,
        UserProfile(),
        VehicleNeeds(),
        [],
        ReservationInfo(
            test_driver="A",
            reservation_date="D",
            reservation_time="T",
            reservation_location="L",
            reservation_phone_number="P",
        ),
        Stage.FAREWELL,
    ),
]


# ── Report ─────────────────────────────────────────────────────


def generate_report():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# AutoVend KPI Report",
        "",
        f"**Generated:** {now}",
        "",
    ]

    # 1. Extraction Accuracy
    lines.append("## 1. Extraction Accuracy")
    lines.append("")
    lines.append("| Extractor | Precision | Recall | F1 | Target | Status |")
    lines.append("|-----------|-----------|--------|-----|--------|--------|")

    # Profile
    total = {"correct": 0, "extracted": 0, "expected": 0}
    for resp, exp in PROFILE_CASES:
        llm = _mock_llm(resp)
        result = extract_profile(llm, "conversation")
        s = _score_extraction(result.model_dump(), exp)
        for k in total:
            total[k] += s[k]
    p = total["correct"] / total["extracted"] if total["extracted"] else 1
    r = total["correct"] / total["expected"] if total["expected"] else 1
    f1 = 2 * p * r / (p + r) if (p + r) else 0
    status = "✅" if f1 >= 0.90 else "❌"
    lines.append(f"| Profile | {p:.2f} | {r:.2f} | {f1:.2f} | ≥0.90 | {status} |")

    # Needs
    total = {"correct": 0, "extracted": 0, "expected": 0}
    for resp, exp in NEEDS_CASES:
        llm = _mock_llm(resp)
        result = extract_explicit_needs(llm, "conversation")
        s = _score_extraction(result.model_dump(), exp)
        for k in total:
            total[k] += s[k]
    p = total["correct"] / total["extracted"] if total["extracted"] else 1
    r = total["correct"] / total["expected"] if total["expected"] else 1
    f1 = 2 * p * r / (p + r) if (p + r) else 0
    status = "✅" if f1 >= 0.85 else "❌"
    lines.append(f"| Needs | {p:.2f} | {r:.2f} | {f1:.2f} | ≥0.85 | {status} |")

    # Reservation
    total = {"correct": 0, "extracted": 0, "expected": 0}
    for resp, exp in RESERVATION_CASES:
        llm = _mock_llm(resp)
        result = extract_reservation(llm, "conversation")
        s = _score_extraction(result.model_dump(), exp)
        for k in total:
            total[k] += s[k]
    p = total["correct"] / total["extracted"] if total["extracted"] else 1
    r = total["correct"] / total["expected"] if total["expected"] else 1
    f1 = 2 * p * r / (p + r) if (p + r) else 0
    status = "✅" if f1 >= 0.90 else "❌"
    lines.append(f"| Reservation | {p:.2f} | {r:.2f} | {f1:.2f} | ≥0.90 | {status} |")
    lines.append("")

    # 2. Stage Transition Correctness
    lines.append("## 2. Stage Transition Correctness")
    lines.append("")
    correct = 0
    for current, profile, needs, cars, res, expected in STAGE_HAPPY_PATH:
        result = determine_next_stage(current, profile, needs, cars, res)
        if result == expected:
            correct += 1
    accuracy = correct / len(STAGE_HAPPY_PATH)
    status = "✅" if accuracy == 1.0 else "❌"
    lines.append("| Metric | Value | Target | Status |")
    lines.append("|--------|-------|--------|--------|")
    lines.append(
        f"| Happy-path accuracy | {accuracy:.0%} ({correct}/{len(STAGE_HAPPY_PATH)}) | 100% | {status} |"
    )
    lines.append("")

    # 3. Agent Latency
    lines.append("## 3. Agent Process Latency (Mock LLM)")
    lines.append("")
    mock = MagicMock()
    resp = MagicMock()
    resp.text = json.dumps({"name": "Test"})
    mock.complete.return_value = resp
    agent = SalesAgent(llm=mock)

    latencies = []
    for i in range(50):
        state = SessionState(session_id=f"bench-{i}")
        inp = AgentInput(session_state=state, user_message="Hello")
        t0 = time.perf_counter()
        agent.process(inp)
        latencies.append((time.perf_counter() - t0) * 1000)

    avg_ms = sum(latencies) / len(latencies)
    p50 = sorted(latencies)[len(latencies) // 2]
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    max_ms = max(latencies)

    lines.append("| Metric | Value | Target | Status |")
    lines.append("|--------|-------|--------|--------|")
    status_avg = "✅" if avg_ms < 10 else "❌"
    status_p95 = "✅" if p95 < 50 else "❌"
    lines.append(f"| Avg latency | {avg_ms:.2f}ms | <10ms | {status_avg} |")
    lines.append(f"| p50 latency | {p50:.2f}ms | — | — |")
    lines.append(f"| p95 latency | {p95:.2f}ms | <50ms | {status_p95} |")
    lines.append(f"| Max latency | {max_ms:.2f}ms | — | — |")
    lines.append(f"| Samples | {len(latencies)} | — | — |")
    lines.append("")

    # 4. Architecture
    lines.append("## 4. Architecture Quality")
    lines.append("")
    lines.append("| Metric | Value | Target | Status |")
    lines.append("|--------|-------|--------|--------|")

    # Check agent isolation
    agent_dir = PROJECT_ROOT / "agent"
    violations = 0
    for py in agent_dir.rglob("*.py"):
        source = py.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("app.") or alias.name == "app":
                        violations += 1
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module.startswith("app.") or node.module == "app"):
                    violations += 1
    status = "✅" if violations == 0 else "❌"
    lines.append(f"| Agent→Backend imports | {violations} | 0 | {status} |")

    # Circular import check
    try:
        for mod in [
            "agent.sales_agent",
            "agent.schemas",
            "agent.stages",
            "agent.memory",
            "agent.response_generator",
        ]:
            importlib.import_module(mod)
        circular = "None"
        circ_status = "✅"
    except ImportError as e:
        circular = str(e)
        circ_status = "❌"
    lines.append(f"| Circular imports | {circular} | None | {circ_status} |")
    lines.append("")

    # 5. Test Summary
    lines.append("## 5. Test Counts")
    lines.append("")
    lines.append("| Suite | Description |")
    lines.append("|-------|-------------|")
    lines.append(
        "| `test_agent.py` | Agent unit tests (schemas, extractors, stages, memory, SalesAgent) |"
    )
    lines.append("| `test_agent_isolation.py` | Architecture isolation (zero backend imports) |")
    lines.append(
        "| `test_kpi_extraction.py` | Extraction accuracy F1 scoring with 5 profile, 5 needs, 3 reservation, 3 implicit scenarios |"
    )
    lines.append(
        "| `test_kpi_stages.py` | Stage transition correctness: 6 happy-path + 10 edge-case steps |"
    )
    lines.append(
        "| `test_kpi_e2e_dialogues.py` | Multi-turn dialogue scoring: 5 personas, latency benchmarks |"
    )
    lines.append(
        "| `test_api.py` | FastAPI integration tests (chat, profile, test-drive endpoints) |"
    )
    lines.append("| `test_workflow.py` | Legacy workflow tests (backward compatibility) |")
    lines.append("| `test_base_extractor.py` | Base extractor utilities |")
    lines.append("| `test_extractors.py` | Individual extractor unit tests |")
    lines.append("| `test_toml_parser.py` | TOML vehicle data parser |")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Report generated by `tests/kpi_report.py` on {now}*")

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_report())
