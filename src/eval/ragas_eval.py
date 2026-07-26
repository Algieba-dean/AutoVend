"""
LLM-judged RAG evaluation (RAGAS).

Answers what the deterministic gate cannot: *given the vehicles we retrieved,
is the recommendation the agent wrote actually supported by them?* Retrieval
metrics say the right cars were in context; faithfulness says the model did not
invent range figures or trim levels once it started writing.

**This never gates CI.** An LLM judge is stochastic and costs API calls, so it
runs on a schedule and on demand, and its output is a trend to read, not a
build status. The blocking gate is `src/eval/gate.py`.

Metrics:
- faithfulness       — claims in the answer entailed by the retrieved context
- answer_relevancy   — does the answer address the question that was asked
- context_precision  — is the retrieved context free of irrelevant vehicles
- context_recall     — did retrieval surface the vehicles the answer needed

Usage:
    python -m src.eval.ragas_eval --sample 30
    python -m src.eval.ragas_eval --sample 10 --system hybrid
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from src.eval.golden_set import load_golden_set
from src.eval.runner import RESULTS_DIR
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Vehicles handed to the generator per question — matches RETRIEVAL_TOP_K in
#: the chat route, so the judged context is the context users actually get.
CONTEXT_TOP_K = 5


def _require_credentials() -> None:
    if not config.has_llm_credentials:
        raise SystemExit(
            "RAGAS evaluation needs LLM credentials. Set LLM_API_KEY (or "
            "GROQ_API_KEY / DEEPSEEK_API_KEY) in .env, or add one as a "
            "repository secret for the scheduled workflow. The deterministic "
            "gate (src.eval.gate) runs without any key."
        )


def resolve_judge(preferred: Optional[str] = None) -> Dict[str, str]:
    """
    Pick which cloud provider judges, probing each for a live quota.

    RAGAS issues several calls per sample, so a provider that is already near
    its daily cap will fail most of the run and leave metrics scored over a
    handful of survivors. Probing once up front costs one request and avoids
    discovering the exhaustion twenty minutes in — which is exactly how the
    first attempt at this was lost.
    """
    from src.llm.router import build_default_router

    router = build_default_router()
    candidates = [
        backend
        for backend in router.cloud_chain
        if preferred is None or preferred in (getattr(backend, "model", "") or "")
    ]
    if not candidates:
        raise SystemExit(f"No cloud provider matches {preferred!r}.")

    for backend in candidates:
        try:
            backend.complete("ping", max_tokens=4, temperature=0.0)
        except Exception as exc:
            logger.warning(f"[ragas] judge candidate {backend.model} unusable: {str(exc)[:160]}")
            continue
        return {
            "model": backend.model,
            "api_key": backend.api_key,
            "base_url": backend.base_url,
        }

    raise SystemExit(
        "Every cloud provider failed a probe call — check quotas before running RAGAS."
    )


def build_samples(
    generator: Dict[str, str],
    system_name: str = "fusion",
    limit: Optional[int] = None,
) -> List[Dict]:
    """
    Produce (question, contexts, answer, reference) rows for RAGAS.

    Each row is one retrieval + one generation, i.e. the same two steps a real
    turn performs — judging a synthetic pipeline would measure something the
    users never see.
    """
    from llama_index.llms.openai_like import OpenAILike

    from src.agent.response_generator import generate_response
    from src.agent.schemas import ReservationInfo, Stage, UserProfile, VehicleNeeds
    from src.retrieval.adapters import search_response_to_cars
    from src.retrieval.hybrid_pipeline import build_default_pipeline

    queries = load_golden_set()
    if limit:
        # Deterministic slice: same subset every run, so the trend is comparable.
        queries = queries[:: max(1, len(queries) // limit)][:limit]

    # The answers under judgement come from the same provider that judges them.
    # Not ideal — a model grading its own prose is a known bias — but it beats
    # the alternative here, which is half the run failing on an exhausted quota.
    # The bias is noted in the report so the number is read with it in mind.
    llm = OpenAILike(
        api_key=generator["api_key"],
        api_base=generator["base_url"],
        model=generator["model"],
        is_chat_model=True,
        temperature=0.0,  # judge the median behaviour, not a lucky sample
        max_tokens=500,
    )

    pipeline = build_default_pipeline(
        enable_llm_parser=False,
        enable_sparse=system_name == "fusion",
    )

    samples: List[Dict] = []
    for query in queries:
        result = pipeline.search(query.query, top_k=CONTEXT_TOP_K, use_llm_fallback=False)
        cars = search_response_to_cars(result.search_response, limit=CONTEXT_TOP_K)
        if not cars:
            logger.warning(f"[ragas] {query.id}: no context retrieved, skipped")
            continue

        contexts = [_car_to_context(car) for car in cars]
        answer = generate_response(
            llm,
            Stage.CAR_SELECTION,
            f"User: {query.query}",
            UserProfile(),
            VehicleNeeds(),
            cars,
            ReservationInfo(),
        )

        samples.append(
            {
                "user_input": query.query,
                "retrieved_contexts": contexts,
                "response": answer,
                # Ground truth for context_recall: the vehicles that *should*
                # have been retrievable, capped so the reference stays readable.
                "reference": ", ".join(query.relevant_car_models[:CONTEXT_TOP_K]),
                "_id": query.id,
                "_tags": query.tags,
            }
        )
        logger.info(f"[ragas] {query.id}: {len(contexts)} contexts, {len(answer)} chars")

    return samples


def _car_to_context(car: Dict) -> str:
    """Render one retrieved vehicle as the context string the judge sees."""
    parts = [f"{key}: {value}" for key, value in car.get("metadata", {}).items()]
    snippet = car.get("text_snippet") or ""
    if snippet:
        parts.append(snippet)
    return " | ".join(parts)


#: Concurrency for judge calls. Groq rate-limits aggressively; anything higher
#: turns most jobs into timeouts, and a timed-out metric silently scores 0 —
#: indistinguishable from a genuinely bad result.
JUDGE_MAX_WORKERS = 3
JUDGE_TIMEOUT_S = 300


def run_ragas(samples: Sequence[Dict], judge_config: Dict[str, str]):
    """Score the samples with RAGAS, using the resolved cloud provider as judge."""
    from langchain_openai import ChatOpenAI
    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )
    from ragas.run_config import RunConfig

    judge = LangchainLLMWrapper(
        ChatOpenAI(
            model=judge_config["model"],
            api_key=judge_config["api_key"],
            base_url=judge_config["base_url"],
            temperature=0.0,
            timeout=JUDGE_TIMEOUT_S,
            max_retries=5,
        )
    )
    # Reuse the local BGE-M3 rather than an embedding API: answer_relevancy only
    # needs a consistent similarity space, and this keeps the run offline apart
    # from the judge itself.
    embeddings = LangchainEmbeddingsWrapper(_LocalBGEEmbeddings())

    dataset = EvaluationDataset.from_list(
        [{k: v for k, v in s.items() if not k.startswith("_")} for s in samples]
    )

    return evaluate(
        dataset=dataset,
        metrics=[
            Faithfulness(llm=judge),
            # strictness=1 asks for a single generation. The default of 3 sets
            # OpenAI's `n` parameter, which Groq rejects outright
            # ("'n' : number must be at most 1"), failing every job.
            AnswerRelevancy(llm=judge, embeddings=embeddings, strictness=1),
            ContextPrecision(llm=judge),
            ContextRecall(llm=judge),
        ],
        run_config=RunConfig(
            timeout=JUDGE_TIMEOUT_S,
            max_workers=JUDGE_MAX_WORKERS,
            max_retries=5,
        ),
    )


def summarize(result) -> Dict[str, Dict]:
    """
    Average each metric over the samples that actually got judged.

    RAGAS records NaN for a job that errored or timed out. Its own aggregate
    treats those as zero, so a rate-limited run reports `context_precision:
    0.0000` — visually identical to a real failure of the retriever. Splitting
    scored from failed keeps "we did not measure this" distinguishable from
    "this scored badly".
    """
    import math

    frame = result.to_pandas()
    summary: Dict[str, Dict] = {}
    for metric in result.to_pandas().columns:
        if metric in ("user_input", "retrieved_contexts", "response", "reference"):
            continue
        values = [v for v in frame[metric].tolist() if isinstance(v, (int, float))]
        scored = [v for v in values if not math.isnan(v)]
        summary[metric] = {
            "score": round(sum(scored) / len(scored), 4) if scored else None,
            "n_scored": len(scored),
            "n_failed": len(values) - len(scored),
        }
    return summary


class _LocalBGEEmbeddings:
    """Adapts the project's BGE-M3 model to the LangChain embeddings interface."""

    def __init__(self):
        from src.rag.embeddings import BGEEmbeddingModel

        self._model = BGEEmbeddingModel()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._model._get_text_embedding(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._model._get_text_embedding(text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        return self.embed_query(text)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=30, help="Number of golden queries to judge")
    parser.add_argument("--system", default="fusion", help="Retrieval system under judgement")
    parser.add_argument("--out", type=Path, default=None, help="Where to write the JSON report")
    parser.add_argument(
        "--judge",
        default=None,
        help="Substring of the judge model id; defaults to the first cloud provider with quota.",
    )
    args = parser.parse_args(argv)

    _require_credentials()

    judge_config = resolve_judge(args.judge)
    print(f"Judge: {judge_config['model']} ({judge_config['base_url']})")

    samples = build_samples(judge_config, args.system, args.sample)
    if not samples:
        print("No samples could be built — is the index built?", file=sys.stderr)
        return 1

    print(f"Judging {len(samples)} samples with {judge_config['model']}...")
    result = run_ragas(samples, judge_config)
    scores = summarize(result)

    report = {
        "system": args.system,
        "judge_model": judge_config["model"],
        "generator_model": judge_config["model"],
        "n_samples": len(samples),
        "scores": scores,
        "query_ids": [s["_id"] for s in samples],
        "caveat": (
            "Answers were generated and judged by the same model; treat "
            "answer_relevancy in particular as an upper bound."
        ),
    }

    out = args.out or (RESULTS_DIR / f"ragas_{args.system}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nRAGAS — {args.system} ({len(samples)} samples, judge {judge_config['model']})")
    degraded = False
    for metric, row in scores.items():
        if row["n_scored"] == 0:
            print(f"  {metric:<20}     n/a  (all {row['n_failed']} judge calls failed)")
            degraded = True
            continue
        note = ""
        if row["n_failed"]:
            note = f"  [{row['n_failed']}/{row['n_scored'] + row['n_failed']} judge calls failed]"
            degraded = True
        print(f"  {metric:<20} {row['score']:.4f}{note}")

    if degraded:
        # A timed-out judge call would otherwise average in as a zero, which
        # reads as "the system is bad" rather than "we did not measure it".
        print(
            "\nSome judge calls failed — scores above are over the successful "
            "subset only. Re-run before quoting them.",
            file=sys.stderr,
        )

    print(f"\nReport: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
