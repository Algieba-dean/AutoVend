"""
Batch API packaging for nightly evaluation.

The synchronous queue is the right tool for a PR gate, where the answer is
needed in minutes. It is the wrong tool for a nightly full-set run: at ~50%
provider discount and no rate-limit pressure, the batch endpoint costs half as
much and cannot fail the run by exhausting a per-minute quota. The trade is
latency — a batch completes within hours, not seconds — which a nightly job has
in abundance and a PR gate does not.

The format is JSONL, one request per line, each carrying a `custom_id` that
comes back attached to its response. That id is the *only* thing linking a
result to the case that produced it: batch responses arrive unordered and
incomplete, so an index-based join silently mismatches results to cases the
moment one request fails.

This module packages and parses. Submission is deliberately left to the caller
— OpenAI, Anthropic and DeepSeek differ on the upload/poll dance, and wrapping
all three behind one interface would hide exactly the details that break.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from src.eval.judge import JudgeMode, StructuredJudge
from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Provider ceiling on a single batch file. Larger sets are split into parts.
MAX_REQUESTS_PER_BATCH = 50_000

#: Provider ceiling on file size (100 MB). Judge prompts carry retrieved
#: context, so a full evaluation set reaches this well before the request cap.
MAX_BATCH_BYTES = 100 * 1024 * 1024


@dataclass
class BatchRequest:
    """One judge call, in batch form."""

    custom_id: str
    model: str
    messages: List[Dict[str, str]]
    temperature: float = 0.0
    max_tokens: int = 1024

    def to_line(self) -> Dict[str, Any]:
        return {
            "custom_id": self.custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.model,
                "messages": self.messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
        }


def build_requests(
    cases: Sequence[Any],
    model: str,
    mode: JudgeMode = JudgeMode.STRUCTURED,
    judge: Optional[StructuredJudge] = None,
) -> List[BatchRequest]:
    """
    Render judge cases as batch requests.

    Prompts are built by the same `StructuredJudge` the synchronous path uses.
    Rebuilding them here would let the batch and sync paths drift apart, and a
    nightly run judging by a different rubric than the PR gate produces two
    incomparable baselines — the failure is silent, because both look fine
    alone.
    """
    judge = judge or StructuredJudge(llm=None, mode=mode)
    prompt_mode = mode if mode is not JudgeMode.ATOMIC else JudgeMode.STRUCTURED
    template = judge._prompt_for(prompt_mode)

    return [
        BatchRequest(
            custom_id=str(case.id),
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": template.format(context=case.context, answer=case.answer),
                }
            ],
        )
        for case in cases
    ]


def write_batch(requests: Sequence[BatchRequest], path: Path) -> List[Path]:
    """
    Write requests as JSONL, splitting into parts at the provider ceilings.

    Returns every part written. Splitting on size as well as count matters:
    a set well under 50k requests still overruns the 100 MB file limit once
    each prompt carries a few thousand tokens of context, and the provider
    rejects the whole upload rather than the overflowing tail.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    seen: set = set()
    for request in requests:
        if request.custom_id in seen:
            # Duplicate ids make the response join ambiguous — one result
            # would overwrite the other with no error anywhere.
            raise ValueError(f"duplicate custom_id: {request.custom_id}")
        seen.add(request.custom_id)

    parts: List[Path] = []
    buffer: List[str] = []
    buffer_bytes = 0

    def flush() -> None:
        nonlocal buffer, buffer_bytes
        if not buffer:
            return
        part_path = (
            path if not parts and len(buffer) == len(requests) else _part_path(path, len(parts))
        )
        part_path.write_text("".join(buffer), encoding="utf-8")
        parts.append(part_path)
        buffer, buffer_bytes = [], 0

    for request in requests:
        line = json.dumps(request.to_line(), ensure_ascii=False) + "\n"
        encoded = len(line.encode("utf-8"))
        if buffer and (
            len(buffer) >= MAX_REQUESTS_PER_BATCH or buffer_bytes + encoded > MAX_BATCH_BYTES
        ):
            flush()
        buffer.append(line)
        buffer_bytes += encoded

    flush()
    logger.info(f"wrote {len(requests)} batch requests to {len(parts)} file(s)")
    return parts


def _part_path(path: Path, index: int) -> Path:
    return path.with_name(f"{path.stem}.part{index:02d}{path.suffix}")


def parse_results(lines: Iterable[str], mode: JudgeMode = JudgeMode.STRUCTURED) -> Dict[str, Any]:
    """
    Parse a batch result file into {custom_id: Verdict}.

    Batch responses arrive unordered, and individual requests can fail while
    the batch as a whole succeeds — so failures are collected rather than
    raised. A caller that treats a missing id as a zero score would mark
    genuinely-unjudged cases as hallucinations; `missing` is reported
    separately so it can be re-queued instead.
    """
    from src.eval.judge import parse_verdict

    verdicts: Dict[str, Any] = {}
    failures: Dict[str, str] = {}

    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        custom_id = row.get("custom_id", "")

        error = row.get("error") or (row.get("response") or {}).get("error")
        if error:
            failures[custom_id] = str(error)[:200]
            continue

        try:
            body = row["response"]["body"]
            raw = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            failures[custom_id] = f"malformed response: {exc}"
            continue

        verdicts[custom_id] = parse_verdict(raw, mode)

    return {"verdicts": verdicts, "failures": failures, "n_ok": len(verdicts)}


def reconcile(cases: Sequence[Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Join batch results back onto the case set, reporting what did not return.

    Named separately from `parse_results` because this is the step that
    decides whether the run is usable at all: a nightly baseline computed over
    whichever 80% of cases happened to come back is not comparable to
    yesterday's, and comparing it anyway is how a gate starts alarming on
    coverage changes it reads as quality regressions.
    """
    verdicts = parsed["verdicts"]
    missing = [str(c.id) for c in cases if str(c.id) not in verdicts]
    coverage = (len(cases) - len(missing)) / len(cases) if cases else 0.0

    if missing:
        logger.warning(f"{len(missing)}/{len(cases)} cases missing from batch results")

    return {
        "n_cases": len(cases),
        "n_judged": len(cases) - len(missing),
        "coverage": round(coverage, 4),
        "missing": missing[:50],
        "failures": parsed["failures"],
        "verdicts": verdicts,
    }
