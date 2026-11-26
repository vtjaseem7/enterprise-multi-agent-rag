# Enterprise Multi-Agent RAG Platform

A production-oriented, multi-tenant Retrieval-Augmented Generation (RAG) platform built with **FastAPI**, **LangGraph**, **Qdrant**, **PostgreSQL**, **Redis**, and **Streamlit**. Designed around strict pre-LLM access control, hybrid dense + sparse retrieval, cross-encoder reranking, security-scoped caching, and automated evaluation.

## Architecture

```text
User (Streamlit UI / API Client)
        │  JWT Bearer Token (tenant_id, role, access_groups)
        ▼
FastAPI Backend (/api/v1/chat, /api/v1/documents/upload)
        │
        ├──► Redis Cache (Security-scoped SHA-256 key: tenant + role + groups + query)
        │
        └──► LangGraph Multi-Agent Workflow
                ├── 1. Router Node (Fast LLM) ──► Classifies query: simple vs. complex
                ├── 2. Retriever Node ──────────► Qdrant Hybrid Search (Dense + BM25 + RRF)
                │                                 + Mandatory Pre-LLM ACL Filter
                │                                 + Local ONNX Cross-Encoder Reranking
                ├── 3. Analyst Node (Complex) ──► Structured root-cause analysis
                └── 4. Responder Node ──────────► Grounded answer + source citations
```

## Key Features

- **Multi-Tenant Pre-LLM Access Control (RBAC):** Qdrant filters chunks by `tenant_id`, `allowed_roles`, and `allowed_groups` at the database layer *before* any document text reaches an LLM.
- **Hybrid Retrieval + Reranking:** Combines `BAAI/bge-small-en-v1.5` dense vectors and `Qdrant/bm25` sparse vectors via Reciprocal Rank Fusion (RRF), followed by local ONNX cross-encoder reranking (`Xenova/ms-marco-MiniLM-L-6-v2`) with score thresholding.
- **Adaptive Multi-Agent Routing:** Built with LangGraph. Simple lookups take the Fast Path (`router → retrieve → respond`); complex investigations route through the Analyst node (`router → retrieve → analyze → respond`).
- **Document Ingestion Pipeline:** Supports `.txt`, `.md`, and `.pdf` (via PyMuPDF) with SHA-256 content fingerprinting and recursive character chunking (800 chars / 120 overlap).
- **Security-Scoped Redis Caching:** Caches repeated queries using a SHA-256 key derived from `tenant_id`, `role`, `access_groups`, and normalized query to prevent cross-role cache leaks and save LLM tokens.
- **Automated Security & Quality Testing:** `pytest` security test suite (`tests/test_api_security.py`) and Golden Dataset evaluation (`scripts/run_eval.py`).

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2, PyJWT |
| **Orchestration** | LangGraph, LangChain-Groq |
| **Vector Database** | Qdrant (Hybrid Dense + BM25 Sparse + RRF) |
| **Embeddings & Reranker** | FastEmbed (Local ONNX CPU inference) |
| **Relational DB** | PostgreSQL 16, SQLAlchemy (Async), AsyncPG |
| **Caching** | Redis 7 |
| **Frontend UI** | Streamlit |
| **Testing & DevOps** | Pytest, HTTPX, Docker, Docker Compose |

## Project Structure

```text
enterprise-multi-agent-rag/
├── app/
│   ├── api/routes/          # FastAPI endpoints (chat, documents)
│   ├── core/                # Config, JWT security, Redis cache
│   ├── database/            # SQLAlchemy async session & models
│   ├── graph/               # LangGraph state & multi-agent workflow
│   ├── ingestion/           # Text extraction, chunking, SHA-256, Qdrant indexing
│   ├── retrieval/           # Hybrid search, ACL filtering, cross-encoder reranking
│   └── main.py              # FastAPI app entrypoint
├── data/
│   ├── evaluation/          # Golden dataset (golden_set.json)
│   └── raw/                 # Uploaded & sample documents
├── frontend/
│   └── app.py               # Streamlit chat & admin upload UI
├── scripts/                 # DB init, connection tests, ingestion & eval runners
├── tests/                   # Pytest API & RBAC security tests
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
└── requirements.txt
```

## Quick Start (Docker)

1. **Clone the repository and configure environment variables:**
   ```bash
   git clone [https://github.com/vtjaseem7/enterprise-multi-agent-rag.git](https://github.com/vtjaseem7/enterprise-multi-agent-rag.git)
   cd enterprise-multi-agent-rag
   cp .env.example .env
   ```
   Open `.env` and set your `GROQ_API_KEY` and a 32+ character `JWT_SECRET_KEY`.

2. **Build and start all 5 services:**
   ```bash
   docker compose up --build -d
   ```

3. **Access the platform:**
   - **Streamlit Chat UI:** `http://localhost:8501`
   - **FastAPI Swagger Docs:** `http://localhost:8000/docs`
   - **Qdrant Dashboard:** `http://localhost:6333/dashboard`

4. **Stop the stack:**
   ```bash
   docker compose down
   ```

## API Endpoints

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | No | Service health check |
| `POST` | `/api/v1/auth/dev-token` | No | Mint a signed JWT for role testing (`customer`, `employee`, `admin`) |
| `POST` | `/api/v1/chat` | Bearer JWT | Run cached or LangGraph multi-agent RAG query |
| `POST` | `/api/v1/documents/upload` | Bearer JWT (`admin`) | Upload & index `.txt`, `.md`, or `.pdf` into Qdrant |

## Running Tests & Evaluation

With your local virtual environment active and Docker services running:

```bash
# Run API & RBAC security tests
pytest -v

# Run Golden Dataset RAG evaluation
python -m scripts.run_eval
```