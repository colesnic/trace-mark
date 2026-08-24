import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_healthz() -> None:
    from tracemark.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
