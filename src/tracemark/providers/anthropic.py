"""Anthropic (Claude Messages API) provider adapter."""

from __future__ import annotations

import logging

import httpx

from tracemark.config import Settings
from tracemark.providers.base import (
    ProviderCompletion,
    ProviderConfig,
)
from tracemark.schemas.proxy import ChatCompletionRequest

logger = logging.getLogger(__name__)

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter:
    name: str
    config: ProviderConfig

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.name = config.name

    async def create_chat_completion(
        self,
        request: ChatCompletionRequest,
        client: httpx.AsyncClient,
        settings: Settings,
    ) -> ProviderCompletion:
        api_key = getattr(settings, self.config.api_key_env.lower())
        if not api_key:
            raise RuntimeError(
                f"provider {self.name} is not configured "
                f"(missing {self.config.api_key_env})"
            )
        url = f"{self.config.base_url.rstrip('/')}/v1/messages"
        system_parts = [m.content for m in request.messages if m.role == "system" and m.content]
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role != "system" and m.content is not None
        ]
        payload: dict = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 1024,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        response = await client.post(
            url,
            json=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
            },
        )
        response.raise_for_status()
        data = response.json()
        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        return ProviderCompletion(
            text=text,
            finish_reason=data.get("stop_reason"),
            model=data.get("model"),
            raw=data,
        )
