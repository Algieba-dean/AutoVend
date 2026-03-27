# AutoVend Backend — KPI Metrics

> Last updated: 2026-03-27 (v3.0 — monorepo consolidation)

## Version History

| Version | Date | Tests | Coverage | Key Change |
|---|---|---|---|---|
| v1.0 | 2026-03-26 | 152 | 86.44% | Monolithic RAG backend |
| v2.0 | 2026-03-27 | 297 | 88.46% | Agent/Backend decoupled |
| v3.0 | 2026-03-27 | 301 | 88.31% | Monorepo consolidation + UX improvements |

## Test Coverage

| Metric | v1.0 | v2.0 | v3.0 (current) |
|---|---|---|---|
| **Total tests** | 152 | 297 | 301 |
| **Line coverage** | 86.44% | 88.46% | 88.31% |
| **Coverage threshold** | 85% | 85% | 85% (enforced) |

### Per-Module Coverage (v3.0)

| Module | Stmts | Miss | Cover | Δ from v1 |
|---|---|---|---|---|
| `agent/extractors/base.py` | 27 | 0 | 100% | — |
| `agent/extractors/*.py` (4 modules) | 40 | 0 | 100% | — |
| `agent/memory.py` | 41 | 0 | 100% | — |
| `agent/response_generator.py` | 38 | 0 | 100% | — |
| `agent/sales_agent.py` | 47 | 1 | 98% | — |
| `agent/schemas.py` | 89 | 0 | 100% | — |
| `agent/stages.py` | 44 | 0 | 100% | ↑ from 68% |
| `app/config.py` | 24 | 0 | 100% | — |
| `app/ingestion/toml_parser.py` | 65 | 0 | 100% | — |
| `app/models/schemas.py` | 43 | 0 | 100% | — |
| `app/models/storage.py` | 79 | 6 | 92% | ↑ from 71% |
| `app/rag/query_engine.py` | 35 | 0 | 100% | — |
| `app/routes/profile.py` | 45 | 2 | 96% | — |
| `app/routes/test_drive.py` | 43 | 4 | 91% | — |
| `app/routes/chat.py` | 90 | 28 | 69% | ↓ (file grew with RAG logic) |
| `app/main.py` | 72 | 21 | 71% | ↑ (file grew, new features covered) |
| `app/rag/vehicle_index.py` | 26 | 5 | 81% | — |
| `app/ingestion/index_builder.py` | 51 | 12 | 76% | — |
| `app/workflow/stage_workflow.py` | 109 | 39 | 64% | — |

## Extraction Accuracy (KPI Report)

| Extractor | Precision | Recall | F1 | Target | Status |
|---|---|---|---|---|---|
| Profile | 1.00 | 1.00 | 1.00 | ≥ 0.90 | ✅ |
| Needs | 1.00 | 1.00 | 1.00 | ≥ 0.85 | ✅ |
| Reservation | 1.00 | 1.00 | 1.00 | ≥ 0.90 | ✅ |

## Stage Transition Correctness

| Metric | Value | Target | Status |
|---|---|---|---|
| Happy-path accuracy | 100% (6/6) | 100% | ✅ |
| Edge-case accuracy | 100% (10/10) | ≥ 95% | ✅ |

## Agent Process Latency (Mock LLM)

| Metric | Value | Target | Status |
|---|---|---|---|
| Avg latency | 1.45ms | < 10ms | ✅ |
| p95 latency | 0.26ms | < 50ms | ✅ |

## Architecture Quality

| Metric | Value | Target | Status |
|---|---|---|---|
| Agent → Backend imports | 0 | 0 | ✅ |
| Circular imports | 0 | 0 | ✅ |

## Code Quality

| Metric | Value |
|---|---|
| **Linter** | Ruff (E, F, W, I rules) |
| **Lint warnings** | 0 |
| **Type annotations** | All public APIs typed |
| **Pydantic models** | 15 schema classes |
| **DRY score** | Extractors share base module (4→1 pattern) |

## Architecture Metrics

| Metric | Value |
|---|---|
| **Modules** | 22 Python modules |
| **API endpoints** | 15 REST endpoints |
| **Conversation stages** | 7 stages with FSM transitions |
| **Extractors** | 4 (profile, explicit needs, implicit needs, reservation) |
| **Prompt templates** | 7 stage-specific + 4 extraction prompts |
| **Middleware** | RequestID (traceability), CORS |

## API Endpoints

| Group | Endpoints |
|---|---|
| **Chat** | `POST /session`, `POST /message`, `GET /session/{id}/messages`, `PUT /session/{id}/end` |
| **Profile** | `GET /default`, `GET /{phone}`, `POST`, `PUT /{phone}`, `DELETE /{phone}`, `GET` (list) |
| **Test Drive** | `POST`, `GET /{phone}`, `PUT /{phone}`, `DELETE /{phone}`, `GET` (list) |
| **System** | `GET /`, `GET /health` (with component status) |

## Performance Characteristics

| Operation | Notes |
|---|---|
| **Startup** | ~10s (loads bge-m3 embedding model) |
| **Chat message round-trip** | ~2-5s (depends on LLM latency) |
| **Vehicle retrieval** | <100ms (local ChromaDB) |
| **Index build** | ~30s for full vehicle dataset |

## Deployment

| Item | Value |
|---|---|
| **Package manager** | uv |
| **Python version** | 3.12 |
| **Dependencies** | 10 direct (see pyproject.toml) |
| **Dev dependencies** | 5 (pytest, httpx, ruff, etc.) |
| **Config** | `.env` file (gitignored) |
