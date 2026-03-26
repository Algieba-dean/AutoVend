# AutoVend RAG Backend — Architecture

## Overview

The AutoVend RAG Backend is a LlamaIndex-based intelligent automotive sales assistant. It uses a Retrieval-Augmented Generation (RAG) pipeline to combine structured vehicle knowledge with LLM-powered conversation to guide users through a multi-stage car purchase journey.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  /chat    │  │  /profile    │  │  /test-drive       │    │
│  │  routes   │  │  routes      │  │  routes            │    │
│  └─────┬─────┘  └──────┬───────┘  └─────────┬──────────┘    │
│        │               │                     │               │
│  ┌─────▼───────────────▼─────────────────────▼──────────┐   │
│  │              StageWorkflow Engine                      │   │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────────┐  │   │
│  │  │  Extractors │ │  Stages    │ │ ResponseGenerator│  │   │
│  │  │  (profile,  │ │  (FSM      │ │ (per-stage       │  │   │
│  │  │   needs,    │ │  transitions│ │  prompt          │  │   │
│  │  │   reserv.)  │ │  logic)    │ │  templates)      │  │   │
│  │  └──────┬──────┘ └────────────┘ └────────┬─────────┘  │   │
│  │         │                                │            │   │
│  │  ┌──────▼────────────────────────────────▼─────────┐  │   │
│  │  │            LLM (DeepSeek via OpenAI-like)        │  │   │
│  │  └─────────────────────────────────────────────────┘  │   │
│  │                                                        │   │
│  │  ┌──────────────────┐  ┌────────────────────────────┐ │   │
│  │  │  ChatMemoryBuffer │  │  RAG Query Engine          │ │   │
│  │  │  (per-session)    │  │  (semantic + metadata)     │ │   │
│  │  └──────────────────┘  └────────────┬───────────────┘ │   │
│  └─────────────────────────────────────┼─────────────────┘   │
│                                        │                     │
│  ┌─────────────────────────────────────▼─────────────────┐   │
│  │              ChromaDB Vector Store                     │   │
│  │              (bge-m3 embeddings, persistent)           │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              File Storage (JSON)                       │   │
│  │   profiles/  │  sessions/  │  test_drives/            │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Module Breakdown

### 1. Ingestion Layer (`app/ingestion/`)

| Module | Responsibility |
|---|---|
| `toml_parser.py` | Parses TOML vehicle data files into LlamaIndex `Document` objects with structured metadata |
| `index_builder.py` | Builds and persists ChromaDB vector index using bge-m3 embeddings |

### 2. RAG Layer (`app/rag/`)

| Module | Responsibility |
|---|---|
| `vehicle_index.py` | Singleton accessor for the persistent vehicle VectorStoreIndex |
| `query_engine.py` | Hybrid retrieval combining semantic similarity with metadata filters |

### 3. Extractors (`app/extractors/`)

| Module | Responsibility |
|---|---|
| `base.py` | Shared utilities: `parse_llm_json`, `merge_model`, `extract_with_llm` |
| `profile_extractor.py` | Extracts user profile fields from conversation |
| `needs_extractor.py` | Extracts explicit vehicle needs from conversation |
| `implicit_deductor.py` | Deduces implicit needs from profile + explicit needs |
| `reservation_extractor.py` | Extracts test-drive reservation details |

### 4. Workflow Layer (`app/workflow/`)

| Module | Responsibility |
|---|---|
| `stages.py` | Stage enum, transition rules, advancement heuristics |
| `response_generator.py` | Per-stage prompt templates and response generation |
| `stage_workflow.py` | Core orchestrator: extraction → transition → retrieval → response |

### 5. Memory (`app/memory/`)

| Module | Responsibility |
|---|---|
| `chat_memory.py` | Per-session `ChatMemoryBuffer` with token-limited history |

### 6. Models (`app/models/`)

| Module | Responsibility |
|---|---|
| `schemas.py` | Pydantic models for all API request/response types |
| `storage.py` | File-based JSON persistence for profiles, sessions, test drives |

### 7. Routes (`app/routes/`)

| Module | Responsibility |
|---|---|
| `chat.py` | Session CRUD, message processing endpoint |
| `profile.py` | User profile CRUD |
| `test_drive.py` | Test drive reservation CRUD |

## Conversation Stage Flow

```
WELCOME → PROFILE_ANALYSIS → NEEDS_ANALYSIS → CAR_SELECTION
                                                    ↓ ↑
                                          RESERVATION_4S
                                                    ↓ ↑
                                    RESERVATION_CONFIRMATION → FAREWELL
```

Each stage has:
- **Extraction focus**: which extractors run (profile, needs, reservation)
- **Advancement heuristic**: rule-based check for enough collected info
- **Response template**: tailored prompt with injected context

## Key Design Decisions

1. **Shared extractor base**: All 4 extractors share `parse_llm_json` + `merge_model` to eliminate duplication.
2. **Graceful degradation**: If vehicle index isn't built, the server starts normally with retrieval disabled.
3. **Stateless API**: Session state lives in-memory (workflow engine) with file-based persistence for profiles/reservations.
4. **OpenAI-compatible LLM**: Uses `llama_index.llms.openai_like.OpenAILike` so any OpenAI-compatible endpoint (DeepSeek, local vLLM, etc.) works.
5. **uv for dependency management**: Reproducible environments with `pyproject.toml` + `uv.lock`.

## Tech Stack

| Component | Technology |
|---|---|
| Web Framework | FastAPI + Uvicorn |
| RAG Framework | LlamaIndex Core |
| Embedding | BAAI/bge-m3 (HuggingFace) |
| Vector Store | ChromaDB (persistent) |
| LLM | DeepSeek (OpenAI-compatible) |
| Data Models | Pydantic v2 |
| Testing | pytest + httpx + Playwright |
| Package Manager | uv |
| Python | 3.12 |
