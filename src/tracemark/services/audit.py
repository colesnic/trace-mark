"""Generation event auditing.

By default only hashes and provenance metadata are stored, never raw prompts
or responses. Raw retention is opt-in and development-only.
"""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from tracemark.config import Settings
from tracemark.db.models import GenerationEvent


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


async def record_generation(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    subject_id: uuid.UUID,
    provider: str | None,
    model: str | None,
    policy_name: str,
    input_text: str | None,
    original_output: str,
    watermarked_output: str,
    opportunity_count: int,
    embedded_count: int,
) -> GenerationEvent:
    settings = Settings()
    retain = settings.retain_raw
    event = GenerationEvent(
        tenant_id=tenant_id,
        subject_id=subject_id,
        provider=provider,
        model=model,
        policy_name=policy_name,
        input_hash=sha256_hex(input_text) if input_text is not None else None,
        original_output_hash=sha256_hex(original_output),
        watermarked_output_hash=sha256_hex(watermarked_output),
        opportunity_count=opportunity_count,
        embedded_count=embedded_count,
        raw_input=input_text if retain else None,
        raw_output=watermarked_output if retain else None,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event
