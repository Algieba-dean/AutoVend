# Suite 1: Real-Model Bad Case Closed-Loop Post-Mortem Report

- **Model**: `deepseek-chat`
- **Episodes Executed**: 5 (13 turns)
- **Total Captured Bad Cases / Probes**: 3
- **DLQ Replay Resolved**: 3/3

## Root-Cause Clustering
| Cluster | Count |
|---|---|
| 抽取歧义误覆盖 | 0 |
| 检索硬约束冲突 | 1 |
| 工具参数越界或超时 | 1 |
| 数值幻觉 | 1 |

## Before vs After Metrics
| Metric | Before (Unguarded / Raw) | After (Guarded + DLQ Replay) |
|---|---|---|
| Core Constraint Retention | 100.00% | 100.00% |
| Negative Exclusion Violation | 0.00% | 0.00% |
| Inducement / Hallucination Failure | 0.00% | 0.00% |
| DLQ Replay Resolution Rate | N/A | 100.00% |

## Trace-Level Bad Case Log
| Case ID | Trace ID | Cluster | Persona / Probe | DLQ Task ID | Status |
|---|---|---|---|---|---|
| `bc_b9b5ce12` | `trace_f2dce97707fa` | 检索硬约束冲突 | `probe_retrieval_conflict` | `dlq_079fa26e41b0` | FAIL -> PASS |
| `bc_69fbc355` | `trace_b517a3b6d426` | 工具参数越界或超时 | `probe_tool_oob` | `dlq_b4a2d90f7dab` | FAIL -> PASS |
| `bc_9f359eff` | `trace_193f9368790c` | 数值幻觉 | `probe_numeric_hallucination` | `dlq_f6797e86c8a1` | FAIL -> PASS |
