"""Watermark API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WatermarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=200_000)
    model_scope: str | None = None
    policy: str = "balanced"


class AppliedTransformationOut(BaseModel):
    rule_id: str
    original: str
    replacement: str
    bit: int
    start: int
    end: int


class WatermarkResponse(BaseModel):
    text: str
    watermarked: bool
    opportunities_found: int
    transformations_applied: int
    subject_tag: str
    transformations: list[AppliedTransformationOut] = Field(default_factory=list)
