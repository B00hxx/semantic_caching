# Intern Guide — Semantic Cache for LLM Cost & Latency Reduction

Read this first. `README.md` tells you **how to run** the stack. This file tells you
**what we are building, why each piece exists, and what still has to be built** to
hit the project deliverables.

- Project: Elyadata / Platform & Sovereign AI — Project #27
- Duration: 8 weeks
- Topic: LLM cost optimization / semantic caching middleware

---

## 1. The problem in one paragraph

In production, a large share of LLM API calls are **semantic duplicates**: same
intent, different wording. "What is your refund policy?" and "how do I get my money
back?" are one question paid for twice. An exact-match (hash) cache never catches
those, because the strings differ. A **semantic cache** catches them by comparing
*meaning*: embed the query into a vector, search for a stored vector that is close
enough, and return the stored answer instead of calling the LLM.

Published results are a 30–70% cost cut and a large p95 latency drop. The catch, and
the whole engineering difficulty of this project:

> **A false cache hit is worse than no cache at all.**

A wrong-but-confident answer served from cache is a correctness bug you cannot see in
your latency graph. Every design decision below is a trade between *hit rate* (money
saved) and *precision* (answers still correct).

---

## 2. Mental model: the pipeline

```
query ──► PII redaction ──► embed ──► vector search ──► hit? ──► return cached answer
                                                          │
                                                          └─ miss ─► LLM ─► store ─► return
```

Four knobs decide everything:

| Knob | Where it lives now | What it trades |
|---|---|---|
| **Embedding model** | `semantic_caching/embedding_services/ollama_embedding.py` | Retrieval quality vs embedding latency/cost |
| **Similarity threshold** | `SemanticCaching(threshold=...)`, set in `API/lifespan.py` | Hit rate vs false-hit rate |
| **Invalidation / TTL** | `CacheEntry(ttl_seconds=3600)` | Freshness vs hit rate |
| **Safety filter** | `semantic_caching/query.py` (Presidio) | Privacy vs hit rate |

Everything else is plumbing around those four.

---

## 3. Vocabulary you must be precise about

Sloppiness here is the #1 source of bugs in this codebase.

- **Embedding** — a fixed-length float vector representing meaning. Our Ollama model
  `qwen3-embedding:0.6b` returns **1024 dims**. That number is hardcoded in
  `API/lifespan.py` and in the Redis index schema; if you change the model you must
  change both, and *drop the old index* — vectors from two different models are not
  comparable.
- **Cosine similarity** — `1.0` = identical direction, `0.0` = unrelated.
- **Cosine distance** — what Redis actually returns in the `score` field:
  `distance = 1 - similarity`. So `0.0` = identical, and **lower is better**.
  In `redis_service.py` the accept test is `score <= 1 - threshold`, i.e.
  "similarity ≥ threshold". Read that line twice before touching it.
- **HNSW** — Hierarchical Navigable Small World, the approximate-nearest-neighbour
  index Redis uses (Malkov & Yashunin, 2018). *Approximate*: it may miss the true
  nearest neighbour. `M` and `EF_CONSTRUCTION` in `create_index()` trade index build
  cost against recall.
- **Hit / miss** — cache served vs LLM called.
- **True positive / false positive** — a hit that was *correct* vs a hit on a query
  that was **not** a real duplicate. False positives are the enemy. Precision,
  recall and F1 in `benchmark/quora_questions/test_over_quora.py` are computed
  against the Quora `is_duplicate` ground-truth label.
- **PII** — personally identifiable information. Presidio *analyzes* (finds spans)
  then *anonymizes* (replaces them). Two separate HTTP services, two calls per query.

---

## 4. Code tour — what each module is responsible for

```
API/                      HTTP surface (FastAPI)
  app.py                  app object; nothing else belongs here
  lifespan.py             ⚠ the wiring/DI root: builds clients, models, cache, thresholds
  routes.py               /ask, /fake_ask, /stats, /delte_cache, /upload-redaction-rules
  schemas/                request models (there are no response models yet — see review)

semantic_caching/         the library. No FastAPI imports allowed in here.
  semantic_caching.py     orchestrator: redact → embed → search → (LLM + store) → return
  query.py                QueryProcessor: Presidio analyze + anonymize client
  cache_entry.py          what we store: question, embedding, answer, created_at, ttl
  llm_services/           LLM abstract base + Ollama impl + fake impl
  embedding_services/     Embedder abstract base + Ollama impl
  vector_store_services/  VectorStore abstract base + Redis (HNSW) impl
  presidio-analyzer/      our own analyzer container: loads custom YAML recognizers
  timing.py               timing decorator (sync only — does not work on coroutines)

benchmark/
  worker.py               async HTTP client that fires queries and records latency
  execute_worker.py       throughput/hit-rate run → results.json
  questions.py            hand-written prompt set
  quora_questions/        correctness run: Quora duplicate pairs → precision/recall/F1

testing/
  fake_components/        FakeLLM / FakeEmbedder / FakeRedis (3-dim vectors, hand-picked)
  unit_tests/             fast, no network — threshold behaviour
  integration_testing/    needs real Redis + Ollama running
```

The abstract base classes (`LLM`, `Embedder`, `VectorStore`) are the important design
decision in the repo: they are what makes "pluggable embedding models and vector
stores" (a stated deliverable) possible. **Any new backend goes behind those
interfaces — never import `redis` or `ollama` inside `semantic_caching.py`.**

---

## 5. How to run it (short version)

```bash
docker compose up --build -d
# first run only: pull the models into the ollama container
docker exec -it ollama ollama pull qwen2.5:0.5b
docker exec -it ollama ollama pull qwen3-embedding:0.6b

curl -X POST localhost:8000/ask -H 'content-type: application/json' \
     -d '{"query":"what is the capital of france?"}'
# repeat with "what is France'\''s capital?" → expect cache_hit: true
```

Tests:

```bash
pytest testing/unit_tests/          # fast, no services needed
pytest testing/integration_testing/ # needs Redis + Ollama up
```

Inspect the cache in RedisInsight at <http://localhost:5540> (keys are `cache:<uuid>`,
index is `cache_index`; try `FT.INFO cache_index`).

---

## 6. Deliverables vs where we actually are

The five deliverables from the project brief, honestly scored:

| Deliverable | Status | Gap |
|---|---|---|
| Cache library with **pluggable** embedding models and vector stores | 🟡 partial | Interfaces exist, but only **one** real embedder (Ollama) and **one** store (Redis). No `sentence-transformers`, no Qdrant/FAISS, no LiteLLM provider abstraction. |
| Benchmark: hit rate **vs correctness** on public traffic | 🟡 partial | Quora pairs give precision/recall/F1 — good. But no LMSYS-Chat-1M / WildChat / ShareGPT run, i.e. no *real traffic* distribution, and no cost metric (tokens saved × price). |
| **Threshold-tuning study** | 🔴 missing | Threshold is a constant in `lifespan.py`. Nothing sweeps it. This is the single highest-value missing artifact: one script, one curve — precision/recall/hit-rate vs threshold. |
| **Cache invalidation strategy comparison** | 🔴 missing | Only a fixed 3600 s TTL, hardcoded in `CacheEntry`. No LRU/LFU, no max-size eviction, no per-entry invalidation, no model-version namespacing. |
| **Production integration recipe** | 🔴 missing | Current Docker setup is dev-only (`--reload`, whole repo bind-mounted, root user). No auth, no metrics endpoint, no single-flight, no graceful degradation when Redis is down. |

Read `docs/CODE_REVIEW.md` for the concrete bug list behind that table, ordered by
severity, with file and line references. The blockers (wrong answers, container
escape) are already fixed on this branch and listed at the top of that file; work
top-down through what is left.

One consequence to keep in mind while benchmarking: the fake-LLM pipeline
(`/fake_ask`) now writes to its own index (`bench:` / `bench_index`), so benchmark
traffic no longer pollutes `/ask`. `/stats` still reports only the main index.

---

## 7. Suggested 8-week shape

Weeks are a guide, not a contract. Each week ends with something committed and
measurable — a number or a plot, not "it works on my machine".

1. **Baseline & measurement.** Make the pipeline honest: response model, real
   server-side latency breakdown (redact / embed / search / LLM), cost counter
   (tokens in+out per miss, tokens saved per hit). You cannot tune what you do not
   measure.
2. **Threshold study.** Make threshold a request/env parameter. Sweep it over Quora
   pairs. Produce the precision/recall/F1/hit-rate curve and *pick* an operating
   point with a written justification.
3. **Real traffic.** Replay LMSYS-Chat-1M or WildChat. Report hit rate on real
   duplicate distribution, not on a curated pair set. Expect much lower hit rates —
   that is the interesting finding.
4. **Pluggability.** Add a second embedder (`sentence-transformers`, e.g.
   `all-MiniLM-L6-v2`) and a second store (Qdrant). Same benchmark, three
   configurations, one table. Now the interfaces have earned their existence.
5. **Invalidation.** Implement and compare: fixed TTL, sliding TTL on hit, LRU with a
   max-entry cap, and explicit model-version namespacing. Metric: hit rate vs
   staleness vs memory.
6. **Safety.** The cache-bypass-on-PII behaviour is already in place (review finding
   #1: redact-and-cache leaked one caller's answer to another). Your job is to measure
   its cost — what fraction of real traffic gets bypassed, and what that does to the
   hit rate — and to handle the failure modes: analyzer down (fail closed: bypass, do
   not cache), per-entity-type policy, and whether a redacted query should reach the
   provider at all.
7. **Hardening.** Single-flight/request coalescing to kill the cache stampede,
   graceful degradation when Redis or the analyzer is down, auth on destructive
   endpoints, non-root container, healthchecks, `/metrics`.
8. **Write-up.** Compare against GPTCache as reference implementation. Numbers,
   plots, threshold recommendation, invalidation recommendation, integration recipe.

---

## 8. Working rules

- **Never let a false hit slip through silently.** Every benchmark that reports a hit
  rate must report a precision number next to it. A hit-rate-only graph is a lie.
- **One measurement, one commit.** If a change moves a number, put the before/after in
  the commit body.
- **`semantic_caching/` stays framework-free.** No FastAPI, no HTTP, no globals. That
  is what lets us swap Redis for Qdrant in week 4 without touching the orchestrator.
- **Prefer `logging` over `print`.** There are prints on the hot path right now
  (including one that echoes the user query to stdout).
- **Big data files do not go in git.** `benchmark/datasets/train.csv` is 61 MB and is
  committed; new datasets get a download script instead.
- **Do not trust a test that cannot fail.** `assert x is False or x is True` is not a
  test (it exists today — see the review).

## 9. Reference reading

- Bang (2023), *GPTCache: An Open-Source Semantic Cache for LLM Applications*, NLP-OSS
  — our reference implementation; read how they combine an exact-match pre-check with
  vector search, and how they handle eviction.
- Chen et al. (2023), *FrugalGPT*, arXiv:2305.05176 — cost-reduction framing.
- Malkov & Yashunin (2018), *HNSW*, IEEE TPAMI — the index Redis uses.
- Karpukhin et al. (2020), *Dense Passage Retrieval*, EMNLP — why embedding choice
  dominates retrieval quality.
- LiteLLM caching docs — provider abstraction we still owe.

Datasets: LMSYS-Chat-1M, WildChat-1M, ShareGPT (real traffic); MS MARCO, Quora
Question Pairs (similarity ground truth).
