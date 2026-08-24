"""Rule D — Dash typography.

``word \u2014 word`` (spaced em dash) vs ``word\u2014word`` (unspaced em dash).

Only touches an em dash flanked by word characters. Hyphens are never touched.
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

_EM_DASH = "\u2014"
_WHITESPACE = re.compile(r"[ \t]")

_METADATA = RuleMetadata(
    rule_id="dash_style",
    safety_tier=SafetyTier.STRICT,
    semantic_risk=0.02,
    style_impact=0.15,
    normalization_robustness=0.5,
    edit_robustness=0.9,
    description="Spaced vs unspaced em dash between words.",
)


class DashStyleRule(TransformRule):
    rule_id = "dash_style"
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
        n = len(text)
        i = 0
        while i < n:
            if text[i] != _EM_DASH:
                i += 1
                continue
            left = i
            right = i + 1
            while left > 0 and text[left - 1] in " \t":
                left -= 1
            while right < n and text[right] in " \t":
                right += 1
            if (
                left > 0
                and right < n
                and _is_word_char(text[left - 1])
                and _is_word_char(text[right])
            ):
                if is_protected(protected_ranges, left, right):
                    i = right
                    continue
                sent_idx = sentence_index(doc, i)
                occurrence = per_sentence.get(sent_idx, 0)
                per_sentence[sent_idx] = occurrence + 1
                span = text[left:right]
                results.append(
                    WatermarkOpportunity(
                        rule_id=self.rule_id,
                        start=left,
                        end=right,
                        original=span,
                        variant_0=" \u2014 ",
                        variant_1=_EM_DASH,
                        canonical_target=" \u2014 ",
                        canonical_context=canonical_context_for(doc, i),
                        safety_tier=self.safety_tier.value,
                        confidence=0.9,
                        occurrence_index=occurrence,
                    )
                )
            i = right
        return results

    def normalize_variants(self, text: str) -> str:
        return re.sub(r"[ \t]*\u2014[ \t]*", " \u2014 ", text)

    def canonicalize_match(self, matched: str) -> str:
        return self.normalize_variants(matched)

    def decode_opportunity(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        chunk = text[start:end]
        if chunk == _EM_DASH:
            return 1
        if _WHITESPACE.search(chunk):
            return 0
        return None


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


rule = DashStyleRule()
register(rule)
