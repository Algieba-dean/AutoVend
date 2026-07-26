"""
Judge-vs-human alignment: Cohen's Kappa, and the sampling workflow around it.

A judge that agrees with human reviewers 90% of the time sounds trustworthy
until you notice that 85% of cases are faithful, so a judge that blindly
answers "faithful" also scores 88%. Raw agreement is inflated by the base rate
of the majority class, and evaluation sets are always imbalanced this way.

Cohen's Kappa removes the agreement expected from chance alone:

    kappa = (p_observed - p_chance) / (1 - p_chance)

0 means "no better than guessing at the observed base rates", 1 means perfect.
The always-faithful judge above scores kappa ≈ 0 while its raw agreement reads
88%, which is the whole point of using it.

**Quadratic weights for ordinal scores.** The judge emits 0–5, not a bit. An
unweighted kappa treats "human 4, judge 5" as exactly as wrong as "human 0,
judge 5", which understates a judge that is calibrated but slightly generous.
`quadratic_kappa` penalises by squared distance instead, so near-misses cost
little and inversions cost a lot.

**On the threshold.** ≥0.85 is a release gate, not a running check. Kappa on a
20-case sample has a wide confidence interval — a single flipped case moves it
by ~0.05 — so a small sample failing the gate means "review more cases", not
"the judge regressed". `alignment_report` returns `n` alongside kappa so the
gate can refuse to fire on a sample too small to mean anything.
"""

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

#: Release gate. Landis & Koch call 0.81–1.00 "almost perfect"; 0.85 sits
#: inside that band with margin for one disagreement on a 20-case sample.
KAPPA_GATE = 0.85

#: Below this, kappa is too noisy to gate on — report it, do not enforce it.
MIN_SAMPLE_FOR_GATE = 20

#: Fraction of each release's evaluation set routed to human review.
HUMAN_SAMPLE_RATE = 0.05


@dataclass
class AlignmentReport:
    """Judge-vs-human agreement on one reviewed sample."""

    n: int
    raw_agreement: float
    kappa: float
    quadratic_kappa: float
    #: Raw agreement a judge would reach by always predicting the majority
    #: label. Printed next to the real number because it is the figure the real
    #: number has to beat to mean anything.
    majority_baseline: float
    disagreements: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def gateable(self) -> bool:
        return self.n >= MIN_SAMPLE_FOR_GATE

    @property
    def passed(self) -> bool:
        return self.gateable and self.kappa >= KAPPA_GATE

    def as_dict(self) -> Dict[str, Any]:
        return {
            "n": self.n,
            "raw_agreement": round(self.raw_agreement, 3),
            "majority_baseline": round(self.majority_baseline, 3),
            "kappa": round(self.kappa, 3),
            "quadratic_kappa": round(self.quadratic_kappa, 3),
            "gate": KAPPA_GATE,
            "gateable": self.gateable,
            "passed": self.passed,
            "n_disagreements": len(self.disagreements),
        }


def cohens_kappa(a: Sequence[Any], b: Sequence[Any]) -> float:
    """
    Unweighted Cohen's Kappa between two label sequences.

    Returns 1.0 when both raters are unanimous and identical: chance agreement
    is then also 1.0, leaving 0/0. Perfect agreement is the honest reading, but
    it is also a degenerate sample — `AlignmentReport.n` is what tells you
    whether to believe it.
    """
    if len(a) != len(b):
        raise ValueError(f"rater lengths differ: {len(a)} vs {len(b)}")
    if not a:
        return 0.0

    n = len(a)
    observed = sum(1 for x, y in zip(a, b) if x == y) / n

    labels = set(a) | set(b)
    chance = sum((_count(a, label) / n) * (_count(b, label) / n) for label in labels)

    if math.isclose(chance, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else 0.0
    return (observed - chance) / (1 - chance)


def quadratic_kappa(a: Sequence[float], b: Sequence[float], max_score: float = 5.0) -> float:
    """
    Quadratically-weighted kappa for ordinal scores.

    Disagreements are weighted by squared distance, so a judge that is one
    point generous is treated very differently from one that inverts verdicts.
    """
    if len(a) != len(b):
        raise ValueError(f"rater lengths differ: {len(a)} vs {len(b)}")
    if not a:
        return 0.0

    n = len(a)
    levels = sorted({int(round(v)) for v in list(a) + list(b)})
    if len(levels) < 2:
        return 1.0 if all(x == y for x, y in zip(a, b)) else 0.0

    index = {level: i for i, level in enumerate(levels)}
    k = len(levels)
    denom = (k - 1) ** 2

    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        observed[index[int(round(x))]][index[int(round(y))]] += 1 / n

    hist_a = [_count([int(round(v)) for v in a], level) / n for level in levels]
    hist_b = [_count([int(round(v)) for v in b], level) / n for level in levels]

    num = den = 0.0
    for i in range(k):
        for j in range(k):
            weight = ((i - j) ** 2) / denom
            num += weight * observed[i][j]
            den += weight * hist_a[i] * hist_b[j]

    return 1.0 - num / den if den else 1.0


def _count(seq: Sequence[Any], value: Any) -> int:
    return sum(1 for x in seq if x == value)


def alignment_report(
    judge_scores: Sequence[float],
    human_scores: Sequence[float],
    pass_mark: float = 0.6,
    max_score: float = 5.0,
    ids: Optional[Sequence[str]] = None,
) -> AlignmentReport:
    """
    Compare judge and human scores on the same cases.

    Both kappas are computed: the binary one against the pass/fail decision the
    gate actually consumes, the quadratic one against the full ordinal scale,
    which catches calibration drift that the binary view rounds away.
    """
    judge_binary = [s >= pass_mark for s in judge_scores]
    human_binary = [s >= pass_mark for s in human_scores]

    n = len(judge_binary)
    agree = sum(1 for x, y in zip(judge_binary, human_binary) if x == y)
    n_true = sum(human_binary)
    majority = max(n_true, n - n_true) / n if n else 0.0

    disagreements = [
        {
            "id": ids[i] if ids else str(i),
            "judge": round(judge_scores[i], 3),
            "human": round(human_scores[i], 3),
            "judge_verdict": "pass" if judge_binary[i] else "fail",
            "human_verdict": "pass" if human_binary[i] else "fail",
        }
        for i in range(n)
        if judge_binary[i] != human_binary[i]
    ]

    return AlignmentReport(
        n=n,
        raw_agreement=agree / n if n else 0.0,
        kappa=cohens_kappa(judge_binary, human_binary),
        quadratic_kappa=quadratic_kappa(
            [s * max_score for s in judge_scores],
            [s * max_score for s in human_scores],
            max_score=max_score,
        ),
        majority_baseline=majority,
        disagreements=disagreements,
    )


def sample_for_review(
    results: Sequence[Dict[str, Any]],
    rate: float = HUMAN_SAMPLE_RATE,
    seed: int = 42,
    min_n: int = MIN_SAMPLE_FOR_GATE,
) -> List[Dict[str, Any]]:
    """
    Draw a stratified review sample.

    Stratified by the judge's own pass/fail call, because a uniform 5% of an
    imbalanced set is almost entirely cases the judge passed — and a sample
    with two failures in it cannot tell you anything about how the judge
    handles failures. Both strata are represented, so kappa is estimated on the
    axis the gate cares about.

    Sampling is seeded: the same results yield the same review queue, so a
    re-run does not silently ask reviewers for fresh work.
    """
    rng = random.Random(seed)
    target = max(min_n, math.ceil(len(results) * rate))
    target = min(target, len(results))

    passed = [r for r in results if r.get("score", 0) >= r.get("pass_mark", 0.6)]
    failed = [r for r in results if r.get("score", 0) < r.get("pass_mark", 0.6)]

    # Half from each stratum where possible; a short stratum donates its
    # shortfall to the other rather than shrinking the sample.
    want_fail = min(len(failed), target // 2)
    want_pass = min(len(passed), target - want_fail)
    want_fail = min(len(failed), target - want_pass)

    sample = rng.sample(failed, want_fail) + rng.sample(passed, want_pass)
    sample.sort(key=lambda r: str(r.get("id", "")))

    # Low-confidence cases are exactly the ones a human should see, so they are
    # force-included regardless of the draw.
    already = {id(r) for r in sample}
    for r in results:
        if r.get("low_confidence") and id(r) not in already:
            sample.append(r)

    return sample


def write_review_queue(sample: Sequence[Dict[str, Any]], path: Path) -> Path:
    """
    Write a review queue as JSONL, one case per line.

    `human_score` is left null for the reviewer to fill in. The judge's own
    score is deliberately **omitted** from the file: showing it first is a
    textbook anchoring effect, and a reviewer who agrees with a number they
    were shown is not an independent rater, which makes the resulting kappa
    meaningless.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for case in sample:
            fh.write(
                json.dumps(
                    {
                        "id": case.get("id"),
                        "context": case.get("context", ""),
                        "answer": case.get("answer", ""),
                        "human_score": None,
                        "note": "",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return path


def load_review_queue(path: Path) -> Dict[str, float]:
    """Read back the reviewed queue as {case_id: human_score}, skipping blanks."""
    labels: Dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("human_score") is not None:
            labels[str(row["id"])] = float(row["human_score"])
    return labels
