from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_factory
from app.models import Incident, Runbook
from app.services.embeddings import runbook_embedding


def load_json(name: str) -> list[dict[str, Any]]:
    path = get_settings().data_dir / name
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"Expected a list in {path}")
    return value


async def seed() -> tuple[int, int]:
    runbooks = load_json("runbooks/runbooks.json")
    fixtures = load_json("incidents/synthetic-incidents.json")
    async with async_session_factory() as session:
        for item in runbooks:
            existing = await session.scalar(select(Runbook).where(Runbook.slug == item["slug"]))
            values = {
                "id": UUID(item["id"]),
                "slug": item["slug"],
                "title": item["title"],
                "content": item["content"],
                "embedding": runbook_embedding(item["title"], item["keywords"]),
                "version": 1,
            }
            if existing is None:
                session.add(Runbook(**values))
            else:
                for key, value in values.items():
                    if key != "id":
                        setattr(existing, key, value)

        for fixture in fixtures:
            incident_id = uuid5(NAMESPACE_URL, f"incident-copilot:{fixture['fixture_id']}")
            if await session.get(Incident, incident_id) is None:
                session.add(Incident(id=incident_id, **fixture["incident"]))
        await session.commit()
    return len(runbooks), len(fixtures)


async def async_main() -> None:
    runbook_count, incident_count = await seed()
    print(f"seeded {runbook_count} runbooks and {incident_count} synthetic incidents")


if __name__ == "__main__":
    asyncio.run(async_main())
