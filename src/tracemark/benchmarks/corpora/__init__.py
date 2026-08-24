"""Public corpus ingestion framework for TraceMark research.

Never commit raw corpus data to git. All raw files live under ``.data/``
(gitignored). Only aggregate statistics, anonymized identifiers and small
synthetic fixtures may be committed.
"""

from __future__ import annotations

from pathlib import Path

from tracemark.benchmarks.corpora.base import (
    CorpusDocument,
    CorpusSource,
    load_processed_jsonl,
    save_processed_jsonl,
)

__all__ = ["CorpusDocument", "CorpusSource", "load_processed_jsonl", "save_processed_jsonl"]


def data_root() -> Path:
    return Path(".data")


def raw_dir() -> Path:
    path = data_root() / "raw"
    path.mkdir(parents=True, exist_ok=True)
    return path


def processed_dir() -> Path:
    path = data_root() / "processed"
    path.mkdir(parents=True, exist_ok=True)
    return path
