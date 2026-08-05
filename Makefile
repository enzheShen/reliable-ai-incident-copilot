SHELL := /bin/sh
COMPOSE := docker compose

.PHONY: bootstrap dev stop test lint typecheck eval load-test chaos-demo seed migrate clean

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
	$(COMPOSE) run --rm backend pytest
	$(COMPOSE) run --rm frontend npm run test:run

lint:
	$(COMPOSE) run --rm backend ruff check .
	$(COMPOSE) run --rm frontend npm run lint

typecheck:
	$(COMPOSE) run --rm backend mypy app
	$(COMPOSE) run --rm frontend npm run typecheck

eval:
	$(COMPOSE) run --rm backend python -m app.evaluation

load-test:
	sh loadtests/run.sh

chaos-demo:
	$(COMPOSE) up -d --build
	python3 chaos/run_demo.py

seed:
	$(COMPOSE) run --rm backend python -m app.seed

migrate:
	$(COMPOSE) run --rm backend alembic upgrade head

clean:
	$(COMPOSE) down --remove-orphans
	find backend frontend mock-llm -type d -name __pycache__ -prune -exec rm -r {} + 2>/dev/null || true
	find backend -type d \( -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -r {} + 2>/dev/null || true
	rm -rf frontend/dist
