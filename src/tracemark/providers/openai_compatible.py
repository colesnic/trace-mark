"""OpenAI-compatible provider adapter.

Works for OpenAI, DeepSeek and any endpoint implementing the
``/chat/completions`` contract.
"""

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


class OpenAICompatibleAdapter:
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
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload = request.model_dump(exclude_none=True)
        logger.info(
            "proxy request provider=%s model=%s messages=%d stream=%s",
            self.name,
            request.model,
            len(request.messages),
            request.stream,
        )
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        data = response.json()
        try:
            choice = data["choices"][0]
            text = choice.get("message", {}).get("content") or ""
        except (KeyError, IndexError) as exc:
            raise RuntimeError("unexpected upstream response shape") from exc
        return ProviderCompletion(
            text=text,
            finish_reason=choice.get("finish_reason"),
            model=data.get("model"),
            raw=data,
        )
