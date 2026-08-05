from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

app = FastAPI(title="Deterministic Incident Mock LLM", version="1.0.0")

SEVERITY = {
    "api-latency-spike": "SEV2",
    "database-connection-saturation": "SEV1",
    "redis-outage": "SEV2",
    "authentication-failure": "SEV1",
    "rate-limit-spike": "SEV3",
    "upstream-dependency-timeout": "SEV2",
    "memory-leak": "SEV2",
    "cpu-saturation": "SEV2",
    "disk-capacity-exhaustion": "SEV1",
    "message-queue-backlog": "SEV2",
    "tls-certificate-expiry": "SEV1",
    "deployment-regression": "SEV2",
}


class AssessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident: dict[str, Any]
    runbooks: list[dict[str, Any]]
    prompt_digest_input: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/assess")
async def assess(request: AssessRequest) -> dict[str, Any]:
    incident = request.incident
    primary = request.runbooks[0] if request.runbooks else None
    slug = str(primary.get("slug", "")) if primary else ""
    severity = SEVERITY.get(slug, "SEV3")
    logs = [str(item)[:500] for item in incident.get("logs", [])[:3]]
    metrics = incident.get("metrics", {})
    evidence = logs + [f"{key}={value}"[:500] for key, value in sorted(metrics.items())[:4]]
    if not evidence:
        evidence = [str(incident.get("symptoms", "Insufficient evidence"))[:500]]
    title = str(primary.get("title", "Unknown cause")) if primary else "Unknown cause"
    content = str(primary.get("content", "Preserve evidence and assign a human owner"))
    actions = [item.strip()[:500] for item in content.split(".") if item.strip()][:3]
    service = str(incident.get("service_name", "unknown-service"))
    symptoms = str(incident.get("symptoms", "Unspecified symptoms"))
    return {
        "severity": severity,
        "summary": f"{service}: {symptoms}"[:1000],
        "likely_causes": [title],
        "evidence": evidence,
        "recommended_actions": actions or ["Assign a human incident owner"],
        "confidence": 0.9 if primary else 0.55,
        "requires_human_escalation": severity in {"SEV1", "SEV2"},
    }
