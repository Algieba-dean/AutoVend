"""
Draw the human review queue for a release.

Run:
    uv run python -m src.eval.review_sample --pairs 12 --out evaluation/review/latest.jsonl

Writes two files side by side:

  latest.jsonl        — for the reviewer. Case text only, `human_score` blank.
  latest.judged.json  — the judge's own scores, written separately.

The split is the point. A reviewer shown the judge's score first anchors on it,
and a reviewer who agrees with a number they were handed is not an independent
rater — the kappa computed from that review measures suggestibility, not
alignment. The gate reads both files and joins on case id.

Scoring is on the same 0–1 normalised scale the judge uses, so `human_score`
is directly comparable: 1.0 fully grounded, 0.0 contradicted by the context.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from src.eval.alignment import HUMAN_SAMPLE_RATE, sample_for_review, write_review_queue
from src.eval.judge import JudgeMode, StructuredJudge
from src.eval.judge_ab import PASS_MARK, build_cases
from src.eval.ragas_eval import resolve_judge
from src.llm.factory import LLMFactory


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=12)
    parser.add_argument("--difficulty", default="subtle", choices=["blatant", "subtle", "mixed"])
    parser.add_argument("--judge", default="deepseek")
    parser.add_argument("--rate", type=float, default=HUMAN_SAMPLE_RATE)
    parser.add_argument("--out", default="evaluation/review/latest.jsonl")
    args = parser.parse_args(argv)

    cases = build_cases(limit=args.pairs, difficulty=args.difficulty)
    judge_config = resolve_judge(args.judge)
    llm = LLMFactory.create_llm(
        provider="openai",
        api_key=judge_config["api_key"],
        model=judge_config["model"],
        base_url=judge_config["base_url"],
    )
    judge = StructuredJudge(llm, mode=JudgeMode.STRUCTURED)

    print(f"judging {len(cases)} cases with {judge_config['model']}...")
    records = []
    for case in cases:
        verdict = judge.judge(case.context, case.answer)
        records.append(
            {
                "id": case.id,
                "context": case.context,
                "answer": case.answer,
                "score": verdict.normalised,
                "pass_mark": PASS_MARK,
                "low_confidence": verdict.low_confidence,
            }
        )

    sample = sample_for_review(records, rate=args.rate)
    out = Path(args.out)
    write_review_queue(sample, out)

    judged_path = out.with_suffix(".judged.json")
    judged_path.write_text(
        json.dumps(
            {"scores": {r["id"]: round(r["score"], 4) for r in sample}},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    n_fail = sum(1 for r in sample if r["score"] < PASS_MARK)
    print(f"\n{len(sample)} cases drawn from {len(records)} ({n_fail} the judge failed)")
    print(f"  reviewer file: {out}")
    print(f"  judge scores:  {judged_path}  (do not show the reviewer)")
    print("\nFill in human_score (0.0–1.0) on every row, then:")
    print(f"  uv run python -m src.eval.alignment_gate --review {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
