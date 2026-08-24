"""API integration tests: admin, watermark, detect over HTTP."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from tracemark.db.session import dispose_engine, get_engine

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client():
    from tracemark.db import models  # noqa: F401
    from tracemark.db.base import Base

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from tracemark.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await dispose_engine()


ADMIN_TOKEN = "dev-admin-token"
A = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


async def _setup(client: AsyncClient, tenant_name: str | None = None) -> dict:
    name = tenant_name or f"tenant-{uuid.uuid4().hex[:8]}"
    resp = await client.post("/v1/admin/tenants", json={"name": name}, headers=A)
    assert resp.status_code == 201, resp.text
    tenant = resp.json()

    resp = await client.post(
        f"/v1/admin/tenants/{tenant['id']}/subjects",
        json={"external_ref": "employee-1"},
        headers=A,
    )
    assert resp.status_code == 201, resp.text
    subject = resp.json()

    resp = await client.post(
        f"/v1/admin/tenants/{tenant['id']}/subjects/{subject['id']}/credentials",
        headers=A,
    )
    assert resp.status_code == 201, resp.text
    credential = resp.json()
    return {"tenant": tenant, "subject": subject, "credential": credential}


async def test_admin_requires_token(client):
    resp = await client.post("/v1/admin/tenants", json={"name": "x"})
    assert resp.status_code == 401


async def test_watermark_requires_bearer(client):
    resp = await client.post(
        "/v1/watermark",
        json={"text": "We do not believe it."},
    )
    assert resp.status_code == 401


async def test_watermark_and_detect_flow(client):
    data = await _setup(client)
    token = data["credential"]["token"]
    text = (
        "The committee reviewed the annual report, the budget and the forecast. "
        "We do not believe the policy is fair, and we will not accept it. "
        "The manager said... it was a red, white and blue flag."
    )
    resp = await client.post(
        "/v1/watermark",
        json={"text": text, "policy": "balanced"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["subject_tag"] == data["subject"]["pseudonymous_tag"]
    assert body["opportunities_found"] >= 4
    assert body["text"] != text

    tenant_id = data["tenant"]["id"]
    resp = await client.post(
        "/v1/detect",
        json={"text": body["text"], "tenant_id": tenant_id, "policy": "balanced"},
        headers=A,
    )
    assert resp.status_code == 200, resp.text
    det = resp.json()
    # Short text -> honest insufficient evidence, never a fabricated attribution.
    assert det["detected"] is False
    assert det["reason"] == "insufficient_evidence"
    assert det["usable_opportunities"] < 20


async def test_detect_rejects_non_admin(client):
    data = await _setup(client)
    resp = await client.post(
        "/v1/detect",
        json={"text": "anything", "tenant_id": data["tenant"]["id"]},
    )
    assert resp.status_code == 401


async def test_watermark_uses_bound_identity(client):
    # The subject identity must come from the credential, not the request body.
    data = await _setup(client)
    token = data["credential"]["token"]
    resp = await client.post(
        "/v1/watermark",
        json={
            "text": "We do not believe it, and we will not accept it.",
            "policy": "balanced",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["subject_tag"] == data["subject"]["pseudonymous_tag"]


async def test_generation_event_recorded(client):
    data = await _setup(client)
    token = data["credential"]["token"]
    text = "The plan covers revenue, expenses and liabilities for the year."
    resp = await client.post(
        "/v1/watermark",
        json={"text": text, "policy": "balanced"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    from sqlalchemy import select

    from tracemark.db.models import GenerationEvent
    from tracemark.db.session import session_scope

    async with session_scope() as session:
        result = await session.execute(select(GenerationEvent))
        events = result.scalars().all()
    assert len(events) == 1
    assert events[0].opportunity_count > 0
    assert events[0].raw_input is None  # raw retention off by default


async def test_unknown_policy_rejected(client):
    data = await _setup(client)
    resp = await client.post(
        "/v1/watermark",
        json={"text": "hello", "policy": "nonsense"},
        headers={"Authorization": f"Bearer {data['credential']['token']}"},
    )
    assert resp.status_code == 422


async def test_detect_unknown_tenant(client):
    resp = await client.post(
        "/v1/detect",
        json={"text": "some text", "tenant_id": str(uuid.uuid4())},
        headers=A,
    )
    assert resp.status_code == 404
