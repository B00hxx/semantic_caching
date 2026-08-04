# Code Review — `semantic_caching` @ `a4636a0`

Reviewed: full tree (~1.6k LOC Python), branch `review/code-audit-and-improvements`
off `main`.

**Overall:** the architecture is right. The abstract `LLM` / `Embedder` /
`VectorStore` interfaces, the async-throughout design, the fake components for unit
tests, and the separation of the Presidio analyzer into its own container are all
good calls that will pay off in weeks 4–6 of the project. The problems below are
almost all in the *edges* — schema stability, sharing of state, benchmark
methodology, and failure handling — not in the core idea.

Findings are ordered by severity. Each has a location, why it is wrong, and the fix.
Severity: 🔴 blocker / 🟠 major / 🟡 minor / 🔵 improvement.

---

## Correctness & privacy

### 🔴 1. Redaction makes distinct queries collide → one user gets another user's answer

`semantic_caching/semantic_caching.py:24-32`, `semantic_caching/query.py:27-38`

The query is redacted **before** embedding, and the *redacted* text is what gets
embedded, cached, and sent to the LLM. Two different users produce byte-identical
redacted queries:

```
"my card is 4111 1111 1111 1111, is it charged?"  →  "my card is <REDACTED>, is it charged?"
"my card is 5500 0000 0000 0004, is it charged?"  →  "my card is <REDACTED>, is it charged?"
```

The second query is a cache hit on the first, and receives an answer computed for a
*different* card. Every anonymizer entity maps to the same `<REDACTED>` string, so
this applies to names, emails, account numbers, employee IDs — the exact values that
change the correct answer.

The project brief asks for "safety filters (**don't cache sensitive queries**)", which
is the correct behaviour: if the analyzer returns any span, **bypass the cache** — no
lookup, no store — and pass the original query to the LLM. If you keep the
redact-and-cache path, it must be opt-in per entity type and must never apply to
entities that carry answer-changing information.

Fix: `QueryProcessor.process()` returns `(text, spans)`. `SemanticCaching.get_answers`
skips both `search()` and `add_entry()` when `spans` is non-empty, and returns
`{"cache_hit": false, "cache_bypassed": true, ...}`.

### 🔴 2. `/ask` and `/fake_ask` share one cache namespace → `"x"` served to real users

`API/lifespan.py:26-36`

```python
testing_redis = RedisService(client=redis_client, dimension=1024)
testing      = SemanticCaching(llm_model=testing_llm, ..., vector_store=testing_redis, ...)
fake_testing = SemanticCaching(llm_model=fake_llm,    ..., vector_store=testing_redis, ...)
```

Both pipelines write into the same index with the same `cache:` prefix, and
`FakeLLMToDeploy.generate()` returns the literal string `"x"`. Any benchmark run
against `/fake_ask` (which is exactly what `benchmark/quora_questions` does, 1000–10000
pairs of it) poisons the cache that `/ask` reads from. A subsequent real request that
lands near a benchmark vector gets `"x"` as its answer.

Fix: give `RedisService` a `prefix`/`index_name` parameter and instantiate a second
store (`bench:` / `bench_index`) for the fake pipeline. Same fix also lets you run
threshold sweeps without wiping production keys.

### 🟠 3. Response field `cosine_distance` actually contains cosine *similarity*

`semantic_caching/semantic_caching.py:42`, `semantic_caching/vector_store_services/redis_service.py:103-113`

Redis returns distance in `score`; the code converts it (`score=1 - score`) and then
publishes that similarity under the key `cosine_distance`. Anyone tuning thresholds
against this API — including `benchmark/worker.py:32` which records the field
verbatim — reads the number backwards.

Fix: rename to `similarity`, and return both if you need compatibility:
`{"similarity": s, "cosine_distance": 1 - s}`. Same review applies to the
`VectorSearchResult.score` attribute — name it `similarity`.

### 🟠 4. Response schema is unstable between hit and miss

`semantic_caching/semantic_caching.py:33-47`

A miss returns 4 keys with `time` as a `datetime` object (FastAPI serializes it to
ISO); a hit returns 6 keys with `time` as a string that came back from Redis, plus
`id` and `ttl`. There is no response model, so nothing enforces or documents this.
Clients cannot rely on either shape.

Fix: one Pydantic response model in `API/schemas/`, all fields present in both
branches (`id: str | None`, `ttl: int | None`), `time: datetime`, declared via
`@router.post("/ask", response_model=AskResponse)`.

### 🟠 5. Cached entries are not namespaced by embedding model or dimension

`semantic_caching/vector_store_services/redis_service.py:29-54`, `API/lifespan.py:26`

Index name (`cache_index`), key prefix (`cache:`) and dimension (`1024`, passed by
hand) are constants. Switch embedder — which week 4 of the plan explicitly requires —
and either index creation silently fails (`create_index` swallows the exception at
line 53) leaving you searching the *old* index with *new* vectors, or dimensions
mismatch at query time. Vectors from two models are not comparable; the cache will
return confident nonsense.

Fix: derive index name from the embedder identity, e.g.
`cache:{model}:{dim}:{version}`, and read the dimension from the embedder
(`Embedder.dimension` property) instead of passing a literal. Add a startup assertion
that the existing index's `DIM` matches.

### 🟡 6. `datetime.now()` is timezone-naive

`semantic_caching/cache_entry.py:7`

`created_at` has no tzinfo, is stringified into Redis at `redis_service.py:64`, and is
returned to clients. Cross-timezone or containerized runs produce unorderable
timestamps. `semantic_caching.py:11` even imports `timezone` and never uses it.

Fix: `datetime.now(timezone.utc)`, store `.isoformat()`, parse back on read.

### 🟡 7. `decode_responses=True` will break any read of the `embedding` field

`config.py:12`, `semantic_caching/vector_store_services/redis_service.py:62,72`

Embeddings are written as raw `float32` bytes, but the client decodes every reply as
UTF-8. `get_entry()` (`HGETALL` on a `cache:*` key) therefore raises
`UnicodeDecodeError` on the binary field. It has not exploded yet only because no
route calls `get_entry`, and `search()` returns only text fields.

Fix: use a `decode_responses=False` client in `RedisService` and decode text fields
explicitly, or store the vector under a separate key. Do not leave a landmine in an
abstract-method implementation.

### 🟡 8. `cosine_similarity` has no zero-vector guard

`utils/cosine_similarity.py:9`

`dot(a,b)/(norm(a)*norm(b))` returns `nan` for a zero vector, and every `nan >
threshold` comparison is `False` — so the fake store silently reports a miss instead
of raising. Guard the denominator and raise on degenerate input.

---

## Security

### 🔴 9. Path traversal in the rules-upload endpoint

`API/routes.py:37-54`

`file.filename` is attacker-controlled and joined straight onto the rules directory:

```python
file_path = os.path.join(rules_dir, file.filename)   # filename = "../../app/config.py"
```

The extension check (`.yaml`/`.yml`) does not stop traversal, and in
`docker-compose.yml` that directory is a host bind mount (`./custom_recognizers`), so
a write escapes the container onto the developer's machine. The endpoint is also
unauthenticated.

Fix: `name = os.path.basename(file.filename)`, reject anything that is not
`[A-Za-z0-9._-]+`, resolve the final path and assert it is inside `rules_dir`
(`Path(p).resolve().is_relative_to(Path(rules_dir).resolve())`), cap the body size,
and put the endpoint behind auth.

### 🟠 10. Destructive endpoint, unauthenticated, and misspelled

`API/routes.py:26-29`

`POST /delte_cache` flushes the whole cache for anyone who can reach the port,
returns `null` (no status), and the path is a typo that is now baked into
`benchmark/quora_questions/test_over_quora.py:31`. Rename to `/cache` with
`DELETE`, require an API key or admin token, return the number of keys deleted, and
update the benchmark.

### 🟡 11. Container hardening reversed on purpose

`docker-compose.yml:54-55`, `Dockerfile:22,28`

`security_opt: [no-new-privileges:false]` explicitly *disables* a default protection —
if something needed that, fix the something. The image also runs as root, bind-mounts
the entire repo over `/app`, and ships `uvicorn --reload` as its `CMD`, so the
"production" image is a dev image. Fix: non-root `USER`, no `--reload` in the image
(override it in compose for dev only), copy only what is needed.

### 🟡 12. Uploaded rules never take effect

`semantic_caching/presidio-analyzer/server.py:204`

`analyzer = create_analyzer()` runs at import, so YAML recognizers are read once at
container start. Uploading a rule file returns `{"status": "uploaded"}` and changes
nothing until someone restarts the analyzer — while `README.md:84` advertises
"dynamically loads … at runtime". Either add a `POST /reload` on the analyzer that
rebuilds the registry (and call it from the upload route), or fix the docs.

---

## Benchmark methodology

These matter more than they look: the benchmark *is* the deliverable. A benchmark
that measures the wrong thing produces a threshold recommendation that is wrong in
production.

### 🔴 13. Parallel Quora benchmark produces meaningless precision/recall

`benchmark/quora_questions/test_over_quora.py:96-156`

Eight workers share one cache and one Redis index while worker 0 periodically flushes
it. Consequences: worker A's `question1` is visible to worker B's `question2` (false
positives that have nothing to do with the threshold), and worker 0's flush deletes
other workers' just-written entries mid-pair (false negatives). The confusion matrix
is contaminated in both directions, so `accuracy/precision/recall/f1` from
`execute_parallel_workers()` cannot be reported.

Fix: isolate per worker — a distinct key prefix/index per worker (needs finding #2's
`prefix` parameter), or run pairs sequentially and parallelize across *thresholds*
instead. Never flush shared state from inside one worker.

### 🟠 14. Hit rate is reported with no correctness label

`benchmark/execute_worker.py:31-35`, `benchmark/questions.py`

`cache_hit_rate` is computed over a hand-written prompt list with no ground truth, and
that list deliberately contains near-miss traps in the same cluster — e.g. `"What is
machine learning?"` sits next to `"What's the difference between machine learning and
deep learning?"`, and `"Capital of France?"` next to `"Capital of Germany?"`. Those
are *different* questions whose embeddings are close; when they hit, the run counts it
as a win. A hit-rate number without a precision number next to it is not a result.

Fix: label `questions.py` into equivalence classes (`cluster_id`), then compute
precision/recall from the cluster labels exactly as the Quora path does. Report hit
rate and precision together, always.

### 🟠 15. Redundant cache clearing hides what is being measured

`benchmark/quora_questions/test_over_quora.py:66,91,148`

`process_pair` already clears the cache after *every* pair, which makes the periodic
`cache_clear_duration` clears (lines 91 and 148) dead code, and means the cache never
holds more than two entries. So the benchmark measures pairwise similarity
discrimination — a useful thing — but explicitly *not* what the brief asks for
(behaviour on real traffic, where the cache holds thousands of entries and the
nearest neighbour may come from an unrelated conversation). At scale, false-positive
rate grows with cache size; this harness can never show that.

Fix: two modes — `pairwise` (clear per pair, for threshold calibration) and
`streaming` (never clear, replay LMSYS/WildChat traffic in order, measure hit rate,
false-positive rate, and memory as the cache grows).

### 🟠 16. No threshold sweep, and threshold is not reachable from outside

`API/lifespan.py:31-32`, `semantic_caching/semantic_caching.py:16`

`threshold=0.75` is a literal in the wiring, and `SemanticCaching`'s own default is
`0.5`, so unit tests, integration tests and the running app all evaluate different
systems. The "threshold-tuning study" deliverable is impossible without restarting the
app per data point.

Fix: `threshold` into `Settings` (env `SIMILARITY_THRESHOLD`), one default in one
place, optional per-request override on `/ask` for sweeps, and a
`benchmark/threshold_sweep.py` that loops thresholds and writes a CSV of
`threshold, hit_rate, precision, recall, f1`.

### 🟠 17. Benchmark worker leaks its client and ignores the one it is handed

`benchmark/worker.py:17-18,57`

```python
async def _send_request(self, client, link, question):
    client = await self.get_client()      # the argument is thrown away
```

`asks()` opens an `AsyncClient` in a `with` block that is never used, while
`self._client` is created lazily and never closed (`Unclosed client session` at exit,
and connections held across the run). Also `timeout=100000.0` (line 8) means a hung
request looks like a slow one — with a 27-hour ceiling, no request can ever time out,
so `errors_count` under-reports.

Fix: drop the `client` parameter (or use it and delete `get_client`), add
`aclose()`/`__aenter__` on `Worker`, and set a realistic timeout (30 s) so hangs are
recorded as errors.

### 🟡 18. Cache stampede is not measured, and is triggered by the default run

`benchmark/execute_worker.py:59`, `semantic_caching/semantic_caching.py:23-32`

Ten workers replay the *same* question list. On a cold cache they all miss the same
question at the same time, all call the LLM, and all `add_entry` — N duplicate entries
for one question and N× the cost the cache was supposed to save. There is no
single-flight/coalescing anywhere in `get_answers`.

Fix (also a week-7 deliverable): per-query in-flight map (`asyncio.Event` keyed by a
hash of the redacted query, or a short Redis `SET NX` lock) so concurrent misses wait
for the first result. Then report "duplicate entries created" as a benchmark metric.

### 🟡 19. Quora sample is `head(1000)`, not a sample

`benchmark/quora_questions/test_over_quora.py:182-196`

`head()` takes the first N rows in file order, inheriting whatever ordering and
class balance the file has. Use a seeded stratified sample over `is_duplicate` so
precision/recall are computed on a known positive/negative ratio, and log that ratio
with the results.

---

## Reliability

### 🟠 20. The app starts "successfully" when Redis is down or the index failed

`semantic_caching/vector_store_services/redis_service.py:19-27,47-54`, `API/lifespan.py:29-39`

`initialize()` catches connection errors into a `status` string; `create_index()`
catches *everything* and prints it (an already-exists error and a schema error look
the same). Then lifespan prints `"Started the pipeline with success!"` regardless.
Every subsequent `/ask` fails at search time with a 500 instead of at boot.

Fix: distinguish "index already exists" from other errors and re-raise the rest; fail
the lifespan startup if Redis is unreachable (or run in an explicit degraded mode that
bypasses the cache and is visible in `/health`).

### 🟠 21. No `/health`, no readiness, no dependency healthchecks

`docker-compose.yml:65-69`, `API/routes.py`

`depends_on` without `condition: service_healthy` only orders container *start*, so
FastAPI regularly boots before Redis Stack has loaded its modules and before the
analyzer is listening — see finding #20 for what that silently does. Also nothing
pulls the Ollama models, so a fresh `docker compose up` gives 500s on `/ask` until
someone runs `ollama pull` by hand (the guide now documents this; a one-shot init
container would be better).

Fix: healthchecks on `redis`, `ollama`, `presidio-*`; `condition: service_healthy` in
`depends_on`; a `/health` route that reports each dependency; a model-pull init
service.

### 🟠 22. No timeouts, retries, or fallback on the LLM and embedding calls

`semantic_caching/llm_services/ollama_service.py:13`, `semantic_caching/embedding_services/ollama_embedding.py:11`

Nothing bounds these calls, and `get_answers` has no error handling, so one slow
model turns into piled-up requests. Middleware in front of an LLM must degrade
predictably: bounded timeout, one retry on connection errors, and a clear 503 when the
provider is down.

### 🟡 23. PII redaction adds two serial HTTP round-trips to every request — including hits

`semantic_caching/query.py:12-38`

A fresh `httpx.AsyncClient` is constructed per call (no connection reuse, new TCP+TLS
setup each time), and the anonymizer is called **even when the analyzer found nothing**
(the common case). On a cache hit — the path whose whole selling point is latency —
that is two avoidable round-trips plus two socket setups. The README's `8 ms` hit
latency is not measured through this path.

Fix: build one `AsyncClient` in lifespan and inject it; return early when
`analyzer_results == []`; add per-stage server-side timing so the cost of each stage
is visible in the response or in metrics.

### 🟡 24. `print()` on the hot path, including the user's query

`semantic_caching/semantic_caching.py:26`, `semantic_caching/query.py:10-11`, `API/lifespan.py:39-51`, `redis_service.py:54,84`

`logger` is defined in `semantic_caching.py:13` and never used. `print(query)` writes
the (redacted) query to stdout on every request — in a privacy-focused component,
logging query text at all is a decision that should be explicit and configurable, not
a leftover debug line. Move everything to `logging`, keep query text at `DEBUG` and
off by default.

### 🟡 25. `timing.py` cannot time the code it was written for

`semantic_caching/timing.py:4-12`

The decorator wraps a sync function; applied to an `async def` it times how long it
takes to *create the coroutine* (microseconds) and prints a misleading number. It is
currently unused, which is the only reason it has not produced a wrong result yet.

Fix: `functools.wraps` + `async def wrapper` with `await`, or delete it in favour of
explicit `perf_counter` spans around redact/embed/search/LLM that end up in the
response and in metrics.

---

## Tests

### 🟠 26. A test that cannot fail

`testing/integration_testing/test_integration.py:107`

```python
assert result["cache_hit"] is False or result["cache_hit"] is True
```

This is a tautology — it asserts nothing about the "less similar" query. Decide the
expected behaviour at the configured threshold and assert it (or assert on the
similarity value with a documented bound).

### 🟠 27. Integration tests never initialize the index

`testing/integration_testing/test_integration.py:21-32`

`_build_pipeline_components()` builds `RedisService` but never calls `initialize()`,
so on a fresh Redis (CI, new laptop) `search()` hits a non-existent `cache_index` and
the tests error out for a reason unrelated to what they test. They pass today only
because someone ran the app first. Call `initialize()` in a fixture, and use a
test-only index prefix so the suite cannot wipe or read real cache data
(`empty_database()` at lines 65/97 currently flushes whatever is there).

### 🟠 28. The PII path has no unit tests at all

`semantic_caching/query.py`, `testing/fake_components/`

There is a `FakeLLM`, a `FakeEmbedder` and a `FakeRedis`, but no `FakeAnalyzer` — so
the component with the privacy requirement (and with finding #1 in it) is only
exercised when the real Presidio containers are up. Add a fake analyzer/anonymizer
(or `respx`-mocked HTTP) and test: no PII → passthrough; PII → bypass/redact;
analyzer down → defined behaviour (fail closed, i.e. do not cache).

### 🟡 29. `test_false_cache_hit` asserts the bug is present

`testing/unit_tests/test_semantic_caching.py:52-60`

Asserting `llm.calls == 1` after an unrelated query encodes "a false hit happens at
threshold 0.1" as the expected outcome. That is a legitimate demonstration, but name
and document it as such (`test_permissive_threshold_causes_false_hit`) so nobody
"fixes" the assertion later. Also note the fake embeddings are 3-dimensional and
hand-picked (`fake_embedding.py:10-16`); threshold behaviour there tells you nothing
about 1024-dim real embeddings — keep threshold *tuning* in the benchmark, not in
unit tests.

### 🟡 30. `pytest.ini` lacks asyncio configuration

`pytest.ini`

With `pytest-asyncio` 1.4 the fixture loop scope is unset, which emits deprecation
warnings and makes loop reuse implicit. Set `asyncio_mode = auto` (and drop the
per-test markers) plus `asyncio_default_fixture_loop_scope = function`. Add markers
for `integration` so `pytest -m "not integration"` works in CI.

---

## Repo hygiene

### 🟠 31. A 61 MB dataset is committed

`benchmark/datasets/train.csv`

Every clone pays for it forever, and it is Quora's data under their terms rather than
ours to redistribute. Add `benchmark/datasets/` to `.gitignore` and ship
`benchmark/datasets/download.py` (or a `make dataset` target) that fetches and
checksums it. Removing it from history is a rewrite — worth doing now while there is
one contributor and no open PRs; ask before rewriting `main`.

### 🟡 32. `requirements.txt` is a `pip freeze` of the whole dev machine

`requirements.txt`

91 pins including `langchain`, `langchain-core`, `langgraph*`, `langsmith`,
`matplotlib`, `sentry-sdk`, `fastapi-cloud-cli`, `detect-installer` — none of which
the code imports. That inflates the image, slows builds, and adds attack surface. It
is also missing what the brief asks for (`sentence-transformers`, `litellm`,
`qdrant-client`) and the analyzer's deps live only in its Dockerfile.

Fix: hand-written `requirements.in` of direct deps → compile with `uv pip compile` or
`pip-tools`; separate `requirements-dev.txt` (pytest, tqdm) and
`requirements-bench.txt` (pandas, matplotlib).

### 🟡 33. Dead constants pointing at the wrong port

`API/routes.py:10-11`

`CUSTOM_RECOGNIZERS_DIR` and `ANALYZER_URL` are unused (the code reads
`settings.presidio.*`), and the fallback URL is wrong anyway
(`presidio-analyzer:5001` — 5001 is the *anonymizer*; the analyzer listens on 3000
inside the network). Delete both; wrong dead config is worse than no config because
the next person will "fix" the working path to match it.

### 🟡 34. Config duplicated three ways

`config.py:31-34`, `semantic_caching/query.py:6-9`, `API/routes.py:10-11`

Presidio URLs are defined in `PresidioSettings`, then defaulted *again* inside
`QueryProcessor.__init__` via `os.getenv`, then a third time as module constants in
`routes.py`. `lifespan.py:28` constructs `QueryProcessor()` with no arguments, so the
`Settings` object is bypassed entirely. Pass settings in explicitly (one source of
truth); `load_dotenv()` at `lifespan.py:42` also runs on *shutdown*, after the config
it would affect has already been read.

### 🟡 35. Root-level `__init__.py` and a 3-dot relative import

`__init__.py`, `testing/integration_testing/test_integration.py:7`

`from ...config import settings` only resolves because the repo root is itself a
package, which also gives the project two importable names for the same module
(`config` and `<root>.config`) and shadows the `semantic_caching` package name with
the identically-named subpackage. Use `from config import settings` (pytest already
sets `pythonpath = .`) and drop the root `__init__.py`. Longer term: move the library
under `src/semantic_cache/` with a `pyproject.toml` so it is `pip install -e .`-able —
the brief asks for a *library*, and right now it cannot be installed.

### 🔵 36. Smaller things worth a cleanup pass

- `semantic_caching/semantic_caching.py:1-2` — `httpx`, `asyncio` imported unused;
  same for `asyncio` in `ollama_service.py:3`, `ollama_embedding.py:4`.
- `redis_service.py:29` — `KNN 1` is hardcoded, so you can never inspect the top-k
  neighbourhood. Make `k` a parameter; returning the top 3 with their similarities is
  invaluable when debugging a false hit.
- `redis_service.py:74-78` — `get_size()` does a full `SCAN` per call; `FT.INFO
  cache_index` gives `num_docs` in O(1).
- `cache_entry.py:3` — `ttl_seconds=3600` is a magic default in a data class; move it
  to settings (it is the invalidation knob the brief asks you to study).
- `cache_entry.py:5` — type hint says `embedding: list`, the code stores
  `np.ndarray`.
- No exact-match fast path: an identical repeat query still pays a full embedding
  call. GPTCache does a hash lookup first; that is a cheap, large latency win.
- `custom_recognizers/gemini-code-1785749213179.yaml` — machine-generated filename for
  a file whose first line says `# custom_rules.yaml`. Rename to
  `employee_and_project_codes.yaml`.
- `vector_store_services.py:19` — docstring "Method to lowkey drop table". Write it
  as `"""Delete all cache entries."""`.
- `VectorStore`/`Embedder`/`LLM` abstract methods are declared `def`, not `async def`,
  while every implementation is async. Declare them `async def` so the interface
  states the contract.

---

## What I would fix first

1. **#1** (redaction collision) and **#2** (shared `/fake_ask` namespace) — both serve
   wrong answers to real callers today.
2. **#9**, **#10** — write-outside-the-container and unauthenticated flush.
3. **#16**, **#13**, **#14** — without these the threshold study, the headline
   deliverable, cannot produce a trustworthy number.
4. **#20**, **#21** — stop the stack from pretending it started correctly.
5. **#26**, **#27**, **#28** — make the suite able to catch the above.

Then the shape of the remaining work is in `docs/INTERN_GUIDE.md` §7.
