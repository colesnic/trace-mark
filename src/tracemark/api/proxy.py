"""POST /v1/chat/completions — watermarking LLM proxy."""

from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tracemark.api.dependencies import get_session, get_settings
from tracemark.auth.dependencies import get_current_identity
from tracemark.config import Settings
from tracemark.crypto.fingerprint import derive_fingerprint
from tracemark.db.models import Subject, Tenant
from tracemark.providers.base import (
    ProviderCompletion,
    build_adapter,
    default_providers,
)
from tracemark.schemas.proxy import (
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from tracemark.services.audit import record_generation
from tracemark.services.subjects import subject_fingerprint_key
from tracemark.watermark.engine import WatermarkResult, apply_watermark
from tracemark.watermark.policy import WatermarkPolicy

router = APIRouter(prefix="/v1", tags=["proxy"])


def _route_model(model: str, settings: Settings):
    """Split a routing id like ``deepseek/deepseek-chat`` into (provider, model)."""
    prefix, _, rest = model.partition("/")
    for config in default_providers():
        if prefix in config.prefixes:
            return config, rest or prefix
    # Unknown prefix: default to OpenAI-compatible pass-through.
    from tracemark.providers.base import ProviderConfig

    return (
        ProviderConfig("openai", "https://api.openai.com/v1", "OPENAI_API_KEY", ("openai",)),
        model,
    )


def _should_watermark(request: ChatCompletionRequest, completion: ProviderCompletion) -> bool:
    """Only plain natural-language assistant content is watermarked."""
    if request.response_format:
        fmt = request.response_format.get("type")
        if fmt in {"json_object", "json_schema"}:
            return False
    raw = completion.raw or {}
    if raw.get("choices") and raw["choices"][0].get("message", {}).get("tool_calls"):
        return False
    if completion.text is None or not completion.text.strip():
        return False
    # Skip if the response is dominated by fenced code (machine-readable output).
    fenced = completion.text.count("```")
    if fenced >= 2:
        code_chars = sum(len(part) for part in _fenced_code_parts(completion.text))
        if code_chars / max(len(completion.text), 1) > 0.5:
            return False
    return True


def _fenced_code_parts(text: str) -> list[str]:
    parts: list[str] = []
    lines = text.splitlines(keepends=True)
    inside = False
    current: list[str] = []
    for line in lines:
        if line.lstrip().startswith("```") or line.lstrip().startswith("~~~"):
            if inside:
                inside = False
                parts.append("".join(current))
                current = []
            else:
                inside = True
        elif inside:
            current.append(line)
    return parts


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    identity: Annotated[tuple[Tenant, Subject], Depends(get_current_identity)],
    session: Annotated[AsyncSession, Depends(get_session)],
    http_request: Request,
) -> ChatCompletionResponse:
    tenant, subject = identity
    settings = get_settings()

    if request.stream:
        raise HTTPException(
            status_code=400,
            detail=(
                "streaming is not supported yet: post-generation watermarking "
                "requires the full response. Use stream=false."
            ),
        )

    provider, internal_model = _route_model(request.model, settings)
    adapter = build_adapter(provider)
    client = http_request.app.state.http_client

    upstream_request = request.model_copy(update={"model": internal_model})
    try:
        completion = await adapter.create_chat_completion(
            upstream_request, client, settings
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # upstream HTTP errors
        raise HTTPException(status_code=502, detail=f"upstream error: {exc}") from exc

    watermark_result: WatermarkResult | None = None
    if _should_watermark(request, completion):
        key = subject_fingerprint_key(tenant.id, subject)
        if provider.name:
            key = derive_fingerprint(
                master_key=Settings().resolve_master_key(),
                tenant_id=tenant.id,
                subject_external_ref=subject.external_ref,
                model_scope=provider.name,
            ).key
        policy = WatermarkPolicy.from_name("balanced")
        watermark_result = apply_watermark(
            text=completion.text, fingerprint_key=key, policy=policy
        )
        final_text = watermark_result.text
    else:
        final_text = completion.text

    await record_generation(
        session,
        tenant_id=tenant.id,
        subject_id=subject.id,
        provider=provider.name,
        model=request.model,
        policy_name="balanced" if watermark_result else "none",
        input_text=None,
        original_output=completion.text,
        watermarked_output=final_text,
        opportunity_count=watermark_result.opportunities_found
        if watermark_result
        else 0,
        embedded_count=watermark_result.transformations_applied
        if watermark_result
        else 0,
    )

    raw_choices = (completion.raw or {}).get("choices") or [{}]
    first = raw_choices[0]
    message = dict(first.get("message") or {})
    message["role"] = "assistant"
    message["content"] = final_text

    return ChatCompletionResponse(
        id=completion.raw.get("id") if completion.raw else f"chatcmpl-{uuid.uuid4().hex}",
        created=(
            completion.raw.get("created", int(time.time()))
            if completion.raw
            else int(time.time())
        ),
        model=request.model,
        choices=[{**first, "message": message}],
        usage=(completion.raw or {}).get("usage"),
    )
