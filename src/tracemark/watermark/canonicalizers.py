"""Canonical-context strategies (experimental).

V1 uses a case-sensitive canonical context: opportunity IDs depend on the
original casing of the sentence. The case-insensitive mode casefolds the
canonical context and target before hashing, making IDs robust to
lowercasing at the cost of more cross-document ID collisions.

Production behavior remains case-sensitive; the case-insensitive mode is a
benchmarked experiment (see ``benchmarks/report_v2.py``).
"""

from __future__ import annotations

from typing import Protocol


class ContextCanonicalizer(Protocol):
    version: str
    casefold: bool


class _CaseSensitive:
    version = "case-sensitive"
    casefold = False

    def canonicalize_context(self, text: str) -> str:
        from tracemark.watermark.opportunities import canonicalize_for_fingerprinting

        return canonicalize_for_fingerprinting(text)


class _CaseInsensitive:
    version = "case-insensitive"
    casefold = True

    def canonicalize_context(self, text: str) -> str:
        from tracemark.watermark.opportunities import canonicalize_for_fingerprinting

        return canonicalize_for_fingerprinting(text).casefold()


CASE_SENSITIVE = _CaseSensitive()
CASEFOLDED = _CaseInsensitive()
