CREATE TABLE IF NOT EXISTS cache_entries (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    embedding vector NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    answer TEXT NOT NULL,
    namespace TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 0,
    last_hit_at TIMESTAMPTZ,
    last_accessed_at TIMESTAMPTZ
);

ALTER TABLE cache_entries
ALTER COLUMN namespace DROP NOT NULL;