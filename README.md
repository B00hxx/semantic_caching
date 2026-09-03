# Semantic Caching Middleware

FastAPI middleware for semantic response caching around LLM applications. It combines Redis Stack HNSW search, PostgreSQL/pgvector persistence, LiteLLM model routing, Ollama inference, Microsoft Presidio analysis, OAuth2 JWT administration, Prometheus metrics, and benchmark tooling.

The application keeps separate cache instances for different invalidation and eviction policies. A request is analyzed for sensitive entities before cache lookup. Clean queries are embedded and searched semantically; misses are sent to the LLM and stored. Sensitive queries bypass embedding and Redis lookup, while the original query is sent to the configured LLM for answer accuracy.

## Contents

- [Architecture](#architecture)
- [Features](#features)
- [Repository Layout](#repository-layout)
- [Docker Services](#docker-services)
- [Configuration](#configuration)
- [Run the Application](#run-the-application)
- [API Reference](#api-reference)
- [Caching Policies](#caching-policies)
- [Privacy and Redaction](#privacy-and-redaction)
- [Persistence and Startup](#persistence-and-startup)
- [Observability](#observability)
- [Benchmarks](#benchmarks)
- [Testing](#testing)
- [Known Implementation Notes](#known-implementation-notes)

## Architecture

```text
Client
  |
  v
FastAPI (/chat, /stats, /delete, /rules, /auth)
  |
  +--> Presidio Analyzer --> sensitive? --yes--> original query to LLM
  |                                      |         (no Redis lookup)
  |                                      +-------> redacted observation attempt
  |
  +--> LiteLLM embedding --> Redis Stack HNSW --> hit: cached answer
  |                                           \--> miss: LiteLLM LLM
  |                                                        |
  +<-------------------------------------------------------+
  |
  +--> PostgreSQL/pgvector persistence and startup pre-warming
  +--> Prometheus metrics
```

The FastAPI application is created in [API/app.py](API/app.py). Its lifespan in [API/lifespan.py](API/lifespan.py) creates the Redis services, PostgreSQL pool, query processor, LLM and embedding clients, cache policies, startup hydration, and background maintenance tasks.

## Features

- Semantic lookup with Redis Stack HNSW indexes and cosine distance.
- Six independent production caches, each with its own Redis key prefix and namespace.
- TTL, inactivity, and hit-count invalidation strategies.
- LRU, LFU, and FIFO capacity eviction strategies.
- PostgreSQL 17 with `pgvector` for durable cache records and access metadata.
- Startup pre-warming of up to 10 top PostgreSQL entries per cache namespace.
- LiteLLM proxy routing for generation and embeddings.
- Ollama-backed local models configured through LiteLLM.
- Presidio built-in and YAML-defined custom recognizers.
- Authenticated custom-rule uploads with analyzer hot reload.
- OAuth2 password login and long-lived HS256 JWTs for admin routes.
- Prometheus metrics for HTTP latency, cache requests, hits, misses, bypasses, lookups, embeddings, invalidations, evictions, and cache size.
- RedisInsight, PgAdmin, Grafana, and Prometheus containers for local inspection.
- Quora duplicate-question threshold benchmarking.
- LMSYS query worker benchmarking.
- Unit tests with fake components and integration tests for live services.

## Repository Layout

```text
.
├── API/
│   ├── app.py                         FastAPI app, routers, HTTP latency metric
│   ├── lifespan.py                    Startup hydration and maintenance loops
│   ├── auth/security.py               Password checks, JWTs, admin dependency
│   ├── routes/
│   │   ├── auth.py                    POST /auth/login
│   │   ├── chat.py                    Public semantic-cache routes
│   │   ├── delete.py                  Authenticated cache deletion
│   │   ├── get_all_hot_entries.py     Authenticated Redis entry dump
│   │   ├── redaction_rules.py         Authenticated YAML upload
│   │   ├── stats.py                   Authenticated Redis statistics
│   │   └── top_k_entries.py            Authenticated PostgreSQL query
│   └── schemas/query_request.py       QueryRequest and NumberOfEntries
├── semantic_caching/
│   ├── semantic_caching.py             Request pipeline and policies
│   ├── query.py                        Presidio client and redaction
│   ├── cache_entry/                    CacheEntry model
│   ├── cache_eviction/                 FIFO, LFU, LRU strategies
│   ├── cache_invalidation/             TTL, inactivity, hit-count strategies
│   ├── embedding_services/             Abstract, LiteLLM, and Ollama clients
│   ├── llm_services/                   Abstract, LiteLLM, Ollama, fake LLM
│   ├── postgres_service/               asyncpg/pgvector persistence
│   ├── presidio_analyzer/              Analyzer service and reload trigger
│   └── vector_store_services/          Redis vector-store abstraction
├── benchmark/
│   ├── main.py                         Quora benchmark entry point
│   ├── run_workers.py                  LMSYS worker benchmark entry point
│   ├── clients/                        Auth and cache HTTP clients
│   ├── datasets/                       Quora and LMSYS data
│   ├── metrics/                        Accuracy, precision, recall, F1
│   ├── quora_questions/                Quora loader and question-pair model
│   ├── runners/                        Sequential benchmark runner
│   └── workers/                        Worker and dataset execution engine
├── custom_recognizers/                 YAML Presidio rules
├── postgres/                           Database creation and SQL schema
├── threshold_tuning/                   Stored threshold results and charts
├── visualizations/                     Threshold chart generator
├── testing/
│   ├── fake_components/                Test doubles
│   ├── unit_tests/                     Unit tests
│   └── integration_testing/            Live-service tests
├── config.py                           Pydantic settings
├── config.yaml                         LiteLLM model routing
├── docker-compose.yml                  Complete local stack
├── Dockerfile                          FastAPI image
├── requirements.txt                    Pinned Python dependencies
├── pytest.ini                          Pytest discovery configuration
└── test.py                             Password-hashing helper
```

## Docker Services

Start the complete stack with:

```bash
docker-compose up --build -d
```

| Service | Host port | Purpose |
|---|---:|---|
| `fastapi` | `8000` | API and semantic-caching pipeline |
| `litellm` | `4000` | Unified LLM and embedding proxy |
| `postgres` | `5432` | LiteLLM database and cache database (`pgvector`) |
| `pgadmin` | `5050` | PostgreSQL web UI |
| `redis` | `6380` | Redis Stack server, container port `6379` |
| `redisinsight` | `5540` | Redis web UI |
| `ollama` | `11434` | Local model server and persistent model volume |
| `presidio-analyzer` | `5002` | Custom Analyzer API, container port `3000` |
| `presidio-anonymizer` | `5001` | Presidio anonymizer service |
| `grafana` | `3000` | Metrics dashboard UI |
| `prometheus` | `9090` | Metrics collection and query UI |

The Docker network is `app-network`. Persistent volumes are defined for Ollama, PostgreSQL, PgAdmin, Grafana, Prometheus, and Presidio rules. The FastAPI container mounts the project at `/app` and runs `uvicorn API.app:app`.

Useful local URLs:

- FastAPI OpenAPI UI: `http://localhost:8000/docs`
- LiteLLM: `http://localhost:4000`
- RedisInsight: `http://localhost:5540`
- PgAdmin: `http://localhost:5050` (`demo@example.com` / `secret` in compose)
- Grafana: `http://localhost:3000` (`admin` / `admin` in compose)
- Prometheus: `http://localhost:9090`
- Presidio health: `http://localhost:5002/health`

The PostgreSQL init script creates the cache user and database from environment variables, enables `vector`, and applies [postgres/schema.sql](postgres/schema.sql). The same PostgreSQL server also hosts the LiteLLM database.

## Configuration

Create a `.env` file in the project root. Top-level settings use their exact names below. Nested Pydantic settings use `__`, for example `LITE_LLM_SETTINGS__MODEL_NAME` when using nested environment loading.

### Required settings

| Variable | Used for |
|---|---|
| `JWT_SECRET_KEY` | JWT signing key |
| `ADMIN_USERNAME` | Admin login username |
| `ADMIN_PASSWORD_HASH` | Bcrypt hash checked at login |
| `ADMIN_PASSWORD` | Benchmark/test login password |
| `MODEL_NAME` | LiteLLM completion model name |
| `API_KEY` | LiteLLM completion key value |
| `EMBEDDING_MODEL_NAME` | LiteLLM embedding model name |
| `API_KEY_EMB` | LiteLLM embedding key value |
| `EMBEDDING_MODEL_DIMENSION` | Embedding vector dimension, normally `1024` |
| `LITELLM_MASTER_KEY` | LiteLLM proxy master key |
| `POSTGRES_PASSWORD` | LiteLLM PostgreSQL password in Compose |
| `CACHE_POSTGRES_DB` | Cache database created by Compose |
| `CACHE_POSTGRES_USER` | Cache database user created by Compose |
| `CACHE_POSTGRES_PASSWORD` | Cache database password |

### Application defaults

| Variable | Default |
|---|---:|
| `REDIS_HOST` | `localhost` |
| `REDIS_PORT` | `6380` locally; `6379` when `REDIS_HOST` is not local |
| `OLLAMA_HOST` | `http://localhost:11434` |
| `ANALYZER_URL` | `http://localhost:5002/analyze` |
| `ANONYMIZER_URL` | `http://localhost:5001/anonymize` |
| `CUSTOM_RULES_DIR` | `./custom_recognizers` |
| `CACHE_POSTGRES_HOST` | `localhost` |
| `CACHE_POSTGRES_PORT` | `5432` |
| `CACHE_POSTGRES_DB` | `semantic_cache` |
| `CACHE_POSTGRES_USER` | `semantic_cache` |
| `CACHE_POSTGRES_PASSWORD` | empty |
| `cache_ttl_seconds` | `900` |
| `cache_inactivity_seconds` | `900` |
| `cache_min_hit_count` | `2` |
| `cache_invalidation_interval` | `900` seconds |
| `cache_eviction_interval` | `1800` seconds |
| `cache_max_size` | `100` |
| `delete_on_shutdown` | `false` |
| `UI_USERNAME`, `UI_PASSWORD` | unset, optional LiteLLM UI credentials |

LiteLLM routing in [config.yaml](config.yaml) maps `qwen` to `ollama/qwen:0.5b` and `qwen-embedding` to `ollama/qwen3-embedding:0.6b`, both through Ollama. Prometheus callbacks are enabled and LiteLLM metrics authentication is disabled.

## Run the Application

### Docker

```bash
docker-compose up --build -d
docker-compose logs -f fastapi
```

### Local Python process

Redis, PostgreSQL, LiteLLM, Ollama, and Presidio must be reachable at the configured URLs.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn API.app:app --host 0.0.0.0 --port 8000 --reload
```

## API Reference

All chat request bodies are JSON objects with one required string field:

```json
{"query": "What is semantic caching?"}
```

Chat routes are public. Statistics, deletion, and rule-upload routes require an admin JWT.

### Authentication

`POST /auth/login` accepts `application/x-www-form-urlencoded` fields `username` and `password`. A successful response is:

```json
{"access_token": "<JWT>", "token_type": "bearer"}
```

Tokens use HS256 and the implementation sets a lifetime of 3,000,000 minutes. Use the token as `Authorization: Bearer <JWT>`.

### Chat routes

| Method | Path | Cache configuration |
|---|---|---|
| `POST` | `/chat/ttl_cache` | threshold `0.8`, TTL invalidation, LRU eviction |
| `POST` | `/chat/inactivity_cache` | threshold `0.8`, inactivity invalidation, LFU eviction |
| `POST` | `/chat/hit_count_cache` | threshold `0.8`, hit-count invalidation, FIFO eviction |
| `POST` | `/chat/fifo_eviction_cache` | threshold `0.8`, FIFO eviction |
| `POST` | `/chat/lfu_eviction_cache` | threshold `0.8`, LFU eviction |
| `POST` | `/chat/lru_eviction_cache` | threshold `0.8`, LRU eviction |
| `POST` | `/chat/fake_ask` | threshold `0.95`, fake LLM returning `"x"`; benchmark cache |

Normal responses contain `cache_hit`, `cosine_distance`, `answer`, and `time`; cache hits also contain `id`. A sensitive-query response contains `cache_hit: false`, `cache_bypassed: true`, and `answer`.

### Admin statistics and inspection

- `GET /stats/stats`: per-cache Redis entry counts and `Memory used (bytes)`.
- `GET /stats/get_all_entries`: all current entries from the six production caches, including IDs, question, answer, namespace, timestamps, hit count, and embedding dimension.
- `POST /stats/postgres_entries`: accepts `{"k": 10}` and returns up to `k` top records for each production namespace, ordered by PostgreSQL hit count.

### Admin deletion and rules

- `DELETE /delete/cache`: deletes keys from all six production Redis prefixes; PostgreSQL rows remain.
- `DELETE /delete/fake_cache`: deletes the benchmark cache.
- `POST /rules/upload-redaction-rules`: multipart upload field `file`; saves a YAML file and calls the analyzer reload endpoint.

### Presidio service

The analyzer is independently exposed on port `5002`:

- `GET /health` returns `{"status": "ok"}`.
- `POST /analyze` accepts `text`, optional `language`, optional `entities`, and `score_threshold`; it returns entity spans and scores.
- `POST /reload` reloads built-in and custom recognizers.

## Caching Policies

Redis indexes are HASH indexes using `FLOAT32` vectors, configured dimension `1024`, cosine distance, `M=16`, and `EF_CONSTRUCTION=200`. Search accepts the nearest result only when Redis distance is at most `1 - threshold`; the API reports the equivalent cosine similarity as `1 - distance`.

### Invalidation

- TTL invalidation removes an entry when its age reaches `cache_ttl_seconds`.
- Inactivity invalidation uses `last_accessed_at`, falling back to `created_at`, and removes idle entries after `cache_inactivity_seconds`.
- Hit-count invalidation removes entries where `hit_count < cache_min_hit_count`.

Invalidation loops run for TTL and hit-count caches at `cache_invalidation_interval`. The inactivity cache loop uses `cache_inactivity_seconds` as its sleep interval.

### Eviction

Eviction runs only when a cache exceeds `cache_max_size`.

- FIFO removes the oldest `created_at` entries.
- LFU removes the entries with the smallest `hit_count`.
- LRU removes the oldest effective access time, using `last_accessed_at` or `created_at`.

The three eviction loops sleep for `cache_eviction_interval`.

## Privacy and Redaction

The query processor calls Presidio with English text. Sensitive types recognized by the application include `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `IBAN_CODE`, `IP_ADDRESS`, `MEDICAL_LICENSE`, `EMPLOYEE_ID`, and `CONFIDENTIAL_PROJECT`.

For a sensitive query:

1. No embedding is generated.
2. Redis lookup and Redis insertion are skipped.
3. The original query is sent to the configured LLM.
4. Local redaction replaces analyzer spans with `<REDACTED>` for the intended observability record.

This design protects cached and intended stored query content, but it does not hide the original query from the LLM provider. Use a trusted provider, encrypted transport, access controls, retention limits, and provider-side log scrubbing in production.

### Custom YAML recognizers

Files in `custom_recognizers/` are loaded at analyzer startup. The upload endpoint requires a basename matching `[A-Za-z0-9._-]+`, a `.yaml` or `.yml` extension, a size of at most 1 MiB, and a top-level `recognizers` key.

```yaml
recognizers:
  - name: EmployeeIDRecognizer
    supported_language: en
    supported_entity: EMPLOYEE_ID
    patterns:
      - name: employee_id_pattern
        regex: "\\bEMP-\\d{5}\\b"
        score: 0.95
```

Recognizer entries may define regex `patterns` and/or a `deny_list`. Uploading a valid file triggers a complete analyzer reload. An example is [custom_recognizers/gemini-code-1785749213179.yaml](custom_recognizers/gemini-code-1785749213179.yaml).

## Persistence and Startup

`cache_entries` stores UUID, question, pgvector embedding, embedding model and dimension, answer, namespace, creation time, hit count, hit/access timestamps, and invalidation/eviction state and strategy timestamps.

Production cache rows use namespaces `ttl`, `inactivity`, `hit_count`, `fifo_eviction`, `lfu_eviction`, and `lru_eviction`. On startup, PostgreSQL returns non-evicted and non-invalidated rows matching the embedding model and dimension, ordered by hit count; each cache hydrates up to 10 rows. Cache deletion and shutdown cleanup affect Redis only.

When `delete_on_shutdown=true`, the lifespan deletes all six production Redis prefixes during shutdown. The fake benchmark cache is not deleted by this shutdown flag. Background tasks are cancelled and Redis/PostgreSQL clients are closed during shutdown.

## Observability

FastAPI exposes an unprotected Prometheus endpoint at `GET /metrics`. HTTP response latency is recorded as `semantic_cache_response_latency_seconds` with method, path, and status labels. The semantic-caching metrics module also tracks cache requests, hits, misses, PII bypasses, lookup latency, embedding latency, invalidations, evictions, and per-cache size.

Prometheus scrapes:

- `prometheus:9090` every 5 seconds.
- `litellm:4000/metrics/`.
- `fastapi:8000/metrics`.

Grafana is included as a dashboard host but no dashboard provisioning is included in this repository.

## Benchmarks

### Quora duplicate-question benchmark

```bash
python -m benchmark.main
```

`benchmark/main.py` loads the first 10,000 rows from `benchmark/datasets/train.csv`, logs in to the API, uses `/chat/fake_ask`, runs question pairs sequentially, and reports accuracy, precision, recall, F1, and confusion-matrix counts. The sequential runner clears the fake cache before each pair and submits both questions.

### LMSYS worker benchmark

```bash
python -m benchmark.run_workers
```

This loads at most 100 queries from `benchmark/datasets/lmsys-chat-1m` and evaluates the cache endpoints sequentially with one worker. The worker runner and dataset loader live under `benchmark/workers/`. Each request records its status, cache-hit flag, and latency. The current run is summarized below; hit and miss latency statistics are calculated from the successful requests in `results.txt`.

#### Latency and cache-hit comparison

| Policy | Requests | Hit rate | Hit mean | Miss mean | Hit p95 | Miss p95 | Mean speedup |
|---|---:|---:|---:|---:|---:|---:|---:|
| TTL | 99 | 19.19% | 1.470s | 47.805s | 4.637s | 131.254s | 32.5x |
| Inactivity | 100 | 19.00% | 1.821s | 74.575s | 3.874s | 200.998s | 41.0x |
| Hit Count | 100 | 33.00% | 1.581s | 22.985s | 3.037s | 71.317s | 14.5x |

The cache has a clear latency effect: successful cache hits take about 1.5 to 1.8 seconds on average, while misses take about 23 to 75 seconds. Hit Count performed best overall in this run because it had the highest hit rate, 33%, and the lowest mean miss latency, 22.985 seconds. TTL had a similar hit rate to Inactivity but lower miss latency. Inactivity shows the largest relative speedup on a hit, 41.0x, although its misses were the slowest on average and at p95.

The TTL analysis contains 99 parsed requests even though the benchmark was configured for 100 queries; this is retained as recorded in `results.txt` and should be checked before treating the policy results as a strict equal-sample comparison. Mean speedup is calculated as `miss mean / hit mean`; p95 is the 95th percentile latency.

#### Estimated savings

The request log can also provide hit counts, hit rates, and an approximate latency saving. The estimate uses the p50 miss latency as the uncached LLM baseline and the p50 hit latency as the cache baseline:

$$
	ext{latency\_saved} \approx \text{hits} \times (\text{p50 miss latency} - \text{p50 hit latency})
$$

| Policy | Requests | Hits | Hit rate | Hit p50 | Miss p50 | Estimated latency saved |
|---|---:|---:|---:|---:|---:|---:|
| TTL | 100 | 19 | 19% | 1.022s | 35.199s | 649.4s (10.8 min) |
| Inactivity | 100 | 19 | 19% | 1.693s | 52.497s | 965.3s (16.1 min) |
| Hit Count | 100 | 33 | 33% | 1.403s | 15.698s | 471.7s (7.9 min) |

The TTL request summary reports 100 requests and 19 hits, but query 1's request-level line is absent from the log excerpt; its p50 latency values therefore use the 99 visible request lines. These latency savings are estimates because the log does not record the uncached LLM latency that each individual hit would have incurred.
### Threshold results

Stored results and charts are under `threshold_tuning/` and `visualizations/`. The included evaluation covers thresholds `0.50` through `0.95` in `0.05` increments. The application's production caches use `0.8`, the documented balanced operating point in the stored results. Regenerate charts with:

```bash
python visualizations/visualize_results.py
```

The repository includes charts for performance versus threshold, F1, precision/recall tradeoff, and confusion-matrix counts.

#### Performance across thresholds

![Semantic cache performance versus similarity threshold](threshold_tuning/results_2/performance_vs_threshold.png)

This view compares accuracy, precision, recall, and F1 as the similarity threshold increases.

#### F1 optimization

![F1 score versus similarity threshold](threshold_tuning/results_2/f1_vs_threshold.png)

The best F1 score in the evaluated results is 68.26% at a similarity threshold of 0.80.

#### Precision and recall tradeoff

![Precision recall tradeoff across similarity thresholds](threshold_tuning/results_2/precision_recall_tradeoff.png)

Higher thresholds improve precision but reduce recall, making the choice dependent on the cost of false-positive cache matches versus missed matches.

#### Confusion matrix by threshold

![Confusion matrix counts versus similarity threshold](threshold_tuning/results_2/confusion_matrix_vs_threshold.png)

This chart shows how true positives, false positives, true negatives, and false negatives change across the tested thresholds.

## Testing

Pytest uses the repository root as `pythonpath`, searches under `testing`, and discovers `test_*.py` files and `test_*` functions.

```bash
pytest
pytest testing/unit_tests/
pytest testing/integration_testing/
```

Unit coverage includes authentication security, invalidation strategies, query processing, semantic caching, and utility behavior. Integration tests require the live Docker dependencies. Test doubles are in `testing/fake_components/`.

## Known Implementation Notes

- Chat routes are intentionally unauthenticated; put them behind a gateway, rate limit, quota, or network policy when required.
- Administrative routes are JWT-protected, but `/metrics` and the Presidio service endpoints are not protected by this FastAPI admin dependency.
- The configured embedding dimension is supplied by settings, but `API/lifespan.py` constructs Redis services with dimension `1024`; keep `EMBEDDING_MODEL_DIMENSION` aligned with `1024` unless the lifecycle wiring is changed too.
- The sensitive-query PostgreSQL branch currently constructs a cache entry but calls `save_entry` with the redacted string instead of that entry object. The exception is caught, so the intended redacted observation is not persisted by the current implementation.
- PostgreSQL persistence records cache misses and hit metadata. Eviction and invalidation mark the PostgreSQL row before deleting the Redis key.
- The Compose PostgreSQL initialization scripts run only when the database volume is first created. Remove the volume deliberately when a fresh initialization is required.

## License

MIT.