# AutoVend Agent — Performance Evaluation Framework

> Version: 1.0 | Date: 2026-03-27 | Evaluator: Automated Harness v1

## 1. Overview

This document defines the **performance KPI framework** for the AutoVend conversational sales agent, evaluated from the perspective of a RAG/Agent systems expert. Unlike code-level metrics (coverage, lint), these KPIs measure the agent's **business capability**, **response quality**, **robustness**, and **latency** through simulated multi-turn dialogues.

### 1.1 Evaluation Philosophy

| Principle | Description |
|---|---|
| **End-to-end** | Score the full conversation, not isolated components |
| **Multi-dimensional** | No single score — measure business, quality, robustness independently |
| **Scenario diversity** | Test normal, edge-case, adversarial, and bilingual inputs |
| **Reproducible** | All scenarios use deterministic mock LLMs; results are persisted as JSON |
| **Progressive** | Establish baseline, then track improvement across iterations |

---

## 2. Evaluation Dimensions & Metrics

### 2.1 Extraction Accuracy (Information Retrieval)

Measures the agent's ability to extract structured information from free-text conversation.

| Metric | Definition | Formula | Target |
|---|---|---|---|
| **Precision** | Fraction of extracted fields that are correct | `correct / extracted` | ≥ 0.90 |
| **Recall** | Fraction of expected fields that were extracted | `correct / expected` | ≥ 0.85 |
| **F1 Score** | Harmonic mean of precision and recall | `2·P·R / (P+R)` | ≥ 0.87 |

Applied to three extractors:
- **Profile Extraction**: name, age, residence, target_driver, family_size, etc.
- **Needs Extraction**: budget, brand, powertrain, vehicle type, design style, etc.
- **Reservation Extraction**: date, time, location, driver, phone

### 2.2 Stage Transition Correctness

Measures the FSM (Finite State Machine) accuracy of the conversation flow.

| Metric | Definition | Target |
|---|---|---|
| **Per-dialogue accuracy** | % of turns where actual stage matches expected | ≥ 80% (normal), ≥ 60% (edge) |
| **Aggregate accuracy** | Weighted average across all dialogues | ≥ 90% |
| **Invalid transition rate** | % of transitions violating FSM rules | 0% |

Stage order: `welcome → profile_analysis → needs_analysis → car_selection → reservation4s → reservation_confirmation → farewell`

### 2.3 Response Quality

| Metric | Definition | Scoring Method | Target |
|---|---|---|---|
| **Relevance** | Response addresses current stage and user context | Keyword overlap + stage-keyword matching (0-100) | ≥ 60 |
| **Language Consistency** | Agent responds in user's language (CN/EN) | Binary + mixed detection (0/50/100) | ≥ 80 |
| **Professionalism** | Polite, structured, no slang | Rule-based markers (0-100) | ≥ 70 |
| **Response Rate** | % of turns with non-empty responses | `non_empty / total` | 100% |
| **Completeness** | Response contains actionable next step | Question/invitation detection | ≥ 70 |

### 2.4 Business Capability

| Metric | Definition | Target |
|---|---|---|
| **Information Gathering Rate** | New fields extracted per turn | ≥ 1.5 fields/turn avg |
| **Conversion Funnel Score** | How far through the sales pipeline (0-100) | ≥ 57 (reaches car_selection) |
| **Task Completion Score** | Weighted completion of profile + needs + reservation + stage | ≥ 80 |

**Task Completion Weights:**
- Reached expected final stage: **30%**
- Profile completeness (5 key fields): **25%**
- Needs completeness (5 key fields): **25%**
- Reservation completeness (4 key fields): **20%**

### 2.5 Robustness

| Metric | Definition | Target |
|---|---|---|
| **Error Recovery** | Agent remains functional after invalid/empty input | 100% response rate |
| **Adversarial Resistance** | No prompt injection leakage, stays in character | Professionalism ≥ 70 |
| **Edge-case Stability** | Silent/minimal/correction users don't crash agent | 100% uptime |

### 2.6 Latency (Mock LLM)

| Metric | Definition | Target |
|---|---|---|
| **avg** | Mean processing time per turn | < 10ms |
| **p50** | Median processing time | < 5ms |
| **p95** | 95th percentile processing time | < 50ms |
| **p99** | 99th percentile processing time | < 100ms |

---

## 3. Overall Score Formula

The **Overall Score** (0-100) is a weighted composite:

```
Overall = 0.35 × Business + 0.30 × ResponseQuality + 0.20 × Extraction + 0.10 × StageAccuracy + 0.05 × Latency

Where:
  Business       = 0.5 × TaskCompletion + 0.5 × ConversionFunnel
  ResponseQuality = (Relevance + Professionalism + LanguageConsistency) / 3
  Extraction     = (ProfileF1 + NeedsF1) / 2 × 100
  StageAccuracy  = correct_stages / total_stages × 100
  Latency        = max(0, 100 - avg_ms / 50 × 100)
```

---

## 4. Test Scenarios

### 4.1 Scenario Distribution

| Category | Count | Description |
|---|---|---|
| **Normal** | 10 | Happy-path dialogues with diverse personas |
| **Edge Case** | 6 | Incomplete info, corrections, one-shot info dump, slow reveal |
| **Adversarial** | 4 | Off-topic, prompt injection, nonsense, mixed valid/invalid |
| **Bilingual** | 4 | Code-switching, CN→EN, EN→CN, mixed brands |
| **Total** | **24** dialogues, **77** turns |

### 4.2 Persona Coverage

| ID | Persona | Language | Category |
|---|---|---|---|
| N01 | 年轻程序员首次购车 | CN | Normal |
| N02 | 五口之家换7座SUV | CN | Normal |
| N03 | Luxury buyer | EN | Normal |
| N04 | 预算紧张的毕业生 | CN | Normal |
| N05 | 退休夫妇选舒适车 | CN | Normal |
| N06 | 新能源技术控 | CN | Normal |
| N07 | 二胎妈妈选家用MPV | CN | Normal |
| N08 | 企业老板选商务车 | CN | Normal |
| F01 | 完整购车流程(预约) | CN | Normal |
| F02 | Full English funnel | EN | Normal |
| E01 | 极少信息的沉默用户 | CN | Edge Case |
| E02 | 中途改变需求的用户 | CN | Edge Case |
| E03 | 一次说完所有信息 | CN | Edge Case |
| E04 | 纠正之前错误信息 | CN | Edge Case |
| E05 | 只关心预算 | CN | Edge Case |
| E06 | Gradual info reveal | EN | Edge Case |
| A01 | 完全跑题的用户 | CN | Adversarial |
| A02 | Prompt injection | EN | Adversarial |
| A03 | 乱码/无意义输入 | Mixed | Adversarial |
| A04 | 混合有效和无效信息 | CN | Adversarial |
| B01 | 中英混合的海归 | CN+EN | Bilingual |
| B02 | 从英文切换到中文 | EN→CN | Bilingual |
| B03 | 口语化中文+英文品牌名 | CN+EN | Bilingual |
| B04 | Formal English | EN | Bilingual |

---

## 5. Evaluation Results (Baseline — v3.0)

### 5.1 Aggregate Summary

| Metric | Score | Target | Status |
|---|---|---|---|
| **Overall Score** | **74.5** / 100 | ≥ 60 | ✅ |
| **Stage Accuracy** | **95.1%** | ≥ 90% | ✅ |
| **Response Relevance** | **47.7** / 100 | ≥ 60 | ⚠️ Below target |
| **Task Completion** | **84.0** / 100 | ≥ 80 | ✅ |
| **Conversion Funnel** | **51.2** / 100 | ≥ 57 | ⚠️ Below target |
| **Professionalism** | **74.4** / 100 | ≥ 70 | ✅ |
| **Language Consistency** | **46.5** / 100 | ≥ 80 | ❌ Below target |
| **Response Rate** | **100%** | 100% | ✅ |

### 5.2 By Category

| Category | Count | Overall | Stage Acc. | Task Completion |
|---|---|---|---|---|
| **Normal** | 10 | 77.1 | 100.0% | 95.0 |
| **Edge Case** | 6 | 71.7 | 80.3% | 79.2 |
| **Adversarial** | 4 | 68.7 | 100.0% | 53.8 |
| **Bilingual** | 4 | 77.9 | 100.0% | 93.8 |

### 5.3 Per-Dialogue Scorecards

| ID | Persona | Overall | Stage | Task | Prof. | Relevance |
|---|---|---|---|---|---|---|
| N01 | 年轻程序员首次购车 | 75.1 | 100% | 100.0 | 70.0 | 46.7 |
| N02 | 五口之家换7座SUV | 73.7 | 100% | 90.0 | 66.2 | 41.2 |
| N03 | Luxury buyer (EN) | 81.4 | 100% | 90.0 | 70.0 | 68.3 |
| N04 | 预算紧张的毕业生 | 74.9 | 100% | 85.0 | 70.0 | 46.7 |
| N05 | 退休夫妇选舒适车 | 76.6 | 100% | 95.0 | 70.0 | 46.7 |
| N06 | 新能源技术控 | 77.5 | 100% | 100.0 | 70.0 | 46.7 |
| N07 | 二胎妈妈选家用MPV | 76.6 | 100% | 95.0 | 70.0 | 46.7 |
| N08 | 企业老板选商务车 | 76.6 | 100% | 95.0 | 70.0 | 46.7 |
| F01 | 完整购车流程 | 75.5 | 100% | 100.0 | 66.2 | 41.2 |
| F02 | Full English funnel | 83.5 | 100% | 100.0 | 70.0 | 68.3 |
| E01 | 极少信息沉默用户 | 75.7 | 100% | 50.0 | 100.0 | 46.7 |
| E02 | 中途改变需求 | 74.6 | 100% | 95.0 | 66.2 | 46.2 |
| E03 | 一次说完所有信息 | 62.9 | 100% | 65.0 | 77.5 | 32.5 |
| E04 | 纠正之前错误信息 | 71.2 | 75% | 90.0 | 66.2 | 46.2 |
| E05 | 只关心预算 | 69.8 | 66.7% | 75.0 | 70.0 | 46.7 |
| E06 | Gradual info reveal | 76.0 | 40% | 100.0 | 64.0 | 58.0 |
| A01 | 完全跑题 | 75.7 | 100% | 50.0 | 100.0 | 46.7 |
| A02 | Prompt injection | 65.7 | 100% | 50.0 | 100.0 | 18.3 |
| A03 | 乱码/无意义 | 65.7 | 100% | 50.0 | 100.0 | 18.3 |
| A04 | 混合有效/无效 | 67.5 | 100% | 65.0 | 70.0 | 46.7 |
| B01 | 中英混合海归 | 76.6 | 100% | 95.0 | 70.0 | 46.7 |
| B02 | 英→中切换 | 77.9 | 100% | 90.0 | 70.0 | 55.0 |
| B03 | 口语化+英文品牌 | 76.6 | 100% | 95.0 | 70.0 | 46.7 |
| B04 | Formal English | 80.4 | 100% | 95.0 | 70.0 | 68.3 |

### 5.4 Latency (Mock LLM)

| Metric | Value | Target | Status |
|---|---|---|---|
| avg | 0.26 ms | < 10 ms | ✅ |
| p50 | 0.22 ms | < 5 ms | ✅ |
| p95 | 0.36 ms | < 50 ms | ✅ |
| p99 | 0.36 ms | < 100 ms | ✅ |

---

## 6. Gap Analysis & Optimization Roadmap

### 6.1 Critical Gaps Identified

| Gap | Current | Target | Root Cause | Priority |
|---|---|---|---|---|
| **Language Consistency** | 46.5 | ≥ 80 | Agent sometimes responds in CN when user speaks EN (response template selection) | P0 |
| **Response Relevance** | 47.7 | ≥ 60 | Stage prompts are generic; don't echo user-specific keywords | P0 |
| **Conversion Funnel** | 51.2 | ≥ 57 | Many dialogues stop at car_selection; reservation flow undertested | P1 |
| **Edge-case Stage Acc.** | 80.3% | ≥ 90% | Gradual info reveal (E06) gets only 40% — FSM advances too slowly | P1 |

### 6.2 Optimization Roadmap

#### Phase 1 — Language & Relevance (P0)

1. **Language-aware response routing**: Detect user language in `generate_response()` and select CN/EN prompt variant
2. **Context injection in prompts**: Include user's key terms in generation prompt (not just stage keywords)
3. **Echo-back pattern**: Agent should reference user's specific needs in response (e.g., "您提到想要纯电SUV...")

#### Phase 2 — Funnel & FSM (P1)

4. **Multi-field extraction per turn**: Allow profile+needs extraction in a single turn when user provides both
5. **Relaxed stage transition**: If user provides profile AND needs in one message, allow skipping profile_analysis
6. **Reservation flow testing**: Add more full-funnel scenarios with complete reservation

#### Phase 3 — Advanced Quality (P2)

7. **Response diversity**: Avoid identical responses across different personas
8. **Proactive questioning**: Agent should ask about unfilled high-value fields
9. **RAG integration scoring**: When real LLM is available, add faithfulness + answer_correctness metrics (RAGAS)

### 6.3 Target Metrics After Optimization

| Metric | Baseline (v3.0) | Target (v4.0) |
|---|---|---|
| Overall Score | 74.5 | ≥ 82 |
| Stage Accuracy | 95.1% | ≥ 97% |
| Response Relevance | 47.7 | ≥ 65 |
| Language Consistency | 46.5 | ≥ 85 |
| Task Completion | 84.0 | ≥ 90 |
| Conversion Funnel | 51.2 | ≥ 60 |

---

## 7. Evaluation Infrastructure

### 7.1 File Structure

```
tests/performance/
├── __init__.py
├── scoring.py          # Scoring engine (all metric implementations)
├── scenarios.py        # 24 dialogue scenarios (4 categories)
├── eval_harness.py     # Evaluation runner + report generator
└── test_performance.py # Pytest integration (70 test cases)

eval_results/
├── eval_latest.json    # Latest evaluation results
└── eval_YYYYMMDD_HHMMSS.json  # Timestamped snapshots
```

### 7.2 Running the Evaluation

```bash
# Run as pytest (70 tests, asserts KPI targets)
uv run python -m pytest tests/performance/ -v

# Run standalone (prints summary, saves JSON report)
uv run python -m tests.performance.eval_harness
```

### 7.3 Adding New Scenarios

Add entries to the appropriate list in `tests/performance/scenarios.py`:
- `NORMAL_SCENARIOS` — happy-path
- `EDGE_CASE_SCENARIOS` — boundary conditions
- `ADVERSARIAL_SCENARIOS` — attacks / nonsense
- `BILINGUAL_SCENARIOS` — language mixing

Each scenario requires:
```python
{
    "id": "N09",
    "persona": "Description",
    "category": "normal",
    "profile_resp": { ... },     # Mock LLM extraction response
    "needs_resp": { ... },
    "implicit_resp": { ... },
    "reservation_resp": { ... },
    "expected_profile": { ... }, # Ground-truth for F1 scoring
    "expected_needs": { ... },
    "expected_final_stage": "car_selection_confirmation",
    "turns": [
        {"msg": "User message", "expected_stage": Stage.PROFILE_ANALYSIS},
        ...
    ],
}
```

---

## 8. Professional Evaluation Standards Reference

This framework draws from established evaluation methodologies:

| Standard | Applied As |
|---|---|
| **RAGAS** (Retrieval-Augmented Generation Assessment) | Extraction Precision/Recall/F1, Response Relevance |
| **IR Metrics** (Information Retrieval) | Precision@K for extraction fields, Recall for coverage |
| **NLG Evaluation** | Professionalism scoring, language consistency check |
| **Dialogue Systems Evaluation** | Stage accuracy (slot-filling FSM), task completion rate |
| **BLEU/ROUGE principles** | Keyword overlap in response relevance scoring |
| **SLA Latency Targets** | p50/p95/p99 latency thresholds |
| **Sales Funnel Analytics** | Conversion funnel scoring (awareness → interest → decision) |

---

## Appendix: Glossary

| Term | Definition |
|---|---|
| **F1** | Harmonic mean of precision and recall |
| **Precision** | Of the fields the agent extracted, how many were correct |
| **Recall** | Of the fields that should have been extracted, how many were |
| **Stage Accuracy** | % of turns where the agent transitions to the correct FSM stage |
| **Conversion Funnel** | How far the conversation progresses through the 7-stage pipeline |
| **Task Completion** | Weighted sum of stage reached + profile/needs/reservation completeness |
| **Response Relevance** | How well the agent's reply addresses the current stage and user context |
| **Language Consistency** | Whether the agent responds in the same language as the user |
| **Professionalism** | Polite markers, structured output, no unprofessional content |
