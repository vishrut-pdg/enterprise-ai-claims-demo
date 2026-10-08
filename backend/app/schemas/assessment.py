from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    recommendation: Literal["accept", "reject", "investigate"]
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    findings: list[str] = Field(
        description="Exact deterministic check codes from checks[].code; no narrative text",
        min_length=1,
    )
    evidence_ids: list[str] = Field(
        description="Exact IDs of supporting evidence from evidence[].id; empty when none exists"
    )
    unresolved_questions: list[str]
    explanation: str = Field(min_length=1, max_length=8000)


class AutonomousAssessment(Assessment):
    recommendation: Literal["accept", "reject"]


class Investigation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    recommendation: Literal["accept", "reject"]
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    findings: list[str] = Field(min_length=1)
    evidence_ids: list[str]
    summary: str = Field(min_length=1, max_length=8000)
    limitations: list[str]


class ProcessRequest(BaseModel):
    expected_version: int = Field(ge=1)


class ManagerRequest(ProcessRequest):
    decision: Literal["accept", "reject", "request_information"]
    rationale: str = Field(min_length=3, max_length=4000)

    @field_validator("rationale")
    @classmethod
    def nonblank_rationale(cls, value):
        if len(value.strip()) < 3:
            raise ValueError(
                "Rationale must contain at least three non-space characters"
            )
        return value.strip()
