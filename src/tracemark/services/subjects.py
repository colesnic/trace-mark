"""Tenant / subject / credential service operations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tracemark.auth.tokens import generate_token, hash_token
from tracemark.config import Settings
from tracemark.crypto.fingerprint import (
    derive_subject_tag,
    derive_tenant_secret,
)
from tracemark.db.models import ApiCredential, Subject, Tenant


async def create_tenant(session: AsyncSession, name: str) -> Tenant:
    tenant = Tenant(name=name)
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def get_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    return await session.get(Tenant, tenant_id)


async def get_tenant_by_name(session: AsyncSession, name: str) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.name == name))
    return result.scalar_one_or_none()


async def create_subject(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    external_ref: str,
) -> Subject:
    """Create a subject and derive its stable pseudonymous tag.

    The tag is deterministic given (master_key, tenant, external_ref), so it
    can be recomputed later without storing any identity in the text.
    """
    settings = Settings()
    master = settings.resolve_master_key()
    tenant_secret = derive_tenant_secret(master_key=master, tenant_id=tenant_id)
    tag = derive_subject_tag(tenant_secret=tenant_secret, subject_external_ref=external_ref)
    subject = Subject(
        tenant_id=tenant_id,
        external_ref=external_ref,
        pseudonymous_tag=tag,
    )
    session.add(subject)
    await session.commit()
    await session.refresh(subject)
    return subject


async def get_subject(
    session: AsyncSession, subject_id: uuid.UUID
) -> Subject | None:
    return await session.get(Subject, subject_id)


async def list_subjects(session: AsyncSession, tenant_id: uuid.UUID) -> list[Subject]:
    result = await session.execute(
        select(Subject).where(Subject.tenant_id == tenant_id).order_by(Subject.created_at)
    )
    return list(result.scalars())


async def create_credential(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    subject_id: uuid.UUID,
) -> tuple[str, ApiCredential]:
    """Create a new API credential. Returns (raw_token, credential)."""
    token = generate_token()
    credential = ApiCredential(
        tenant_id=tenant_id,
        subject_id=subject_id,
        token_hash=hash_token(token),
    )
    session.add(credential)
    await session.commit()
    await session.refresh(credential)
    return token, credential


async def resolve_token(
    session: AsyncSession, token: str
) -> tuple[Tenant, Subject] | None:
    """Resolve a raw bearer token to its (tenant, subject)."""
    from tracemark.auth.tokens import hash_token

    digest = hash_token(token)
    result = await session.execute(
        select(ApiCredential).where(ApiCredential.token_hash == digest)
    )
    credential = result.scalar_one_or_none()
    if credential is None or credential.revoked_at is not None:
        return None
    tenant = await session.get(Tenant, credential.tenant_id)
    subject = await session.get(Subject, credential.subject_id)
    if tenant is None or subject is None or not subject.active:
        return None
    return tenant, subject


def subject_fingerprint_key(tenant_id: uuid.UUID, subject: Subject) -> bytes:
    """Derive the fingerprint key for a stored subject (uses its tag)."""
    from tracemark.crypto.fingerprint import derive_key_from_subject_tag

    settings = Settings()
    master = settings.resolve_master_key()
    tenant_secret = derive_tenant_secret(master_key=master, tenant_id=tenant_id)
    return derive_key_from_subject_tag(
        tenant_secret=tenant_secret, subject_tag=subject.pseudonymous_tag
    )
