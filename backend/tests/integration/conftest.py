from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from alembic.config import Config


@pytest.fixture(scope="session")
def integration_urls() -> tuple[str, str]:
    database_url = os.getenv("INTEGRATION_DATABASE_URL")
    redis_url = os.getenv("INTEGRATION_REDIS_URL")
    if not database_url or not redis_url:
        pytest.skip("PostgreSQL and Redis integration URLs are not configured")
    return database_url, redis_url


@pytest_asyncio.fixture
async def db_session(integration_urls: tuple[str, str]) -> AsyncIterator[AsyncSession]:
    database_url, _ = integration_urls
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        await asyncio.to_thread(command.upgrade, config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE assessment_runbooks, idempotency_keys, assessments, "
                "reliability_events, incidents, runbooks CASCADE"
            )
        )
    async with factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def integration_redis(integration_urls: tuple[str, str]) -> AsyncIterator[Redis]:
    _, redis_url = integration_urls
    client = Redis.from_url(redis_url, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()
