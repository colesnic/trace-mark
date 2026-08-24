"""Rule I — Abbreviation alternatives.

Very restricted whitelist:

    for example <-> e.g.
    that is    <-> i.e.

Preserves capitalization and surrounding punctuation. "that is" is only
matched when followed by a comma (avoiding the demonstrative sense in
sentences like "I think that is correct"). EXPERIMENTAL / BALANCED.
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

_ABBR_RE = re.compile(
    r"(?<![a-zA-Z0-9])(?:for example|that is|e\.g\.|i\.e\.)(?![a-zA-Z0-9])",
    re.IGNORECASE,
)

_LONG_FORMS = {"for example", "that is"}
_SHORT_FORMS = {"e.g.", "i.e."}

_METADATA = RuleMetadata(
    rule_id="abbreviations",
    safety_tier=SafetyTier.EXPERIMENTAL,
    semantic_risk=0.2,
    style_impact=0.4,
    normalization_robustness=0.7,
    edit_robustness=0.9,
    description="Long phrase vs standard abbreviation (for example/e.g.).",
)


def _apply_case(word: str, template: str) -> str:
    if template[:1].isupper():
        return word.capitalize()
    return word.lower()


class AbbreviationsRule(TransformRule):
    rule_id = "abbreviations"
    safety_tier = SafetyTier.EXPERIMENTAL
    metadata = _METADATA

    def find_opportunities(
        self,
        text: str,
        doc: spacy.tokens.Doc,
        protected_ranges: list[TextRange],
    ) -> list[WatermarkOpportunity]:
        results: list[WatermarkOpportunity] = []
        per_sentence: dict[int, int] = {}
        for match in _ABBR_RE.finditer(text):
            start, end = match.start(), match.end()
            original = text[start:end]
            lower = original.lower()
            if lower == "that is":
                # Require a following comma to avoid the demonstrative sense.
                j = end
                while j < len(text) and text[j] in " \t":
                    j += 1
                if j >= len(text) or text[j] != ",":
                    continue
            if is_protected(protected_ranges, start, end):
                continue
            sent_idx = sentence_index(doc, start)
            occurrence = per_sentence.get(sent_idx, 0)
            per_sentence[sent_idx] = occurrence + 1
            if lower in _LONG_FORMS:
                short = "e.g." if lower == "for example" else "i.e."
                long_form = original
                short_form = _apply_case(short, original)
            else:
                short_form = original
                long_form = "for example" if lower == "e.g." else "that is"
                long_form = _apply_case(long_form, original)
            results.append(
                WatermarkOpportunity(
                    rule_id=self.rule_id,
                    start=start,
                    end=end,
                    original=original,
                    variant_0=long_form,
                    variant_1=short_form,
                    canonical_target=long_form,
                    canonical_context=canonical_context_for(doc, start),
                    safety_tier=self.safety_tier.value,
                    confidence=0.8,
                    occurrence_index=occurrence,
                )
            )
        return results

    def normalize_variants(self, text: str) -> str:
        def repl(match: re.Match) -> str:
            lower = match.group(0).lower()
            if lower == "e.g.":
                return _apply_case("for example", match.group(0))
            if lower == "i.e.":
                return _apply_case("that is", match.group(0))
            return match.group(0)

        return _ABBR_RE.sub(repl, text)

    def canonicalize_match(self, matched: str) -> str:
        return self.normalize_variants(matched)

    def decode_opportunity(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        lower = text[start:end].lower()
        if lower in _LONG_FORMS:
            return 0
        if lower in _SHORT_FORMS:
            return 1
        return None


rule = AbbreviationsRule()
register(rule)
