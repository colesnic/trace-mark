"""Detection API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from tracemark.schemas.admin import SubjectRef


class DetectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=200_000)
    tenant_id: str
    policy: str = "balanced"


class CandidateScoreOut(BaseModel):
    subject_tag: str
    model_scope: str | None
    subject: SubjectRef | None = None
    opportunities: int
    matches: int
    match_rate: float
    p_value: float
    adjusted_p_value: float
    evidence_score: float


class DetectResponse(BaseModel):
    detected: bool
    usable_opportunities: int
    best_candidate: CandidateScoreOut | None
    runner_up: CandidateScoreOut | None
    candidates_tested: int
    reason: str
