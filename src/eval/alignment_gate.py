"""
Release gate: does the judge still agree with human reviewers?

Run:
    uv run python -m src.eval.alignment_gate --review evaluation/review/latest.jsonl

Exits non-zero when Cohen's Kappa falls below `KAPPA_GATE`, and **also** when
the review file is missing, empty, or too small to gate on. A gate that passes
because nobody reviewed anything is worse than no gate: it reports a green tick
for a judge whose calibration is entirely unknown.

This is the only tier that blocks on an LLM-derived number, and it blocks on
the judge's agreement with humans rather than on any individual verdict —
individual verdicts are stochastic, calibration is not supposed to be.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from src.eval.alignment import (
    KAPPA_GATE,
    MIN_SAMPLE_FOR_GATE,
    alignment_report,
    load_review_queue,
)
from src.eval.judge_ab import PASS_MARK
from src.eval.runner import RESULTS_DIR


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, help="Reviewed JSONL with human_score filled in")
    parser.add_argument(
        "--judged",
        default="",
        help="Judge results JSON. Defaults to the scores recorded alongside the review file.",
    )
    parser.add_argument("--gate", type=float, default=KAPPA_GATE)
    parser.add_argument(
        "--min-sample",
        type=int,
        default=MIN_SAMPLE_FOR_GATE,
        help="Below this the sample is too small for kappa to mean anything.",
    )
    args = parser.parse_args(argv)

    review_path = Path(args.review)
    if not review_path.exists():
        print(f"FAIL: no review file at {review_path}")
        print(
            "  A release gate with no human review is not a passing gate.\n"
            "  Generate one:  uv run python -m src.eval.review_sample --out "
            f"{review_path}"
        )
        return 1

    human = load_review_queue(review_path)
    if not human:
        print(
            f"FAIL: {review_path} has no filled-in human_score values "
            f"({_line_count(review_path)} rows)"
        )
        return 1

    judged_path = Path(args.judged) if args.judged else review_path.with_suffix(".judged.json")
    if not judged_path.exists():
        print(f"FAIL: no judge scores at {judged_path}")
        return 1

    judged = json.loads(judged_path.read_text(encoding="utf-8"))
    scores = {str(k): float(v) for k, v in judged.get("scores", judged).items()}

    # Only cases with both a human and a judge score can contribute. A silent
    # inner join would let a review file drift out of sync with the judged run
    # and still report a kappa, computed over whatever happened to overlap.
    ids = sorted(set(human) & set(scores))
    dropped = (set(human) | set(scores)) - set(ids)
    if dropped:
        print(f"note: {len(dropped)} case(s) present on only one side, excluded")

    report = alignment_report(
        [scores[i] for i in ids],
        [human[i] for i in ids],
        pass_mark=PASS_MARK,
        ids=ids,
    )

    print(f"\nreviewed cases:      {report.n}")
    print(f"raw agreement:       {report.raw_agreement:.1%}")
    print(f"  majority baseline: {report.majority_baseline:.1%}  ← what agreement must beat")
    print(f"Cohen's kappa:       {report.kappa:.3f}  (gate {args.gate})")
    print(f"quadratic kappa:     {report.quadratic_kappa:.3f}")

    if report.disagreements:
        print(f"\n{len(report.disagreements)} disagreement(s):")
        for d in report.disagreements[:10]:
            print(
                f"  {d['id']}: judge {d['judge_verdict']} ({d['judge']:.2f}) "
                f"vs human {d['human_verdict']} ({d['human']:.2f})"
            )

    out = RESULTS_DIR / f"alignment_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {**report.as_dict(), "disagreements": report.disagreements},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\n→ {out}")

    if report.n < args.min_sample:
        print(
            f"\nFAIL: {report.n} reviewed cases is below the {args.min_sample} needed for a "
            "meaningful kappa.\n  One flipped verdict on a sample this size moves kappa by "
            "more than the gate's own margin."
        )
        return 1

    if report.kappa < args.gate:
        print(f"\nFAIL: kappa {report.kappa:.3f} < {args.gate}")
        print("  The judge and its reviewers no longer agree; every judged metric downstream")
        print("  of it is measuring something other than what it claims to.")
        return 1

    print(f"\nPASS: kappa {report.kappa:.3f} >= {args.gate}")
    return 0


def _line_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


if __name__ == "__main__":
    sys.exit(main())
