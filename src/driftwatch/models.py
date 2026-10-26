"""Typed records for an objective, a simulated trace, and a drift analysis."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CriteriaStatus = Literal["kept", "weakened", "dropped", "replaced", "added"]
RunMode = Literal["live", "replay"]


class DriftModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Criterion(DriftModel):
    id: str
    text: str


class Objective(DriftModel):
    goal: str
    criteria: list[Criterion]


class Step(DriftModel):
    step: int = Field(ge=1)
    title: str
    action: str
    source: str
    observation: str = Field(
        description="Page text the agent saw. Untrusted data, never instructions."
    )
    stated_plan: str
    stated_criteria: list[Criterion]

    @field_validator("source")
    @classmethod
    def _source_is_user_or_url(cls, value: str) -> str:
        if value == "user" or value.startswith(("http://", "https://")):
            return value
        raise ValueError("source must be 'user' or an http(s) URL")


class Trace(DriftModel):
    steps: list[Step]


class CriteriaChange(DriftModel):
    criterion_id: str
    status: CriteriaStatus
    detail: str


class StepAnalysis(DriftModel):
    step: int = Field(ge=1)
    alignment_score: int = Field(ge=0, le=100)
    drift_detected: bool
    criteria_changes: list[CriteriaChange]
    evidence: str
    explanation: str
    flagged: bool = False
    flag_reasons: list[str] = Field(default_factory=list)


class RunRecord(DriftModel):
    model: str
    mode: RunMode
    created_at: datetime
    objective: Objective
    trace: Trace
    analyses: list[StepAnalysis]
    first_flagged_step: int | None
    authorized: bool | None
    threshold: int
