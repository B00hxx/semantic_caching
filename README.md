# Semantic Caching & PII Redaction Middleware

A high-performance, privacy-focused **Semantic Caching & Data Anonymization Middleware** designed for Large Language Model (LLM) applications.

This repository provides an end-to-end asynchronous pipeline that combines **Vector Similarity Search (Redis HNSW)**, **Privacy Protection / PII Redaction (Microsoft Presidio)**, **Local LLM & Embedding Services (Ollama)**, and a **Benchmarking & Testing Framework**.

> **New to the project?** Start with [`docs/INTERN_GUIDE.md`](docs/INTERN_GUIDE.md) —
> what we are building and why, the vocabulary, a module-by-module tour, and the
> deliverables roadmap. Then read [`docs/CODE_REVIEW.md`](docs/CODE_REVIEW.md) for the
> current, prioritized list of known bugs and gaps.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [Repository Structure](#-repository-structure)
- [Prerequisites](#-prerequisites)
- [Quick Start & Setup](#-quick-start--setup)
- [Configuration & Environment Variables](#-configuration--environment-variables)
- [API Endpoints](#-api-endpoints)
- [Custom PII Redaction Rules](#-custom-pii-redaction-rules)
- [Benchmarking](#-benchmarking)
- [Testing](#-testing)
- [License](#-license)

---

## 🔍 Overview

Querying LLMs directly for recurring or semantically similar prompts introduces unnecessary latency, high compute overhead, and privacy risks when user prompts contain Sensitive / Personally Identifiable Information (PII).

This middleware solves these problems by:
1. **Redacting Sensitive PII Data** before queries reach the LLM or cache storage using Presidio Analyzer/Anonymizer microservices.
2. **Embedding & Searching Queries** against a Redis Vector Store using cosine distance calculation (HNSW index).
3. **Serving Instant Cache Hits** when semantically similar queries are detected above a configurable similarity threshold.
4. **Delegating Cache Misses** to an LLM provider (e.g., Ollama), then caching the resulting response for future matching.

---

## 🏗️ System Architecture

```
                       ┌─────────────────────────┐
                       │       Client Request    │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │   FastAPI Web Server    │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │     QueryProcessor      │
                       │ (Presidio PII Redact)   │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │ Ollama Embedding Service│
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │ Redis Vector Store HNSW │
                       └──────┬───────────┬──────┘
                              │           │
                   Cache Hit  │           │ Cache Miss
                              ▼           ▼
                      ┌──────────┐     ┌─────────────────────┐
                      │ Return   │     │ Ollama LLM Service  │
                      │ Cached   │     └──────────┬──────────┘
                      │ Response │                │
                      └──────────┘                ▼
                                       ┌─────────────────────┐
                                       │ Store in Redis Cache│
                                       └─────────────────────┘
```

---

## ✨ Features

- **🚀 Async Semantic Caching**: Powered by Redis Stack with HNSW vector index (`FLOAT32`, Cosine distance metric).
- **🔒 Automated PII Redaction**: Integrates Presidio Analyzer and Anonymizer to replace sensitive entities with `<REDACTED>`.
- **🧩 Custom Rule Engine**: Dynamically loads custom YAML-defined regex and pattern recognizers at runtime.
- **🦙 Ollama Integration**: Out-of-the-box support for asynchronous local LLM inference (`qwen2.5:0.5b`) and vector embeddings (`qwen3-embedding:0.6b`).
- **📊 Cache Analytics & Management**: Endpoints for inspecting cache memory usage, key counts, and flushing the database.
- **⚡ Concurrent Benchmark Suite**: Built-in multi-worker load tester to measure throughput (RPS), hit rates, and hit/miss latencies.
- **🧪 Comprehensive Test Coverage**: Unit tests with mock components (`FakeLLM`, `FakeEmbedder`, `FakeRedisService`) and real integration tests.

---

## 📁 Repository Structure

```
.
├── API/                          # FastAPI web application layer
│   ├── app.py                    # Main FastAPI app initialization
│   ├── lifespan.py               # Async startup/shutdown initialization & cleanup
│   ├── routes.py                 # Endpoint route handlers (/ask, /stats, /upload-redaction-rules, etc.)
│   └── schemas/                  # Pydantic request/response validation models
│       └── query_request.py      # QueryRequest and DeleteQuery schemas
├── benchmark/                    # Load testing and performance benchmarking
│   ├── execute_worker.py         # Multi-worker benchmark runner script
│   ├── worker.py                 # Async HTTP worker client
│   └── questions.py              # Categorized prompt dataset for hit/miss benchmarking
├── custom_recognizers/           # Custom Presidio YAML recognizer rules directory
│   └── gemini-code-1785749213179.yaml
├── semantic_caching/             # Core semantic caching & privacy modules
│   ├── semantic_caching.py       # Main SemanticCaching orchestration engine
│   ├── query.py                  # QueryProcessor client for Presidio microservices
│   ├── cache_entry.py            # Cache entry data structure
│   ├── timing.py                 # Execution time measurement utilities
│   ├── embedding_services/       # Abstract and concrete embedder classes (Ollama)
│   ├── llm_services/             # Abstract and concrete LLM classes (Ollama, FakeLLM)
│   ├── presidio-analyzer/       # Custom Presidio Analyzer FastAPI microservice container
│   │   ├── Dockerfile
│   │   └── server.py             # Presidio analyzer API with dynamic YAML rule loader
│   └── vector_store_services/    # Abstract and concrete vector store classes (Redis)
├── testing/                      # Test suite
│   ├── fake_components/          # Mocks for unit testing (FakeLLM, FakeEmbedder, FakeRedis)
│   ├── unit_tests/               # Pytest unit tests for pipeline & threshold logic
│   └── integration_testing/      # End-to-end integration tests against real services
├── utils/                        # Utility helper functions
│   └── cosine_similarity.py      # NumPy cosine similarity calculation helper
├── config.py                     # Centralized settings & Pydantic env config
├── Dockerfile                    # Container definition for FastAPI app
├── docker-compose.yml            # Multi-service stack composition
├── pytest.ini                    # Pytest configuration
└── requirements.txt              # Python project dependencies
```

---

## ⚙️ Prerequisites

- **Docker** & **Docker Compose** (recommended for quick setup)
- **Python 3.12+** (if running locally without Docker)
- **Redis Stack Server** (with RediSearch enabled)
- **Ollama** installed and running with models pulled (`qwen2.5:0.5b` and `qwen3-embedding:0.6b` or configured equivalents)

---

## 🚀 Quick Start & Setup

### 1. Using Docker Compose (Recommended)

Start the full stack including Redis, RedisInsight, Ollama, Presidio Analyzer, Presidio Anonymizer, and FastAPI:

```bash
docker-compose up --build -d
```

The services will be available at:
- **FastAPI Application**: `http://localhost:8000`
- **RedisInsight (GUI)**: `http://localhost:5540`
- **Presidio Analyzer**: `http://localhost:5002`
- **Presidio Anonymizer**: `http://localhost:5001`
- **Ollama API**: `http://localhost:11434`

### 2. Manual Local Setup

1. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start local services** (Redis Stack, Ollama, Presidio microservices).

4. **Launch the FastAPI application**:
   ```bash
   uvicorn API.app:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 🛠️ Configuration & Environment Variables

System configuration is defined in [`config.py`](config.py) and can be overridden via environment variables or a `.env` file:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `REDIS_HOST` | `localhost` | Hostname of the Redis Stack server |
| `REDIS_PORT` | `6379` | Port of the Redis Stack server |
| `OLLAMA_HOST` | `http://localhost:11434` | Endpoint of the Ollama server |
| `ANALYZER_URL` | `http://localhost:5002/analyze` | Presidio Analyzer endpoint |
| `ANONYMIZER_URL` | `http://localhost:5001/anonymize` | Presidio Anonymizer endpoint |
| `CUSTOM_RULES_DIR` | `./custom_recognizers` | Directory containing custom Presidio YAML rules |
| `DELETE_ON_SHUTDOWN` | `false` | If `true`, flushes the Redis vector cache on app shutdown |

---

## 📡 API Endpoints

### 1. Ask Question (Main Pipeline)
- **URL**: `POST /ask`
- **Body**:
  ```json
  {
    "query": "What is machine learning?"
  }
  ```
- **Response**:
  ```json
  {
    "cache_hit": false,
    "cosine_distance": null,
    "answer": "Machine learning is a subset of artificial intelligence...",
    "time": "2026-08-04T12:00:00.000000"
  }
  ```

### 2. Fast/Fake Ask (Benchmarking Mock LLM)
- **URL**: `POST /fake_ask`
- **Body**:
  ```json
  {
    "query": "What is Python?"
  }
  ```

### 3. Cache Statistics
- **URL**: `GET /stats`
- **Response**:
  ```json
  {
    "Total keys": 42,
    "Memory used (bytes)": 1542000
  }
  ```

### 4. Clear Cache
- **URL**: `POST /delte_cache`
- **Body**:
  ```json
  {
    "state": true
  }
  ```

### 5. Upload Custom Redaction Rules
- **URL**: `POST /upload-redaction-rules/`
- **Form Data**: `file` (`.yaml` / `.yml`)

---

## 🛡️ Custom PII Redaction Rules

Custom YAML rules can be placed in `custom_recognizers/` or uploaded via the `/upload-redaction-rules/` endpoint.

Example YAML structure:
```yaml
recognizers:
  - name: "EmployeeIDRecognizer"
    supported_language: "en"
    supported_entity: "EMPLOYEE_ID"
    patterns:
      - name: "emp_id_pattern"
        regex: "\\bEMP-\\d{5}\\b"
        score: 0.95
```

---

## 📊 Benchmarking

Run the concurrent worker benchmark suite to test latency, throughput, and hit rates:

```bash
python -m benchmark.execute_worker
```

Results are printed to the console and exported to `results.json`:

```text
================ BENCHMARK SUMMARY ================
  total_requests: 129
  total_duration_sec: 1.25
  requests_per_sec: 103.2
  cache_hit_rate: 65.1%
  avg_hit_latency_sec: 0.0084
  avg_miss_latency_sec: 0.3120
  errors_count: 0
====================================================
```

---

## 🧪 Testing

### Unit Tests
Run fast unit tests with mock LLM and vector store components:

```bash
pytest testing/unit_tests/
```

### Integration Tests
Run end-to-end integration tests against live Ollama and Redis services:

```bash
pytest testing/integration_testing/
```

---

## 📄 License

This project is open-source and available under the standard MIT License.
