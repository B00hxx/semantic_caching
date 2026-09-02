CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS cache_entries (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    embedding vector NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    answer TEXT NOT NULL,
    namespace TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 0,
    last_hit_at TIMESTAMPTZ,
    last_accessed_at TIMESTAMPTZ,
    evicted BOOLEAN NOT NULL DEFAULT FALSE,
    evicted_at TIMESTAMPTZ,
    invalidated BOOLEAN NOT NULL DEFAULT FALSE,
    invalidated_at TIMESTAMPTZ,
    invalidation_strategy TEXT,
    eviction_strategy TEXT
);

ALTER TABLE cache_entries
ADD COLUMN IF NOT EXISTS evicted BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE cache_entries
ADD COLUMN IF NOT EXISTS invalidated BOOLEAN NOT NULL DEFAULT FALSE;