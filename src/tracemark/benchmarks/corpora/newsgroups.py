"""20 Newsgroups corpus — informal human writing across many authors/topics.

Download: https://qwone.com/~jason/20Newsgroups/20news-bydate.tar.gz
"""

from __future__ import annotations

import email
import email.policy
import subprocess
import sys
import tarfile
from collections.abc import Iterable
from pathlib import Path

from tracemark.benchmarks.corpora.base import CorpusDocument, pseudonymize

_TARBALL = "20news-bydate.tar.gz"
_URL = "https://qwone.com/~jason/20Newsgroups/20news-bydate.tar.gz"


class NewsgroupsSource:
    name = "newsgroups"

    def fetch(self, cache_dir: Path) -> None:
        out = cache_dir / _TARBALL
        if out.exists() and out.stat().st_size > 10_000_000:
            return
        subprocess.run(
            [
                sys.executable,
                "-m",
                "tracemark.benchmarks.scripts.fetch_corpora",
                "--corpus",
                "newsgroups",
            ],
            check=True,
        )

    def iter_documents(self, cache_dir: Path) -> Iterable[CorpusDocument]:
        tarball = cache_dir / _TARBALL
        if not tarball.exists():
            self.fetch(cache_dir)
        with tarfile.open(tarball, "r:gz") as tar:
            for member in tar:
                if not member.isfile():
                    continue
                parts = member.name.split("/")
                # 20news-bydate-{train,test}/<category>/<msg>
                if len(parts) < 3 or len(parts) > 4:
                    continue
                category = parts[-2]
                fh = tar.extractfile(member)
                if fh is None:
                    continue
                try:
                    raw = fh.read().decode("utf-8", errors="replace")
                finally:
                    fh.close()
                doc = _clean_newsgroup_post(raw, category, member.name)
                if doc is not None:
                    yield doc


def _decode_payload(payload: bytes, charset: str | None) -> str:
    if charset:
        try:
            return payload.decode(charset, errors="replace")
        except (LookupError, UnicodeDecodeError):
            pass
    return payload.decode("utf-8", errors="replace")


def _clean_newsgroup_post(raw: str, category: str, member_name: str) -> CorpusDocument | None:
    try:
        msg = email.message_from_string(raw, policy=email.policy.default)
    except Exception:
        msg = None
    if msg is not None and msg.get("from"):
        author = pseudonymize(msg.get("from", ""))
        body_parts: list[str] = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        body_parts.append(_decode_payload(payload, part.get_content_charset()))
        else:
            payload = msg.get_payload(decode=True)
            if isinstance(payload, bytes):
                body_parts.append(_decode_payload(payload, msg.get_content_charset()))
        body = "\n".join(body_parts)
    else:
        author = pseudonymize(member_name)
        # Fallback: strip RFC headers (everything before first blank line).
        split = raw.split("\n\n", 1)
        body = split[1] if len(split) > 1 else split[0]

    lines = [ln for ln in body.splitlines() if not ln.strip().startswith(">")]
    text = "\n".join(lines).strip()
    words = len(text.split())
    if words < 15:
        return None
    alpha = sum(c.isalpha() for c in text)
    if alpha / max(len(text), 1) < 0.5:
        return None
    return CorpusDocument(
        corpus="newsgroups",
        document_id=pseudonymize(member_name),
        text=text,
        category=category,
        author_id=author,
        human_or_machine="human",
        generator=None,
        word_count=words,
    )
