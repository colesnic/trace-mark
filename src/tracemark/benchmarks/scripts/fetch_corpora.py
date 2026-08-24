"""Download public corpora into ``.data/raw/``.

Usage::

    python -m tracemark.benchmarks.scripts.fetch_corpora --corpus enron
    python -m tracemark.benchmarks.scripts.fetch_corpora --corpus hc3 --domain finance
    python -m tracemark.benchmarks.scripts.fetch_corpora --corpus newsgroups

Only fetches what is missing; never redownloads complete files.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

_RAW = Path(".data/raw")


def _download(url: str, dest: Path, label: str) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[skip] {label}: {dest} already present")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[get]  {label}: {url}")
    urllib.request.urlretrieve(url, dest)  # noqa: S310 - public dataset mirror
    print(f"[ok]   {label}: {dest} ({dest.stat().st_size} bytes)")


def fetch_enron() -> None:
    _download(
        "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz",
        _RAW / "enron" / "enron_mail_20150507.tar.gz",
        "enron",
    )


def fetch_hc3(domain: str | None = None) -> None:
    domains = [domain] if domain else ["finance", "medicine", "open_qa", "reddit_eli5", "wiki_csai"]
    for d in domains:
        _download(
            f"https://huggingface.co/datasets/Hello-SimpleAI/HC3/resolve/main/{d}.jsonl",
            _RAW / "hc3" / f"hc3_{d}.jsonl",
            f"hc3:{d}",
        )


def fetch_newsgroups() -> None:
    _download(
        "https://qwone.com/~jason/20Newsgroups/20news-bydate.tar.gz",
        _RAW / "newsgroups" / "20news-bydate.tar.gz",
        "newsgroups",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch TraceMark benchmark corpora")
    parser.add_argument("--corpus", required=True, choices=["enron", "hc3", "newsgroups"])
    parser.add_argument("--domain", default=None, help="HC3 domain to fetch")
    args = parser.parse_args()

    if args.corpus == "enron":
        fetch_enron()
    elif args.corpus == "hc3":
        fetch_hc3(args.domain)
    elif args.corpus == "newsgroups":
        fetch_newsgroups()
    sys.exit(0)


if __name__ == "__main__":
    main()
