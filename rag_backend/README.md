# AutoVend RAG Backend

LlamaIndex-based intelligent automotive sales assistant with RAG (Retrieval-Augmented Generation) architecture.

## Architecture

- **LLM**: DeepSeek (OpenAI-compatible API)
- **Embedding**: bge-m3 (local HuggingFace, Chinese + English)
- **Vector Store**: ChromaDB (persistent local storage)
- **Web Framework**: FastAPI
- **Dialog Memory**: LlamaIndex ChatMemoryBuffer

## Quick Start

### 1. Install Dependencies

```bash
cd rag_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Unified configuration
│   ├── ingestion/           # Data parsing & indexing
│   ├── rag/                 # RAG query engine
│   ├── extractors/          # Structured information extraction
│   ├── workflow/            # Dialog stage workflow
│   ├── memory/              # Chat memory management
│   ├── models/              # Pydantic schemas & storage
│   └── routes/              # API endpoints
├── data/                    # ChromaDB persistent storage
├── docs/                    # KPI, architecture, API docs
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
├── .env.example
├── requirements.txt
└── README.md
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test module
pytest tests/test_toml_parser.py -v
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

### Test Drive
- `POST /api/test-drive` — Create reservation
- `GET /api/test-drive/{phone}` — Get reservation
- `PUT /api/test-drive/{phone}` — Update reservation
- `DELETE /api/test-drive/{phone}` — Delete reservation
- `GET /api/test-drive` — List reservations
