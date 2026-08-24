"""M4 — Multi-Generator, Multi-Domain, Multi-Lingual Machine-Generated Text.

Reference: https://huggingface.co/datasets/shotan23/M4-Machine-Generated-Text

The HF dataset is gated; this source attempts download and degrades to an
empty iterator with a logged notice when credentials/acceptance are absent.
When a local mirror exists at ``<cache_dir>/m4/`` as JSONL with records
``{"text", "label", "topic", "generator"}`` it is ingested from there.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path

from tracemark.benchmarks.corpora.base import CorpusDocument, pseudonymize

logger = logging.getLogger(__name__)

_MIRROR = "m4"
_DOMAINS = [
    "news",
    "abstract",
    "reddit_eli5",
    "tldr",
    "wikiHow",
    "paragraph",
    "wikinews",
    "recipe",
]


class M4Source:
    name = "m4"

    def fetch(self, cache_dir: Path) -> None:
        # Gated on HuggingFace; nothing to do automatically without approval.
        logger.info(
            "M4 is gated on HuggingFace. Place accepted export under "
            "%s/%s as JSONL to use it.", cache_dir, _MIRROR
        )

    def iter_documents(self, cache_dir: Path) -> Iterable[CorpusDocument]:
        mirror = cache_dir / _MIRROR
        if not mirror.exists():
            self.fetch(cache_dir)
            return
        for path in sorted(mirror.glob("*.jsonl")):
            yield from self._iter_jsonl(path)

    def _iter_jsonl(self, path: Path) -> Iterable[CorpusDocument]:
        with open(path, encoding="utf-8") as fh:
            for idx, line in enumerate(fh):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = (record.get("text") or "").strip()
                if not text:
                    continue
                label = record.get("label")
                generator = record.get("generator") or record.get("model") or "unknown"
                category = record.get("topic") or record.get("domain")
                yield CorpusDocument(
                    corpus=self.name,
                    document_id=pseudonymize(f"m4:{path.name}:{idx}"),
                    text=text,
                    category=str(category) if category else None,
                    author_id=None,
                    human_or_machine="machine" if label == 1 else "human",
                    generator=str(generator),
                    word_count=len(text.split()),
                    metadata={"label": label},
                )
