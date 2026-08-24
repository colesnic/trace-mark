"""Rule C — Ellipsis style.

``...`` (three dots) vs ``\u2026`` (single ellipsis character).

Only matched when the dots are clearly prose punctuation: exactly three dots,
not part of a longer run, and not adjacent to digits.
"""

from __future__ import annotations

import re

import spacy

from tracemark.watermark.opportunities import canonical_context_for
from tracemark.watermark.policy import SafetyTier
from tracemark.watermark.protection import TextRange, is_protected
from tracemark.watermark.rules._scan import sentence_index
from tracemark.watermark.rules.base import (
    RuleMetadata,
    TransformRule,
    WatermarkOpportunity,
    register,
)

_EXACT_THREE_DOTS = re.compile(r"(?<!\.)\.{3}(?!\.)")
_ELLIPSIS_CHAR = "\u2026"

_METADATA = RuleMetadata(
    rule_id="ellipsis",
    safety_tier=SafetyTier.STRICT,
    semantic_risk=0.02,
    style_impact=0.15,
    normalization_robustness=0.4,
    edit_robustness=0.95,
    description="Three dots vs single ellipsis character.",
)


class EllipsisRule(TransformRule):
    rule_id = "ellipsis"
    safety_tier = SafetyTier.STRICT
    metadata = _METADATA

    def find_opportunities(
        self,
        text: str,
        doc: spacy.tokens.Doc,
        protected_ranges: list[TextRange],
    ) -> list[WatermarkOpportunity]:
        results: list[WatermarkOpportunity] = []
        per_sentence: dict[int, int] = {}
        for match in _EXACT_THREE_DOTS.finditer(text):
            start, end = match.start(), match.end()
            if is_protected(protected_ranges, start, end):
                continue
            before = text[start - 1] if start > 0 else ""
            after = text[end] if end < len(text) else ""
            if before.isdigit() or after.isdigit():
                continue
            if before.isalpha() and after.isalpha():
                continue
            self._append(results, per_sentence, doc, start, end, "...")
        for start in _find_ellipsis_chars(text):
            if is_protected(protected_ranges, start, start + 1):
                continue
            before = text[start - 1] if start > 0 else ""
            after = text[start + 1] if start + 1 < len(text) else ""
            if before.isdigit() or after.isdigit():
                continue
            if before.isalpha() and after.isalpha():
                continue
            self._append(results, per_sentence, doc, start, start + 1, "\u2026")
        return results

    def _append(
        self,
        results: list[WatermarkOpportunity],
        per_sentence: dict[int, int],
        doc: spacy.tokens.Doc,
        start: int,
        end: int,
        original: str,
    ) -> None:
        sent_idx = sentence_index(doc, start)
        occurrence = per_sentence.get(sent_idx, 0)
        per_sentence[sent_idx] = occurrence + 1
        results.append(
            WatermarkOpportunity(
                rule_id=self.rule_id,
                start=start,
                end=end,
                original=original,
                variant_0="...",
                variant_1="\u2026",
                canonical_target="...",
                canonical_context=canonical_context_for(doc, start),
                safety_tier=self.safety_tier.value,
                confidence=0.9,
                occurrence_index=occurrence,
            )
        )

    def normalize_variants(self, text: str) -> str:
        return text.replace("\u2026", "...")

    def canonicalize_match(self, matched: str) -> str:
        return self.normalize_variants(matched)

    def decode_opportunity(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        chunk = text[start:end]
        if chunk == "...":
            return 0
        if chunk == "\u2026":
            return 1
        return None


def _find_ellipsis_chars(text: str) -> list[int]:
    """Positions of standalone ellipsis characters not adjacent to letters on
    both sides (mirrors the safety checks used for the three-dot form)."""
    positions = []
    for i, ch in enumerate(text):
        if ch == _ELLIPSIS_CHAR:
            positions.append(i)
    return positions


rule = EllipsisRule()
register(rule)
