"""Rule K — Markdown equivalent markers.

``**bold**`` vs ``__bold__`` and ``- item`` vs ``* item``.

Only applied to content the engine has determined is Markdown. EXPERIMENTAL.
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

_BOLD_ASTERISK = re.compile(r"\*\*([^*\n]+)\*\*")
_BOLD_UNDERSCORE = re.compile(r"__([^_\n]+)__")
_LIST_ITEM = re.compile(r"(?m)^[-*] ", )

_METADATA = RuleMetadata(
    rule_id="markdown",
    safety_tier=SafetyTier.EXPERIMENTAL,
    semantic_risk=0.1,
    style_impact=0.3,
    normalization_robustness=0.9,
    edit_robustness=0.8,
    description="Equivalent Markdown emphasis/list markers.",
)


class MarkdownRule(TransformRule):
    rule_id = "markdown"
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

        def add(start: int, end: int, original: str, variant_0: str, variant_1: str) -> None:
            if is_protected(protected_ranges, start, end):
                return
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
                    canonical_target=variant_0,
                    canonical_context=canonical_context_for(doc, start),
                    safety_tier=self.safety_tier.value,
                    confidence=0.85,
                    occurrence_index=occurrence,
                )
            )

        for match in _BOLD_ASTERISK.finditer(text):
            content = match.group(1)
            add(
                match.start(),
                match.end(),
                match.group(0),
                f"**{content}**",
                f"__{content}__",
            )
        for match in _BOLD_UNDERSCORE.finditer(text):
            content = match.group(1)
            add(
                match.start(),
                match.end(),
                match.group(0),
                f"**{content}**",
                f"__{content}__",
            )
        for match in _LIST_ITEM.finditer(text):
            marker = match.group(0).strip()
            add(
                match.start(),
                match.end(),
                marker + " ",
                "- ",
                "* ",
            )
        return results

    def normalize_variants(self, text: str) -> str:
        out = _BOLD_UNDERSCORE.sub(lambda m: f"**{m.group(1)}**", text)
        out = re.sub(r"(?m)^\* ", "- ", out)
        return out

    def canonicalize_match(self, matched: str) -> str:
        return self.normalize_variants(matched)

    def decode_opportunity(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        chunk = text[start:end]
        if chunk.startswith("**") or chunk.startswith("__"):
            return 0 if chunk.startswith("**") else 1
        stripped = chunk.strip()
        if stripped in {"-", "*"}:
            return 0 if stripped == "-" else 1
        return None


rule = MarkdownRule()
register(rule)
