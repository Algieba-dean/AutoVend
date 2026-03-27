# AutoVend RAG Backend — KPI Metrics

## Test Coverage

| Metric | Value |
|---|---|
| **Total unit tests** | 152 |
| **Line coverage** | 86.44% |
| **Coverage threshold** | 85% (enforced) |
| **Playwright e2e tests** | 20 |

### Per-Module Coverage

| Module | Stmts | Miss | Cover |
|---|---|---|---|
| `extractors/base.py` | 27 | 0 | 100% |
| `extractors/profile_extractor.py` | 10 | 0 | 100% |
| `extractors/needs_extractor.py` | 10 | 0 | 100% |
| `extractors/implicit_deductor.py` | 10 | 0 | 100% |
| `extractors/reservation_extractor.py` | 10 | 0 | 100% |
| `ingestion/toml_parser.py` | 65 | 0 | 100% |
| `models/schemas.py` | 113 | 0 | 100% |
| `memory/chat_memory.py` | 41 | 0 | 100% |
| `rag/query_engine.py` | 35 | 0 | 100% |
| `workflow/response_generator.py` | 38 | 0 | 100% |
| `config.py` | 24 | 0 | 100% |
| `routes/chat.py` | 44 | 2 | 95% |
| `routes/profile.py` | 45 | 2 | 96% |
| `routes/test_drive.py` | 43 | 4 | 91% |
| `ingestion/index_builder.py` | 51 | 12 | 76% |
| `rag/vehicle_index.py` | 26 | 5 | 81% |
| `models/storage.py` | 79 | 23 | 71% |
| `workflow/stage_workflow.py` | 109 | 39 | 64% |
| `workflow/stages.py` | 47 | 15 | 68% |
| `main.py` | 42 | 16 | 62% |

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
| **Modules** | 20 Python modules |
| **API endpoints** | 15 REST endpoints |
| **Conversation stages** | 7 stages with FSM transitions |
| **Extractors** | 4 (profile, explicit needs, implicit needs, reservation) |
| **Prompt templates** | 7 stage-specific + 4 extraction prompts |

## API Endpoints

| Group | Endpoints |
|---|---|
| **Chat** | `POST /session`, `POST /message`, `GET /session/{id}/messages`, `PUT /session/{id}/end` |
| **Profile** | `GET /default`, `GET /{phone}`, `POST`, `PUT /{phone}`, `DELETE /{phone}`, `GET` (list) |
| **Test Drive** | `POST`, `GET /{phone}`, `PUT /{phone}`, `DELETE /{phone}`, `GET` (list) |
| **System** | `GET /`, `GET /health` |

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
