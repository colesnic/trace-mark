"""Database + authentication integration tests (SQLite, in-memory)."""

from __future__ import annotations

from datetime import UTC

import pytest

from tracemark.auth.tokens import hash_token
from tracemark.db.session import dispose_engine, get_engine, get_session_factory
from tracemark.services.subjects import (
    create_credential,
    create_subject,
    create_tenant,
    list_subjects,
    resolve_token,
    subject_fingerprint_key,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
async def db_session():
    from tracemark.db import models  # noqa: F401
    from tracemark.db.base import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_session_factory()
    async with factory() as session:
        yield session
    await dispose_engine()


async def test_tenant_subject_credential_flow(db_session):
    tenant = await create_tenant(db_session, "Acme")
    assert tenant.id is not None

    subject = await create_subject(db_session, tenant.id, "employee-1")
    assert subject.pseudonymous_tag
    assert "employee-1" not in subject.pseudonymous_tag

    token, credential = await create_credential(db_session, tenant.id, subject.id)
    assert token
    assert credential.token_hash == hash_token(token)

    resolved = await resolve_token(db_session, token)
    assert resolved is not None
    r_tenant, r_subject = resolved
    assert r_tenant.id == tenant.id
    assert r_subject.id == subject.id


async def test_revoked_credential_rejected(db_session):
    tenant = await create_tenant(db_session, "RevCo")
    subject = await create_subject(db_session, tenant.id, "employee-2")
    token, credential = await create_credential(db_session, tenant.id, subject.id)

    from datetime import datetime

    credential.revoked_at = datetime.now(UTC)
    await db_session.commit()

    assert await resolve_token(db_session, token) is None


async def test_subject_tag_deterministic(db_session):
    tenant = await create_tenant(db_session, "DetCo")
    s1 = await create_subject(db_session, tenant.id, "same-ref")
    # Recompute the tag independently; it must match what was stored.
    from tracemark.config import Settings
    from tracemark.crypto.fingerprint import derive_subject_tag, derive_tenant_secret

    master = Settings().resolve_master_key()
    secret = derive_tenant_secret(master_key=master, tenant_id=tenant.id)
    recomputed = derive_subject_tag(tenant_secret=secret, subject_external_ref="same-ref")
    assert s1.pseudonymous_tag == recomputed


async def test_subject_fingerprint_key_stable_and_distinct(db_session):
    tenant = await create_tenant(db_session, "KeyCo")
    a = await create_subject(db_session, tenant.id, "alice")
    b = await create_subject(db_session, tenant.id, "bob")
    key_a1 = subject_fingerprint_key(tenant.id, a)
    key_a2 = subject_fingerprint_key(tenant.id, a)
    key_b = subject_fingerprint_key(tenant.id, b)
    assert key_a1 == key_a2
    assert key_a1 != key_b


async def test_list_subjects(db_session):
    tenant = await create_tenant(db_session, "ListCo")
    await create_subject(db_session, tenant.id, "x")
    await create_subject(db_session, tenant.id, "y")
    subjects = await list_subjects(db_session, tenant.id)
    assert len(subjects) == 2


async def test_unknown_token_rejected(db_session):
    assert await resolve_token(db_session, "not-a-real-token") is None
