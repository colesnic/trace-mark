"""Development-only demo data seeding for the browser UI."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tracemark.db.models import Subject, Tenant
from tracemark.services.subjects import create_credential, create_subject, create_tenant

_DEMO_EMPLOYEES = {
    "alice": "employee-alice",
    "bob": "employee-bob",
    "carol": "employee-carol",
}


async def ensure_demo_data(session: AsyncSession) -> dict:
    """Create the Demo Corp tenant + subjects + credentials.

    Returns ``{"tenant_id": ..., "subjects": {subject_id: {"name", "token"}}}``.
    Development-only; never call in production.
    """
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.name == "Demo Corp")
    )
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        tenant = await create_tenant(session, "Demo Corp")

    subjects: dict[str, dict] = {}
    for external_ref in _DEMO_EMPLOYEES.values():
        subject_result = await session.execute(
            select(Subject).where(
                Subject.tenant_id == tenant.id, Subject.external_ref == external_ref
            )
        )
        subject = subject_result.scalar_one_or_none()
        if subject is None:
            subject = await create_subject(session, tenant.id, external_ref)

        # Mint a fresh credential every startup so the demo token is available.
        token, _credential = await create_credential(session, tenant.id, subject.id)
        subjects[str(subject.id)] = {
            "name": external_ref,
            "token": token,
            "tag": subject.pseudonymous_tag,
        }
    return {"tenant_id": str(tenant.id), "subjects": subjects}
