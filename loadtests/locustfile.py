import json
import random
from pathlib import Path
from uuid import uuid4

from locust import HttpUser, between, task

FIXTURES = json.loads(Path("/data/incidents/synthetic-incidents.json").read_text(encoding="utf-8"))


class IncidentAnalyst(HttpUser):
    wait_time = between(0.2, 1.0)

    @task
    def analyse_incident(self) -> None:
        fixture = random.choice(FIXTURES)  # noqa: S311 - load distribution is not security-sensitive
        with self.client.post(
            "/api/v1/incidents/analyse",
            json=fixture["incident"],
            headers={"Idempotency-Key": str(uuid4())},
            name="POST /api/v1/incidents/analyse",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"unexpected status {response.status_code}")
                return
            body = response.json()
            required = {"incident_id", "severity", "provider_used", "processing_time_ms"}
            if not required <= set(body):
                response.failure("response did not satisfy assessment contract")
