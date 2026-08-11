FROM node:22-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN corepack enable && corepack prepare pnpm@10.28.0 --activate \
    && pnpm install --frozen-lockfile
COPY frontend ./
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN pnpm build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PROJECT_ROOT=/app

WORKDIR /app

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/tests ./tests
COPY backend/start.sh /usr/local/bin/start-app
COPY chaos ./chaos
COPY data ./data
COPY frontend/src/types ./frontend/src/types
COPY --from=frontend-build /frontend/dist ./frontend/dist

RUN pip install --upgrade pip && pip install ".[dev]"

RUN addgroup --system app && adduser --system --ingroup app app \
    && chmod +x /usr/local/bin/start-app \
    && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["/usr/local/bin/start-app"]
