# Semantic Caching & PII Redaction Middleware

A high-performance, privacy-focused **Semantic Caching & Data Anonymization Middleware** designed for Large Language Model (LLM) applications.

This repository provides an end-to-end asynchronous pipeline that combines **Vector Similarity Search (Redis HNSW)**, **Privacy Protection / PII Redaction (Microsoft Presidio)**, **Local LLM & Embedding Services (Ollama)**, **JWT Authentication & Access Control**, and a **Classification & Performance Benchmarking Framework**.

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
- [Benchmarking & Visualizations](#-benchmarking--visualizations)
- [Testing](#-testing)
- [License](#-license)

---

## 🔍 Overview

Querying LLMs directly for recurring or semantically similar prompts introduces unnecessary latency, high compute overhead, and privacy risks when user prompts contain Sensitive / Personally Identifiable Information (PII).

This middleware solves these problems by:
1. **Redacting Sensitive PII Data** before queries reach the LLM or cache storage using Presidio Analyzer/Anonymizer microservices with runtime rule reloading.
2. **Embedding & Searching Queries** against a Redis Vector Store using cosine distance calculation (HNSW index).
3. **Serving Instant Cache Hits** when semantically similar queries are detected above a configurable similarity threshold.
4. **Delegating Cache Misses** to an LLM provider (e.g., Ollama), then caching the resulting response for future matching.
5. **Securing Administrative Actions** via OAuth2 JWT Bearer authentication.

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
                       │   (JWT Auth & Routers)  │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │     QueryProcessor      │
                       │ (Presidio PII Redact &  │
                       │ Dynamic Rule Reloading) │
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
- **🔄 Dynamic Presidio Rule Reloading**: Dynamically uploads custom YAML rules and hot-reloads the Presidio Analyzer service in real time without restarting containers.
- **🔐 JWT Authentication & Security**: Secures administrative API endpoints (such as cache deletion) using OAuth2 JWT Bearer tokens.
- **🦙 Ollama Integration**: Out-of-the-box support for asynchronous local LLM inference (`qwen2.5:0.5b`) and vector embeddings (`qwen3-embedding:0.6b`).
- **📊 Cache Analytics & Management**: Endpoints for inspecting cache memory usage, key counts, and clearing the database.
- **⚡ Classification Benchmarking Suite**: Evaluates cache duplicate detection performance on datasets (e.g., Quora Question Pairs) and outputs classification metrics including Confusion Matrix (TP, FP, TN, FN), Accuracy, Precision, Recall, and F1 Score.
- **🧪 Comprehensive Test Coverage**: Unit tests with mock components (`FakeLLM`, `FakeEmbedder`, `FakeRedisService`) and real integration tests.

---

## 📁 Repository Structure

```
.
├── API/                          # FastAPI web application layer
│   ├── app.py                    # Main FastAPI app initialization & router composition
│   ├── lifespan.py               # Async startup/shutdown initialization & cleanup
│   ├── auth/                     # JWT authentication & security utilities
│   │   └── security.py           # Password hashing, JWT token generation & verification
│   ├── routes/                   # Modular APIRouters
│   │   ├── auth.py               # Authentication endpoint (/auth/login)
│   │   ├── chat.py               # Query processing endpoints (/chat/ask, /chat/fake_ask)
│   │   ├── delete.py             # Protected cache deletion routes (/delete/cache, /delete/fake_cache)
│   │   ├── redaction_rules.py    # Dynamic Presidio rules upload (/rules/upload-redaction-rules)
│   │   └── stats.py              # Cache statistics route (/stats/stats)
│   └── schemas/                  # Pydantic request/response validation models
│       └── query_request.py      # QueryRequest schema
├── benchmark/                    # Load testing and performance benchmarking framework
│   ├── main.py                   # Main benchmark entrypoint script
│   ├── clients/                  # API clients (AuthClient, CacheClient)
│   ├── datasets/                 # Benchmarking datasets (train.csv)
│   ├── metrics/                  # Classification metrics (ClassificationMetrics)
│   ├── quora_questions/          # Dataloader & schemas for Quora Question Pairs
│   ├── runners/                  # Benchmark execution runners (SequentialBenchmarkRunner)
│   └── workers/                  # Worker execution engine (Worker)
├── custom_recognizers/           # Custom Presidio YAML recognizer rules directory
│   └── gemini-code-1785749213179.yaml
├── semantic_caching/             # Core semantic caching & privacy modules
│   ├── semantic_caching.py       # Main SemanticCaching orchestration engine
│   ├── query.py                  # QueryProcessor client for Presidio microservices
│   ├── cache_entry.py            # Cache entry data structure
│   ├── timing.py                 # Execution time measurement utilities
│   ├── embedding_services/       # Abstract and concrete embedder classes (Ollama)
│   ├── llm_services/             # Abstract and concrete LLM classes (Ollama, FakeLLM)
│   ├── presidio-analyzer/        # Custom Presidio Analyzer microservice container
│   │   ├── Dockerfile
│   │   ├── prisidio_reload_service.py # Dynamic rule reload client service
│   │   └── server.py             # Presidio analyzer API with dynamic YAML rule loader
│   └── vector_store_services/    # Abstract and concrete vector store classes (Redis)
├── testing/                      # Test suite
│   ├── fake_components/          # Mocks for unit testing (FakeLLM, FakeEmbedder, FakeRedis)
│   ├── unit_tests/               # Pytest unit tests for pipeline & threshold logic
│   └── integration_testing/      # End-to-end integration tests against real services
├── utils/                        # Utility helper functions
│   └── cosine_similarity.py      # NumPy cosine similarity calculation helper
├── visualizations/               # Benchmark visualization scripts & generated charts
│   ├── visualize_results.py      # Plot generation script for performance metrics
│   └── results.json              # Evaluated threshold benchmark results
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

System configuration is defined in [`config.py`](file:///home/baha/Documents/internship/config.py) and can be overridden via environment variables or a `.env` file:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `REDIS_HOST` | `localhost` | Hostname of the Redis Stack server |
| `REDIS_PORT` | `6379` | Port of the Redis Stack server |
| `OLLAMA_HOST` | `http://localhost:11434` | Endpoint of the Ollama server |
| `ANALYZER_URL` | `http://localhost:5002/analyze` | Presidio Analyzer endpoint |
| `ANONYMIZER_URL` | `http://localhost:5001/anonymize` | Presidio Anonymizer endpoint |
| `CUSTOM_RULES_DIR` | `./custom_recognizers` | Directory containing custom Presidio YAML rules |
| `DELETE_ON_SHUTDOWN` | `true` | If `true`, flushes the Redis vector cache on app shutdown |
| `JWT_SECRET_KEY` | *(Required)* | Secret key used for signing JWT access tokens |
| `ADMIN_USERNAME` | *(Required)* | Administrative username for API authentication |
| `ADMIN_PASSWORD_HASH` | *(Required)* | Hashed password for admin authentication |
| `ADMIN_PASSWORD` | *(Required)* | Admin password used during login authentication |

---

## 📡 API Endpoints

### 1. Authentication (Login)
- **URL**: `POST /auth/login`
- **Body** (Form-Data):
  - `username`: Admin username
  - `password`: Admin password
- **Response**:
  ```json
  {
    "access_token": "<JWT_TOKEN>",
    "token_type": "bearer"
  }
  ```

### 2. Ask Question (Main Pipeline)
- **URL**: `POST /chat/ask`
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

### 3. Fast/Fake Ask (Benchmarking Mock LLM)
- **URL**: `POST /chat/fake_ask`
- **Body**:
  ```json
  {
    "query": "What is Python?"
  }
  ```

### 4. Cache Statistics
- **URL**: `GET /stats/stats`
- **Response**:
  ```json
  {
    "Total keys": 42,
    "Memory used (bytes)": 1542000
  }
  ```

### 5. Clear Cache (Protected)
- **URL**: `DELETE /delete/cache`
- **Headers**: `Authorization: Bearer <JWT_TOKEN>`
- **Response**:
  ```json
  {
    "message": "Cache deleted successfully."
  }
  ```

### 6. Clear Fake Cache (Protected)
- **URL**: `DELETE /delete/fake_cache`
- **Headers**: `Authorization: Bearer <JWT_TOKEN>`
- **Response**:
  ```json
  {
    "message": "Fake Cache deleted successfully."
  }
  ```

### 7. Upload Custom Redaction Rules
- **URL**: `POST /rules/upload-redaction-rules`
- **Form Data**: `file` (`.yaml` / `.yml`)
- **Note**: Uploading a valid YAML rule file automatically triggers a real-time hot reload of the Presidio Analyzer recognizer registry.

---

## 🛡️ Custom PII Redaction Rules

Custom YAML rules can be placed in `custom_recognizers/` or uploaded via the `/rules/upload-redaction-rules` endpoint.

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

## 📊 Benchmarking & Visualizations

### 🏃 Running Benchmarks

Run the classification benchmarking framework against live or mock endpoints:

```bash
python -m benchmark.main
```

The runner logs in to obtain a JWT token, passes questions from the Quora dataset (`benchmark/datasets/train.csv`), and evaluates the cache classification quality:

```text
===== Benchmark Results =====
true_positives: 45
false_positives: 2
true_negatives: 48
false_negatives: 5
accuracy: 0.9300
precision: 0.9574
recall: 0.9000
f1_score: 0.9278
```

### 📈 Performance & Threshold Visualizations

To analyze performance across various similarity thresholds, run the visualization script:

```bash
python visualizations/visualize_results.py
```

This generates comprehensive analysis plots based on the evaluated benchmark dataset:

#### 1. Performance Metrics vs. Similarity Threshold
Shows how **Accuracy**, **Precision**, **Recall**, and **F1 Score** evolve across similarity thresholds (ranging from 0.50 to 0.95). As the similarity threshold increases, precision improves while recall decreases.

![Performance vs Threshold](performance_vs_threshold.png)

#### 2. F1 Score Optimization
Highlights the F1 Score curve across similarity thresholds, pinpointing the optimal threshold value that balances precision and recall.

![F1 Score vs Threshold](f1_vs_threshold.png)

#### 3. Precision–Recall Tradeoff
Displays the trade-off curve between Precision and Recall with annotations for each evaluated similarity threshold.

![Precision-Recall Tradeoff](precision_recall_tradeoff.png)

#### 4. Confusion Matrix Breakdown
Tracks the exact counts of **True Positives (TP)**, **False Positives (FP)**, **True Negatives (TN)**, and **False Negatives (FN)** across different threshold values.

![Confusion Matrix Breakdown](confusion_matrix_vs_threshold.png)

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

