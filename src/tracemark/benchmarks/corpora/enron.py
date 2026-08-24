"""Enron email cleaning pipeline and corpus source.

The Enron corpus contains real people's communications. Even though it is
public, it is treated as privacy-sensitive research data:

- never commit raw emails to git
- never send raw emails to external LLM APIs
- use anonymized author identifiers in any results
"""

from __future__ import annotations

import email
import email.policy
import re
from collections.abc import Iterable
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from tracemark.benchmarks.corpora.base import CorpusDocument, pseudonymize

# --- conservative email-body cleaning -------------------------------------

_FORWARD_MARKERS = re.compile(
    r"^-{3,}.*(?:original message|forwarded message|forwarded by).*$-|"
    r"^from:\s.*$",
    re.IGNORECASE | re.MULTILINE,
)

_QUOTED_MARKER = re.compile(
    r"^\s*on\s+.+\s+wrote:\s*$", re.IGNORECASE | re.MULTILINE
)

_ENRON_DISCLAIMER = re.compile(
    r"this e-?mail is the property of the employer and is intended for",
    re.IGNORECASE,
)

_MACHINE_NOTICE = re.compile(
    r"(mail delivery subsystem|this is an? (automated|auto-generated)|"
    r"your (request|message) has been (processed|received)|"
    r"delivery (failure|has failed)|undeliverable|autoreply|out of office|"
    r"per this (notice|request)|terms? and conditions of use)",
    re.IGNORECASE,
)

_SIGNATURE_LINES = re.compile(
    r"^(phone|fax|pager|e-?mail|address|website|www\.|"
    r"\d{3}[\)\-. ]?\d{3}[-\. ]?\d{4}|"
    r"(legal|margaret|human resources|merchant energy|power company).*\d{4})$",
    re.IGNORECASE,
)


@dataclass
class CleanEmail:
    author_id: str
    text: str

    original_word_count: int
    cleaned_word_count: int

    removed_quoted_reply: bool
    removed_signature: bool


def clean_enron_email(raw_message: str) -> CleanEmail | None:
    """Extract natural-language email body from a raw RFC822 message.

    Returns None when the message is not usable (attachments, routing
    metadata, machine notices, or too little prose).
    """
    original_words = len(raw_message.split())

    msg = _parse_message(raw_message)
    if msg is None:
        return None

    body = _extract_text_body(msg)
    if body is None:
        return None

    lines = body.splitlines()
    cleaned: list[str] = []
    removed_quoted = False
    removed_signature = False

    quote_started = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append(line)
            continue
        if stripped.startswith(">"):
            removed_quoted = True
            continue
        if _QUOTED_MARKER.match(stripped):
            removed_quoted = True
            quote_started = True
            continue
        if _FORWARD_MARKERS.match(stripped):
            removed_quoted = True
            quote_started = True
            continue
        if _ENRON_DISCLAIMER.search(stripped):
            removed_signature = True
            break
        if re.match(r"^-----$", stripped):
            removed_signature = True
            break
        if quote_started:
            removed_quoted = True
            continue
        cleaned.append(line)

    text = "\n".join(cleaned).strip()
    if not text:
        return None

    text, removed_signature = _trim_trailing_signature(text, removed_signature)

    # Reject machine-generated notices / mostly non-prose content.
    if _MACHINE_NOTICE.search(text) and len(text.split()) < 40:
        return None

    cleaned_words = len(text.split())
    if cleaned_words < 15:
        return None

    alpha = sum(c.isalpha() for c in text)
    if alpha / max(len(text), 1) < 0.5:  # tables / binary junk
        return None

    return CleanEmail(
        author_id="",
        text=text,
        original_word_count=original_words,
        cleaned_word_count=cleaned_words,
        removed_quoted_reply=removed_quoted,
        removed_signature=removed_signature,
    )


def _trim_trailing_signature(text: str, removed_signature: bool) -> tuple[str, bool]:
    """Remove a trailing contact-information block (phone/fax/email/URL)."""
    lines = text.splitlines()
    end = len(lines)
    while end > 0:
        line = lines[end - 1].strip()
        if not line:
            end -= 1
            continue
        if _SIGNATURE_LINES.match(line) or re.match(
            r"^(thanks|regards|sincerely|best|thank you|v/r|\/\/?\/?\s*-?)$",
            line,
            re.IGNORECASE,
        ):
            end -= 1
            continue
        break
    if end != len(lines):
        return "\n".join(lines[:end]).strip(), True
    return text, removed_signature


def _parse_message(raw: str) -> EmailMessage | None:
    try:
        return email.message_from_string(raw, policy=email.policy.default)
    except Exception:
        return None


def _extract_text_body(msg: EmailMessage) -> str | None:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
        return None
    payload = msg.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return None


# --- Enron corpus source ---------------------------------------------------


class EnronSource:
    """Ingests the CMU Enron maildir corpus (2015 version)."""

    name = "enron"

    TARBALL = "enron_mail_20150507.tar.gz"
    SOURCE_URL = "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz"

    def fetch(self, cache_dir: Path) -> None:
        raw = cache_dir / self.TARBALL
        if raw.exists() and raw.stat().st_size > 400_000_000:
            return
        import subprocess
        import sys

        subprocess.run(
            [
                sys.executable,
                "-m",
                "tracemark.benchmarks.scripts.fetch_corpora",
                "--corpus",
                "enron",
            ],
            check=True,
        )

    def iter_documents(self, cache_dir: Path) -> Iterable[CorpusDocument]:
        tarball = cache_dir / self.TARBALL
        if not tarball.exists():
            self.fetch(cache_dir)
        for _idx, doc in enumerate(self._iter_from_tar(tarball)):
            yield doc

    def _iter_from_tar(self, tarball: Path) -> Iterable[CorpusDocument]:
        import tarfile

        with tarfile.open(tarball, "r:gz") as tar:
            for member in tar:
                if not member.isfile():
                    continue
                path = member.name  # e.g. maildir/<employee>/<folder>/<msg>
                parts = path.split("/")
                if len(parts) < 4 or parts[0] != "maildir":
                    continue
                employee = parts[1]
                fh = tar.extractfile(member)
                if fh is None:
                    continue
                try:
                    raw = fh.read().decode("utf-8", errors="replace")
                finally:
                    fh.close()
                cleaned = clean_enron_email(raw)
                if cleaned is None:
                    continue
                cleaned.author_id = pseudonymize(employee)
                doc_id = pseudonymize(f"{employee}:{member.name}")
                yield CorpusDocument(
                    corpus=self.name,
                    document_id=doc_id,
                    text=cleaned.text,
                    category="email",
                    author_id=cleaned.author_id,
                    human_or_machine="human",
                    generator=None,
                    word_count=cleaned.cleaned_word_count,
                    metadata={
                        "original_word_count": cleaned.original_word_count,
                        "removed_quoted_reply": cleaned.removed_quoted_reply,
                        "removed_signature": cleaned.removed_signature,
                    },
                )
