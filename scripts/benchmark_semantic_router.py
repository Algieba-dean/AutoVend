#!/usr/bin/env python3
"""
Benchmark AutoVend's Semantic Router throughput and accuracy metrics.
"""

import sys
sys.path.insert(0, ".")
import time
import numpy as np
from src.semantic_router import get_router

def benchmark():
    router = get_router()
    if router is None:
        print("❌ Semantic Router not loaded — anchors artifact missing.")
        return

    summary = router.summary()
    print("==================================================")
    print("🧠 AutoVend Semantic Router (语义路由器性能微基准测试)")
    print("==================================================")
    print(f"锚点总数 (n_anchors): {summary['n_anchors']} 个常驻内存 (FP32)")
    print(f"向量维度 (dim)      : {summary['dim']} 维 (BAAI/bge-m3)")
    print(f"意图分类 (intents)  : {len(summary['intents'])} 种意图 (控制流 + 需求流)")
    print(f"内存常驻 (resident) : {summary['resident_bytes'] / 1024:.1f} KB")
    print(f"判定阈值 (threshold): {summary['threshold']} | 边际差 (margin): {summary['margin']}")
    print("--------------------------------------------------")

    # Benchmarking pure matmul classification speed (excluding embedding call)
    dummy_vec = np.random.randn(1024).astype(np.float32)
    dummy_vec /= np.linalg.norm(dummy_vec)

    # Warmup
    for _ in range(100):
        _ = dummy_vec @ router._matrix

    n_runs = 50000
    start = time.perf_counter()
    for _ in range(n_runs):
        scores = dummy_vec @ router._matrix
        best_idx = int(np.argmax(scores))
        _ = float(scores[best_idx])
    elapsed = time.perf_counter() - start

    qps = n_runs / elapsed
    latency_us = (elapsed / n_runs) * 1e6

    print(f"⚡ 纯算子极限分类吞吐量 (Pure Classifier Throughput): {qps:.1f} QPS")
    print(f"⏱️ 纯向量分类时延 (Classification Latency)       : {latency_us:.2f} μs (微秒)")
    print("==================================================")

    # Test sample Chinese control-flow and needs-flow utterances
    test_cases = [
        ("行，听你的", "affirm", "control_flow"),
        ("我再想想", "defer", "control_flow"),
        ("预算不太够", "budget_objection", "control_flow"),
        ("想要纯电 SUV", "powertrain", "needs_flow"),
        ("续航 600 公里以上", "driving_range", "needs_flow"),
        ("今天天气真好呀", None, None), # Unrelated smalltalk
    ]

    print("\n🔍 实际话术检测与路由匹配示例:")
    print("--------------------------------------------------")
    for text, expected_intent, expected_family in test_cases:
        decision = router.classify(text)
        status = "✅ 命中" if decision.matched else "⚪ 未命中"
        print(f"话术: \"{text}\"")
        print(f"   -> 状态: {status} | 意图: [{decision.intent}] | 相似度: {decision.score:.4f} | 边际差: {decision.margin:.4f}")
    print("==================================================")

if __name__ == "__main__":
    benchmark()
