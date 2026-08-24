"""POST /v1/watermark."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tracemark.api.dependencies import get_session
from tracemark.auth.dependencies import get_current_identity
from tracemark.config import Settings
from tracemark.crypto.fingerprint import derive_fingerprint
from tracemark.db.models import Subject, Tenant
from tracemark.schemas.watermark import (
    AppliedTransformationOut,
    WatermarkRequest,
    WatermarkResponse,
)
from tracemark.services.audit import record_generation
from tracemark.watermark.engine import apply_watermark
from tracemark.watermark.policy import WatermarkPolicy

router = APIRouter(prefix="/v1", tags=["watermark"])


@router.post("/watermark", response_model=WatermarkResponse)
async def watermark_endpoint(
    request: WatermarkRequest,
    identity: Annotated[tuple[Tenant, Subject], Depends(get_current_identity)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WatermarkResponse:
    tenant, subject = identity
    try:
        policy = WatermarkPolicy.from_name(request.policy)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if request.model_scope:
        fingerprint = derive_fingerprint(
            master_key=Settings().resolve_master_key(),
            tenant_id=tenant.id,
            subject_external_ref=subject.external_ref,
            model_scope=request.model_scope,
        )
        key = fingerprint.key
        subject_tag = fingerprint.subject_tag
    else:
        from tracemark.services.subjects import subject_fingerprint_key

        key = subject_fingerprint_key(tenant.id, subject)
        subject_tag = subject.pseudonymous_tag

    result = apply_watermark(text=request.text, fingerprint_key=key, policy=policy)

    await record_generation(
        session,
        tenant_id=tenant.id,
        subject_id=subject.id,
        provider=None,
        model=request.model_scope,
        policy_name=policy.name,
        input_text=request.text,
        original_output=request.text,
        watermarked_output=result.text,
        opportunity_count=result.opportunities_found,
        embedded_count=result.transformations_applied,
    )

    return WatermarkResponse(
        text=result.text,
        watermarked=result.transformations_applied > 0,
        opportunities_found=result.opportunities_found,
        transformations_applied=result.transformations_applied,
        subject_tag=subject_tag,
        transformations=[
            AppliedTransformationOut(
                rule_id=t.rule_id,
                original=t.original,
                replacement=t.replacement,
                bit=t.bit,
                start=t.start,
                end=t.end,
            )
            for t in result.transformations
        ],
    )
