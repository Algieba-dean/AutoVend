# Suite 3: Async Concurrency, Chaos/Idempotency & Cost/SLA Report

- **Model**: `deepseek-chat`
- **Redis DistributedSessionStore**: `True`

## Concurrency SLA (P50 / P95 / P99)
| Concurrency | Succeeded | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Avg TTFT (ms) | Cost/Turn (USD) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 10/10 | 8.06 | 855.9 | 1159.1 | 1221.5 | 443.7 | $0.000032 |
| 30 | 30/30 | 25.76 | 585.8 | 1037.7 | 1134.9 | 391.2 | $0.000032 |
| 50 | 50/50 | 52.77 | 733.0 | 915.2 | 944.8 | 403.9 | $0.000032 |

## Chaos & Fault Injection
- **Tool Timeout Recovery**: 4/4 gracefully degraded via CircuitBreaker
- **Idempotency Guard (`idempotency_key`)**: 1 unique execution, 9/10 replayed from cache
- **Same-Session Lock Contention (Redis SETNX)**: 1 succeeded, 7 rejected with 429 (`SessionLockTimeoutError`) out of 8 concurrent writers

## Cost vs Accuracy Tradeoff
| Profile | Cost/Turn (USD) | Avg Latency (ms) | Constraint Accuracy |
|---|---:|---:|---:|
| `fast_control_only` | $0.000091 | 854.0 | 0% |
| `autovend_hybrid_compacted` | $0.000136 | 1164.7 | 67% |
| `full_crag_and_llm_audit` | $0.000168 | 1849.6 | 67% |
