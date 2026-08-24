"""LLM proxy integration tests using a mocked OpenAI-compatible upstream."""

from __future__ import annotations

import uuid

import httpx
import pytest

from tracemark.db.session import dispose_engine, get_engine

pytestmark = pytest.mark.anyio

ADMIN = {"Authorization": "Bearer dev-admin-token"}


def _upstream_response(text: str) -> dict:
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "deepseek-chat",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 20, "total_tokens": 25},
    }


@pytest.fixture
async def client(monkeypatch):
    from tracemark.db import models  # noqa: F401
    from tracemark.db.base import Base

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    upstream_calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        upstream_calls.append({"url": str(request.url), "json": request.content})
        body = request.read()
        payload = __import__("json").loads(body)
        model = payload.get("model", "deepseek-chat")
        return httpx.Response(
            200,
            json=_upstream_response(
                f"The report covers revenue, expenses and liabilities for {model}."
            ),
        )

    transport = httpx.MockTransport(handler)
    upstream_client = httpx.AsyncClient(transport=transport, base_url="https://upstream")

    from tracemark.main import app

    app.state.http_client = upstream_client
    transport_app = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport_app, base_url="http://test") as c:
        yield c, upstream_calls
    await upstream_client.aclose()
    await dispose_engine()


async def _setup_subject(client):
    resp = await client.post(
        "/v1/admin/tenants", json={"name": f"proxy-{uuid.uuid4().hex[:8]}"}, headers=ADMIN
    )
    tenant = resp.json()
    resp = await client.post(
        f"/v1/admin/tenants/{tenant['id']}/subjects",
        json={"external_ref": "employee-p"},
        headers=ADMIN,
    )
    subject = resp.json()
    resp = await client.post(
        f"/v1/admin/tenants/{tenant['id']}/subjects/{subject['id']}/credentials",
        headers=ADMIN,
    )
    token = resp.json()["token"]
    return token, tenant, subject


async def test_proxy_watermarks_assistant_content(client):
    c, upstream_calls = client
    token, _, _ = await _setup_subject(c)
    resp = await c.post(
        "/v1/chat/completions",
        json={
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": "Summarize the report."}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    content = body["choices"][0]["message"]["content"]
    # The upstream was called with the internal model name (prefix stripped).
    assert any(b"deepseek-chat" in u["json"] for u in upstream_calls)
    # Natural-language content got watermarked: serial comma present or expanded.
    assert "revenue, expenses" in content or "revenue, expenses," in content
    # Model is echoed back under the public routing id.
    assert body["model"] == "deepseek/deepseek-chat"


async def test_proxy_skips_json_mode(client):
    c, _ = client
    token, _, _ = await _setup_subject(c)
    resp = await c.post(
        "/v1/chat/completions",
        json={
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": "Return JSON."}],
            "response_format": {"type": "json_object"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    content = resp.json()["choices"][0]["message"]["content"]
    assert content == "The report covers revenue, expenses and liabilities for deepseek-chat."


async def test_proxy_rejects_streaming(client):
    c, _ = client
    token, _, _ = await _setup_subject(c)
    resp = await c.post(
        "/v1/chat/completions",
        json={
            "model": "openai/gpt-4o",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "streaming is not supported" in resp.json()["detail"]


async def test_proxy_requires_auth(client):
    c, _ = client
    resp = await c.post(
        "/v1/chat/completions",
        json={
            "model": "openai/gpt-4o",
            "messages": [{"role": "user", "content": "Hi"}],
        },
    )
    assert resp.status_code == 401
