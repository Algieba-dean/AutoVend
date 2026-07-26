"""
Offline anchor build.

    python -m src.semantic_router.build
    python -m src.semantic_router.build --k 4 --probe

Embeds the seed corpus, clusters each intent, and writes `data/anchors.npz`.
Run it whenever the seeds or the embedding model change — the artifact is tied
to both, and the router refuses nothing at load time, so a stale artifact would
silently degrade routing rather than fail.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from src.semantic_router.anchors import DEFAULT_K, build_anchor_set
from src.semantic_router.seeds import seed_count

#: Paraphrases the seeds do not contain verbatim, plus deliberately off-domain
#: sentences. The latter matter most: they check the router says "no match"
#: rather than forcing every input into its nearest intent. Both off-domain
#: probes score *above* the 0.62 threshold — it is the margin guard that
#: rejects them, which is why a single cut-off would not be enough.
PROBE_UTTERANCES = [
    ("行，听你的", "affirm"),
    ("我再想想吧", "defer"),
    ("太贵了，超预算", "budget_objection"),
    ("我有35万的预算", "budget"),
    ("我要油车，不要电车", "powertrain"),
    ("平时就是上下班代步", "usage"),
    ("想看看七座的SUV", "category"),
    ("今天天气真不错", None),
    ("这个螺丝刀多少钱", None),
]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=DEFAULT_K, help="Clusters per intent")
    parser.add_argument("--out", type=Path, default=None, help="Artifact path")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Classify a few known utterances after building, as a smoke test.",
    )
    args = parser.parse_args(argv)

    print(f"Embedding {seed_count()} seed utterances...")
    anchors = build_anchor_set(k=args.k)
    path = anchors.save(args.out)

    summary = anchors.summary()
    print(f"\nAnchors: {summary['n_anchors']} vectors x {summary['dim']} dims")
    print(f"Model:   {summary['model']}")
    print(f"Written: {path} ({path.stat().st_size / 1024:.1f} KB)")
    print("\nPer intent:")
    for intent, count in sorted(summary["intents"].items()):
        print(f"  {intent:<20} {count}")

    if args.probe:
        from src.semantic_router.router import SemanticRouter

        router = SemanticRouter(anchors)
        print(f"\nProbe (threshold {router.threshold}, margin {router.margin}):")
        wrong = 0
        for text, expected in PROBE_UTTERANCES:
            decision = router.classify(text)
            got = decision.intent
            ok = got == expected
            wrong += 0 if ok else 1
            flag = " " if ok else "✗"
            print(
                f" {flag} {text:<20} → {str(got):<18} "
                f"score={decision.score:.3f} margin={decision.margin:.3f} "
                f"(expected {expected})"
            )
        if wrong:
            # Non-zero so CI catches it. A seed or threshold change that breaks
            # routing is otherwise invisible — an unbuilt or mis-tuned router
            # does not error, it just quietly sends every turn the long way.
            print(
                f"\n{wrong}/{len(PROBE_UTTERANCES)} probes disagree — "
                "tune --k or the thresholds in src/semantic_router/router.py.",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
