"""Minimal browser demo UI (FastAPI + Jinja2, no build pipeline)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tracemark.api.dependencies import get_session

router = APIRouter(tags=["ui"])

_templates = Jinja2Templates(directory="src/tracemark/templates")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def demo_page(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HTMLResponse:
    from tracemark.db.models import Subject

    result = await session.execute(
        select(Subject).where(Subject.active).order_by(Subject.created_at)
    )
    subjects = result.scalars().all()

    demo = getattr(request.app.state, "demo", {})
    # Only ever expose the development demo credentials.
    if demo:
        demo_js = {
            "admin_token": getattr(request.app.state, "admin_token", None),
            "tenant_id": demo.get("tenant_id"),
            "subjects": demo.get("subjects", {}),
        }
    else:
        demo_js = {"admin_token": None, "tenant_id": None, "subjects": {}}

    return _templates.TemplateResponse(
        request=request,
        name="demo.html",
        context={
            "subjects": subjects,
            "demo_js": demo_js,
        },
    )
