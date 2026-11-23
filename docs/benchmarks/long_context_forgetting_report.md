# Suite 2: Long-Conversation (10 / 20 / 30 / 50 Turns) Token Bloat & Forgetting Report

- **Model**: `deepseek-chat`

## Comparative Benchmark Results
| Turns | Strategy | Prompt Tokens | Cached Tokens | KV Prefix Hit | TTFT (ms) | Constraint Retention |
|---:|---|---:|---:|---:|---:|---:|
| 10 | `full_history` | 1315 | 0 | 0.0% | 315.9 | 4/4 (100%) |
| 10 | `sliding_window_20` | 917 | 0 | 0.0% | 260.6 | 0/4 (0%) |
| 10 | `autovend_compact` | 1289 | 0 | 11.8% | 526.0 | 4/4 (100%) |
| 20 | `full_history` | 2506 | 0 | 0.0% | 801.0 | 4/4 (100%) |
| 20 | `sliding_window_20` | 939 | 0 | 0.0% | 252.7 | 0/4 (0%) |
| 20 | `autovend_compact` | 1256 | 0 | 12.1% | 448.3 | 4/4 (100%) |
| 30 | `full_history` | 3936 | 0 | 0.0% | 575.8 | 4/4 (100%) |
| 30 | `sliding_window_20` | 1126 | 0 | 0.0% | 447.4 | 0/4 (0%) |
| 30 | `autovend_compact` | 1256 | 0 | 12.1% | 313.8 | 4/4 (100%) |
| 50 | `full_history` | 6318 | 0 | 0.0% | 250.8 | 4/4 (100%) |
| 50 | `sliding_window_20` | 939 | 0 | 0.0% | 285.8 | 0/4 (0%) |
| 50 | `autovend_compact` | 1256 | 0 | 12.1% | 448.6 | 4/4 (100%) |
