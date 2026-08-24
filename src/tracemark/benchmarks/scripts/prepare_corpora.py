"""Prepare processed JSONL corpora under ``.data/processed/``.

Reads raw sources, applies cleaning, anonymizes identifiers, and writes one
JSONL file per corpus. Repeatable and idempotent.

Usage::

    python -m tracemark.benchmarks.scripts.prepare_corpora --corpus enron
    python -m tracemark.benchmarks.scripts.prepare_corpora --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_RAW = Path(".data/raw")
_PROCESSED = Path(".data/processed")


def prepare_corpus(name: str) -> int:
    from tracemark.benchmarks.corpora.base import save_processed_jsonl
    from tracemark.benchmarks.corpora.registry import get_source

    source = get_source(name)
    raw_cache = _RAW / name
    out = _PROCESSED / f"{name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"[prepare] {name} -> {out}")
    docs = list(source.iter_documents(raw_cache))
    save_processed_jsonl(docs, out)
    print(f"[ok] {name}: {len(docs)} documents, {out.stat().st_size} bytes")
    return len(docs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare TraceMark corpora")
    parser.add_argument("--corpus", default=None, help="corpus name")
    parser.add_argument("--all", action="store_true", help="prepare every corpus")
    args = parser.parse_args()

    from tracemark.benchmarks.corpora.registry import available_sources

    if args.all:
        names = available_sources()
    elif args.corpus:
        names = [args.corpus]
    else:
        parser.error("provide --corpus NAME or --all")

    total = 0
    for name in names:
        try:
            total += prepare_corpus(name)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"[error] {name}: {exc}", file=sys.stderr)
    print(f"[done] {total} documents prepared")


if __name__ == "__main__":
    main()
