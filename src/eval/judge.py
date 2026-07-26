"""
LLM judge with hallucination suppression.

A judge asked "is this answer supported by this context, 0-5?" will answer
fluently and unreliably. It reads the answer, recognises it as plausible
automotive advice, and scores it on that recognition — using pre-training
rather than the context it was given. The failure is invisible in aggregate:
the scores look reasonable, they are simply not measuring grounding.

Three layers address that, and each is independently switchable so the
contribution of each can be measured (see `src/eval/judge_ab.py`):

## 1. Forced decode path (mechanism layer)

The prompt fixes the output order: `<quotes>` → `<reasoning>` → `<score>`.
Because generation is autoregressive, the model must emit verbatim evidence
*before* it can emit a score, and the score is then conditioned on text it has
already committed to. Asking for the score first, or for a bare number, leaves
the model free to decide and rationalise afterwards.

A verdict whose `<quotes>` is empty is therefore an assertion without evidence.
`StructuredJudge` treats that as an automatic fail rather than trusting the
number that followed it.

## 2. Atomic decomposition + NLI (algorithm layer)

Rather than judging a paragraph as a whole, the answer is split into atomic
statements and each is checked against the context independently. This is what
RAGAS does internally and the reason it works: a paragraph with six claims,
five supported and one invented, reads as "mostly right" to a holistic judge,
while per-claim NLI puts the invented one at 0 and the aggregate at 5/6. It
also keeps each judgement short, which is where attention drift comes from.

## 3. Consensus (architecture layer)

Borderline cases get sampled several times at non-zero temperature. Agreement
means the verdict is stable; disagreement means the judge is guessing, and the
case is flagged `low_confidence` for human review instead of being averaged
into a number that looks decided.
"""

import re
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

from src.utils.logger import get_logger

logger = get_logger(__name__)


class JudgeMode(str, Enum):
    """Which suppression layers are active. Used by the A/B harness."""

    #: Score only. The baseline this module exists to beat.
    NAIVE = "naive"
    #: Reasoning before score, no evidence requirement.
    COT = "cot"
    #: Forced quotes → reasoning → score, empty quotes fail.
    STRUCTURED = "structured"
    #: Structured, applied per atomic statement.
    ATOMIC = "atomic"


@dataclass
class Verdict:
    """One judgement."""

    score: float
    max_score: float = 5.0
    quotes: List[str] = field(default_factory=list)
    reasoning: str = ""
    raw: str = ""
    mode: JudgeMode = JudgeMode.NAIVE
    low_confidence: bool = False
    samples: List[float] = field(default_factory=list)
    error: str = ""
    #: The response contained a <quotes> block. False means the judge ignored
    #: the format, which is a parse failure rather than a verdict.
    format_ok: bool = True

    @property
    def normalised(self) -> float:
        return self.score / self.max_score if self.max_score else 0.0

    @property
    def has_evidence(self) -> bool:
        return bool(self.quotes) and self.quotes != ["无"]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "normalised": round(self.normalised, 4),
            "mode": self.mode.value,
            "n_quotes": len(self.quotes),
            "has_evidence": self.has_evidence,
            "low_confidence": self.low_confidence,
            "format_ok": self.format_ok,
            "samples": self.samples,
            "reasoning": self.reasoning[:300],
            "error": self.error,
        }


# ── Prompts ───────────────────────────────────────────────────────────

NAIVE_PROMPT = """评估下面的【回复】是否忠实于【上下文】。

【上下文】
{context}

【回复】
{answer}

输出 0-5 的整数分数，5 表示完全由上下文支撑，0 表示存在严重幻觉。
只输出数字。
"""

COT_PROMPT = """# Role
你是一个严格的汽车销售系统质量评估专家。

# Task
评估【回复】是否忠实于【上下文】提供的事实。

# 评估标准（0-5 分）
- 5 分：完全正确，所有陈述都能由上下文支撑。
- 3 分：主要内容正确，但有次要细节无法从上下文得到印证。
- 0 分：捏造了上下文中不存在的信息（严重幻觉）。

【上下文】
{context}

【回复】
{answer}

# 输出要求
请先在 <reasoning> 标签内一步步分析，然后在 <score> 标签内输出最终整数得分。
"""

STRUCTURED_PROMPT = """<instruction>
你是一个严格的 NLI 评估裁判。你的唯一事实来源是 <context>，禁止使用你的先验知识——
即使某个说法在现实中是对的，只要 <context> 里没有，就不算被支撑。

请按以下严格顺序输出，不得调换：
1. <quotes>：逐字摘抄 <context> 中能证明或证伪【回复】的原文句子，每行一句。
   如果找不到任何相关原文，必须输出「无」。
2. <reasoning>：仅基于上面摘抄的 quotes 进行推理。不得引入 quotes 之外的信息。
3. <score>：0-5 的整数。5 表示全部陈述都有 quotes 支撑，0 表示存在 quotes 无法
   支撑的捏造内容。
</instruction>

<context>
{context}
</context>

<answer>
{answer}
</answer>
"""

ATOMIC_DECOMPOSE_PROMPT = """把下面这段回复拆解成若干条独立的、可独立验证的原子断言。

要求：
- 每条断言只包含一个事实点。
- 保留原文的具体数值和专有名词，不要概括。
- 忽略纯粹的礼貌用语和主观修辞。

【回复】
{answer}

只输出 JSON 数组，形如 ["断言1", "断言2"]。
"""

ATOMIC_NLI_PROMPT = """<instruction>
你是一个严格的 NLI 评估裁判。你的唯一事实来源是 <context>，禁止使用先验知识。

判断 <statement> 能否由 <context> 推导出来。按以下顺序输出，不得调换：
1. <quotes>：逐字摘抄 <context> 中与该断言直接相关的原文。找不到必须输出「无」。
2. <reasoning>：仅基于 quotes 的三段论推理。
3. <score>：1 表示能由 quotes 支撑，0 表示不能。
</instruction>

<context>
{context}
</context>

<statement>
{statement}
</statement>
"""

#: Appended on a retry after the judge ignored the output format.
FORMAT_REMINDER = """

【重要】上一次输出没有遵守格式。必须严格按顺序输出三个标签，缺一不可：
<quotes>...</quotes>
<reasoning>...</reasoning>
<score>...</score>
"""


# ── Parsing ───────────────────────────────────────────────────────────

_TAG = "<{tag}>(.*?)</{tag}>"


def _extract_tag(text: str, tag: str) -> str:
    match = re.search(_TAG.format(tag=tag), text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_score(text: str, max_score: float) -> Optional[float]:
    """
    Pull the score out, preferring the tagged form.

    Falls back to the last number in the text: models occasionally drop the
    closing tag, and discarding an otherwise complete verdict over that would
    inflate the failure rate with parse errors rather than real ones.
    """
    tagged = _extract_tag(text, "score")
    if tagged:
        numbers = re.findall(r"-?\d+(?:\.\d+)?", tagged)
        if numbers:
            return max(0.0, min(max_score, float(numbers[0])))

    numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
    if numbers:
        return max(0.0, min(max_score, float(numbers[-1])))
    return None


def _extract_quotes(text: str) -> List[str]:
    block = _extract_tag(text, "quotes")
    if not block:
        return []
    lines = [ln.strip(" -•\t") for ln in block.splitlines() if ln.strip()]
    if len(lines) == 1 and lines[0] in ("无", "None", "none", "N/A"):
        return []
    return lines


def _has_quotes_tag(text: str) -> bool:
    """
    Whether the response contained a `<quotes>` block at all.

    This distinguishes two failures the first version of this module conflated,
    at a measured cost of 30% false alarms:

    - `<quotes>无</quotes>` — the judge looked and found nothing. A verdict
      scored above zero on that basis is unsupported, and zeroing it is right.
    - no tag at all — the judge did not follow the format. That is a parse
      failure, and scoring it zero marks a *faithful* answer as hallucinated.

    Only the first is evidence about the answer. The second is evidence about
    the prompt.
    """
    return bool(re.search(r"<quotes>", text, re.IGNORECASE))


def parse_verdict(raw: str, mode: JudgeMode, max_score: float = 5.0) -> Verdict:
    """Parse a judge response. Never raises — a bad response is a failed one."""
    structured = mode in (JudgeMode.STRUCTURED, JudgeMode.ATOMIC)
    score = _extract_score(raw, max_score)
    if score is None:
        # A response with no parseable score produced no verdict about the
        # answer at all. It must report `format_ok=False` for the same reason a
        # missing `<quotes>` block does: the caller drops format failures, and
        # letting one through as a legitimate zero marks a faithful answer as
        # hallucinated.
        return Verdict(
            score=0.0,
            max_score=max_score,
            raw=raw,
            mode=mode,
            error="no score found in response",
            format_ok=False,
        )
    return Verdict(
        score=score,
        max_score=max_score,
        quotes=_extract_quotes(raw),
        reasoning=_extract_tag(raw, "reasoning"),
        raw=raw,
        mode=mode,
        format_ok=_has_quotes_tag(raw) if structured else True,
    )


# ── Evidence verification ─────────────────────────────────────────────


def verify_quotes(quotes: Sequence[str], context: str) -> Dict[str, Any]:
    """
    Check the quotes are actually in the context.

    The decode path forces the judge to *emit* evidence; nothing forces that
    evidence to be real. A judge that invents a supporting quote and then scores
    against it has performed the ritual and skipped the point, and this is the
    only way to catch it — the reasoning downstream will look impeccable.

    Matching is on normalised text, since models routinely reflow whitespace
    and swap full-width punctuation while copying.
    """
    if not quotes:
        return {"n": 0, "n_grounded": 0, "grounded_ratio": 0.0, "fabricated": []}

    haystack = _normalise(context)
    fabricated = [q for q in quotes if _normalise(q) not in haystack]
    grounded = len(quotes) - len(fabricated)
    return {
        "n": len(quotes),
        "n_grounded": grounded,
        "grounded_ratio": round(grounded / len(quotes), 4),
        "fabricated": fabricated[:3],
    }


_PUNCT = str.maketrans({"，": ",", "。": ".", "；": ";", "：": ":", "（": "(", "）": ")"})


def _normalise(text: str) -> str:
    return re.sub(r"\s+", "", text.translate(_PUNCT)).lower()


# ── Judge ─────────────────────────────────────────────────────────────

#: Normalised scores in this band are treated as borderline and re-sampled.
#: Chosen around the 3/5 pass mark, where a one-point disagreement flips the
#: verdict; scores at the extremes rarely move.
BORDERLINE_BAND = (0.4, 0.8)

#: Samples taken for a borderline case, and the temperature used. Temperature
#: must be non-zero or the samples are identical and consensus measures nothing.
CONSENSUS_SAMPLES = 3
CONSENSUS_TEMPERATURE = 0.5

#: Score spread above which the samples are considered to disagree.
CONSENSUS_MAX_STDEV = 0.75

#: How per-statement NLI results become one score.
#:
#: "ratio" is RAGAS's faithfulness — supported / total. Correct when the
#: question is "how much of this is grounded".
#:
#: "strict" caps the score as soon as any statement is unsupported. Correct
#: when the question is "does this contain a fabrication", which is what a
#: release gate asks. Measured: with "ratio", a single injected falsehood among
#: five true claims scored 0.83 and sailed past a 0.6 pass mark — averaging
#: dilutes exactly the thing being detected.
ATOMIC_AGGREGATION = "strict"

#: Ceiling applied under "strict" when any statement is unsupported. Not zero:
#: the rest of the answer may still be usable, and collapsing everything to 0
#: would lose the difference between one bad claim and an entirely invented
#: answer.
STRICT_UNSUPPORTED_CEILING = 0.4


class StructuredJudge:
    """
    Judge with configurable suppression layers.

    `llm` is anything with `.complete(prompt, **kwargs) -> str`, which both the
    cloud clients and the local one satisfy.
    """

    def __init__(
        self,
        llm,
        mode: JudgeMode = JudgeMode.STRUCTURED,
        max_score: float = 5.0,
        require_evidence: bool = True,
        consensus: bool = True,
        verify_evidence: bool = True,
        atomic_aggregation: str = ATOMIC_AGGREGATION,
    ):
        self.llm = llm
        self.mode = mode
        self.max_score = max_score
        self.require_evidence = require_evidence
        self.consensus = consensus
        self.verify_evidence = verify_evidence
        self.atomic_aggregation = atomic_aggregation

    # ── single-shot ───────────────────────────────────────────────────

    def judge(self, context: str, answer: str) -> Verdict:
        """Judge one answer against one context."""
        if self.mode is JudgeMode.ATOMIC:
            return self._judge_atomic(context, answer)

        prompt = self._prompt_for(self.mode).format(context=context, answer=answer)
        verdict = self._one_shot(prompt, temperature=0.0)
        verdict = self._apply_evidence_rules(verdict, context)

        # One retry on a format miss. Models drop the structure occasionally
        # even at temperature 0, and discarding the case would bias the sample
        # toward whatever the model finds easy to format.
        if not verdict.format_ok:
            logger.debug("format miss; retrying once with an explicit reminder")
            retry = self._one_shot(prompt + FORMAT_REMINDER, temperature=0.0)
            retry = self._apply_evidence_rules(retry, context)
            if not retry.error:
                verdict = retry

        if self.consensus and self._is_borderline(verdict):
            verdict = self._consensus(prompt, verdict, context)

        return verdict

    def _prompt_for(self, mode: JudgeMode) -> str:
        return {
            JudgeMode.NAIVE: NAIVE_PROMPT,
            JudgeMode.COT: COT_PROMPT,
            JudgeMode.STRUCTURED: STRUCTURED_PROMPT,
        }[mode]

    def _one_shot(self, prompt: str, temperature: float) -> Verdict:
        try:
            raw = self.llm.complete(prompt, temperature=temperature, max_tokens=800)
        except Exception as exc:
            # `format_ok=False` for the same reason an unparseable response
            # sets it: a call that never returned produced no verdict. Left at
            # the default True, a transport error would be counted as a
            # legitimate score of 0 — i.e. a network blip would be recorded as
            # the judge finding the answer hallucinated.
            return Verdict(
                score=0.0,
                max_score=self.max_score,
                mode=self.mode,
                error=str(exc)[:200],
                format_ok=False,
            )
        return parse_verdict(str(raw), self.mode, self.max_score)

    def _apply_evidence_rules(self, verdict: Verdict, context: str) -> Verdict:
        """
        Zero any verdict whose evidence does not hold up.

        Only meaningful for modes that ask for quotes; NAIVE and COT have none
        to check, which is precisely their weakness.
        """
        if self.mode not in (JudgeMode.STRUCTURED, JudgeMode.ATOMIC):
            return verdict

        if not verdict.format_ok:
            # The judge ignored the format. Its number is not a verdict about
            # the answer, so it is reported as an error rather than as a zero —
            # zeroing it marked faithful answers as hallucinated.
            #
            # An error already set here came from the transport or the parser
            # and names the actual cause; overwriting it makes a run that failed
            # entirely on connection errors report "format not followed" for
            # every case, which sends you to debug the prompt instead.
            if not verdict.error:
                verdict.error = "no <quotes> block; format not followed"
            return verdict

        if self.require_evidence and not verdict.has_evidence and verdict.score > 0:
            # The judge said it found no supporting text, then scored the answer
            # highly anyway. That verdict contradicts itself, so it is evidence
            # about the judge, not about the answer.
            #
            # The first version zeroed these, which read as "this answer is
            # hallucinated" and produced a 25% false-alarm rate on answers that
            # were entirely faithful. Flagging is the honest response: an
            # unreliable verdict should be excluded or reviewed, not inverted.
            logger.debug("verdict claims no evidence but scored above 0; flagging")
            verdict.low_confidence = True
            verdict.error = "inconsistent: scored above 0 with an empty quotes block"
            return verdict

        if self.verify_evidence and verdict.quotes:
            check = verify_quotes(verdict.quotes, context)
            if check["fabricated"]:
                logger.debug(f"fabricated quote(s): {check['fabricated']}")
                verdict.score = 0.0
                verdict.error = f"fabricated {len(check['fabricated'])} quote(s)"
        return verdict

    # ── consensus ─────────────────────────────────────────────────────

    def _is_borderline(self, verdict: Verdict) -> bool:
        if verdict.error:
            return False
        return BORDERLINE_BAND[0] <= verdict.normalised <= BORDERLINE_BAND[1]

    def _consensus(self, prompt: str, first: Verdict, context: str) -> Verdict:
        """
        Re-sample a borderline verdict and check the samples agree.

        Disagreement is not averaged away. A judge that scores the same case 2,
        4 and 5 has no opinion, and a mean of 3.67 hides that — the case is
        flagged for a human instead.
        """
        samples = [first.score]
        for _ in range(CONSENSUS_SAMPLES - 1):
            extra = self._one_shot(prompt, temperature=CONSENSUS_TEMPERATURE)
            extra = self._apply_evidence_rules(extra, context)
            if not extra.error:
                samples.append(extra.score)

        first.samples = samples
        if len(samples) >= 2:
            spread = statistics.pstdev(samples)
            first.score = statistics.median(samples)
            first.low_confidence = spread > CONSENSUS_MAX_STDEV
            if first.low_confidence:
                logger.info(f"low-confidence verdict: samples={samples} stdev={spread:.2f}")
        return first

    # ── atomic ────────────────────────────────────────────────────────

    def decompose(self, answer: str) -> List[str]:
        """Split an answer into independently checkable claims."""
        from src.agent.extractors.base import parse_llm_json

        try:
            raw = self.llm.complete(
                ATOMIC_DECOMPOSE_PROMPT.format(answer=answer),
                temperature=0.0,
                max_tokens=600,
            )
            parsed = parse_llm_json(str(raw))
        except Exception as exc:
            logger.warning(f"decomposition failed: {exc}")
            return []

        if isinstance(parsed, dict):
            for key in ("statements", "claims", "items"):
                if isinstance(parsed.get(key), list):
                    parsed = parsed[key]
                    break
        if not isinstance(parsed, list):
            return []
        return [str(s).strip() for s in parsed if str(s).strip()]

    def _judge_atomic(self, context: str, answer: str) -> Verdict:
        """
        Score as the fraction of atomic statements the context entails.

        Falls back to the structured single-shot when decomposition yields
        nothing — an answer too short to split is not an answer that needs it.
        """
        statements = self.decompose(answer)
        if not statements:
            fallback = StructuredJudge(
                self.llm,
                mode=JudgeMode.STRUCTURED,
                max_score=self.max_score,
                require_evidence=self.require_evidence,
                consensus=self.consensus,
                verify_evidence=self.verify_evidence,
            )
            verdict = fallback.judge(context, answer)
            verdict.mode = JudgeMode.ATOMIC
            return verdict

        supported = 0
        all_quotes: List[str] = []
        notes: List[str] = []

        for statement in statements:
            prompt = ATOMIC_NLI_PROMPT.format(context=context, statement=statement)
            single = self._one_shot(prompt, temperature=0.0)
            single.max_score = 1.0
            single = self._apply_evidence_rules(single, context)

            entailed = single.score >= 0.5 and not single.error
            supported += int(entailed)
            all_quotes.extend(single.quotes)
            notes.append(f"{'✓' if entailed else '✗'} {statement[:60]}")

        ratio = supported / len(statements)
        if self.atomic_aggregation == "strict" and supported < len(statements):
            ratio = min(ratio, STRICT_UNSUPPORTED_CEILING)
        return Verdict(
            score=round(ratio * self.max_score, 3),
            max_score=self.max_score,
            quotes=all_quotes,
            reasoning="\n".join(notes),
            mode=JudgeMode.ATOMIC,
        )
