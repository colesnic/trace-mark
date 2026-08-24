"""LLM rewrite attacks and current-model generation (optional).

Requires provider API keys. Everything is cached on disk under
``.data/rewrite_cache/`` so repeated benchmark runs do not repeatedly incur
API costs. Privacy-sensitive corpora (Enron) are NEVER sent to providers.

Not required for CI.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from enum import Enum
from pathlib import Path

from tracemark.providers.base import ProviderAdapter
from tracemark.schemas.proxy import ChatCompletionRequest

CACHE_DIR = Path(".data/rewrite_cache")

_PROMPTS: dict[str, str] = {
    "light": (
        "Proofread the following text and make only minimal wording changes. "
        "Preserve the structure and the meaning exactly. Output only the revised text.\n\n{text}"
    ),
    "moderate": (
        "Rewrite the following text clearly while preserving all information and "
        "meaning. Keep the same length and structure. Output only the revised text.\n\n{text}"
    ),
    "heavy": (
        "Paraphrase the following text substantially while preserving the underlying "
        "meaning. Use different words and sentence constructions. Output only the "
        "revised text.\n\n{text}"
    ),
    "style": (
        "Rewrite the following text as a concise professional business memo while "
        "preserving all information and meaning. Output only the revised text.\n\n{text}"
    ),
}


class RewriteStrength(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    STYLE = "style"


def _cache_path(text: str, model: str, strength: str) -> Path:
    digest = hashlib.sha256(f"{model}:{strength}:{text}".encode()).hexdigest()[:24]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{digest}.json"


async def llm_rewrite_attack(
    *,
    text: str,
    provider: ProviderAdapter,
    model: str,
    strength: RewriteStrength,
) -> str:
    """Rewrite text via an LLM provider, reading from cache when available."""
    cache = _cache_path(text, model, strength.value)
    if cache.exists():
        record = json.loads(cache.read_text(encoding="utf-8"))
        return record["output"]

    prompt = _PROMPTS[strength.value].format(text=text)
    request = ChatCompletionRequest(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5 if strength in (RewriteStrength.LIGHT, RewriteStrength.MODERATE) else 0.8,
    )
    from tracemark.config import Settings

    completion = await provider.create_chat_completion(request, _client(), Settings())
    output = completion.text.strip()
    cache.write_text(json.dumps({"model": model, "strength": strength.value, "output": output}), encoding="utf-8")
    return output


async def generate_llm_benchmark_corpus(
    *,
    provider: ProviderAdapter,
    model: str,
    prompts: Sequence[dict],
    output_path: Path,
) -> None:
    """Generate a watermark-corpus via a live provider (public-safe prompts only)."""
    from tracemark.config import Settings

    output_path.parent.mkdir(parents=True, exist_ok=True)
    client = _client()
    records: list[dict] = []
    for prompt in prompts:
        request = ChatCompletionRequest(
            model=model,
            messages=[{"role": "user", "content": prompt["prompt"]}],
            temperature=prompt.get("temperature", 0.7),
        )
        completion = await provider.create_chat_completion(request, client, Settings())
        records.append(
            {
                "prompt_id": prompt["id"],
                "category": prompt["category"],
                "provider": provider.name,
                "model": model,
                "text": completion.text.strip(),
                "word_count": len(completion.text.split()),
            }
        )
    with open(output_path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _client():
    import httpx

    return httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))


def load_rewrite_prompts() -> list[dict]:
    from pathlib import Path

    prompts: list[dict] = []
    for path in sorted(Path("benchmarks/prompts").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                prompts.append(json.loads(line))
    return prompts
