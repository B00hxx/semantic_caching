from prometheus_client import Counter, Gauge, Histogram

CACHE_REQUESTS = Counter(
    "semantic_cache_requests_total",
    "Total number of requests received by the semantic cache",
)

CACHE_HITS = Counter(
    "semantic_cache_hits_total",
    "Total number of semantic cache hits",
)

CACHE_MISSES = Counter(
    "semantic_cache_misses_total",
    "Total number of semantic cache misses",
)

CACHE_BYPASSES = Counter(
    "semantic_cache_bypasses_total",
    "Total number of requests bypassing the semantic cache",
)

CACHE_LOOKUP_LATENCY = Histogram(
    "semantic_cache_lookup_latency_seconds",
    "Time spent performing semantic cache lookup",
)

EMBEDDING_LATENCY = Histogram(
    "semantic_cache_embedding_latency_seconds",
    "Time spent generating query embeddings",
)

CACHE_INVALIDATIONS = Counter(
    "semantic_cache_invalidations_total",
    "Total number of cache entries invalidated",
    ["strategy"],
)

CACHE_EVICTIONS = Counter(
    "semantic_cache_evictions_total",
    "Total number of cache entries evicted",
    ["strategy"],
)

CACHE_SIZE = Gauge(
    "semantic_cache_size",
    "Current number of entries in the semantic cache",
)