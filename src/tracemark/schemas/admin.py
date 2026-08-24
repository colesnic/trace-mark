"""Admin API schemas."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_version: int
    created_at: dt.datetime


class SubjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_ref: str = Field(min_length=1, max_length=200)


class SubjectRef(BaseModel):
    id: uuid.UUID
    external_ref: str


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    external_ref: str
    pseudonymous_tag: str
    active: bool
    created_at: dt.datetime


class CredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    subject_id: uuid.UUID
    created_at: dt.datetime
    revoked_at: dt.datetime | None


class CredentialCreateResponse(BaseModel):
    id: uuid.UUID
    token: str
