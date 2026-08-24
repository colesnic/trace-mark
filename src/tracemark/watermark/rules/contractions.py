"""Rule H — Contractions.

Whitelisted contracted/expanded pairs only:

    do not <-> don't      does not <-> doesn't   did not <-> didn't
    is not <-> isn't      are not <-> aren't     was not <-> wasn't
    were not <-> weren't  has not <-> hasn't     have not <-> haven't
    cannot <-> can't      will not <-> won't

``shall not``, ``may not`` and ``must not`` are intentionally NOT included
(legal/regulatory modal language). Contractions inside quoted text are never
touched. This rule belongs to BALANCED mode.
"""

from __future__ import annotations

import re

import spacy

from tracemark.watermark.opportunities import canonical_context_for
from tracemark.watermark.policy import SafetyTier
from tracemark.watermark.protection import TextRange, is_protected
from tracemark.watermark.rules._scan import (
    find_enclosing_quote_range,
    scan_quote_pairs,
    sentence_index,
)
from tracemark.watermark.rules.base import (
    RuleMetadata,
    TransformRule,
    WatermarkOpportunity,
    register,
)

CONTRACTED_TO_EXPANDED = {
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "hasn't": "has not",
    "haven't": "have not",
    "can't": "cannot",
    "won't": "will not",
}

EXPANDED_FORMS = set(CONTRACTED_TO_EXPANDED.values())
CONTRACTED_FORMS = set(CONTRACTED_TO_EXPANDED.keys())
EXPANDED_TO_CONTRACTED = {v: k for k, v in CONTRACTED_TO_EXPANDED.items()}
EXPANDED_TO_CONTRACTED["can not"] = "can't"

_CONTRACTED_RE = re.compile(
    r"\b(?:don't|doesn't|didn't|isn't|aren't|wasn't|weren't|hasn't|haven't|can't|won't)\b",
    re.IGNORECASE,
)

_EXPANDED_RE = re.compile(
    r"\b(?:do not|does not|did not|is not|are not|was not|were not|"
    r"has not|have not|cannot|can not|will not)\b",
    re.IGNORECASE,
)

_VERB_POS = {"AUX", "VERB", "MOD"}

_METADATA = RuleMetadata(
    rule_id="contractions",
    safety_tier=SafetyTier.BALANCED,
    semantic_risk=0.1,
    style_impact=0.5,
    normalization_robustness=0.6,
    edit_robustness=0.85,
    description="Whitelisted contracted vs expanded verb phrases.",
)


def _apply_case(word: str, template: str) -> str:
    if template.isupper():
        return word.upper()
    if template[:1].isupper():
        return word.capitalize()
    return word.lower()


def expand_contractions(text: str) -> str:
    """Expand every whitelisted contracted form to its expanded canonical form."""

    def repl(match: re.Match) -> str:
        lower = match.group(0).lower()
        expanded = CONTRACTED_TO_EXPANDED[lower]
        return _apply_case(expanded, match.group(0))

    out = _CONTRACTED_RE.sub(repl, text)
    # "can not" (two words) is normalized to "cannot" for stability.
    out = re.sub(r"\bcan not\b", lambda m: _apply_case("cannot", m.group(0)), out)
    return out


class ContractionsRule(TransformRule):
    rule_id = "contractions"
    safety_tier = SafetyTier.BALANCED
    metadata = _METADATA

    def find_opportunities(
        self,
        text: str,
        doc: spacy.tokens.Doc,
        protected_ranges: list[TextRange],
    ) -> list[WatermarkOpportunity]:
        results: list[WatermarkOpportunity] = []
        pairs = scan_quote_pairs(text)
        per_sentence: dict[int, int] = {}

        matches: list[tuple[int, int, bool]] = []
        for match in _CONTRACTED_RE.finditer(text):
            matches.append((match.start(), match.end(), True))
        for match in _EXPANDED_RE.finditer(text):
            matches.append((match.start(), match.end(), False))
        matches.sort(key=lambda m: m[0])

        def handle(start: int, end: int, contracted: bool) -> None:
            if find_enclosing_quote_range(pairs, start, end) is not None:
                return
            if is_protected(protected_ranges, start, end):
                return
            if not contracted:
                span = doc.char_span(start, end)
                if span is None:
                    return
                if len(span) == 1:
                    if span[0].pos_ not in _VERB_POS:
                        return
                else:
                    if span[0].pos_ not in _VERB_POS:
                        return
                    if span[-1].dep_ != "neg":
                        return
            original = text[start:end]
            lower = original.lower()
            if contracted:
                expanded = CONTRACTED_TO_EXPANDED[lower]
                contracted_form = _apply_case(lower, original)
                expanded_form = _apply_case(expanded, original)
            else:
                expanded = "cannot" if lower == "can not" else lower
                contracted_form = _apply_case(EXPANDED_TO_CONTRACTED[lower], original)
                expanded_form = _apply_case(expanded, original)
            sent_idx = sentence_index(doc, start)
            occurrence = per_sentence.get(sent_idx, 0)
            per_sentence[sent_idx] = occurrence + 1
            results.append(
                WatermarkOpportunity(
                    rule_id=self.rule_id,
                    start=start,
                    end=end,
                    original=original,
                    variant_0=expanded_form,
                    variant_1=contracted_form,
                    canonical_target=expanded_form,
                    canonical_context=canonical_context_for(doc, start),
                    safety_tier=self.safety_tier.value,
                    confidence=0.9,
                    occurrence_index=occurrence,
                )
            )

        for start, end, contracted in matches:
            handle(start, end, contracted)
        return results

    def normalize_variants(self, text: str) -> str:
        return expand_contractions(text)

    def canonicalize_match(self, matched: str) -> str:
        lower = matched.lower()
        if lower in CONTRACTED_TO_EXPANDED:
            return _apply_case(CONTRACTED_TO_EXPANDED[lower], matched)
        if lower == "can not":
            return _apply_case("cannot", matched)
        return matched

    def decode_opportunity(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        lower = text[start:end].lower()
        if lower in CONTRACTED_FORMS:
            return 1
        if lower in EXPANDED_FORMS or lower == "can not":
            return 0
        return None


rule = ContractionsRule()
register(rule)
