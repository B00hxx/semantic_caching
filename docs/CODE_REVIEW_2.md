# Code Review #2 — Semantic Caching Middleware

**Reviewer:** Ahmed Elloumi
**Date:** 2026-08-28
**Branch reviewed:** `feat/grafana-observability` (7 commits ahead of `main`, unmerged)
**Review branch:** `review/final-audit`
**Previous review:** `docs/CODE_REVIEW.md` on `review/code-audit-and-improvements`

---

## 0. Scope and method

Everything below was verified against the code on `feat/grafana-observability`, not
inferred from the README. Where I say something is broken, I ran it. Where I say a
number is wrong, I recomputed it from the raw JSON in `threshold_tuning/`.

Branch state at review time:

| Branch | Merged into `main`? |
| --- | --- |
| `feature/add-litellm-integration` | yes |
| `feat/cache-history` | yes |
| `feat/cache-warming-and-metrics` | yes |
| `feat/cache-invalidation-strategy` | yes |
| `feature/cache-eviction` | yes |
| `fix/*` (5 branches) | yes |
| **`feat/grafana-observability`** | **no — this is the review target** |

---

## 1. Status of the three blockers from review #1

| # | Blocker | Status |
| --- | --- | --- |
| 1 | Redaction used as normalisation → distinct users collapse onto one cache key | **Fixed.** `contains_sensitive_data()` now gates the whole path; sensitive requests never touch the vector store. |
| 2 | LLM receives the mutilated query instead of the original | **Fixed.** `semantic_caching.py:204` sends the original `query` to `llm.generate()`. |
| 3 | No namespace/tenant isolation in Redis | **Partially fixed.** The mechanism is there (`TagField("namespace")`, pre-filtered KNN at `redis_service.py:97`) but it is not wired to a caller identity — see BLOCKER-3 below. |

Good work on 1 and 2. The pipeline shape in `get_answers()` is now correct and the
detector/rewriter split is exactly what I asked for.

---

## 2. Blockers

### BLOCKER-1 — The entire test suite fails to run

`README.md` documents `pytest testing/unit_tests/` as the way to test the project.
That command does not complete.

```
$ python -m pytest testing/unit_tests/ -q
E   File "testing/unit_tests/test_invalidation_strategies.py", line 62
E     question="What is Inactivity?",
E   SyntaxError: keyword argument repeated: question
ERROR testing/unit_tests/test_auth_security.py
ERROR testing/unit_tests/test_invalidation_strategies.py
!!!! Interrupted: 2 errors during collection !!!!
```

Three separate faults:

1. **`testing/unit_tests/test_invalidation_strategies.py:57-66`** — a copy-paste
   duplicated the whole kwarg block inside one `CacheEntry(...)` call. Hard
   `SyntaxError`; the module cannot even be imported.
2. **Same file** — zero occurrences of `namespace=` across all 6 `CacheEntry(...)`
   constructions. `CacheEntry.__init__` raises `ValueError("namespace cannot be
   empty")` when it is missing, so every one of these tests fails *after* the syntax
   error is fixed. Fixing the syntax is not enough.
3. **`config.py:2`** — `import ollama` at module top. `API/auth/security.py` imports
   `config`, so `test_auth_security.py` dies with `ModuleNotFoundError: No module named
   'ollama'`. Ollama is now reached through LiteLLM; `OllamaSettings` and
   `ollama_client` are dead code. Drop the import and the class.

Of the modules that *do* collect, 4 more fail:

```
FAILED test_semantic_caching.py::test_semantic_pipeline
FAILED test_semantic_caching.py::test_true_positive
FAILED test_semantic_caching.py::test_false_cache_hit
FAILED test_semantic_caching.py::test_better_threshold
AttributeError: 'FakeEmbedder' object has no attribute 'model_name'
  at semantic_caching/semantic_caching.py:166
```

`CacheEntry` gained `embedding_model` / `embedding_dimension`, but
`testing/fake_components/fake_embedding.py` was never updated to match the `Embedder`
contract. Net result across the suite: **3 passed, 4 failed, 2 collection errors.**

This is the blocker I care about most, because it means none of the invalidation,
eviction, auth, or pipeline work merged over the last three weeks has a green test
behind it. Fix this first — before any new feature.

### BLOCKER-2 — `/stats/get_all_entries` returns 500 on every call

`API/routes/get_all_hot_entries.py:20` reads `entry.ttl_seconds`. `CacheEntry` has no
such attribute (`semantic_caching/cache_entry/cache_entry.py:23-35`). Every request to
this endpoint raises `AttributeError` inside the list comprehension.

**Fix:** delete the field, or compute it from `created_at` + the strategy's TTL. Then
add a test that actually hits the route.

### BLOCKER-3 — "Namespace isolation" is per-strategy, not per-caller

The Redis-side mechanism is correct. The wiring is not. In `API/lifespan.py:139-211`
the namespace is a **constant baked into each cache instance** — `"ttl"`,
`"inactivity"`, `"hit_count"`, `"fifo_eviction"`, `"lfu_eviction"`, `"lru_eviction"`.
`QueryRequest` (`API/schemas/query_request.py:3-4`) carries only `query`. The
`/chat/*` routes are unauthenticated and take no tenant parameter.

So every caller of `/chat/ttl_cache` shares one namespace. The original finding —
"any caller's answer can be served to any other caller" — is still true; the partition
key just moved from *nothing* to *which eviction strategy you picked*, which is not a
security boundary.

**Fix:** namespace must come from the request, and it must be authenticated —
a JWT claim, an API key mapped server-side to a tenant id, or a header validated
against an allowlist. Never a raw client-supplied string, because it feeds a
RediSearch `TAG` filter (see HIGH-4).

### BLOCKER-4 — The PII bypass path writes the unredacted LLM answer to PostgreSQL

`semantic_caching/semantic_caching.py:200-217`:

```python
redacted_query = self.query_processor.redact(query=query, analyzer_results=spans)
answer_by_llm = await self.llm.generate(query=query)   # original query — correct
entry = CacheEntry(
    question=redacted_query,   # redacted
    answer=answer_by_llm,      # NOT redacted
    ...
)
await self.postgres.save_entry(entry)
```

The question is scrubbed; the answer is not. LLMs routinely echo the input back —
*"Hello Ahmed, based on a salary of 84,000 TND your bracket is…"*. The PII you removed
from column `question` lands in column `answer` of the same row. The redaction buys
nothing.

**Fix:** run the analyzer over `answer_by_llm` and redact it before persisting, or
drop the row entirely and persist only non-content metadata (timestamp, entity types
detected, latency, token counts). The second option is cheaper and is what you
actually need for observability.

---

## 3. High

### HIGH-1 — README documents privacy behaviour the code does not implement

`README.md` states, twice, that bypass observations are stored with `namespace = NULL`
and are therefore excluded from hydration. The code sets `namespace="bypassed"`
(`semantic_caching.py:213`), and `CacheEntry.__init__` **raises** on a falsy namespace,
so `NULL` is not even reachable.

Functionally the rows are still excluded from `get_top_entries()` (nothing queries
`"bypassed"`), so there is no live leak — but a privacy claim in the README that does
not match the code is the kind of thing that gets caught in an audit, not a review.
Make the code match the doc or the doc match the code. Also: `"bypassed"` discards the
caller's real namespace, so bypass observations from every tenant land in one bucket.

### HIGH-2 — Six production caches, one per strategy

`lifespan.py` constructs six `SemanticCaching` instances, six `RedisService` instances,
six HNSW indexes, and six background loops — one per invalidation/eviction strategy.
`chat.py` exposes six corresponding endpoints. `delete.py` and `stats.py` each
enumerate all six by hand.

This is a benchmark harness living in the production path. A deployment runs **one**
cache with **one** configured strategy. Cost today: 6× index memory, 6× warming
queries at boot, 6 always-on loops, and every new route has to be written six times.

**Fix:** one cache. Strategy selected from config (`CACHE_INVALIDATION_STRATEGY`,
`CACHE_EVICTION_STRATEGY`). Move the six-way comparison into `benchmark/`, where it
belongs — spin the variants up inside the benchmark process, not inside the API.

### HIGH-3 — No timeouts on the LLM or embedding calls

`lite_llm_service.py:20` — `timeout=None`. `litellm_embedding_service.py:9-12` —
no timeout, so it inherits the SDK default of 600 s. `benchmark/workers/worker.py:9` —
`timeout=None` again.

For middleware that sits in front of every LLM call, an upstream stall means requests
pile up until the worker pool is exhausted. This is the classic way a cache takes down
the service it was added to protect.

**Fix:** explicit timeouts everywhere (a few seconds for embeddings, tens of seconds
for completions), plus a bounded retry. Make them configurable.

### HIGH-4 — Cache failures fail the request instead of degrading to pass-through

`QueryProcessor.process()` raises `RuntimeError` when the analyzer is unreachable
(`query.py:34-37`). `get_answers()` does not catch it. Redis errors propagate the same
way. If Redis or Presidio is down, `/chat/*` returns 500 — the LLM is healthy and the
user still gets an error.

A cache must be *optional* at runtime. Decide and document the policy per dependency:

- **Redis down** → fail open. Skip lookup, call the LLM, skip the store. Log + metric.
- **Presidio down** → fail closed *toward the LLM*, not toward the user: treat the
  query as sensitive, bypass the cache, call the LLM with the original query. Never a
  500, and never a cache write you could not screen.

Add a `semantic_cache_degraded_total{dependency,reason}` counter so Grafana shows it.

Related: `redis_service.py:97` interpolates the namespace into a RediSearch `TAG`
filter via a query param. Params are not escaped for tag syntax, so a namespace
containing `-`, `{`, `}`, or `|` is tokenised and the filter silently matches the wrong
set. Once namespaces are caller-supplied (BLOCKER-3) this becomes a filter-bypass.
**Fix:** `TagField("namespace", separator="|")`, and validate namespaces against
`^[A-Za-z0-9_]{1,64}$` at the edge.

### HIGH-5 — `/stats/postgres_entries` can never return anything

`API/routes/top_k_entries.py:9-14` hardcodes `namespace="default"`,
`embedding_model="qwen-embedding"`, `embedding_dimension=1024`. No cache in
`lifespan.py` writes namespace `"default"` — they write `ttl`, `inactivity`,
`hit_count`, `fifo_eviction`, `lfu_eviction`, `lru_eviction`, `fake_test`, `bypassed`.
The query matches zero rows, always. Take namespace and model as request parameters.

### HIGH-6 — Admin tokens effectively never expire, and the plaintext password is required in config

`API/auth/security.py:16` — `ACCESS_TOKEN_EXPIRE_MINUTES = 3000000`. That is 5.7 years.
There is no revocation list, so a leaked admin token is valid until the signing key is
rotated. Bring it to 15–60 minutes and add a refresh flow.

`config.py:99` — `admin_password: str` is a **required** setting sitting next to
`admin_password_hash`. Nothing reads it (`auth.py` verifies against the hash). It only
guarantees the plaintext admin password is present in `.env` and in the process
environment. Delete the field.

### HIGH-7 — Invalidation and eviction load the whole cache into memory every cycle

`invalidate_entries()` and `evict_entries()` both call
`vector_store.get_all_entries()`, which `SCAN`s the keyspace, `HGETALL`s every entry,
and deserialises every 1024-dim `float32` embedding into a Python list — ~4 KB of
bytes becoming ~32 KB of Python floats per entry. At 100k entries that is a
multi-gigabyte allocation on a timer, and it blocks the event loop while it runs.

`get_size()` has the same shape: a full `SCAN` just to count.

**Fix:** for TTL, use Redis-native `EXPIRE` at write time and delete the sweep. For the
metadata-driven strategies, keep a per-namespace sorted set (`ZADD` keyed by
`last_accessed_at` / `hit_count`) and pull only the candidates. Track size with a
counter key, not a scan. If you keep the sweep as a fallback, make it batched and
`return_fields`-limited so embeddings are never fetched.

---

## 4. Medium

**MED-1 — `lifespan.py:79` and `:82` both call `settings.postgres_service.get_service()`.**
Two `asyncpg` pools are created; the first is overwritten and never closed. Connections
leak for the process lifetime. Delete line 79.

**MED-2 — `lifespan.py:280`, `load_dotenv()` after `yield`.** Runs at shutdown. Dead
code — and if it were meant to make `delete_on_shutdown` reloadable, it does not work,
because `settings` was already constructed at import time.

**MED-3 — `/delete/cache` does not delete.** It empties Redis but leaves every row in
PostgreSQL. On the next boot `initialize()` re-hydrates the top-K entries and the
"deleted" answers are served again. Either cascade the delete to PostgreSQL or rename
the endpoint to `/cache/flush` and say so in the README.

**MED-4 — Embedding dimension is hardcoded in three places.** `lifespan.py:66-74`
passes `dimension=1024` to every `RedisService` while the embedder reads
`EMBEDDING_MODEL_DIMENSION` from the environment. `top_k_entries.py:11` hardcodes
`1024` again. Change the model and the HNSW index silently mismatches the vectors.
Read it from settings in one place.

**MED-5 — Raw detected PII is logged at INFO.** `semantic_caching.py:138-144` logs
`query[span["start"]:span["end"]]` — the matched substring itself. It sits in the
*non*-sensitive branch, so it only prints entities outside `SENSITIVE_ENTITIES`
(`DATE_TIME`, `LOCATION`, `NRP`, `URL`) — which are still personal data under GDPR, and
they go to stdout, to Docker's log driver, and to anything scraping it. Log
`entity_type` and `score`, never the text.

**MED-6 — `postgres/schema.sql` has no indexes.** `get_top_entries()` filters on
`(embedding_model, embedding_dimension, namespace, evicted, invalidated)` and sorts by
`hit_count DESC`. That is a sequential scan on every boot, growing with history.
Add a composite index. The `embedding vector` column has no dimension constraint and
no `hnsw`/`ivfflat` index either — fine while nothing does vector search in Postgres,
worth deciding before it does.

**MED-7 — Secrets and hardening in `docker-compose.yml`.**
`GF_SECURITY_ADMIN_PASSWORD=admin` (line 149); pgAdmin `demo@example.com` / `secret`
with `MASTER_PASSWORD_REQUIRED: 'False'` published on `:5050` (lines 44-47);
`no-new-privileges:false` on the API container (line 110) — that flag exists to be
`true`; Redis has no password, no `maxmemory`, and no `maxmemory-policy`, which for a
cache is the one setting you cannot omit; the API bind-mounts the whole repo
(`.:/app`, line 136), `.env` included. No healthchecks anywhere, and `fastapi`
`depends_on` omits `postgres` and `litellm` even though `lifespan` connects to both at
startup — `docker compose up` is a boot race.

**MED-8 — Naming: `cosine_distance` is a similarity.** `redis_service.py:120` returns
`score = 1 - score`, i.e. cosine *similarity*, and `get_answers()` returns it under the
key `"cosine_distance"`. Anyone thresholding on that field downstream will invert their
comparison. Rename to `similarity`.

**MED-9 — Redis entries never carry `evicted` / `invalidated`.** `add_entry()` does not
write them and `get_all_entries()` does not read them, so `entry.invalidated = True` at
`semantic_caching.py:65` mutates an object that is discarded a line later. It works only
because a delete follows immediately. Fragile — anything that stops short of the delete
leaves a stale entry servable.

**MED-10 — `semantic_caching.py:188`, `identifier.split(":", 1)[-1]`.** With
`prefix="lite_ttl"` this yields the UUID, correctly. With any prefix containing a colon
it yields `"rest:of:the:uuid"` and the Postgres update silently matches nothing. Use
`rsplit(":", 1)[-1]`.

**MED-11 — `save_entry` has no `ON CONFLICT`.** Cache-warming re-inserts rows that
already exist if an entry is ever re-created with the same id, and the whole call is
wrapped in a bare `except Exception: logger.exception(...)`, so a genuine persistence
outage looks identical to a duplicate key. Add `ON CONFLICT (id) DO UPDATE` and narrow
the except.

---

## 5. Benchmark and threshold study

The threshold sweep is the piece of evidence the whole project rests on, so I checked
the arithmetic rather than the prose.

### FINDING — The 0.75 row is corrupt, and it is the row the README recommends

From `threshold_tuning/results_2/final_results.json` (also duplicated verbatim at
`visualizations/final_results.json`):

| Threshold | TP | FP | FN | Recall |
| --- | --- | --- | --- | --- |
| 0.65 | 2412 | 2270 | 1299 | 65.00% |
| 0.70 | 2379 | 1949 | 1332 | 64.11% |
| **0.75** | **3056** | **2185** | **655** | **82.35%** |
| 0.80 | 2755 | 1606 | 956 | 74.24% |
| 0.85 | 2253 | 968 | 1458 | 60.71% |

Raising a similarity threshold can only ever make the matcher *stricter*. TP is
monotonically non-increasing and FP is monotonically non-increasing, by construction —
every pair that clears 0.75 also cleared 0.70. The data violates both at exactly one
point: TP jumps +677 and FP jumps +236 going from 0.70 to 0.75, then falls again at
0.80. Recall does the same. That is not a real operating point; it is contamination.

The 100-pair pilot (`threshold_tuning/results_1/results.json`) is perfectly monotone —
TP `27, 27, 27, 27, 27, 26, 23, 21, 15, 8` — which confirms the harness *can* produce
clean data and that something specific went wrong in the 10k run. Most likely the cache
was not flushed between threshold sweeps, so the 0.75 pass inherited entries written
during an earlier, looser pass.

**Consequences:**

- README's headline — *"Peak F1 Score (Threshold 0.75)… highest F1 (68.28%) with strong
  recall (82.35%)"* — rests entirely on the bad row. Delete that claim.
- Among the rows that *are* self-consistent, F1 peaks at **0.80 (68.26%)** and accuracy
  peaks at **0.85 (75.74%)**. The 100-pair pilot also puts the peak at 0.85. The
  currently deployed `threshold=0.8` is defensible; the *justification* in the README is
  not.
- **Re-run the sweep with a hard cache flush between thresholds**, and add a monotonicity
  assertion to the harness so a contaminated run fails loudly instead of becoming a
  slide.

### The precision number deserves a sentence in the README

At the recommended threshold, precision is **63%**. In cache terms that means roughly
**one in three cache hits serves an answer to a question the user did not ask.** That
may well be acceptable for FAQ-style traffic and unacceptable for anything
transactional — but the README currently frames it as "optimal balance" without saying
what the failure mode looks like to a user. State it plainly and recommend 0.90+
(78% precision) as the conservative default.

### The benchmark is still single-threaded

`benchmark/workers/runner.py:18-41` — `WorkerRunner` constructs exactly **one**
`Worker` and iterates queries in a plain `for` loop, awaiting each. Despite the naming,
there is no concurrency. This is why 10k pairs "takes too long": you are paying full
LLM latency serially, ~N × 2 s.

**Fix:** N workers behind an `asyncio.Semaphore`, results gathered with
`asyncio.gather`. Make N a parameter and report it alongside the numbers — throughput
without a concurrency level is not a measurement.

Also: `httpx.AsyncClient(timeout=None)` (`worker.py:9`) means one hung request stalls
the entire run with no way to notice.

### Still no cost model — this is the one thing I asked for that did not move

The project's stated goal is *"LLM API Cost and Latency Reduction"*. There is nothing
in the repo that computes either. `run_workers.py` reports hit rate and nothing else.

Minimum viable version:

```
tokens_saved   = Σ (prompt_tokens + completion_tokens) over cache hits
cost_saved     = tokens_saved × provider_rate_per_1k / 1000
latency_saved  = Σ (p50_llm_latency − p50_cache_latency) over hits
net_saving     = cost_saved − (embedding_calls × embedding_rate) − infra_cost
```

That last term matters and is the part people forget: **every miss pays for an
embedding call on top of the LLM call**, so a low-hit-rate workload is strictly more
expensive with the cache than without it. Compute the break-even hit rate and put it
in the README — that single number is the business case for the whole project.

LiteLLM already returns `usage` on every response and you already scrape its Prometheus
callback (`config.yaml:20-21`). Two counters —
`semantic_cache_tokens_saved_total` and `semantic_cache_cost_saved_usd_total` — and a
Grafana panel would close this. Add rates to config, not to code.

Also missing from the benchmark: a **no-cache baseline** run. Without it there is no
before/after, and no way to show the latency win you asked about.

### Dataset drift

`run_workers.py` loads **lmsys-chat-1m** (`load_lmsys_queries`), while
`benchmark/main.py`, `benchmark/quora_questions/`, `benchmark/metrics/`, and the whole
README benchmark section are **Quora**. Two harnesses, one dataset each, and the new one
computes no precision/recall at all. Pick one path, delete the other, and say in the
README which dataset produced which table.

---

## 6. Low / nits

- `README.md` says `qwen2.5:0.5b`; `config.yaml:4` says `ollama/qwen:0.5b`.
- `semantic_caching/presidio_analyzer/prisidio_reload_service.py` — typo in filename
  (`prisidio` → `presidio`).
- `semantic_caching.py:158` — `"No approprite match"`.
- `semantic_caching.py:156` — `if response_from_vector_store == None` → `is None`.
- `semantic_caching.py:68` / `:107` — `id = entry.id` shadows the builtin for no reason.
- `benchmark/test.py` and `test.py` at repo root — scratch files, not tests; `pytest.ini`
  sets `python_files = test_*`, so root `test.py` is outside `testpaths` but the name is
  still confusing. Delete or rename.
- `map.txt` — I asked for this to be deleted in review #1. Still on `main`. (It is gone
  on this branch — make sure that survives the merge.)
- `docker-compose.yml:174` — `presidio-rules` volume is declared and never mounted.
- `eviction_loop` (`lifespan.py:42-51`) checks `get_size()` and then `evict_entries()`
  re-checks it — two full scans per cycle instead of one.
- No `.env.example` in the repo. Every new contributor has to reverse-engineer the
  required variables out of `config.py`, and two of them (`jwt_secret_key`,
  `admin_username`) are required with no default, so the app will not boot without them.

---

## 7. Suggested order of work

1. **BLOCKER-1** — make the test suite run and go green. Nothing else gets reviewed
   until this is done; it is three small fixes (`syntax`, `namespace=`, `import ollama`)
   plus updating `FakeEmbedder`.
2. **BLOCKER-2** — one-line fix, and add the route test that would have caught it.
3. **BLOCKER-4** — redact the answer, or stop persisting content on the bypass path.
4. **BLOCKER-3 + HIGH-4** — request-scoped authenticated namespace, with charset
   validation and `separator="|"` on the tag field.
5. **HIGH-3 + HIGH-4 (degradation)** — timeouts, and cache failures that degrade to
   pass-through instead of 500.
6. **Re-run the threshold sweep** with a flush between passes and a monotonicity
   assertion. Correct the README table and the recommendation.
7. **Cost model + no-cache baseline + parallel benchmark workers.** This is the
   deliverable the project is named after.
8. **HIGH-2** — collapse the six caches to one config-driven cache; move the comparison
   into `benchmark/`.
9. Everything in §4 and §6.

---

## 8. What is genuinely good

Worth saying, because a review that only lists faults is not an accurate picture:

- The detector/bypass split in `get_answers()` is exactly right, and it was the hardest
  of the three original blockers to get correct.
- The strategy pattern for invalidation and eviction is clean — small, single-purpose
  classes behind an ABC, easy to test and easy to add to. That is the right structure.
- Moving to LiteLLM was the correct call. Deleting the hand-rolled Ollama wrappers in
  favour of one gateway is a real simplification, and it makes provider swaps a config
  change.
- Prometheus metric naming and label cardinality in `metrics.py` are sane — low
  cardinality, `_total` suffixes, histograms for latency. No cardinality bombs.
- The README is genuinely good: architecture diagram, endpoint contract, env table,
  quick start. The problem is that parts of it describe intent rather than the code —
  which is a fixable problem and a much better one to have than no README.
- Turnaround on review #1 was fast and two of three blockers were fixed properly rather
  than papered over.
