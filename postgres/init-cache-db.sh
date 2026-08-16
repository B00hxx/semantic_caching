#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<-EOSQL

CREATE USER ${CACHE_POSTGRES_USER}
WITH PASSWORD '${CACHE_POSTGRES_PASSWORD}';

CREATE DATABASE ${CACHE_POSTGRES_DB}
OWNER ${CACHE_POSTGRES_USER};

EOSQL

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$CACHE_POSTGRES_DB" <<-EOSQL

CREATE EXTENSION IF NOT EXISTS vector;

EOSQL

psql -v ON_ERROR_STOP=1 \
  --username "$CACHE_POSTGRES_USER" \
  --dbname "$CACHE_POSTGRES_DB" \
  -f /docker-entrypoint-initdb.d/schema.sql