"""
src/rag_service/onnx_reranker.py
Lightweight Cross-Encoder Reranker using ONNX Runtime.
"""

import logging
from pathlib import Path
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class OnnxCrossEncoderReranker:
    """
    Lightweight Cross-Encoder Reranker using ONNX Runtime.
    Provides standard Sigmoid normalization without arbitrary magic scale factors.
    """

    def __init__(self, model_path: Optional[str] = None, tokenizer_path: Optional[str] = None):
        self.model_path = model_path
        self.session = None
        self.tokenizer = None

        if model_path and Path(model_path).exists():
            try:
                import onnxruntime as ort

                opts = ort.SessionOptions()
                opts.intra_op_num_threads = 4
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                self.session = ort.InferenceSession(
                    model_path, opts, providers=["CPUExecutionProvider"]
                )
                logger.info(f"Loaded ONNX Cross-Encoder from {model_path}")

                tok_dir = tokenizer_path or str(Path(model_path).parent)
                try:
                    from transformers import AutoTokenizer

                    self.tokenizer = AutoTokenizer.from_pretrained(tok_dir, local_files_only=True)
                except Exception:
                    self.tokenizer = None
            except Exception as e:
                logger.warning(f"Failed to initialize ONNX Runtime session: {e}")
                self.session = None

    def score_pairs(self, query: str, doc_texts: List[str]) -> np.ndarray:
        """
        Score (query, doc) pairs using an ONNX Cross-Encoder model when loaded,
        or fall back to a token-overlap lexical heuristic when the model is unavailable.
        Returns normalized scores mapped into [0.0, 1.0].
        """
        if not doc_texts:
            return np.empty((0,), dtype=np.float32)

        if self.session is not None:
            try:
                pairs = [[query, doc] for doc in doc_texts]
                if self.tokenizer is not None:
                    encoded = self.tokenizer(
                        pairs,
                        padding=True,
                        truncation=True,
                        max_length=512,
                        return_tensors="np",
                    )
                    inputs = {}
                    for inp in self.session.get_inputs():
                        if inp.name in encoded:
                            inputs[inp.name] = encoded[inp.name].astype(np.int64)
                    raw_out = self.session.run(None, inputs)[0]
                    logits = np.squeeze(raw_out)
                    if logits.ndim == 0:
                        logits = np.array([float(logits)], dtype=np.float32)
                    probabilities = 1.0 / (1.0 + np.exp(-logits))
                    return probabilities
            except Exception as e:
                logger.warning(
                    f"ONNX inference failed: {e}. Falling back to token-overlap lexical heuristic scoring."
                )

        # Fallback: Token-overlap lexical heuristic with bilingual tokenization.
        # NOTE: This is a purely lexical overlap baseline (not neural cross-attention).
        from src.retrieval.bm25_index import tokenize

        clean_q = query.lower()
        q_tokens = tokenize(clean_q)
        if not q_tokens:
            q_tokens = [t for t in clean_q.split() if t]

        logits = []
        for doc in doc_texts:
            d_lower = doc.lower()
            if not q_tokens:
                logits.append(0.0)
                continue
            matched = sum(1.0 for t in q_tokens if t in d_lower)
            ratio = matched / len(q_tokens)
            # Center around 0 with spread
            logit = (ratio - 0.5) * 4.0
            logits.append(logit)

        logits_arr = np.array(logits, dtype=np.float32)
        # Standard Sigmoid normalization strictly into [0.0, 1.0]
        probabilities = 1.0 / (1.0 + np.exp(-logits_arr))
        return probabilities
