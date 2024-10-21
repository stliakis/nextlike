#!/bin/bash

docker-compose exec app "python" "scripts/playground.py" "$@"