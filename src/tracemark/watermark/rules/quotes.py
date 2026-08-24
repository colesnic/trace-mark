"""Rule A — Quote style.

``"policy"`` (straight) vs ``\u201cpolicy\u201d`` (curly double) and
``'example'`` (straight) vs ``\u2018example\u2019`` (curly single).

Semantic risk: very low. Robustness: low against typography normalization.
"""

from __future__ import annotations

import spacy

from tracemark.watermark.opportunities import canonical_context_for
from tracemark.watermark.policy import SafetyTier
from tracemark.watermark.protection import TextRange, is_protected
from tracemark.watermark.rules._scan import scan_quote_pairs, sentence_index
from tracemark.watermark.rules.base import (
    RuleMetadata,
    TransformRule,
    WatermarkOpportunity,
    register,
)

_CURLY_TO_STRAIGHT = str.maketrans(
    {"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'"}
)
_STRAIGHT_TO_CURLY = str.maketrans(
    {'"': "\u201c", "'": "\u2018"}
)

_METADATA = RuleMetadata(
    rule_id="quotes",
    safety_tier=SafetyTier.STRICT,
    semantic_risk=0.01,
    style_impact=0.25,
    normalization_robustness=0.3,
    edit_robustness=0.9,
    description="Straight vs curly quotation marks around paired quoted text.",
)


class QuotesRule(TransformRule):
    rule_id = "quotes"
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
        for pair in scan_quote_pairs(text):
            if is_protected(protected_ranges, pair.start, pair.end):
                continue
            content = text[pair.start : pair.end]
            inner = content[1:-1]
            variant_0 = '"' + inner + '"' if pair.kind == "double" else "'" + inner + "'"
            variant_1 = "\u201c" + inner + "\u201d" if pair.kind == "double" else (
                "\u2018" + inner + "\u2019"
            )
            sent_idx = sentence_index(doc, pair.start)
            occurrence = per_sentence.get(sent_idx, 0)
            per_sentence[sent_idx] = occurrence + 1
            results.append(
                WatermarkOpportunity(
                    rule_id=self.rule_id,
                    start=pair.start,
                    end=pair.end,
                    original=content,
                    variant_0=variant_0,
                    variant_1=variant_1,
                    canonical_target=variant_0,
                    canonical_context=canonical_context_for(doc, pair.start),
                    safety_tier=self.safety_tier.value,
                    confidence=0.95,
                    occurrence_index=occurrence,
                )
            )
        return results

    def normalize_variants(self, text: str) -> str:
        return text.translate(_CURLY_TO_STRAIGHT)

    def canonicalize_match(self, matched: str) -> str:
        return self.normalize_variants(matched)

    def decode_opportunity(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        chunk = text[start:end]
        if not chunk:
            return None
        first = chunk[0]
        if first in {'"', "'"}:
            return 0
        if first in {"\u201c", "\u2018"}:
            return 1
        return None


rule = QuotesRule()
register(rule)
