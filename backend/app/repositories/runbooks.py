from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Runbook
from app.services.embeddings import deterministic_embedding


@dataclass(frozen=True)
class RunbookMatch:
    id: UUID
    slug: str
    title: str
    content: str
    version: int
    relevance: float


class RunbookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, query: str, limit: int = 3) -> list[RunbookMatch]:
        embedding = deterministic_embedding(query)
        distance = Runbook.embedding.cosine_distance(embedding)
        statement = select(Runbook, distance.label("distance")).order_by(distance).limit(limit)
        rows = (await self.session.execute(statement)).all()
        return [
            RunbookMatch(
                id=runbook.id,
                slug=runbook.slug,
                title=runbook.title,
                content=runbook.content,
                version=runbook.version,
                relevance=max(0.0, min(1.0, 1.0 - float(score))),
            )
            for runbook, score in rows
        ]
