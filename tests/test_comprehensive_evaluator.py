"""
Unit tests for Comprehensive Agent & RAG Evaluator (src/eval/comprehensive_evaluator.py).
"""

from src.eval.comprehensive_evaluator import ComprehensiveEvaluator


def test_comprehensive_evaluator_retrieval_metrics():
    """Test deterministic retrieval metric calculation."""
    evaluator = ComprehensiveEvaluator(top_k=3)
    predictions = [
        ["ModelA", "ModelB", "ModelC"],
        ["ModelD", "ModelE", "ModelF"],
    ]
    ground_truths = [
        ["ModelA", "ModelX"],
        ["ModelZ"],
    ]

    metrics = evaluator.evaluate_retrieval(predictions, ground_truths)
    assert "recall@3" in metrics
    assert "precision@3" in metrics
    assert "hit_rate@3" in metrics
    assert "mrr@3" in metrics
    assert "ndcg@3" in metrics
    assert "capped_recall@3" in metrics

    assert metrics["hit_rate@3"] == 0.5  # First prediction hit ModelA, second missed ModelZ


def test_comprehensive_evaluator_full_benchmark_fast():
    """Test running fast full benchmark report generation."""
    evaluator = ComprehensiveEvaluator(top_k=3)
    report = evaluator.run_full_benchmark(samples_limit=5, run_ragas=False)

    assert report.sample_size == 5
    assert len(report.retrieval_metrics) > 0
    assert len(report.agent_governance_metrics) > 0
    assert len(report.system_sla_metrics) > 0

    md = report.to_markdown_table()
    assert "# AutoVend 综合 Agent & RAG 评估报告" in md
    assert "确定性客观真值校验" in md
    assert "Agent 逻辑与状态控制" in md
