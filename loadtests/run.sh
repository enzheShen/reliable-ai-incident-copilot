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
attempt=0
until curl -fsS http://localhost:8000/health/ready >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    echo "backend did not become ready before the load test" >&2
    exit 1
  fi
  sleep 1
done
docker compose --profile loadtest run --rm --no-deps locust
python3 loadtests/summarize.py
