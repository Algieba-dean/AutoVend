# AutoVend

Intelligent automotive sales assistant powered by LLM and RAG (Retrieval-Augmented Generation).

AutoVend guides customers through a multi-stage conversation — from greeting and profile collection, through needs analysis and vehicle recommendation, to test-drive reservation — all driven by a decoupled AI agent.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  frontend/  (React + MUI)                           │
│  Chat UI · User Profile · Dealer Portal             │
└──────────────────────┬──────────────────────────────┘
                       │  HTTP /api/*
┌──────────────────────┴──────────────────────────────┐
│  backend/                                           │
│  ┌────────────────────────────────────────────────┐ │
│  │  agent/  (Pure AI logic, zero backend deps)    │ │
│  │  Extractors · Stages FSM · Response Generator  │ │
│  │  SalesAgent.process(AgentInput) → AgentResult  │ │
│  └────────────────────┬───────────────────────────┘ │
│                       │ protocol boundary            │
│  ┌────────────────────┴───────────────────────────┐ │
│  │  app/  (FastAPI, Storage, RAG Index)           │ │
│  │  Routes → SalesAgent · RAG retrieval           │ │
│  │  Session lifecycle · JSON file storage         │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer       | Technology                                      |
|-------------|------------------------------------------------|
| Frontend    | React 18, Material-UI, Axios                   |
| Backend     | FastAPI, Pydantic v2, Uvicorn                   |
| AI Agent    | LlamaIndex, DeepSeek LLM (OpenAI-compatible)   |
| Embeddings  | bge-m3 (HuggingFace, Chinese + English)         |
| Vector Store| ChromaDB (persistent local)                     |
| CI          | GitHub Actions (Ruff lint, pytest, KPI report)  |

## Quick Start

### Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) (Python project manager)
- Node.js ≥ 18 (for frontend)

### Backend

```bash
cd backend
uv sync --extra dev
cp .env.example ../.env   # Edit ../.env and set OPENAI_API_KEY
python -m scripts.build_index   # Build vehicle knowledge index
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm start
```

Opens at http://localhost:3000 (proxies API requests to backend on port 8000).

## Project Structure

```
AutoVend/
├── backend/                # FastAPI backend + AI agent
│   ├── agent/              # Standalone AI agent (zero backend deps)
│   ├── app/                # FastAPI app (routes, models, RAG, config)
│   ├── tests/              # Full test suite (unit, KPI, e2e)
│   ├── docs/               # Architecture & KPI documentation
│   ├── scripts/            # Index building scripts
│   └── pyproject.toml
├── frontend/               # React frontend
│   ├── src/components/     # Chat, UserProfile, DealerPortal, etc.
│   ├── src/services/       # API client (api.js)
│   └── package.json
├── DataInUse/              # Vehicle data (TOML files)
├── Doc/                    # Project documentation & design docs
├── .github/workflows/      # CI pipeline
└── README.md
```

## Testing

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=agent --cov=app --cov-report=term-missing

# Architecture isolation check
uv run pytest tests/test_agent_isolation.py -v

# KPI report
uv run python tests/kpi_report.py
```

## Conversation Stages

```
WELCOME → PROFILE_ANALYSIS → NEEDS_ANALYSIS → CAR_SELECTION
                                                    ↓ ↑
                                          RESERVATION_4S
                                                    ↓ ↑
                                    RESERVATION_CONFIRMATION → FAREWELL
```

## Documentation

- [Backend README](backend/README.md) — API endpoints, setup, architecture details
- [Architecture v2](backend/docs/v2_architecture.md) — Decoupled Agent/Backend design
- [KPI Testing Guide](backend/docs/kpi_testing_guide.md) — How to run and interpret KPI tests
- [CI Pipeline](.github/workflows/ci.yml) — Lint, test, coverage, KPI report, arch guard

## License

MIT
