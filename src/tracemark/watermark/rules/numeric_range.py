"""Rule E — Numeric range typography.

``10-12`` (hyphen) vs ``10\u201312`` (en dash).

Only applied when the token is *unquestionably* a numeric range:

- hyphen-separated, no surrounding spaces (avoid subtraction and spaced dashes)
- 1–4 digit numbers on both sides
- rejected when date-like (first number 1–12 AND second 1–31)
- rejected when part of a longer hyphenated sequence, a phone number, a
  version number, or negative numbers
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

_RANGE_RE = re.compile(r"(?<!\d)(\d{1,4})[-\u2013](\d{1,4})(?!\d)")

_METADATA = RuleMetadata(
    rule_id="numeric_range",
    safety_tier=SafetyTier.STRICT,
    semantic_risk=0.03,
    style_impact=0.1,
    normalization_robustness=0.6,
    edit_robustness=0.95,
    description="Hyphen vs en dash in unambiguous numeric ranges.",
)


class NumericRangeRule(TransformRule):
    rule_id = "numeric_range"
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
        for match in _RANGE_RE.finditer(text):
            start, end = match.start(), match.end()
            first = int(match.group(1))
            second = int(match.group(2))
            if not self._safe_range(first, second, text, start, end):
                continue
            if is_protected(protected_ranges, start, end):
                continue
            sent_idx = sentence_index(doc, start)
            occurrence = per_sentence.get(sent_idx, 0)
            per_sentence[sent_idx] = occurrence + 1
            original = text[start:end]
            hyphen_form = re.sub(r"\u2013", "-", original)
            en_form = re.sub(r"-", "\u2013", hyphen_form)
            results.append(
                WatermarkOpportunity(
                    rule_id=self.rule_id,
                    start=start,
                    end=end,
                    original=original,
                    variant_0=hyphen_form,
                    variant_1=en_form,
                    canonical_target=hyphen_form,
                    canonical_context=canonical_context_for(doc, start),
                    safety_tier=self.safety_tier.value,
                    confidence=0.9,
                    occurrence_index=occurrence,
                )
            )
        return results

    def _safe_range(
        self, first: int, second: int, text: str, start: int, end: int
    ) -> bool:
        # Date-like: first is a month (1–12) and second is a day (1–31).
        if 1 <= first <= 12 and 1 <= second <= 31:
            return False
        # Require first < second (a true range, not an ID or code).
        if first >= second:
            return False
        # Must not be part of a longer hyphenated token.
        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""
        return not (before == "-" or after == "-")

    def normalize_variants(self, text: str) -> str:
        return re.sub(r"(?<!\d)(\d{1,4})\u2013(\d{1,4})(?!\d)", r"\1-\2", text)

    def canonicalize_match(self, matched: str) -> str:
        return self.normalize_variants(matched)

    def decode_opportunity(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        chunk = text[start:end]
        if "\u2013" in chunk:
            return 1
        if "-" in chunk:
            return 0
        return None


rule = NumericRangeRule()
register(rule)
