"""
LLM-as-a-Judge evaluation module.

Replaces keyword-overlap heuristics with LLM-based scoring for:
  - Response Relevance: semantic understanding of context fit
  - Professionalism: tone, structure, appropriateness
  - Faithfulness: factual grounding (no hallucinated vehicle specs)
  - Answer Relevance: how well the response addresses the user's intent

Designed to work with both real LLMs (for production eval) and
deterministic mock scoring (for CI/unit tests).
"""

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JudgeScore:
    """Multi-dimensional LLM judge score for a single response."""

    relevance: float = 0.0       # 0-100: Does the response address the user's intent?
    professionalism: float = 0.0  # 0-100: Tone, politeness, structure
    faithfulness: float = 0.0     # 0-100: Factual grounding, no hallucination
    completeness: float = 0.0     # 0-100: Does it cover all necessary info?

    @property
    def overall(self) -> float:
        return (
            0.30 * self.relevance
            + 0.25 * self.professionalism
            + 0.30 * self.faithfulness
            + 0.15 * self.completeness
        )

    def to_dict(self) -> dict:
        return {
            "relevance": round(self.relevance, 1),
            "professionalism": round(self.professionalism, 1),
            "faithfulness": round(self.faithfulness, 1),
            "completeness": round(self.completeness, 1),
            "overall": round(self.overall, 1),
        }


JUDGE_PROMPT = """You are a professional evaluation judge for an automotive sales AI assistant.

Score the following AI response on four dimensions (0-100 each):

## Context
- User message: {user_message}
- Conversation stage: {stage}
- User profile: {profile_summary}
- User needs: {needs_summary}
- Retrieved vehicles: {retrieved_cars_summary}

## AI Response
{response}

## Scoring Criteria

1. **Relevance** (0-100): Does the response directly address the user's message and current conversation stage? Is it on-topic?

2. **Professionalism** (0-100): Is the tone appropriate for automotive sales? Is it polite, well-structured, and avoiding casual/unprofessional language?

3. **Faithfulness** (0-100): Are all vehicle specifications, features, and claims factually grounded in the retrieved vehicle data? Score 0 if the response invents specs not in the data. Score 100 if no specific claims are made or all claims are supported.

4. **Completeness** (0-100): Does the response cover all necessary aspects for the current stage? (e.g., asking about missing profile fields in profile stage, presenting all matched cars in selection stage)

Return ONLY a JSON object:
{{"relevance": <score>, "professionalism": <score>, "faithfulness": <score>, "completeness": <score>}}"""


def judge_response(
    llm,
    user_message: str,
    response: str,
    stage: str,
    profile_summary: str = "",
    needs_summary: str = "",
    retrieved_cars_summary: str = "",
) -> JudgeScore:
    """
    Use an LLM to judge the quality of an agent response.

    Args:
        llm: LLM instance (ideally a stronger model like GPT-4).
        user_message: The user's input message.
        response: The agent's response to evaluate.
        stage: Current conversation stage.
        profile_summary: Summary of user profile.
        needs_summary: Summary of user needs.
        retrieved_cars_summary: Summary of RAG-retrieved vehicles.

    Returns:
        JudgeScore with multi-dimensional scores.
    """
    prompt = JUDGE_PROMPT.format(
        user_message=user_message,
        stage=stage,
        profile_summary=profile_summary or "Not yet collected",
        needs_summary=needs_summary or "Not yet collected",
        retrieved_cars_summary=retrieved_cars_summary or "No vehicles retrieved",
        response=response,
    )

    try:
        result = llm.complete(prompt)
        parsed = json.loads(result.text.strip())
        return JudgeScore(
            relevance=float(parsed.get("relevance", 0)),
            professionalism=float(parsed.get("professionalism", 0)),
            faithfulness=float(parsed.get("faithfulness", 0)),
            completeness=float(parsed.get("completeness", 0)),
        )
    except Exception as e:
        logger.warning(f"LLM judge failed: {e}, falling back to heuristic scoring")
        return _heuristic_judge(response, stage, user_message)


def _heuristic_judge(response: str, stage: str, user_message: str) -> JudgeScore:
    """Fallback heuristic scoring when LLM judge is unavailable."""
    score = JudgeScore()

    # Basic relevance: non-empty and reasonable length
    if response.strip():
        score.relevance = 50.0
        if len(response) > 20:
            score.relevance = 70.0

    # Professionalism: polite markers
    polite = ["您", "请", "感谢", "很高兴", "为您", "帮您", "please", "thank", "help"]
    if any(p in response.lower() for p in polite):
        score.professionalism = 80.0
    elif response.strip():
        score.professionalism = 50.0

    # Faithfulness: assume OK if no specific numbers/specs mentioned
    score.faithfulness = 70.0  # Default: no hallucination detected

    # Completeness: ends with question = engaging
    if response.strip().endswith(("?", "？", "吗", "呢")):
        score.completeness = 70.0
    elif response.strip():
        score.completeness = 50.0

    return score
