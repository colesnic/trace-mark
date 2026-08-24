"""Provider adapter interfaces."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from tracemark.config import Settings
from tracemark.schemas.proxy import ChatCompletionRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    # Public routing prefixes that map to this provider, e.g. ("openai", "deepseek").
    prefixes: tuple[str, ...]


@dataclass
class ProviderMessage:
    role: str
    content: str | None


@dataclass
class ProviderCompletion:
    text: str
    finish_reason: str | None = None
    model: str | None = None
    raw: dict | None = None


class ProviderAdapter(Protocol):
    """An upstream LLM provider that TraceMark can proxy."""

    name: str
    config: ProviderConfig

    async def create_chat_completion(
        self,
        request: ChatCompletionRequest,
        client: httpx.AsyncClient,
        settings: Settings,
    ) -> ProviderCompletion: ...


def build_adapter(config: ProviderConfig) -> ProviderAdapter:
    """Return the concrete adapter for a provider configuration."""
    from tracemark.providers.anthropic import AnthropicAdapter
    from tracemark.providers.openai_compatible import OpenAICompatibleAdapter

    if config.name == "anthropic":
        return AnthropicAdapter(config)
    return OpenAICompatibleAdapter(config)


def default_providers() -> list[ProviderConfig]:
    return [
        ProviderConfig(
            name="openai",
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            prefixes=("openai",),
        ),
        ProviderConfig(
            name="deepseek",
            base_url="https://api.deepseek.com",
            api_key_env="DEEPSEEK_API_KEY",
            prefixes=("deepseek",),
        ),
        ProviderConfig(
            name="anthropic",
            base_url="https://api.anthropic.com",
            api_key_env="ANTHROPIC_API_KEY",
            prefixes=("anthropic", "claude"),
        ),
    ]
