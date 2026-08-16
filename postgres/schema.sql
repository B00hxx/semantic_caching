CREATE TABLE IF NOT EXISTS cache_entries (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    embedding vector NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    answer TEXT NOT NULL,
    namespace TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    ttl_seconds INTEGER NOT NULL
);