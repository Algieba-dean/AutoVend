"""
Unit tests for Online RAG Evaluation & Query Drift Alerting Engine (src/rag_service/eval_monitor.py).
"""

from src.rag_service.eval_monitor import RAGEvalMonitor


def test_zero_result_alert_trigger():
    """Test critical alert when search returns zero candidates."""
    monitor = RAGEvalMonitor()
    alerts = monitor.record_retrieval(
        query_text="不存在的奇葩车型_999",
        results=[],
        candidate_count=0,
        latency_ms=25.0,
    )

    assert len(alerts) >= 1
    zero_alerts = [a for a in alerts if a.alert_type == "ZERO_RESULT_SPIKE"]
    assert len(zero_alerts) == 1
    assert zero_alerts[0].severity == "CRITICAL"


def test_latency_spike_alert_trigger():
    """Test warning alert when search latency exceeds threshold."""
    monitor = RAGEvalMonitor(max_latency_ms_threshold=500.0)
    alerts = monitor.record_retrieval(
        query_text="中型纯电SUV",
        results=[{"score": 0.85}],
        candidate_count=10,
        latency_ms=1200.0,
    )

    assert len(alerts) >= 1
    lat_alerts = [a for a in alerts if a.alert_type == "LATENCY_DRIFT"]
    assert len(lat_alerts) == 1
    assert lat_alerts[0].severity == "WARNING"


def test_out_of_domain_drift_rolling_alert():
    """Test rolling window Out-of-Domain query drift detection."""
    monitor = RAGEvalMonitor(window_size=20, ood_alert_ratio_threshold=0.15)

    # Record 10 automotive queries
    for _ in range(10):
        monitor.record_retrieval("想买一辆混动SUV", [{"score": 0.8}], 10, 100.0)

    # Record 5 out-of-domain queries (e.g. food/weather/code)
    alerts = []
    for _ in range(5):
        alerts = monitor.record_retrieval("请问附近哪里的火锅好吃", [{"score": 0.2}], 2, 120.0)

    ood_alerts = [a for a in alerts if a.alert_type == "OUT_OF_DOMAIN_DRIFT"]
    assert len(ood_alerts) == 1
    assert "语义漂移" in ood_alerts[0].message

    summary = monitor.get_summary_statistics()
    assert summary["window_sample_count"] == 15
    assert summary["ood_query_rate"] > 0.0
