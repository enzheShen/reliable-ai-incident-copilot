import os
import re
from pathlib import Path

from app.schemas import IncidentAssessment, IncidentCreate

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).parents[3]))
FRONTEND_TYPES = PROJECT_ROOT / "frontend/src/types/api.ts"


def interface_fields(source: str, name: str) -> set[str]:
    match = re.search(rf"export interface {name} \{{(?P<body>.*?)\n\}}", source, re.DOTALL)
    assert match, f"TypeScript interface {name} was not found"
    fields = set()
    for line in match.group("body").splitlines():
        field = re.match(r"\s*([a-z_]+)\??:", line)
        if field:
            fields.add(field.group(1))
    return fields


def test_frontend_incident_contract_matches_pydantic_fields() -> None:
    source = FRONTEND_TYPES.read_text(encoding="utf-8")
    assert interface_fields(source, "IncidentCreate") == set(IncidentCreate.model_fields)
    assert interface_fields(source, "IncidentAssessment") == set(IncidentAssessment.model_fields)


def test_frontend_severity_and_environment_enums_match_backend() -> None:
    source = FRONTEND_TYPES.read_text(encoding="utf-8")
    severity = re.search(r"export type Severity = (?P<values>[^\n]+)", source)
    environment = re.search(r"export type Environment = (?P<values>[^\n]+)", source)
    assert severity and set(re.findall(r"'([^']+)'", severity.group("values"))) == {
        "SEV1",
        "SEV2",
        "SEV3",
        "SEV4",
    }
    assert environment and set(re.findall(r"'([^']+)'", environment.group("values"))) == {
        "development",
        "staging",
        "production",
    }
