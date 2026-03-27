# AutoVend KPI Testing Guide

## Overview

This document describes the KPI (Key Performance Indicator) testing framework for the AutoVend RAG Backend. The framework measures extraction accuracy, stage transition correctness, response quality, agent latency, and architectural integrity through automated tests and a CI-generated report.

## KPI Targets

| Category | Metric | Target | Test File |
|----------|--------|--------|-----------|
| **Extraction** | Profile extraction F1 | ≥ 0.90 | `test_kpi_extraction.py` |
| **Extraction** | Needs extraction F1 | ≥ 0.85 | `test_kpi_extraction.py` |
| **Extraction** | Reservation extraction F1 | ≥ 0.90 | `test_kpi_extraction.py` |
| **Extraction** | Implicit deduction recall | ≥ 0.80 | `test_kpi_extraction.py` |
| **Stage** | Happy-path transition accuracy | 100% | `test_kpi_stages.py` |
| **Stage** | Edge-case transition accuracy | ≥ 95% | `test_kpi_stages.py` |
| **Dialogue** | Multi-turn stage progression | ≥ 95% | `test_kpi_e2e_dialogues.py` |
| **Dialogue** | Response generation rate | 100% | `test_kpi_e2e_dialogues.py` |
| **Latency** | Agent avg latency (mock LLM) | < 10ms | `test_kpi_e2e_dialogues.py` |
| **Latency** | Agent p95 latency (mock LLM) | < 50ms | `test_kpi_e2e_dialogues.py` |
| **Architecture** | Agent → Backend imports | 0 | `test_agent_isolation.py` |
| **Architecture** | Circular imports | 0 | `test_agent_isolation.py` |
| **Coverage** | Total test coverage | ≥ 85% | `pytest --cov` |

## Test Structure

### 1. Extraction Accuracy (`test_kpi_extraction.py`)

Tests extraction accuracy using **AI-generated annotated dialogue samples**. Each sample contains:
- A realistic conversation snippet with a specific user persona
- A mock LLM response simulating what the LLM would extract
- Ground-truth expected values for comparison

**Scoring Method:** For each extractor, we compute:
- **Precision** = correct / extracted (how many extracted fields are correct)
- **Recall** = correct / expected (how many expected fields were extracted)
- **F1** = 2 × P × R / (P + R)

**Personas tested:**

| ID | Persona | Language | Key traits |
|----|---------|----------|------------|
| P01 | Young tech worker | Chinese | Age 26, beginner, single |
| P02 | Family father | Chinese | Age 38, 5-person family, budget-conscious |
| P03 | Retired couple | Chinese | Age 62, buying for spouse |
| P04 | Car enthusiast | English | Age 33, expert, family of 3 |
| P05 | College graduate | Chinese | Age 24, very budget-conscious |
| N01 | EV lover | Chinese | Pure EV SUV, 20-30万 |
| N02 | Family SUV buyer | Chinese | 7-seat AWD, L2 autonomy |
| N03 | Performance seeker | English | 0-100 < 4s, BMW/Porsche |
| N04 | Economy commuter | Chinese | Under 10万, low fuel |
| N05 | Luxury buyer | Chinese | No budget limit, max safety |
| R01-R03 | Various reservation styles | Chinese | Quick/detailed/partial info |
| I01-I03 | Implicit deduction | Mixed | Family, beginner, luxury |

### 2. Stage Transition Correctness (`test_kpi_stages.py`)

Tests the deterministic stage state machine with:
- **6 happy-path steps**: Complete journey from Welcome → Farewell
- **10 edge-case steps**: Boundary conditions, incomplete data, terminal state

Each test verifies that `determine_next_stage()` returns the correct next stage given specific profile/needs/cars/reservation data.

### 3. Multi-Turn Dialogue Scoring (`test_kpi_e2e_dialogues.py`)

Runs **5 complete dialogue scenarios** through the full `SalesAgent.process()` pipeline:

| ID | Persona | Turns | Journey |
|----|---------|-------|---------|
| D01 | Young EV buyer | 5 | Welcome → Profile → Needs → CarSelection |
| D02 | Family SUV upgrader | 4 | Welcome → Profile → Needs → CarSelection |
| D03 | Luxury performance | 3 | Welcome → Profile → Needs → CarSelection |
| D04 | Budget graduate | 3 | Welcome → Profile → Needs → CarSelection |
| D05 | Retired comfort seeker | 3 | Welcome → Profile → Needs → CarSelection |

**Scoring per dialogue:**
- Stage progression accuracy (expected vs actual stage after each turn)
- Response generation rate (non-empty response for every turn)
- Process latency (wall-clock time per turn with mock LLM)
- Profile completeness (% of profile fields filled after profile stage)
- Needs completeness (% of key needs fields filled after needs stage)

### 4. Agent Isolation (`test_agent_isolation.py`)

Uses Python AST analysis to verify:
- **Zero `app.*` imports** in any file under `agent/`
- **Only allowed packages**: `agent`, `pydantic`, `llama_index`, `typing`, stdlib

### 5. KPI Report Generator (`tests/kpi_report.py`)

Standalone script that:
1. Runs extraction accuracy benchmarks
2. Runs stage transition checks
3. Benchmarks agent latency (50 iterations)
4. Checks architecture isolation via AST
5. Outputs a Markdown report to stdout

Run locally:
```bash
uv run python tests/kpi_report.py
```

## Running KPI Tests

```bash
# Run all KPI tests
uv run pytest tests/test_kpi_extraction.py tests/test_kpi_stages.py tests/test_kpi_e2e_dialogues.py -v

# Run with coverage
uv run pytest tests/ --cov=agent --cov=app --cov-report=term-missing

# Generate KPI report
uv run python tests/kpi_report.py > kpi-report.md

# Run architecture guard only
uv run pytest tests/test_agent_isolation.py -v
```

## CI Integration

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and PR:

| Job | Purpose |
|-----|---------|
| **lint** | Ruff check + format verification |
| **test** | Full test suite + coverage report (artifact) |
| **kpi-report** | Generate and upload KPI Markdown report (artifact) |
| **arch-guard** | Agent isolation check + circular import detection |

Artifacts are retained for 30–90 days and can be downloaded from the Actions tab.

## Adding New Test Scenarios

### Adding a new extraction scenario:

1. Add a dict to the appropriate `*_SCENARIOS` list in `test_kpi_extraction.py`
2. Include: `id`, `persona`, `conversation`, `llm_response`, `expected`
3. The `llm_response` simulates what the LLM would return
4. The `expected` dict is the ground truth for scoring

### Adding a new dialogue scenario:

1. Add a dict to `DIALOGUE_SCENARIOS` in `test_kpi_e2e_dialogues.py`
2. Include: `id`, `persona`, `profile_resp`, `needs_resp`, `implicit_resp`, `reservation_resp`, `turns`
3. Each turn has: `msg` (user message) and `expected_stage` (Stage after processing)

### Adding edge-case stage tests:

1. Add a dict to `EDGE_CASE_STEPS` in `test_kpi_stages.py`
2. Include: `id`, `description`, `current`, `profile`, `needs`, `cars`, `reservation`, `expected`
