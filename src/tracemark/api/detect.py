"""POST /v1/detect."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tracemark.api.dependencies import get_session
from tracemark.auth.dependencies import require_admin
from tracemark.schemas.admin import SubjectRef
from tracemark.schemas.detection import (
    CandidateScoreOut,
    DetectRequest,
    DetectResponse,
)
from tracemark.services.subjects import (
    get_tenant,
    list_subjects,
    subject_fingerprint_key,
)
from tracemark.watermark.detector import (
    FingerprintCandidate,
    detect_fingerprint,
)
from tracemark.watermark.policy import WatermarkPolicy

router = APIRouter(prefix="/v1", tags=["detect"])


@router.post("/detect", response_model=DetectResponse)
async def detect_endpoint(
    request: DetectRequest,
    _admin: Annotated[None, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DetectResponse:
    try:
        tenant_id = uuid.UUID(request.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid tenant_id") from exc

    tenant = await get_tenant(session, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")

    try:
        policy = WatermarkPolicy.from_name(request.policy)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    subjects = await list_subjects(session, tenant.id)
    active = [s for s in subjects if s.active]
    candidates = [
        FingerprintCandidate(
            subject_tag=s.pseudonymous_tag,
            model_scope=None,
            key=subject_fingerprint_key(tenant.id, s),
        )
        for s in active
    ]
    if not candidates:
        raise HTTPException(status_code=422, detail="tenant has no active subjects")

    result = detect_fingerprint(
        text=request.text, candidates=candidates, policy=policy
    )

    subject_by_tag = {s.pseudonymous_tag: s for s in active}

    def to_out(score) -> CandidateScoreOut | None:
        if score is None:
            return None
        subject = subject_by_tag.get(score.subject_tag)
        return CandidateScoreOut(
            subject_tag=score.subject_tag,
            model_scope=score.model_scope,
            subject=SubjectRef(id=subject.id, external_ref=subject.external_ref)
            if subject
            else None,
            opportunities=score.opportunities,
            matches=score.matches,
            match_rate=score.match_rate,
            p_value=score.p_value,
            adjusted_p_value=score.adjusted_p_value,
            evidence_score=score.evidence_score,
        )

    return DetectResponse(
        detected=result.detected,
        usable_opportunities=result.usable_opportunities,
        best_candidate=to_out(result.best_candidate),
        runner_up=to_out(result.runner_up),
        candidates_tested=result.candidates_tested,
        reason=result.reason,
    )
