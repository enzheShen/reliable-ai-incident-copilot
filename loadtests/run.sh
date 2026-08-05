#!/bin/sh
set -eu

mode=${1:-}
if [ "$mode" != "cold" ] && [ "$mode" != "warm" ]; then
  echo "usage: $0 cold|warm" >&2
  exit 2
fi

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
LOAD_MODE=$mode
LOAD_USERS=${LOAD_USERS:-20}
LOAD_DURATION=${LOAD_DURATION:-5m}
export LOAD_MODE LOAD_USERS LOAD_DURATION
report_dir="reports/loadtests/$mode"
mkdir -p "$report_dir"

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

docker compose exec -T redis redis-cli -n 0 FLUSHDB >/dev/null
curl -fsS http://localhost:8000/metrics -o "$report_dir/metrics-before.prom"
docker compose --profile loadtest run --rm --no-deps \
  -e LOAD_MODE="$mode" \
  locust \
  -f /mnt/locust/locustfile.py \
  --host http://backend:8000 \
  --headless \
  -u "$LOAD_USERS" \
  -r 4 \
  -t "$LOAD_DURATION" \
  --csv "/reports/$mode/latest" \
  --html "/reports/$mode/latest.html"
curl -fsS http://localhost:8000/metrics -o "$report_dir/metrics-after.prom"
python3 loadtests/summarize.py
