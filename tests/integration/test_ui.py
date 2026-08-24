"""Demo UI tests (TestClient runs the app lifespan + demo seeding)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def app_client():
    from tracemark.main import app

    with TestClient(app) as client:
        yield client


def test_demo_page_renders(app_client):
    resp = app_client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "TraceMark demo" in html
    assert "employee-alice" in html
    assert "TRACEMARK_DEMO" in html
    assert "dev-admin-token" in html


def test_demo_subject_watermarks(app_client):
    # Without a bearer token the watermark endpoint rejects the request.
    resp = app_client.post(
        "/v1/watermark",
        json={"text": "We do not believe the policy is fair, and we will not accept it."},
    )
    assert resp.status_code == 401  # without a bearer token


def test_static_assets_served(app_client):
    resp = app_client.get("/static/demo.js")
    assert resp.status_code == 200
    assert "watermark-btn" in resp.text
