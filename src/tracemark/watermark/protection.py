"""Protected-span detection.

TraceMark must never modify content where a change could break functionality:
code blocks, URLs, emails, JSON/XML, markdown links, file paths, and so on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TEXT_RANGE_KIND = "text"

_FENCED_CODE = re.compile(r"(```+|~~~+)[^\n]*\n.*?\n?\1", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_URL = re.compile(r"https?://\S+")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\([^)]+\)")
_REF_LINK = re.compile(r"\[[^\]]*\]\[[^\]]*\]")
_XML_TAG = re.compile(r"<[a-zA-Z][^>]*>.*?</[a-zA-Z][^>]*>|<[a-zA-Z][^>]*/>")
_FILEPATH = re.compile(r"((?:/[\w.-]+)+|(?:[A-Za-z]:\\)[\w\\.-]*|~\/(?:[\w.-]+/)*[\w.-]+)")
# Conservative JSON-like block: balanced braces on a single line containing a quote.
_JSON_LIKE = re.compile(r"\{[^{}\n]*\"[^{}\n]*\"[^{}\n]*\}")


@dataclass(frozen=True)
class TextRange:
    start: int
    end: int
    kind: str = _TEXT_RANGE_KIND

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"invalid range {self.start}:{self.end}")

    def contains(self, other: TextRange) -> bool:
        return self.start <= other.start and other.end <= self.end

    def intersects(self, other: TextRange) -> bool:
        return self.start < other.end and other.start < self.end


def detect_protected_ranges(text: str) -> list[TextRange]:
    """Find spans of text that must never be modified.

    Ranges are merged when they overlap so a later rule can quickly test
    whether an opportunity intersects any protected span.
    """
    raw: list[TextRange] = []
    for pattern, kind in (
        (_FENCED_CODE, "code_fence"),
        (_INLINE_CODE, "inline_code"),
        (_URL, "url"),
        (_EMAIL, "email"),
        (_MARKDOWN_LINK, "markdown_link"),
        (_REF_LINK, "markdown_ref"),
        (_JSON_LIKE, "json"),
        (_XML_TAG, "xml"),
        (_FILEPATH, "filepath"),
    ):
        for match in pattern.finditer(text):
            raw.append(TextRange(match.start(), match.end(), kind))

    return _merge(sorted(raw, key=lambda r: (r.start, r.end)))


def _merge(ranges: list[TextRange]) -> list[TextRange]:
    merged: list[TextRange] = []
    for rng in ranges:
        if merged and rng.start <= merged[-1].end:
            prev = merged[-1]
            merged[-1] = TextRange(prev.start, max(prev.end, rng.end), prev.kind)
        else:
            merged.append(rng)
    return merged


def is_protected(protected: list[TextRange], start: int, end: int) -> bool:
    """True if the span [start, end) intersects any protected range."""
    for rng in protected:
        if rng.end <= start:
            continue
        if rng.start >= end:
            break
        return True
    return False
