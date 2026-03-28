"""
Performance Scoring Engine — professional evaluation metrics for AutoVend Agent.

Scoring Dimensions:
  1. Extraction Accuracy  (Precision / Recall / F1)
  2. Stage Transition Correctness (Accuracy / Weighted Accuracy)
  3. Response Quality (Relevance / Completeness / Language Consistency / Professionalism)
  4. Business Capability (Information Gathering Rate / Conversion Funnel / Task Completion)
  5. Robustness (Error Recovery / Edge-case Handling / Adversarial Resistance)
  6. Latency (avg / p50 / p95 / p99)

Each metric uses a 0–100 scale. Per-dialogue and aggregate scores are computed.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from tests.performance.llm_judge import JudgeScore  # noqa: F401
    from tests.performance.rag_metrics import RAGEvaluation  # noqa: F401

# ── Extraction Accuracy ──────────────────────────────────────────────────────


@dataclass
class ExtractionScore:
    """Field-level extraction precision/recall/F1."""

    correct: int = 0
    extracted: int = 0
    expected: int = 0

    @property
    def precision(self) -> float:
        return self.correct / self.extracted if self.extracted else 1.0

    @property
    def recall(self) -> float:
        return self.correct / self.expected if self.expected else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def score_extraction(extracted: dict, expected: dict) -> ExtractionScore:
    """Compare extracted fields against ground-truth expected values."""
    score = ExtractionScore()
    for key, expected_val in expected.items():
        if not expected_val:
            continue
        score.expected += 1
        extracted_val = extracted.get(key, "")
        if extracted_val:
            score.extracted += 1
            if str(extracted_val).strip().lower() == str(expected_val).strip().lower():
                score.correct += 1
    return score


# ── Response Quality ─────────────────────────────────────────────────────────


def score_response_relevance(response: str, stage: str, context_keywords: List[str]) -> float:
    """
    Score how relevant the response is to the current stage and context.

    Heuristic scoring (0-100):
    - Contains stage-appropriate keywords → +40
    - Contains context keywords from user message → +30
    - Non-trivial length (>20 chars) → +15
    - Ends with question or action prompt → +15
    """
    score = 0.0
    resp_lower = response.lower()

    # Stage-appropriate keyword sets
    stage_keywords = {
        "welcome": ["你好", "欢迎", "hello", "hi", "welcome", "autovend", "请问", "what"],
        "profile_analysis": ["名字", "年龄", "家", "name", "age", "family", "请问", "who", "住"],
        "needs_analysis": [
            "预算",
            "品牌",
            "车型",
            "budget",
            "brand",
            "type",
            "偏好",
            "prefer",
            "需求",
        ],
        "car_selection_confirmation": [
            "推荐",
            "recommend",
            "车型",
            "model",
            "试驾",
            "test drive",
            "对比",
            "compare",
        ],
        "reservation4s": [
            "预约",
            "日期",
            "时间",
            "地点",
            "reservation",
            "date",
            "time",
            "location",
            "schedule",
        ],
        "reservation_confirmation": ["确认", "confirm", "信息", "details", "预约", "reservation"],
        "farewell": ["感谢", "thank", "再见", "goodbye", "祝", "期待", "look forward"],
    }

    keywords = stage_keywords.get(stage, [])
    if any(kw in resp_lower for kw in keywords):
        score += 40.0

    # Context keywords from user
    if context_keywords:
        matched = sum(1 for kw in context_keywords if kw.lower() in resp_lower)
        score += min(30.0, (matched / max(len(context_keywords), 1)) * 30.0)

    # Non-trivial length
    if len(response.strip()) > 20:
        score += 15.0

    # Ends with engagement (question mark or invitation)
    if response.strip().endswith(("?", "？", "吗", "呢", "吧")):
        score += 15.0
    elif any(w in resp_lower for w in ["请", "please", "您觉得", "what do you think"]):
        score += 10.0

    return min(score, 100.0)


def score_language_consistency(user_message: str, response: str) -> float:
    """
    Score whether the agent responds in the same language as the user.
    0 = wrong language, 50 = mixed, 100 = correct language.
    """

    def has_chinese(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text))

    user_cn = has_chinese(user_message)
    resp_cn = has_chinese(response)

    if not response.strip():
        return 0.0

    # Both Chinese or both English
    if user_cn == resp_cn:
        return 100.0

    # Mixed response: partial credit
    if user_cn and resp_cn:
        return 50.0

    return 0.0


def score_response_professionalism(response: str) -> float:
    """
    Score the professionalism of the response (0-100).
    - No offensive/casual slang → +40
    - Polite markers present → +30
    - Structured (not just a single word) → +30
    """
    score = 0.0
    resp_lower = response.lower()

    # Check for unprofessional content
    bad_patterns = ["lol", "haha", "lmao", "wtf", "omg", "shit", "damn"]
    if not any(p in resp_lower for p in bad_patterns):
        score += 40.0

    # Polite markers
    polite_cn = ["您", "请", "感谢", "很高兴", "为您", "帮您"]
    polite_en = ["please", "thank", "glad", "happy to", "help you", "would you"]
    if any(p in resp_lower for p in polite_cn + polite_en):
        score += 30.0

    # Structured response (multi-sentence)
    sentences = re.split(r"[。！？.!?\n]", response)
    meaningful = [s for s in sentences if len(s.strip()) > 5]
    if len(meaningful) >= 2:
        score += 30.0
    elif len(meaningful) >= 1:
        score += 15.0

    return min(score, 100.0)


# ── Business Capability ──────────────────────────────────────────────────────


def score_information_gathering_rate(
    profile_before: dict,
    profile_after: dict,
    needs_before: dict,
    needs_after: dict,
) -> float:
    """
    Measure how effectively the agent gathers information per turn.
    Returns 0-100 based on new fields filled.
    """

    def count_filled(d: dict) -> int:
        return sum(1 for v in d.values() if v and str(v).strip())

    profile_new = count_filled(profile_after) - count_filled(profile_before)
    needs_new = count_filled(needs_after) - count_filled(needs_before)
    total_new = profile_new + needs_new

    # Normalize: 3+ new fields per turn is excellent
    return min(100.0, (total_new / 3.0) * 100.0)


def score_conversion_funnel(stages_visited: List[str]) -> float:
    """
    Score how far the conversation progresses through the sales funnel.
    Full funnel = 100, partial = proportional.
    """
    funnel = [
        "welcome",
        "profile_analysis",
        "needs_analysis",
        "car_selection_confirmation",
        "reservation4s",
        "reservation_confirmation",
        "farewell",
    ]
    max_idx = -1
    for stage in stages_visited:
        if stage in funnel:
            idx = funnel.index(stage)
            max_idx = max(max_idx, idx)

    if max_idx < 0:
        return 0.0
    return ((max_idx + 1) / len(funnel)) * 100.0


def score_task_completion(
    stages_visited: List[str],
    profile: dict,
    needs_explicit: dict,
    reservation: dict,
    expected_final_stage: str,
) -> float:
    """
    Comprehensive task completion score (0-100).
    Weights:
      - Reached expected final stage: 30%
      - Profile completeness: 25%
      - Needs completeness: 25%
      - Reservation completeness: 20% (only if expected)
    """
    score = 0.0

    # Stage reached
    if expected_final_stage in stages_visited:
        score += 30.0
    else:
        # Partial credit for partial progress
        funnel = [
            "welcome",
            "profile_analysis",
            "needs_analysis",
            "car_selection_confirmation",
            "reservation4s",
            "reservation_confirmation",
            "farewell",
        ]
        if expected_final_stage in funnel:
            target_idx = funnel.index(expected_final_stage)
            max_idx = max(
                (funnel.index(s) for s in stages_visited if s in funnel),
                default=-1,
            )
            if target_idx > 0:
                score += 30.0 * (max_idx / target_idx)

    # Profile completeness
    profile_fields = ["name", "age", "target_driver", "family_size", "residence"]
    filled = sum(1 for f in profile_fields if profile.get(f))
    score += 25.0 * (filled / len(profile_fields))

    # Needs completeness (key fields)
    needs_fields = ["prize", "brand", "powertrain_type", "vehicle_category_bottom", "design_style"]
    filled = sum(1 for f in needs_fields if needs_explicit.get(f))
    score += 25.0 * (filled / len(needs_fields))

    # Reservation completeness (if expected)
    if expected_final_stage in ("reservation4s", "reservation_confirmation", "farewell"):
        res_fields = ["test_driver", "reservation_date", "reservation_time", "reservation_location"]
        filled = sum(1 for f in res_fields if reservation.get(f))
        score += 20.0 * (filled / len(res_fields))
    else:
        score += 20.0  # Not expected, full credit

    return min(score, 100.0)


# ── Latency ──────────────────────────────────────────────────────────────────


@dataclass
class LatencyStats:
    """Latency statistics from a set of measurements."""

    values_ms: List[float] = field(default_factory=list)

    @property
    def avg(self) -> float:
        return statistics.mean(self.values_ms) if self.values_ms else 0.0

    @property
    def p50(self) -> float:
        return statistics.median(self.values_ms) if self.values_ms else 0.0

    @property
    def p95(self) -> float:
        if not self.values_ms:
            return 0.0
        s = sorted(self.values_ms)
        return s[min(int(len(s) * 0.95), len(s) - 1)]

    @property
    def p99(self) -> float:
        if not self.values_ms:
            return 0.0
        s = sorted(self.values_ms)
        return s[min(int(len(s) * 0.99), len(s) - 1)]

    @property
    def max_val(self) -> float:
        return max(self.values_ms) if self.values_ms else 0.0

    def to_dict(self) -> dict:
        return {
            "avg_ms": round(self.avg, 2),
            "p50_ms": round(self.p50, 2),
            "p95_ms": round(self.p95, 2),
            "p99_ms": round(self.p99, 2),
            "max_ms": round(self.max_val, 2),
            "samples": len(self.values_ms),
        }


# ── Dialogue Scorecard ───────────────────────────────────────────────────────


@dataclass
class TurnScore:
    """Scores for a single conversation turn."""

    turn_idx: int = 0
    user_message: str = ""
    agent_response: str = ""
    expected_stage: str = ""
    actual_stage: str = ""
    stage_correct: bool = False
    response_relevance: float = 0.0
    language_consistency: float = 0.0
    professionalism: float = 0.0
    info_gathering_rate: float = 0.0
    latency_ms: float = 0.0
    extraction_profile: Optional[ExtractionScore] = None
    extraction_needs: Optional[ExtractionScore] = None
    judge_score: Optional[Any] = None     # JudgeScore from LLM-as-a-Judge
    rag_eval: Optional[Any] = None        # RAGEvaluation metrics

    def to_dict(self) -> dict:
        d = {
            "turn": self.turn_idx,
            "user_message": self.user_message,
            "agent_response": (
                self.agent_response[:200] + ("..." if len(self.agent_response) > 200 else "")
            ),
            "expected_stage": self.expected_stage,
            "actual_stage": self.actual_stage,
            "stage_correct": self.stage_correct,
            "response_relevance": round(self.response_relevance, 1),
            "language_consistency": round(self.language_consistency, 1),
            "professionalism": round(self.professionalism, 1),
            "info_gathering_rate": round(self.info_gathering_rate, 1),
            "latency_ms": round(self.latency_ms, 2),
        }
        if self.extraction_profile:
            d["extraction_profile_f1"] = round(self.extraction_profile.f1, 3)
        if self.extraction_needs:
            d["extraction_needs_f1"] = round(self.extraction_needs.f1, 3)
        if self.judge_score:
            d["judge"] = self.judge_score.to_dict()
        if self.rag_eval:
            d["rag"] = self.rag_eval.to_dict()
        return d


@dataclass
class DialogueScorecard:
    """Comprehensive scorecard for a complete dialogue evaluation."""

    dialogue_id: str = ""
    persona: str = ""
    category: str = ""  # normal / edge_case / adversarial / bilingual
    total_turns: int = 0
    turn_scores: List[TurnScore] = field(default_factory=list)
    stages_visited: List[str] = field(default_factory=list)
    expected_final_stage: str = ""
    latency: LatencyStats = field(default_factory=LatencyStats)

    # Aggregate extraction
    profile_extraction: ExtractionScore = field(default_factory=ExtractionScore)
    needs_extraction: ExtractionScore = field(default_factory=ExtractionScore)

    # Final state snapshots
    final_profile: Dict[str, Any] = field(default_factory=dict)
    final_needs_explicit: Dict[str, Any] = field(default_factory=dict)
    final_reservation: Dict[str, Any] = field(default_factory=dict)

    # ── Computed aggregate scores ──

    @property
    def stage_accuracy(self) -> float:
        correct = sum(1 for t in self.turn_scores if t.stage_correct)
        return correct / self.total_turns if self.total_turns else 0.0

    @property
    def avg_response_relevance(self) -> float:
        vals = [t.response_relevance for t in self.turn_scores]
        return statistics.mean(vals) if vals else 0.0

    @property
    def avg_language_consistency(self) -> float:
        vals = [t.language_consistency for t in self.turn_scores]
        return statistics.mean(vals) if vals else 0.0

    @property
    def avg_professionalism(self) -> float:
        vals = [t.professionalism for t in self.turn_scores]
        return statistics.mean(vals) if vals else 0.0

    @property
    def response_generation_rate(self) -> float:
        nonempty = sum(1 for t in self.turn_scores if t.agent_response.strip())
        return nonempty / self.total_turns if self.total_turns else 0.0

    @property
    def conversion_score(self) -> float:
        return score_conversion_funnel(self.stages_visited)

    @property
    def task_completion_score(self) -> float:
        return score_task_completion(
            self.stages_visited,
            self.final_profile,
            self.final_needs_explicit,
            self.final_reservation,
            self.expected_final_stage,
        )

    @property
    def overall_score(self) -> float:
        """
        Weighted overall score (0-100).
        Weights:
          - Business Capability (task completion + conversion): 35%
          - Response Quality (relevance + professionalism + language): 30%
          - Extraction Accuracy (profile + needs F1): 20%
          - Stage Correctness: 10%
          - Latency (inverted, 10ms=100, 100ms=0): 5%
        """
        # Business
        biz = 0.5 * self.task_completion_score + 0.5 * self.conversion_score

        # Response quality
        resp = (
            self.avg_response_relevance + self.avg_professionalism + self.avg_language_consistency
        ) / 3.0

        # Extraction
        prof_f1 = self.profile_extraction.f1 * 100 if self.profile_extraction.expected > 0 else 100
        needs_f1 = self.needs_extraction.f1 * 100 if self.needs_extraction.expected > 0 else 100
        extraction = (prof_f1 + needs_f1) / 2.0

        # Stage
        stage = self.stage_accuracy * 100

        # Latency (lower is better; 1ms=100, 50ms=0)
        avg_lat = self.latency.avg
        latency_score = max(0, 100 - (avg_lat / 50.0) * 100) if avg_lat < 50 else 0

        return 0.35 * biz + 0.30 * resp + 0.20 * extraction + 0.10 * stage + 0.05 * latency_score

    def to_dict(self) -> dict:
        return {
            "dialogue_id": self.dialogue_id,
            "persona": self.persona,
            "category": self.category,
            "total_turns": self.total_turns,
            "scores": {
                "overall": round(self.overall_score, 1),
                "stage_accuracy": round(self.stage_accuracy * 100, 1),
                "response_relevance": round(self.avg_response_relevance, 1),
                "language_consistency": round(self.avg_language_consistency, 1),
                "professionalism": round(self.avg_professionalism, 1),
                "response_generation_rate": round(self.response_generation_rate * 100, 1),
                "conversion_funnel": round(self.conversion_score, 1),
                "task_completion": round(self.task_completion_score, 1),
                "extraction_profile_f1": round(self.profile_extraction.f1, 3),
                "extraction_needs_f1": round(self.needs_extraction.f1, 3),
            },
            "latency": self.latency.to_dict(),
            "stages_visited": self.stages_visited,
            "expected_final_stage": self.expected_final_stage,
            "turns": [t.to_dict() for t in self.turn_scores],
        }


# ── Aggregate Report ─────────────────────────────────────────────────────────


@dataclass
class EvaluationReport:
    """Aggregate report across all dialogue evaluations."""

    scorecards: List[DialogueScorecard] = field(default_factory=list)
    timestamp: str = ""

    @property
    def total_dialogues(self) -> int:
        return len(self.scorecards)

    @property
    def total_turns(self) -> int:
        return sum(s.total_turns for s in self.scorecards)

    def _avg(self, fn) -> float:
        vals = [fn(s) for s in self.scorecards]
        return statistics.mean(vals) if vals else 0.0

    @property
    def avg_overall(self) -> float:
        return self._avg(lambda s: s.overall_score)

    @property
    def avg_stage_accuracy(self) -> float:
        return self._avg(lambda s: s.stage_accuracy * 100)

    @property
    def avg_response_relevance(self) -> float:
        return self._avg(lambda s: s.avg_response_relevance)

    @property
    def avg_task_completion(self) -> float:
        return self._avg(lambda s: s.task_completion_score)

    @property
    def avg_conversion(self) -> float:
        return self._avg(lambda s: s.conversion_score)

    @property
    def avg_professionalism(self) -> float:
        return self._avg(lambda s: s.avg_professionalism)

    @property
    def avg_language_consistency(self) -> float:
        return self._avg(lambda s: s.avg_language_consistency)

    def by_category(self) -> Dict[str, List[DialogueScorecard]]:
        cats: Dict[str, List[DialogueScorecard]] = {}
        for s in self.scorecards:
            cats.setdefault(s.category, []).append(s)
        return cats

    def to_dict(self) -> dict:
        cats = self.by_category()
        cat_summaries = {}
        for cat, cards in cats.items():
            cat_summaries[cat] = {
                "count": len(cards),
                "avg_overall": round(statistics.mean([c.overall_score for c in cards]), 1),
                "avg_stage_accuracy": round(
                    statistics.mean([c.stage_accuracy * 100 for c in cards]), 1
                ),
                "avg_task_completion": round(
                    statistics.mean([c.task_completion_score for c in cards]), 1
                ),
            }

        return {
            "timestamp": self.timestamp,
            "summary": {
                "total_dialogues": self.total_dialogues,
                "total_turns": self.total_turns,
                "avg_overall_score": round(self.avg_overall, 1),
                "avg_stage_accuracy": round(self.avg_stage_accuracy, 1),
                "avg_response_relevance": round(self.avg_response_relevance, 1),
                "avg_task_completion": round(self.avg_task_completion, 1),
                "avg_conversion_funnel": round(self.avg_conversion, 1),
                "avg_professionalism": round(self.avg_professionalism, 1),
                "avg_language_consistency": round(self.avg_language_consistency, 1),
            },
            "by_category": cat_summaries,
            "dialogues": [s.to_dict() for s in self.scorecards],
        }
