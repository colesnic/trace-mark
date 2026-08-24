"""Corpus ingestion base types and processing helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class CorpusDocument:
    """A single processed document from a public corpus.

    ``author_id`` and ``document_id`` are anonymized/pseudonymous — never raw
    personal identifiers for sensitive corpora.
    """

    corpus: str
    document_id: str

    text: str

    category: str | None = None
    author_id: str | None = None

    human_or_machine: str | None = None
    generator: str | None = None

    word_count: int = 0

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.word_count:
            self.word_count = len(self.text.split())


class CorpusSource(Protocol):
    """Interface for a downloadable public corpus.

    ``fetch`` must be repeatable and must not redownload when the expected
    files already exist. ``iter_documents`` yields cleaned ``CorpusDocument``
    records.
    """

    name: str

    def fetch(self, cache_dir: Path) -> None: ...

    def iter_documents(self, cache_dir: Path) -> Iterable[CorpusDocument]: ...


def pseudonymize(value: str, salt: str = "tracemark-corpus") -> str:
    """Stable short pseudonym for an identifier (never reversible easily)."""
    digest = hashlib.sha256(f"{salt}:{value}".encode()).digest()
    return digest[:16].hex()


def save_processed_jsonl(documents: Iterable[CorpusDocument], path: Path) -> None:
    """Persist processed documents as JSONL (anonymized, safe to keep local)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for doc in documents:
            fh.write(json.dumps(_doc_to_dict(doc), ensure_ascii=False) + "\n")


def load_processed_jsonl(path: Path) -> list[CorpusDocument]:
    documents: list[CorpusDocument] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            record = json.loads(line)
            documents.append(_doc_from_dict(record))
    return documents


def _doc_to_dict(doc: CorpusDocument) -> dict[str, Any]:
    return {
        "corpus": doc.corpus,
        "document_id": doc.document_id,
        "text": doc.text,
        "category": doc.category,
        "author_id": doc.author_id,
        "human_or_machine": doc.human_or_machine,
        "generator": doc.generator,
        "word_count": doc.word_count,
        "metadata": doc.metadata,
    }


def _doc_from_dict(record: dict[str, Any]) -> CorpusDocument:
    return CorpusDocument(
        corpus=record["corpus"],
        document_id=record["document_id"],
        text=record["text"],
        category=record.get("category"),
        author_id=record.get("author_id"),
        human_or_machine=record.get("human_or_machine"),
        generator=record.get("generator"),
        word_count=record.get("word_count", 0),
        metadata=record.get("metadata", {}),
    )
