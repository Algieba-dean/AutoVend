# AutoVend RAG Backend

[![CI](https://github.com/Algieba-dean/AutoVend/actions/workflows/ci.yml/badge.svg)](https://github.com/Algieba-dean/AutoVend/actions/workflows/ci.yml)

LlamaIndex-based intelligent automotive sales assistant with RAG (Retrieval-Augmented Generation) architecture.

## Architecture (v2 — Decoupled)

```
┌─────────────────────────────────────────────────┐
│  agent/  (Pure AI logic, zero backend deps)     │
│  ┌─────────┐ ┌────────────┐ ┌───────────────┐  │
│  │Extractors│ │ Stages FSM │ │Resp. Generator│  │
│  └────┬─────┘ └─────┬──────┘ └──────┬────────┘  │
│       └─────────┬───┘───────────────┘            │
│           SalesAgent.process(AgentInput)          │
│                 → AgentResult                     │
└────────────────────┬────────────────────────────┘
                     │ protocol boundary
┌────────────────────┴────────────────────────────┐
│  app/  (FastAPI, Storage, RAG Index)            │
│  Routes → ChatService → SalesAgent              │
│  RAG retrieval, session lifecycle, JSON storage  │
└─────────────────────────────────────────────────┘
```

- **LLM**: DeepSeek (OpenAI-compatible API)
- **Embedding**: bge-m3 (local HuggingFace, Chinese + English)
- **Vector Store**: ChromaDB (persistent local storage)
- **Web Framework**: FastAPI
- **Dialog Memory**: LlamaIndex ChatMemoryBuffer
- **Agent**: Standalone `agent/` package — no backend dependencies

## Quick Start

### 1. Install Dependencies

Requires [uv](https://docs.astral.sh/uv/) for project management.

```bash
cd rag_backend
uv sync --extra dev
```

### 2. Configure Environment

Copy `.env.example` and fill in your API key:

```bash
cp .env.example ../.env
# Edit ../.env and set OPENAI_API_KEY
```

### 3. Build Vehicle Knowledge Index

```bash
python -m scripts.build_index
```

### 4. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs available at: http://localhost:8000/docs

## Project Structure

```
rag_backend/
├── agent/                   # Standalone AI agent (zero backend deps)
│   ├── sales_agent.py       # SalesAgent.process(AgentInput) → AgentResult
│   ├── schemas.py           # Protocol: AgentInput, AgentResult, SessionState
│   ├── stages.py            # Conversation stage FSM
│   ├── memory.py            # Chat memory (LlamaIndex ChatMemoryBuffer)
│   ├── response_generator.py # Stage-aware response generation
│   └── extractors/          # Profile, needs, reservation extraction
├── app/                     # FastAPI backend (thin orchestrator)
│   ├── main.py              # App entry point + SalesAgent wiring
│   ├── config.py            # Unified configuration
│   ├── ingestion/           # Data parsing & indexing
│   ├── rag/                 # RAG query engine
│   ├── models/              # API schemas & file storage
│   └── routes/              # API endpoints (delegate to agent)
├── .github/workflows/       # CI pipeline (lint, test, KPI report)
├── docs/                    # Architecture, KPI, testing docs
├── tests/                   # Full test suite (unit, KPI, e2e)
├── pyproject.toml
└── README.md
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=agent --cov=app --cov-report=term-missing

# Run KPI tests only
uv run pytest tests/test_kpi_extraction.py tests/test_kpi_stages.py tests/test_kpi_e2e_dialogues.py -v

# Generate KPI report
uv run python tests/kpi_report.py

# Architecture isolation check
uv run pytest tests/test_agent_isolation.py -v
```

## API Endpoints

### Chat

- `POST /api/chat/session` — Start new chat session
- `POST /api/chat/message` — Send message
- `GET /api/chat/session/{id}/messages` — Get message history
- `PUT /api/chat/session/{id}/end` — End session

### Profile

- `GET /api/profile/default` — Get default profile
- `GET /api/profile/{phone}` — Get user profile
- `POST /api/profile` — Create profile
- `PUT /api/profile/{phone}` — Update profile
- `DELETE /api/profile/{phone}` — Delete profile
- `GET /api/profile` — List all profiles

### Test Drive

- `POST /api/test-drive` — Create reservation
- `GET /api/test-drive/{phone}` — Get reservation
- `PUT /api/test-drive/{phone}` — Update reservation
- `DELETE /api/test-drive/{phone}` — Delete reservation
- `GET /api/test-drive` — List reservations

### System

- `GET /` — API info
- `GET /health` — Health check

## Documentation

- [Architecture v1](docs/architecture.md) — Original system design and module breakdown
- [Architecture v2](docs/v2_architecture.md) — Decoupled Agent/Backend architecture and KPI targets
- [KPI Metrics v1](docs/kpi.md) — v1 test coverage, code quality, performance metrics
- [KPI Testing Guide](docs/kpi_testing_guide.md) — How to run, interpret, and extend KPI tests
- [CI Pipeline](.github/workflows/ci.yml) — Lint, test, coverage, KPI report, arch guard

## Conversation Stages

```
WELCOME → PROFILE_ANALYSIS → NEEDS_ANALYSIS → CAR_SELECTION
                                                    ↓ ↑
                                          RESERVATION_4S
                                                    ↓ ↑
                                    RESERVATION_CONFIRMATION → FAREWELL
```

Each stage drives specific extractors, retrieval, and response generation.
