from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.incidents import Severity


class ProviderAssessment(BaseModel):
    """Strict untrusted-provider response before application metadata is attached."""

    model_config = ConfigDict(extra="forbid")

    severity: Severity
    summary: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=1_000)
    ]
    likely_causes: Annotated[
        list[
            Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
        ],
        Field(min_length=1, max_length=5),
    ]
    evidence: Annotated[
        list[
            Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
        ],
        Field(min_length=1, max_length=10),
    ]
    recommended_actions: Annotated[
        list[
            Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
        ],
        Field(min_length=1, max_length=10),
    ]
    confidence: Annotated[float, Field(ge=0, le=1)]
    requires_human_escalation: bool
