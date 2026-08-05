#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
mkdir -p reports/loadtests

restore_backend() {
  docker compose up -d --force-recreate backend >/dev/null 2>&1 || true
}
trap restore_backend EXIT INT TERM

RATE_LIMIT_PER_MINUTE=100000 docker compose up -d --build backend
docker compose --profile loadtest run --rm locust
python3 loadtests/summarize.py
