import hashlib
import json
from collections.abc import Sequence

from app.repositories import RunbookMatch
from app.schemas import IncidentCreate


def canonical_incident(incident: IncidentCreate) -> str:
    return json.dumps(
        incident.model_dump(mode="json", exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def request_hash(incident: IncidentCreate) -> str:
    return hashlib.sha256(canonical_incident(incident).encode()).hexdigest()


def assessment_cache_key(
    incident: IncidentCreate,
    runbooks: Sequence[RunbookMatch],
    provider_name: str,
    model: str,
) -> str:
    material = {
        "incident": json.loads(canonical_incident(incident)),
        "provider": provider_name,
        "model": model,
        "runbooks": [{"id": str(item.id), "version": item.version} for item in runbooks],
    }
    digest = hashlib.sha256(
        json.dumps(material, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    return f"assessment:v1:{digest}"
