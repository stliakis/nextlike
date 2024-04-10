#! /usr/bin/env bash

docker-compose exec app alembic revision --autogenerate -m "$1"
docker-compose exec app alembic upgrade head