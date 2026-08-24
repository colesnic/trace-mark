"""Rule B — Apostrophe style.

``company's`` (straight U+0027) vs ``company\u2019s`` (curly U+2019).

Semantic risk: very low. Only touches apostrophes between/bordering word
characters and never quote-pair delimiters.
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

_APOSTROPHES = {"'", "\u2019"}

_METADATA = RuleMetadata(
    rule_id="apostrophes",
    safety_tier=SafetyTier.STRICT,
    semantic_risk=0.01,
    style_impact=0.2,
    normalization_robustness=0.3,
    edit_robustness=0.95,
    description="Straight vs curly apostrophe in possessives and contractions.",
)


class ApostrophesRule(TransformRule):
    rule_id = "apostrophes"
    safety_tier = SafetyTier.STRICT
    metadata = _METADATA

    def find_opportunities(
        self,
        text: str,
        doc: spacy.tokens.Doc,
        protected_ranges: list[TextRange],
    ) -> list[WatermarkOpportunity]:
        results: list[WatermarkOpportunity] = []
        pairs = scan_quote_pairs(text)
        boundary = {
            pos
            for pair in pairs
            if pair.kind == "single"
            for pos in (pair.start, pair.end - 1)
        }
        per_sentence: dict[int, int] = {}
        for i, ch in enumerate(text):
            if ch not in _APOSTROPHES:
                continue
            if i in boundary:
                continue
            if i == 0:
                continue
            prev = text[i - 1]
            if not (prev.isalnum() or prev == "_"):
                continue
            if is_protected(protected_ranges, i, i + 1):
                continue
            sent_idx = sentence_index(doc, i)
            occurrence = per_sentence.get(sent_idx, 0)
            per_sentence[sent_idx] = occurrence + 1
            results.append(
                WatermarkOpportunity(
                    rule_id=self.rule_id,
                    start=i,
                    end=i + 1,
                    original=ch,
                    variant_0="'",
                    variant_1="\u2019",
                    canonical_target="'",
                    canonical_context=canonical_context_for(doc, i),
                    safety_tier=self.safety_tier.value,
                    confidence=0.95,
                    occurrence_index=occurrence,
                )
            )
        return results

    def normalize_variants(self, text: str) -> str:
        return text.replace("\u2019", "'")

    def canonicalize_match(self, matched: str) -> str:
        return self.normalize_variants(matched)

    def decode_opportunity(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        ch = text[start : start + 1]
        if ch == "'":
            return 0
        if ch == "\u2019":
            return 1
        return None


rule = ApostrophesRule()
register(rule)
