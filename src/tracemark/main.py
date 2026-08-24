"""TraceMark FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from tracemark.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Shared outbound HTTP client for all provider adapters.
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=10.0),
        follow_redirects=True,
    )
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


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
