"""Authentication dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tracemark.auth.tokens import constant_time_equals
from tracemark.config import Settings
from tracemark.db.models import Subject, Tenant
from tracemark.db.session import get_session
from tracemark.services.subjects import resolve_token


async def get_current_identity(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> tuple[Tenant, Subject]:
    """Resolve the Bearer token to its bound (tenant, subject)."""
    token = _extract_bearer(authorization)
    result = await resolve_token(session, token)
    if result is None:
        raise HTTPException(
            status_code=401, detail="invalid or revoked API credential"
        )
    return result


async def require_admin(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Require the development admin bearer token."""
    token = _extract_bearer(authorization)
    expected = Settings().resolve_admin_token()
    if not expected or not constant_time_equals(token, expected):
        raise HTTPException(status_code=401, detail="invalid admin token")


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing bearer token")
    return token
