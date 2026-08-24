"""Admin API endpoints (development admin token)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tracemark.api.dependencies import get_session
from tracemark.auth.dependencies import require_admin
from tracemark.schemas.admin import (
    CredentialCreateResponse,
    SubjectCreate,
    SubjectOut,
    TenantCreate,
    TenantOut,
)
from tracemark.services.subjects import (
    create_credential,
    create_subject,
    create_tenant,
    get_tenant,
    get_tenant_by_name,
    list_subjects,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/tenants", response_model=TenantOut, status_code=201)
async def admin_create_tenant(
    body: TenantCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TenantOut:
    existing = await get_tenant_by_name(session, body.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail="tenant name already exists")
    tenant = await create_tenant(session, body.name)
    return TenantOut.model_validate(tenant)


@router.get("/tenants/{tenant_id}", response_model=TenantOut)
async def admin_get_tenant(
    tenant_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TenantOut:
    tenant = await get_tenant(session, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")
    return TenantOut.model_validate(tenant)


@router.post("/tenants/{tenant_id}/subjects", response_model=SubjectOut, status_code=201)
async def admin_create_subject(
    tenant_id: uuid.UUID,
    body: SubjectCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SubjectOut:
    tenant = await get_tenant(session, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")
    subject = await create_subject(session, tenant_id, body.external_ref)
    return SubjectOut.model_validate(subject)


@router.get("/tenants/{tenant_id}/subjects", response_model=list[SubjectOut])
async def admin_list_subjects(
    tenant_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SubjectOut]:
    subjects = await list_subjects(session, tenant_id)
    return [SubjectOut.model_validate(s) for s in subjects]


@router.post(
    "/tenants/{tenant_id}/subjects/{subject_id}/credentials",
    response_model=CredentialCreateResponse,
    status_code=201,
)
async def admin_create_credential(
    tenant_id: uuid.UUID,
    subject_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CredentialCreateResponse:
    tenant = await get_tenant(session, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")
    from tracemark.db.models import Subject

    subject = await session.get(Subject, subject_id)
    if subject is None or subject.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="subject not found")
    token, credential = await create_credential(session, tenant_id, subject_id)
    return CredentialCreateResponse(id=credential.id, token=token)
