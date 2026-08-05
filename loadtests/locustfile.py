import copy
import json
import os
import random
from pathlib import Path
from uuid import uuid4

from locust import HttpUser, between, task

FIXTURES = json.loads(Path("/data/incidents/synthetic-incidents.json").read_text(encoding="utf-8"))
LOAD_MODE = os.getenv("LOAD_MODE", "warm")

if LOAD_MODE not in {"cold", "warm"}:
    raise RuntimeError("LOAD_MODE must be 'cold' or 'warm'")


class IncidentAnalyst(HttpUser):
    wait_time = between(0.2, 1.0)

    @task
    def analyse_incident(self) -> None:
        fixture = random.choice(FIXTURES)  # noqa: S311 - load distribution is not security-sensitive
        incident = copy.deepcopy(fixture["incident"])
        if LOAD_MODE == "cold":
            incident["reporter"] = f"synthetic-load-cold-{uuid4()}"
        with self.client.post(
            "/api/v1/incidents/analyse",
            json=incident,
            headers={"Idempotency-Key": str(uuid4())},
            name="POST /api/v1/incidents/analyse",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"unexpected status {response.status_code}")
                return
            body = response.json()
            required = {
                "cache_hit",
                "fallback_used",
                "incident_id",
                "processing_time_ms",
                "provider_used",
                "severity",
            }
            if not required <= set(body):
                response.failure("response did not satisfy assessment contract")
