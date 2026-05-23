RAG Backend
===========

Purpose
-------
This project is a FastAPI-based Retrieval-Augmented Generation (RAG) backend that ingests documents, stores embeddings in Qdrant, tracks metadata in PostgreSQL, and supports chat queries with optional booking flows. It is intended for AI engineers to integrate and extend, and for project managers to understand system scope, dependencies, and operating requirements.

Core Capabilities
-----------------
- Document ingestion with configurable chunking and embedding generation.
- Vector search and RAG-based answers using Qdrant.
- Chat endpoint with intent classification and booking flows.
- Persistent metadata in PostgreSQL and chat memory in Redis.
- JSON structured logging for production observability.

Architecture Overview
---------------------
- API: FastAPI app in [app/main.py](app/main.py) exposes REST endpoints.
- Ingestion: Parses files, chunks text, embeds, and stores vectors.
- Storage:
	- PostgreSQL: document metadata and chunk references.
	- Qdrant: vector embeddings for retrieval.
	- Redis: chat memory and booking state.

Tech Stack
----------
- Python 3.12
- FastAPI + Uvicorn
- PostgreSQL, Redis, Qdrant
- SQLAlchemy (async) + Alembic
- Sentence Transformers for embeddings
- Groq API for LLM responses

Repository Layout
-----------------
- [app/](app/): application code
- [app/api/](app/api/): API routing
- [app/services/](app/services/): ingestion, RAG, and booking services
- [app/db/](app/db/): database session setup
- [app/models/](app/models/): SQLAlchemy models
- [app/schemas/](app/schemas/): request/response schemas
- [alembic/](alembic/): migrations
- [docker-compose.yml](docker-compose.yml): local service stack
- [Dockerfile](Dockerfile): API container image

Quick Start (Docker)
--------------------
1) Create environment file:
	 - Copy [.env.example](.env.example) to [.env](.env).
	 - Set `GROQ_API_KEY` and review hostnames for your environment.

2) Build and run:
```bash
docker compose up --build
```

3) Apply migrations:
```bash
docker compose exec api alembic upgrade head
```

4) Verify health:
```bash
curl http://localhost:8000/health
```

Local Development (Non-Docker API)
----------------------------------
Use this if you want the API to run on your host but keep PostgreSQL, Redis, and Qdrant in Docker.

1) Start dependencies:
```bash
docker compose up -d postgres redis qdrant
```

2) Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3) Configure [.env](.env) for local API use:
	 - Set `DATABASE_URL=postgresql+asyncpg://raguser:ragpassword@localhost:5432/rag_db`
	 - Set `REDIS_URL=redis://localhost:6379/0`
	 - Set `QDRANT_URL=http://localhost:6333`

4) Run migrations:
```bash
alembic upgrade head
```

5) Start the API:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Configuration
-------------
All runtime configuration is read from [.env](.env) using Pydantic settings in [app/core/config.py](app/core/config.py).

Required
--------
- `GROQ_API_KEY`: API key for the Groq LLM service.

Common Settings
---------------
- `APP_NAME`: application name used in logging and metadata. Default: `rag_backend`.
- `ENVIRONMENT`: deployment environment name. Default: `local`.
- `LOG_LEVEL`: logging level. Default: `INFO`.
- `DATABASE_URL`: PostgreSQL DSN for async SQLAlchemy.
- `REDIS_URL`: Redis DSN for chat memory and booking state.
- `QDRANT_URL`: Qdrant base URL.
- `QDRANT_API_KEY`: Qdrant API key (if authentication is enabled).
- `QDRANT_COLLECTION`: collection name for stored vectors.
- `GROQ_CHAT_MODEL`: Groq model name. Default: `llama-3.1-70b-versatile`.
- `EMBEDDING_MODEL_NAME`: sentence-transformers model name.
- `EMBEDDING_DIM`: embedding vector size. Default: `384`.
- `CHUNK_SIZE_DEFAULT`: default chunk size. Default: `512`.
- `CHUNK_OVERLAP_DEFAULT`: default overlap. Default: `64`.
- `TOP_K_RETRIEVE`: vector search top-k. Default: `10`.
- `TOP_K_RERANK`: rerank top-k. Default: `5`.
- `CHAT_MEMORY_LIMIT`: max messages retained. Default: `10`.
- `CHAT_MEMORY_TTL`: chat memory TTL in seconds. Default: `3600`.
- `BOOKING_TTL`: booking state TTL in seconds. Default: `3600`.
- `REQUEST_TIMEOUT_S`: outbound request timeout. Default: `60`.

API Reference
-------------
Base URL: `http://localhost:8000`

Health Check
------------
GET `/health`

Document Ingestion
------------------
POST `/api/v1/documents/ingest`

Multipart form fields:
- `file`: file to ingest
- `chunking_strategy`: `fixed` or `recursive`
- `chunk_size`: optional integer
- `chunk_overlap`: optional integer

Example:
```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
	-F file=@/path/to/document.pdf \
	-F chunking_strategy=fixed \
	-F chunk_size=512 \
	-F chunk_overlap=64
```

Response (schema):
- `document_id`, `filename`, `chunk_count`, `status`, `chunking_strategy`, `last_chunk`

Chat Query
----------
POST `/api/v1/chat/query`

JSON body:
```json
{
	"session_id": "session-123",
	"query": "What is our refund policy?",
	"document_id": null
}
```

Response (schema):
- `response`: assistant response
- `intent`: intent label (for example, booking or RAG)
- `sources`: list of source chunks
- `booking`: optional booking state

Data Stores
-----------
- PostgreSQL: document metadata and chunk references (via SQLAlchemy models in [app/models/](app/models/)).
- Qdrant: vector embeddings and retrieval.
- Redis: chat memory and booking state.

Logging
-------
Structured JSON logs are configured in [app/core/logging.py](app/core/logging.py). Set `LOG_LEVEL` to control verbosity.

Migrations
----------
Alembic uses `DATABASE_URL` from the environment (see [alembic/env.py](alembic/env.py)).

Common commands:
```bash
alembic upgrade head
alembic revision --autogenerate -m "add_new_table"
```

Operational Notes
-----------------
- Ensure `EMBEDDING_DIM` matches the embedding model output size.
- Use separate values in [.env](.env) for local vs containerized runs.
- Never commit secrets; keep `GROQ_API_KEY` in local secrets storage or CI vault.

Troubleshooting
---------------
- Ingestion fails with vector errors: verify Qdrant is running and `QDRANT_URL` is correct.
- Database connection errors: confirm `DATABASE_URL` matches your running PostgreSQL host and port.
- Chat responses fail: validate `GROQ_API_KEY` and model name.

Support and Ownership
---------------------
If you are a project manager, this is the baseline operational documentation. If you are an AI engineer, start from Quick Start, configure [.env](.env), and integrate via the API Reference section.
