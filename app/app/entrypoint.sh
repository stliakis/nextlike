#!/bin/bash

## Create the pgvector extension
psql "$POSTGRES_CONNECTION_STRING" -c "CREATE EXTENSION IF NOT EXISTS vector"

alembic upgrade head

uvicorn app.main:app --workers 8 --host 0.0.0.0 --port 80
