"""HC3 — Human ChatGPT Comparison Corpus.

Public dataset: https://huggingface.co/datasets/Hello-SimpleAI/HC3
JSONL files with ``question``, ``human_answers``, ``chatgpt_answers``,
``detector`` per line.

Used to compare watermark statistics on human-written vs LLM-written source
text (before TraceMark applies a watermark). TraceMark is NOT an AI detector.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from tracemark.benchmarks.corpora.base import CorpusDocument, pseudonymize

_DOMAINS = ["finance", "medicine", "open_qa", "reddit_eli5", "wiki_csai"]


class HC3Source:
    name = "hc3"

    def fetch(self, cache_dir: Path) -> None:
        for domain in _DOMAINS:
            out = cache_dir / f"hc3_{domain}.jsonl"
            if out.exists() and out.stat().st_size > 100_000:
                continue
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tracemark.benchmarks.scripts.fetch_corpora",
                    "--corpus",
                    "hc3",
                    "--domain",
                    domain,
                ],
                check=True,
            )

    def iter_documents(self, cache_dir: Path) -> Iterable[CorpusDocument]:
        for domain in _DOMAINS:
            path = cache_dir / f"hc3_{domain}.jsonl"
            if not path.exists():
                self.fetch(cache_dir)
            yield from self._iter_jsonl(path, domain)

    def _iter_jsonl(self, path: Path, domain: str) -> Iterable[CorpusDocument]:
        with open(path, encoding="utf-8") as fh:
            for idx, line in enumerate(fh):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                question = record.get("question", "")
                for a_idx, answer in enumerate(record.get("human_answers") or []):
                    text = answer.strip()
                    if text and question:
                        text = f"Q: {question}\nA: {text}"
                    elif not text:
                        continue
                    yield CorpusDocument(
                        corpus=self.name,
                        document_id=pseudonymize(f"{domain}:human:{idx}:{a_idx}"),
                        text=text,
                        category=domain,
                        author_id=None,
                        human_or_machine="human",
                        generator=None,
                        word_count=len(text.split()),
                        metadata={"question": question},
                    )
                for a_idx, answer in enumerate(record.get("chatgpt_answers") or []):
                    text = answer.strip()
                    if not text:
                        continue
                    if question:
                        text = f"Q: {question}\nA: {text}"
                    yield CorpusDocument(
                        corpus=self.name,
                        document_id=pseudonymize(f"{domain}:chatgpt:{idx}:{a_idx}"),
                        text=text,
                        category=domain,
                        author_id=None,
                        human_or_machine="machine",
                        generator="chatgpt",
                        word_count=len(text.split()),
                        metadata={"question": question},
                    )
