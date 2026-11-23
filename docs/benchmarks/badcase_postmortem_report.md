# Suite 1: Real-Model Bad Case Closed-Loop Post-Mortem Report

- **Model**: `deepseek-chat`
- **Episodes Executed**: 5 (12 turns)
- **Total Captured Bad Cases / Probes**: 4
- **DLQ Replay Resolved**: 4/4

## Root-Cause Clustering
| Cluster | Count |
|---|---|
| 抽取歧义误覆盖 | 1 |
| 检索硬约束冲突 | 1 |
| 工具参数越界或超时 | 1 |
| 数值幻觉 | 1 |

## Before vs After Metrics
| Metric | Before (Unguarded / Raw) | After (Guarded + DLQ Replay) |
|---|---|---|
| Core Constraint Retention | 100.00% | 100.00% |
| Negative Exclusion Violation | 0.00% | 0.00% |
| Inducement / Hallucination Failure | 0.00% | 0.00% |
| Adversarial Probe Failure Rate (4 Clusters) | 100.00% | 0.00% |
| DLQ Replay Resolution Rate | N/A | 100.00% |

## Trace-Level Bad Case Log
| Case ID | Trace ID | Cluster | Persona / Probe | DLQ Task ID | Status |
|---|---|---|---|---|---|
| `bc_74239b17` | `trace_32c6a8fe30f8` | 抽取歧义误覆盖 | `probe_extraction_ambiguity` | `dlq_c20e2ccdb3d3` | FAIL -> PASS |
| `bc_be369396` | `trace_0a2a59e48182` | 检索硬约束冲突 | `probe_retrieval_conflict` | `dlq_209cf612fb0f` | FAIL -> PASS |
| `bc_feb32f71` | `trace_d2c2e117472c` | 工具参数越界或超时 | `probe_tool_oob` | `dlq_1cc2a3ec9227` | FAIL -> PASS |
| `bc_4d88a3b8` | `trace_f32e63273508` | 数值幻觉 | `probe_numeric_hallucination` | `dlq_1b3c13eddea4` | FAIL -> PASS |
