# AutoVend v2 Architecture — Agent / Backend Decoupling

## Version History

| Version | Date | Description | Tests | Coverage |
|---|---|---|---|---|
| v1.0 | 2026-03-26 | Monolithic RAG backend | 152 unit + 20 e2e | 86.44% |
| v2.0 | 2026-03-27 | Agent/Backend decoupled | TBD | Target ≥ 90% |

## Problem (v1)

In v1, `StageWorkflow` is a God Object mixing:
- Agent logic (LLM extraction, stage FSM, response generation, memory)
- Backend logic (session CRUD, API response formatting, RAG index access)

This makes the Agent untestable without HTTP infrastructure and prevents
reuse of the Agent in other contexts (CLI, batch processing, different backends).

## Target Architecture (v2)

```
┌──────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend (app/)                     │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐         │
│  │  /chat    │  │  /profile    │  │  /test-drive       │         │
│  │  routes   │  │  routes      │  │  routes            │         │
│  └─────┬─────┘  └──────┬───────┘  └─────────┬──────────┘         │
│        │               │                     │                    │
│        │         ┌─────▼──────────────┐      │                    │
│        │         │  FileStorage       │      │                    │
│        │         │  (profiles, drives) │      │                    │
│        │         └────────────────────┘      │                    │
│  ┌─────▼────────────────────────────────────▼───────────────┐    │
│  │              Backend Service Layer                        │    │
│  │  - Owns session lifecycle (create/get/end)                │    │
│  │  - Delegates AI processing to Agent                       │    │
│  │  - Builds ChatResponse from AgentResult                   │    │
│  │  - Calls RAG retriever and passes results to Agent        │    │
│  └────────────────────────┬──────────────────────────────────┘    │
│                           │                                       │
│  ┌────────────────────────▼──────────────────────────────────┐   │
│  │              RAG Layer (app/rag/)                          │   │
│  │  - vehicle_index.py (ChromaDB loader)                     │   │
│  │  - query_engine.py (semantic + metadata retrieval)        │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                            │
                    Protocol: AgentResult
                            │
┌──────────────────────────▼───────────────────────────────────────┐
│                     Agent Package (agent/)                        │
│                                                                   │
│  ┌────────────────┐                                               │
│  │  SalesAgent     │ ← Single entry point                        │
│  │  .process()     │   Input: AgentInput (message, state, cars)  │
│  │                 │   Output: AgentResult (response, new state)  │
│  └───────┬─────────┘                                              │
│          │                                                        │
│  ┌───────▼─────────────────────────────────────────────────────┐ │
│  │  Extractors                                                  │ │
│  │  base.py → profile / needs / implicit / reservation          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Stage Engine                                                │ │
│  │  stages.py (FSM transitions + advancement heuristics)        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Response Generator                                          │ │
│  │  response_generator.py (per-stage prompt templates)          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Memory                                                      │ │
│  │  chat_memory.py (per-session ChatMemoryBuffer)               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Schemas (agent/schemas.py)                                  │ │
│  │  AgentInput, AgentResult, SessionState                       │ │
│  │  + domain models: Stage, UserProfile, VehicleNeeds, etc.     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Key Design Principles

1. **Agent is a pure function**: `AgentResult = SalesAgent.process(AgentInput)`
   - No HTTP, no storage, no vector DB inside Agent
   - Depends only on: LLM interface, schemas
   - Vehicle retrieval results are passed IN, not fetched internally

2. **Backend is thin orchestrator**:
   - Owns HTTP, storage, RAG index
   - Passes retrieval results to Agent
   - Converts AgentResult to API response

3. **Clean protocol boundary**:
   - `AgentInput`: session state + user message + retrieved vehicles
   - `AgentResult`: updated state + response text + stage transition

## Module Ownership

| Module | Owner | Dependencies |
|---|---|---|
| `agent/schemas.py` | Agent | pydantic only |
| `agent/extractors/` | Agent | LLM interface + schemas |
| `agent/stages.py` | Agent | schemas only |
| `agent/response_generator.py` | Agent | LLM interface + schemas |
| `agent/memory.py` | Agent | llama_index.core.memory |
| `agent/sales_agent.py` | Agent | all above |
| `app/routes/` | Backend | FastAPI + agent protocol |
| `app/models/storage.py` | Backend | filesystem + schemas |
| `app/rag/` | Backend | ChromaDB + LlamaIndex |
| `app/main.py` | Backend | wires Agent + RAG + routes |

## KPIs

### RAG System KPIs

| KPI | Target | Measurement |
|---|---|---|
| Index build time | < 60s for full dataset | `time python -m scripts.build_index` |
| Retrieval latency (p50) | < 200ms | pytest benchmark |
| Retrieval recall@5 | ≥ 80% | manual eval on 20 test queries |
| Metadata filter accuracy | 100% | unit tests with known data |
| Index persistence | Survives restart | integration test |
| Embedding dimension | 1024 (bge-m3) | assert in test |

### Agent System KPIs

| KPI | Target | Measurement |
|---|---|---|
| Extraction accuracy (profile) | ≥ 90% F1 | eval on 20 annotated dialogues |
| Extraction accuracy (needs) | ≥ 85% F1 | eval on 20 annotated dialogues |
| Stage transition correctness | 100% on happy path | unit tests |
| Stage transition correctness | ≥ 95% on edge cases | unit tests |
| Response relevance | ≥ 4.0/5.0 | manual eval |
| Agent unit test coverage | ≥ 95% | pytest-cov |
| Agent has zero backend imports | 100% | import lint check |
| Process latency (no LLM) | < 10ms | mock LLM unit test |

### Backend System KPIs

| KPI | Target | Measurement |
|---|---|---|
| API response time (p95) | < 5s | load test |
| API error rate | < 1% | monitoring |
| Unit test coverage | ≥ 85% | pytest-cov |
| E2E test pass rate | 100% | Playwright |
| Storage CRUD correctness | 100% | unit tests |
| Concurrent sessions | ≥ 50 | load test |

### Code Quality KPIs

| KPI | Target | Measurement |
|---|---|---|
| Ruff lint warnings | 0 | `ruff check` |
| Type annotation coverage | 100% public APIs | manual review |
| Circular imports | 0 | import test |
| Agent ↔ Backend coupling | 0 direct imports | automated check |
| Documentation | All public modules have docstrings | ruff D rules |

## Migration Plan

1. Create `agent/` package with schemas, extractors, stages, memory, response generator
2. Create `AgentInput`/`AgentResult` protocol types
3. Create `SalesAgent` class with single `.process()` method
4. Write agent unit tests (TDD — tests first, then move code)
5. Refactor backend: `StageWorkflow` → thin `ChatService` that delegates to `SalesAgent`
6. Write import isolation test (agent must not import from app)
7. Run full test suite + coverage
8. Update docs with v2 metrics
