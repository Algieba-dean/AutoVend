"""
AutoVend Agent Performance Evaluation Harness.

Runs all dialogue scenarios through the SalesAgent, scores each turn
and dialogue on multiple dimensions, and produces a comprehensive
evaluation report with per-dialogue scorecards.

Usage:
    python -m tests.performance.eval_harness
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from agent.sales_agent import SalesAgent
from agent.schemas import AgentInput, SessionState, Stage
from tests.performance.scenarios import ALL_SCENARIOS
from tests.performance.scoring import (
    DialogueScorecard,
    EvaluationReport,
    LatencyStats,
    TurnScore,
    score_extraction,
    score_information_gathering_rate,
    score_language_consistency,
    score_response_professionalism,
    score_response_relevance,
)

EVAL_RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "eval_results"


# ── Mock LLM Factory ─────────────────────────────────────────────────────────


def create_scenario_llm(scenario: dict) -> MagicMock:
    """
    Create a mock LLM that returns scenario-specific JSON for extractors
    and natural-sounding response text for generation prompts.

    The mock simulates realistic LLM behavior:
    - Extraction prompts → JSON matching scenario ground truth
    - Generation prompts → context-aware Chinese/English response
    """
    mock = MagicMock()
    profile_resp = scenario.get("profile_resp", {})
    needs_resp = scenario.get("needs_resp", {})
    implicit_resp = scenario.get("implicit_resp", {})
    reservation_resp = scenario.get("reservation_resp", {})

    # Pre-build response templates based on stage
    stage_responses = {
        "welcome": "您好！欢迎来到AutoVend智能选车助手。我是您的专属汽车顾问，请问您怎么称呼？",
        "profile": "感谢您的信息！为了更好地为您推荐车型，请问您主要在什么场景用车呢？",
        "needs": "了解了您的需求。根据您的偏好，我来为您筛选合适的车型。请问您对品牌有特别的偏好吗？",
        "selection": (
            "根据您的需求，我为您推荐以下车型。这些车都很好地匹配了您的要求，您觉得哪款更感兴趣？"
        ),
        "reservation": "好的，我来帮您安排试驾预约。请问您方便的日期和时间是？",
        "confirmation": "好的，我确认一下您的预约信息。请确认以上信息是否正确？",
        "farewell": "感谢您的咨询！祝您用车愉快，如有任何问题随时联系我们。再见！",
        "english_welcome": (
            "Hello! Welcome to AutoVend. I'm your dedicated automotive consultant. "
            "May I have your name please?"
        ),
        "english_profile": (
            "Thank you for sharing! To recommend the best options, "
            "could you tell me about your driving needs?"
        ),
        "english_needs": (
            "Great, I understand your requirements. Let me find the best matches for you. "
            "Any brand preferences?"
        ),
        "english_selection": (
            "Based on your needs, I'd recommend these models. They match your criteria well. "
            "Which one interests you?"
        ),
    }

    def side_effect(prompt):
        resp = MagicMock()
        p = prompt.lower()

        # Extraction prompts → JSON
        if "profile" in p and "extract" in p:
            resp.text = json.dumps(profile_resp)
        elif "vehicle requirements" in p or "explicit" in p or "vehicle needs" in p:
            resp.text = json.dumps(needs_resp)
        elif "deduce" in p or "implicit" in p:
            resp.text = json.dumps(implicit_resp)
        elif "reservation" in p and "extract" in p:
            resp.text = json.dumps(reservation_resp)
        else:
            # Generation prompt — detect stage and language
            is_english = "english" in p or "hello" in p or "hi " in p or "i'm" in p
            if "welcome" in p or "greet" in p:
                resp.text = (
                    stage_responses["english_welcome"] if is_english else stage_responses["welcome"]
                )
            elif "profile" in p and "missing" in p:
                resp.text = (
                    stage_responses["english_profile"] if is_english else stage_responses["profile"]
                )
            elif "needs" in p or "vehicle" in p and "explore" in p:
                resp.text = (
                    stage_responses["english_needs"] if is_english else stage_responses["needs"]
                )
            elif "recommend" in p or "matched" in p or "selection" in p:
                resp.text = (
                    stage_responses["english_selection"]
                    if is_english
                    else stage_responses["selection"]
                )
            elif "reservation" in p and "collect" in p:
                resp.text = stage_responses["reservation"]
            elif "confirm" in p:
                resp.text = stage_responses["confirmation"]
            elif "farewell" in p or "goodbye" in p:
                resp.text = stage_responses["farewell"]
            else:
                resp.text = stage_responses["welcome"]

        return resp

    mock.complete.side_effect = side_effect
    return mock


# ── Evaluation Runner ─────────────────────────────────────────────────────────


def evaluate_dialogue(scenario: dict) -> DialogueScorecard:
    """
    Run a single dialogue scenario through the agent and produce a scorecard.
    """
    llm = create_scenario_llm(scenario)
    agent = SalesAgent(llm=llm)
    state = SessionState(session_id=f"eval-{scenario['id']}")

    scorecard = DialogueScorecard(
        dialogue_id=scenario["id"],
        persona=scenario["persona"],
        category=scenario.get("category", "normal"),
        expected_final_stage=scenario.get("expected_final_stage", "car_selection_confirmation"),
        latency=LatencyStats(),
    )

    expected_profile = scenario.get("expected_profile", {})
    expected_needs = scenario.get("expected_needs", {})

    for turn_idx, turn in enumerate(scenario["turns"]):
        # Snapshot before
        profile_before = state.profile.model_dump()
        needs_before = state.needs.explicit.model_dump()

        # Process turn
        inp = AgentInput(
            session_state=state,
            user_message=turn["msg"],
        )
        t0 = time.perf_counter()
        result = agent.process(inp)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        state = result.session_state
        response = result.response_text

        # Snapshot after
        profile_after = state.profile.model_dump()
        needs_after = state.needs.explicit.model_dump()

        # Extract keywords from user message for relevance scoring
        context_keywords = [w for w in turn["msg"].split() if len(w) > 1]

        # Score this turn
        expected_stage_val = (
            turn["expected_stage"].value
            if isinstance(turn["expected_stage"], Stage)
            else turn["expected_stage"]
        )
        actual_stage_val = state.stage.value if isinstance(state.stage, Stage) else state.stage

        turn_score = TurnScore(
            turn_idx=turn_idx,
            user_message=turn["msg"],
            agent_response=response,
            expected_stage=expected_stage_val,
            actual_stage=actual_stage_val,
            stage_correct=(actual_stage_val == expected_stage_val),
            response_relevance=score_response_relevance(
                response, actual_stage_val, context_keywords
            ),
            language_consistency=score_language_consistency(turn["msg"], response),
            professionalism=score_response_professionalism(response),
            info_gathering_rate=score_information_gathering_rate(
                profile_before, profile_after, needs_before, needs_after
            ),
            latency_ms=elapsed_ms,
        )

        scorecard.turn_scores.append(turn_score)
        scorecard.stages_visited.append(actual_stage_val)
        scorecard.latency.values_ms.append(elapsed_ms)

    # Final state
    scorecard.total_turns = len(scenario["turns"])
    scorecard.final_profile = state.profile.model_dump()
    scorecard.final_needs_explicit = state.needs.explicit.model_dump()
    scorecard.final_reservation = state.reservation.model_dump()

    # Aggregate extraction scores
    if expected_profile:
        scorecard.profile_extraction = score_extraction(scorecard.final_profile, expected_profile)
    if expected_needs:
        scorecard.needs_extraction = score_extraction(
            scorecard.final_needs_explicit, expected_needs
        )

    return scorecard


def run_full_evaluation() -> EvaluationReport:
    """Run all scenarios and produce a complete evaluation report."""
    report = EvaluationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    for scenario in ALL_SCENARIOS:
        scorecard = evaluate_dialogue(scenario)
        report.scorecards.append(scorecard)

    return report


def save_report(report: EvaluationReport, filename: str | None = None) -> Path:
    """Save evaluation report as JSON."""
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_{ts}.json"

    filepath = EVAL_RESULTS_DIR / filename
    filepath.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return filepath


def print_summary(report: EvaluationReport) -> None:
    """Print a human-readable summary of the evaluation."""
    d = report.to_dict()
    s = d["summary"]

    print("=" * 72)
    print("  AutoVend Agent Performance Evaluation Report")
    print("=" * 72)
    print(f"  Timestamp:        {d['timestamp']}")
    print(f"  Total Dialogues:  {s['total_dialogues']}")
    print(f"  Total Turns:      {s['total_turns']}")
    print()
    print("  ── Aggregate Scores ──────────────────────────────────────")
    print(f"  Overall Score:         {s['avg_overall_score']:.1f} / 100")
    print(f"  Stage Accuracy:        {s['avg_stage_accuracy']:.1f}%")
    print(f"  Response Relevance:    {s['avg_response_relevance']:.1f} / 100")
    print(f"  Task Completion:       {s['avg_task_completion']:.1f} / 100")
    print(f"  Conversion Funnel:     {s['avg_conversion_funnel']:.1f} / 100")
    print(f"  Professionalism:       {s['avg_professionalism']:.1f} / 100")
    print(f"  Language Consistency:  {s['avg_language_consistency']:.1f} / 100")
    print()

    # By category
    print("  ── By Category ───────────────────────────────────────────")
    for cat, info in d.get("by_category", {}).items():
        print(
            f"  [{cat:12s}] count={info['count']:2d}  overall={info['avg_overall']:.1f}  "
            f"stage_acc={info['avg_stage_accuracy']:.1f}%  task={info['avg_task_completion']:.1f}"
        )
    print()

    # Per-dialogue summary
    print("  ── Per-Dialogue Scores ───────────────────────────────────")
    for sc in d["dialogues"]:
        scores = sc["scores"]
        print(
            f"  [{sc['dialogue_id']:4s}] {sc['persona'][:30]:30s} "
            f"overall={scores['overall']:5.1f}  stage={scores['stage_accuracy']:5.1f}%  "
            f"task={scores['task_completion']:5.1f}  prof={scores['professionalism']:5.1f}"
        )

    print()
    print("=" * 72)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    report = run_full_evaluation()
    filepath = save_report(report)
    print_summary(report)
    print(f"\n  Results saved to: {filepath}")
