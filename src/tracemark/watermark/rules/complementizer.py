"""Rule J — Optional complementizer "that".

``We believe that the rule applies.`` (with "that", bit 1)
vs ``We believe the rule applies.`` (without "that", bit 0)

Only a small whitelist of verbs is used: believe, think, know, say, report,
expect. The complement clause must directly follow the verb. EXPERIMENTAL.
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

_WHITELIST = {"believe", "think", "know", "say", "report", "expect"}
_COMPLEMENT_DEP = {"ccomp", "attr"}

_METADATA = RuleMetadata(
    rule_id="complementizer_that",
    safety_tier=SafetyTier.EXPERIMENTAL,
    semantic_risk=0.25,
    style_impact=0.3,
    normalization_robustness=0.8,
    edit_robustness=0.7,
    description="Optional complementizer 'that' after a small verb whitelist.",
)


class ComplementizerThatRule(TransformRule):
    rule_id = "complementizer_that"
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
        for token in doc:
            if token.dep_ not in _COMPLEMENT_DEP:
                continue
            verb = token.head
            if verb.lemma_.lower() not in _WHITELIST:
                continue
            that_marker = None
            for child in token.children:
                if child.lower_ == "that" and child.dep_ == "mark":
                    that_marker = child
                    break
            if that_marker is not None:
                # "that" must directly follow the verb.
                if that_marker.i != verb.i + 1:
                    continue
                start = that_marker.idx
                end = that_marker.idx + len(that_marker.text)
                original = text[start:end]
                variant_0 = ""  # no "that"
                variant_1 = "that"  # with "that"
                canonical_target = ""
            else:
                # Insertion point is the gap between the verb and the clause.
                between = [t for t in doc if verb.i < t.i < token.i]
                if not between:
                    continue
                first_gap = between[0]
                if first_gap.pos_ in {"ADV", "PART", "SCONJ", "ADP", "PUNCT"}:
                    continue
                if any(t.is_punct for t in between):
                    continue
                start = verb.idx + len(verb.text)
                end = token.idx
                if start > end:
                    continue
                original = text[start:end]
                variant_0 = original  # no "that"
                variant_1 = "that" + original  # with "that"
                canonical_target = ""
            if is_protected(protected_ranges, start, end):
                continue
            sent_idx = sentence_index(doc, start)
            occurrence = per_sentence.get(sent_idx, 0)
            per_sentence[sent_idx] = occurrence + 1
            results.append(
                WatermarkOpportunity(
                    rule_id=self.rule_id,
                    start=start,
                    end=end,
                    original=original,
                    variant_0=variant_0,
                    variant_1=variant_1,
                    canonical_target=canonical_target,
                    canonical_context=canonical_context_for(doc, start),
                    safety_tier=self.safety_tier.value,
                    confidence=0.7,
                    occurrence_index=occurrence,
                )
            )
        return results

    def normalize_variants(self, text: str) -> str:
        # Remove a "that" marker directly after a whitelisted verb.
        return re.sub(
            r"\b(believe|think|know|say|report|expect)\b\s+that\b",
            r"\1",
            text,
            flags=re.IGNORECASE,
        )

    def canonicalize_match(self, matched: str) -> str:
        return self.normalize_variants(matched)

    def decode_opportunity(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        chunk = text[start:end]
        if "that" in chunk:
            return 1
        if chunk.strip() == "":
            return 0
        if chunk.startswith(" ") or chunk.strip().endswith(" "):
            return 0
        return 0


rule = ComplementizerThatRule()
register(rule)
