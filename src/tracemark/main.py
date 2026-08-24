"""TraceMark FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tracemark.api.admin import router as admin_router
from tracemark.api.detect import router as detect_router
from tracemark.api.proxy import router as proxy_router
from tracemark.api.ui import router as ui_router
from tracemark.api.watermark import router as watermark_router
from tracemark.config import get_settings

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Shared outbound HTTP client for all provider adapters.
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=10.0),
        follow_redirects=True,
    )
    if settings.is_development:
        # Ensure tables exist and seed demo data for the browser UI.
        from tracemark.db.session import init_db, session_scope
        from tracemark.services.demo import ensure_demo_data

        await init_db()
        async with session_scope() as session:
            app.state.demo = await ensure_demo_data(session)
            app.state.admin_token = settings.resolve_admin_token()
    logger.info("TraceMark starting (env=%s)", settings.env)
    yield
    await app.state.http_client.aclose()
    logger.info("TraceMark shutting down")


app = FastAPI(
    title="TraceMark",
    version="0.1.0",
    description="Model-agnostic forensic watermarking gateway for LLM text",
    lifespan=lifespan,
)

app.include_router(admin_router)
app.include_router(watermark_router)
app.include_router(detect_router)
app.include_router(proxy_router)
app.include_router(ui_router)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
