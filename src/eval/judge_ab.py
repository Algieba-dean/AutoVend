"""
A/B harness for judge hallucination suppression.

Claiming a judge is "less hallucinatory" needs ground truth about the *judge*,
not about the system it judges — and that is the hard part, because normally
nobody knows the right answer for a free-form generation.

So the cases are **constructed with a known verdict**. Each takes a real
vehicle from the catalogue, builds a context from its actual fields, and pairs
it with an answer that is either:

- **faithful** — every claim traceable to the context, correct verdict: high;
- **hallucinated** — the same answer with one specific fact replaced by an
  invention (a range that is not in the context, a feature the car lacks),
  correct verdict: low.

A judge that scores both alike is not judging grounding. That gives four
measurable quantities:

| metric | what it catches |
|---|---|
| separation | mean(faithful) − mean(hallucinated). The headline. |
| detection rate | share of hallucinated cases scored below the pass mark |
| false alarms | share of faithful cases wrongly scored below it |
| stability | score variance across repeated runs of the same case |

Every mode is measured on the *same* cases with the same model, so a difference
is attributable to the prompt structure and nothing else.
"""

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from src.eval.alignment import alignment_report
from src.eval.judge import JudgeMode, StructuredJudge, Verdict, verify_quotes
from src.eval.runner import RESULTS_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Normalised score at or above which an answer is treated as accepted. 3/5 is
#: the rubric's "mostly right" mark.
PASS_MARK = 0.6


@dataclass
class JudgeCase:
    """One constructed case with a known correct verdict."""

    id: str
    context: str
    answer: str
    #: True when the answer contains an invented fact.
    hallucinated: bool
    #: What was invented, for error analysis.
    injected: str = ""

    @property
    def expected_high(self) -> bool:
        return not self.hallucinated


# ── Case construction ─────────────────────────────────────────────────

#: Fabrications injected into otherwise-faithful answers. Each contradicts or
#: exceeds the context rather than merely being unmentioned — a claim the
#: context is silent about is genuinely ambiguous, and grading a judge on
#: ambiguous cases measures the case design, not the judge.
#:
#: Two difficulty tiers, because they separate different judges. The blunt tier
#: is caught by anything that reads the answer at all, so a case set made only
#: of those cannot distinguish a careful judge from a fluent one.
BLATANT_INJECTIONS = [
    ("续航", "该车实测续航可达 1200 公里，远超同级。"),
    ("价格", "目前该车型有 8 万元的官方直降优惠。"),
    ("配置", "标配 L4 级全自动驾驶系统，可完全脱手。"),
    ("保修", "厂家提供终身免费保养和不限里程质保。"),
    ("动力", "零百加速仅需 1.9 秒，为量产车最快。"),
]

#: The tier that matters. Each is a plausible, unremarkable sentence about a
#: field the context genuinely contains — stated with a value the context does
#: not support. A judge scoring on recognition rather than on grounding waves
#: these through, because they read exactly like the true claims around them.
SUBTLE_INJECTIONS = [
    ("质保", "整车质保为 3 年或 10 万公里。"),
    ("能耗", "综合工况油耗约为每百公里 6.8 升。"),
    ("尺寸", "车身轴距为 2870 毫米，后排空间宽裕。"),
    ("安全", "该车配备 6 个安全气囊，通过五星安全认证。"),
    ("充电", "支持 800V 高压快充，30 分钟可充至 80%。"),
]


def build_cases(limit: int = 20, seed: int = 42, difficulty: str = "mixed") -> List[JudgeCase]:
    """
    Build paired faithful / hallucinated cases from the real catalogue.

    Pairs share a context, so a difference in score between the two members of
    a pair is caused by the injected claim alone.

    Args:
        difficulty: "blatant", "subtle", or "mixed". Report the subtle number —
            the blatant tier saturates and stops discriminating.
    """
    import random
    import sqlite3

    from src.utils.config import config

    rng = random.Random(seed)
    conn = sqlite3.connect(config.vehicle_db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT car_model, brand, vehicle_category_bottom, prize, powertrain_type, "
        "seat_layout, driving_range, drive_type FROM vehicles "
        "WHERE brand != '' AND prize != '' ORDER BY car_model LIMIT 400"
    ).fetchall()
    conn.close()

    if not rows:
        raise SystemExit("vehicle catalogue is empty — run `python -m src.main build`")

    chosen = rng.sample(list(rows), min(limit, len(rows)))
    cases: List[JudgeCase] = []

    for index, row in enumerate(chosen):
        context = _render_context(row)
        faithful = _render_answer(row)

        if difficulty == "blatant":
            pool = BLATANT_INJECTIONS
        elif difficulty == "subtle":
            pool = SUBTLE_INJECTIONS
        else:
            pool = BLATANT_INJECTIONS if index % 2 == 0 else SUBTLE_INJECTIONS
        label, injection = pool[index % len(pool)]
        tier = "blatant" if pool is BLATANT_INJECTIONS else "subtle"

        cases.append(
            JudgeCase(id=f"c{index:03d}-ok", context=context, answer=faithful, hallucinated=False)
        )
        cases.append(
            JudgeCase(
                id=f"c{index:03d}-halluc",
                context=context,
                answer=f"{faithful}{injection}",
                hallucinated=True,
                injected=f"{tier}/{label}",
            )
        )

    return cases


def _render_context(row) -> str:
    fields = [
        ("车型", row["car_model"]),
        ("品牌", row["brand"]),
        ("类别", row["vehicle_category_bottom"]),
        ("价格区间", row["prize"]),
        ("动力形式", row["powertrain_type"]),
        ("座位布局", row["seat_layout"]),
        ("续航", row["driving_range"]),
        ("驱动形式", row["drive_type"]),
    ]
    return "\n".join(f"{k}: {v}" for k, v in fields if v)


def _render_answer(row) -> str:
    parts = [f"为您推荐 {row['car_model']}，这是一款 {row['brand']} 的"]
    if row["vehicle_category_bottom"]:
        parts.append(f"{row['vehicle_category_bottom']}")
    parts.append("。")
    if row["prize"]:
        parts.append(f"价格区间为 {row['prize']}。")
    if row["powertrain_type"]:
        parts.append(f"动力形式是 {row['powertrain_type']}。")
    if row["seat_layout"]:
        parts.append(f"座位布局为 {row['seat_layout']}。")
    return "".join(parts)


# ── Scoring ───────────────────────────────────────────────────────────


@dataclass
class ModeResult:
    """How one judge mode performed across the case set."""

    mode: str
    n_cases: int = 0
    faithful_mean: float = 0.0
    hallucinated_mean: float = 0.0
    separation: float = 0.0
    detection_rate: float = 0.0
    false_alarm_rate: float = 0.0
    evidence_rate: float = 0.0
    format_failure_rate: float = 0.0
    fabricated_quote_rate: float = 0.0
    low_confidence_rate: float = 0.0
    #: Cohen's Kappa against the constructed truth. Reported next to
    #: `raw_agreement` because agreement alone is inflated by the 50/50 split
    #: here and would be inflated far worse on a real, mostly-faithful set.
    kappa: float = 0.0
    raw_agreement: float = 0.0
    n_errors: int = 0
    verdicts: List[Dict] = field(default_factory=list)

    def as_dict(self) -> Dict:
        payload = {k: v for k, v in self.__dict__.items() if k != "verdicts"}
        return payload


def evaluate_mode(
    llm,
    cases: Sequence[JudgeCase],
    mode: JudgeMode,
    consensus: bool = False,
    verify_evidence: bool = True,
) -> ModeResult:
    """Run one judge mode over every case."""
    judge = StructuredJudge(
        llm,
        mode=mode,
        consensus=consensus,
        verify_evidence=verify_evidence,
        require_evidence=mode in (JudgeMode.STRUCTURED, JudgeMode.ATOMIC),
    )

    faithful: List[float] = []
    hallucinated: List[float] = []
    with_evidence = 0
    format_failures = 0
    fabricated = 0
    low_confidence = 0
    errors = 0
    records: List[Dict] = []

    for case in cases:
        verdict: Verdict = judge.judge(case.context, case.answer)
        if verdict.error and "no score" in verdict.error:
            errors += 1
        if not verdict.format_ok:
            format_failures += 1
            # A judge that ignored the output format produced no verdict about
            # this answer. Counting it as a low score would mark the faithful
            # half as hallucinated — measured at 30% before this was split out.
            continue

        if verdict.has_evidence:
            with_evidence += 1
            if verify_quotes(verdict.quotes, case.context)["fabricated"]:
                fabricated += 1
        if verdict.low_confidence:
            low_confidence += 1

        (hallucinated if case.hallucinated else faithful).append(verdict.normalised)
        records.append({"case": case.id, "hallucinated": case.hallucinated, **verdict.as_dict()})
        logger.info(
            f"[{mode.value}] {case.id}: {verdict.normalised:.2f} "
            f"(expected {'low' if case.hallucinated else 'high'})"
        )

    n = len(cases) or 1
    faithful_mean = statistics.mean(faithful) if faithful else 0.0
    hallucinated_mean = statistics.mean(hallucinated) if hallucinated else 0.0

    # The constructed truth stands in for a human rater here: each case is
    # known-faithful or known-fabricated by construction. That makes kappa
    # measurable without a review round, but it is a *proxy* — constructed
    # cases are cleaner than production answers, so this number is an upper
    # bound on what human review would report, not a substitute for it.
    judge_scores = [r["normalised"] for r in records]
    truth_scores = [0.0 if r["hallucinated"] else 1.0 for r in records]
    alignment = alignment_report(
        judge_scores, truth_scores, pass_mark=PASS_MARK, ids=[r["case"] for r in records]
    )

    return ModeResult(
        mode=mode.value,
        n_cases=len(cases),
        faithful_mean=round(faithful_mean, 4),
        hallucinated_mean=round(hallucinated_mean, 4),
        separation=round(faithful_mean - hallucinated_mean, 4),
        detection_rate=round(sum(1 for s in hallucinated if s < PASS_MARK) / len(hallucinated), 4)
        if hallucinated
        else 0.0,
        false_alarm_rate=round(sum(1 for s in faithful if s < PASS_MARK) / len(faithful), 4)
        if faithful
        else 0.0,
        evidence_rate=round(with_evidence / n, 4),
        format_failure_rate=round(format_failures / n, 4),
        fabricated_quote_rate=round(fabricated / n, 4),
        low_confidence_rate=round(low_confidence / n, 4),
        kappa=round(alignment.kappa, 4),
        raw_agreement=round(alignment.raw_agreement, 4),
        n_errors=errors,
        verdicts=records,
    )


def measure_stability(llm, cases: Sequence[JudgeCase], mode: JudgeMode, repeats: int = 3) -> float:
    """
    Mean per-case score standard deviation across repeated runs.

    Run at temperature 0.5 deliberately: at temperature 0 a well-behaved model
    is trivially stable, which measures the sampler rather than the prompt.
    The question is whether the structure holds the verdict steady when the
    model is free to vary.
    """
    judge = StructuredJudge(llm, mode=mode, consensus=False)
    spreads: List[float] = []

    for case in cases:
        prompt_mode = mode if mode is not JudgeMode.ATOMIC else JudgeMode.STRUCTURED
        prompt = judge._prompt_for(prompt_mode).format(context=case.context, answer=case.answer)
        scores = []
        for _ in range(repeats):
            verdict = judge._one_shot(prompt, temperature=0.5)
            if not verdict.error:
                scores.append(verdict.normalised)
        if len(scores) >= 2:
            spreads.append(statistics.pstdev(scores))

    return round(statistics.mean(spreads), 4) if spreads else 0.0


# ── CLI ───────────────────────────────────────────────────────────────


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=10, help="Faithful/hallucinated pairs")
    parser.add_argument(
        "--difficulty",
        default="subtle",
        choices=["blatant", "subtle", "mixed"],
        help="Blatant injections saturate; subtle is what discriminates.",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["naive", "cot", "structured"],
        choices=[m.value for m in JudgeMode],
    )
    parser.add_argument("--stability", action="store_true", help="Also measure run-to-run spread")
    parser.add_argument("--consensus", action="store_true", help="Enable consensus re-sampling")
    parser.add_argument("--judge", default=None, help="Substring of the judge model id")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    from src.eval.ragas_eval import resolve_judge
    from src.llm.factory import LLMFactory

    judge_config = resolve_judge(args.judge)
    print(f"Judge model: {judge_config['model']}")
    llm = LLMFactory.create_llm(
        provider="openai",
        api_key=judge_config["api_key"],
        model=judge_config["model"],
        base_url=judge_config["base_url"],
    )

    cases = build_cases(limit=args.pairs, difficulty=args.difficulty)
    print(
        f"{len(cases)} cases ({args.pairs} faithful / {args.pairs} hallucinated), "
        f"difficulty={args.difficulty}\n"
    )

    results: List[ModeResult] = []
    for name in args.modes:
        mode = JudgeMode(name)
        print(f"Evaluating mode: {mode.value}...")
        results.append(evaluate_mode(llm, cases, mode, consensus=args.consensus))

    header = (
        f"{'mode':<12} {'faithful':>9} {'halluc':>8} {'separation':>11} "
        f"{'detect':>8} {'false+':>8} {'kappa':>7} {'agree':>7} "
        f"{'evidence':>9} {'fmt-fail':>9} {'fabricated':>11}"
    )
    print(f"\n{header}")
    for r in results:
        print(
            f"{r.mode:<12} {r.faithful_mean:>9.3f} {r.hallucinated_mean:>8.3f} "
            f"{r.separation:>11.3f} {r.detection_rate:>8.0%} {r.false_alarm_rate:>8.0%} "
            f"{r.kappa:>7.3f} {r.raw_agreement:>7.0%} "
            f"{r.evidence_rate:>9.0%} {r.format_failure_rate:>9.0%} "
            f"{r.fabricated_quote_rate:>11.0%}"
        )

    baseline = next((r for r in results if r.mode == "naive"), None)
    best = max(results, key=lambda r: r.separation)
    if baseline and best is not baseline:
        gain = best.separation - baseline.separation
        print(
            f"\n{best.mode} vs naive: separation {baseline.separation:.3f} → "
            f"{best.separation:.3f} ({gain:+.3f}), "
            f"detection {baseline.detection_rate:.0%} → {best.detection_rate:.0%}, "
            f"kappa {baseline.kappa:.3f} → {best.kappa:.3f}"
        )

    report: Dict = {
        "judge_model": judge_config["model"],
        "n_cases": len(cases),
        "difficulty": args.difficulty,
        "pass_mark": PASS_MARK,
        "modes": [r.as_dict() for r in results],
        "verdicts": {r.mode: r.verdicts for r in results},
    }

    if args.stability:
        print("\nStability (mean per-case stdev over 3 runs at temperature 0.5):")
        stability: Dict[str, float] = {}
        subset = cases[: min(6, len(cases))]
        for name in args.modes:
            spread = measure_stability(llm, subset, JudgeMode(name))
            stability[name] = spread
            print(f"  {name:<12} {spread:.4f}")
        report["stability"] = stability
        if "naive" in stability and len(stability) > 1:
            best_mode = min(stability, key=stability.get)
            base = stability["naive"]
            if base > 0:
                print(
                    f"  → {best_mode} is {(1 - stability[best_mode] / base):.0%} more stable "
                    f"than naive"
                )

    out = args.out or (RESULTS_DIR / "judge_ab.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
