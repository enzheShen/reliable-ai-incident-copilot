SHELL := /bin/sh
COMPOSE := docker compose

.PHONY: bootstrap dev stop test lint typecheck eval load-test load-test-cold load-test-warm chaos-demo seed migrate clean

bootstrap:
	test -f .env || cp .env.example .env
	$(COMPOSE) build
	$(COMPOSE) run --rm backend alembic upgrade head
	$(COMPOSE) run --rm backend python -m app.seed

dev:
	$(COMPOSE) up --build -d

stop:
	$(COMPOSE) down

test:
	$(COMPOSE) up -d postgres redis mock-llm toxiproxy toxiproxy-config
	-$(COMPOSE) exec -T postgres createdb -U incident incident_copilot_test
	$(COMPOSE) run --rm --build \
		-e DATABASE_URL=postgresql+psycopg://incident:incident@postgres:5432/incident_copilot_test \
		-e REDIS_URL=redis://redis:6379/1 \
		-e INTEGRATION_DATABASE_URL=postgresql+psycopg://incident:incident@postgres:5432/incident_copilot_test \
		-e INTEGRATION_REDIS_URL=redis://redis:6379/1 \
		backend pytest
	$(COMPOSE) run --rm --build frontend pnpm test:run

lint:
	$(COMPOSE) run --rm --build backend ruff check .
	$(COMPOSE) run --rm --build frontend npm run lint

typecheck:
	$(COMPOSE) run --rm --build backend mypy app
	$(COMPOSE) run --rm --build frontend npm run typecheck

eval:
	$(COMPOSE) up -d postgres redis mock-llm toxiproxy toxiproxy-config
	-$(COMPOSE) exec -T postgres createdb -U incident incident_copilot_eval
	$(COMPOSE) run --rm --build \
		-e DATABASE_URL=postgresql+psycopg://incident:incident@postgres:5432/incident_copilot_eval \
		-e REDIS_URL=redis://redis:6379/2 \
		backend sh -c 'alembic upgrade head && python -m app.seed && python -m app.evaluation'

load-test:
	$(MAKE) load-test-cold
	$(MAKE) load-test-warm
	python3 loadtests/compare.py

load-test-cold:
	sh loadtests/run.sh cold

load-test-warm:
	sh loadtests/run.sh warm

chaos-demo:
	$(COMPOSE) up -d --build
	python3 -m chaos.run_demo

seed:
	$(COMPOSE) run --rm backend python -m app.seed

migrate:
	$(COMPOSE) run --rm backend alembic upgrade head

clean:
	$(COMPOSE) down --remove-orphans
	find backend frontend mock-llm -type d -name __pycache__ -prune -exec rm -r {} + 2>/dev/null || true
	find backend -type d \( -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -r {} + 2>/dev/null || true
	rm -rf frontend/dist
