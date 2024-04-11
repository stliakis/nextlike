#!/bin/bash

## Create the pgvector extension
psql "$POSTGRES_CONNECTION_STRING" -c "CREATE EXTENSION IF NOT EXISTS vector"

alembic upgrade head

uvicorn main:app --host 0.0.0.0 --port 80
