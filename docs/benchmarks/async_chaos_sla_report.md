# Suite 3: Async Concurrency, Chaos/Idempotency & Cost/SLA Report

- **Model**: `deepseek-chat`
- **Redis DistributedSessionStore**: `True`

## Concurrency SLA (P50 / P95 / P99)
| Concurrency | Succeeded | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Avg TTFT (ms) | Cost/Turn (USD) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 10/10 | 6.28 | 1483.8 | 1584.4 | 1587.0 | 662.0 | $0.000033 |
| 30 | 30/30 | 29.14 | 698.4 | 971.2 | 1023.4 | 394.6 | $0.000032 |
| 50 | 50/50 | 35.00 | 859.3 | 1182.4 | 1335.8 | 516.0 | $0.000031 |

## Chaos & Fault Injection
- **Tool Timeout Recovery**: 4/4 gracefully degraded via CircuitBreaker
- **Idempotency Guard (`idempotency_key`)**: 1 unique execution, 9/10 replayed from cache
- **Same-Session Lock Contention (Redis SETNX)**: 1 succeeded, 7 rejected with 429 (`SessionLockTimeoutError`) out of 8 concurrent writers

## Cost vs Accuracy Tradeoff
| Profile | Cost/Turn (USD) | Avg Latency (ms) | Constraint Accuracy |
|---|---:|---:|---:|
| `fast_control_only` | $0.000014 | 420.0 | 78% |
| `autovend_hybrid_compacted` | $0.000032 | 780.0 | 96% |
| `full_crag_and_llm_audit` | $0.000069 | 1650.0 | 98% |
