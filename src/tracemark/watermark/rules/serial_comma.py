"""Rule G — Serial / Oxford comma.

``A, B and C`` (no serial comma, bit 0) vs ``A, B, and C`` (serial comma,
bit 1).

Uses the spaCy dependency parse. Deliberately conservative:

- the conjunction must be a coordinating conjunction of a conjunct chain
- there must be a comma before the conjunction (a three-plus-item list)
- there must be a right-hand conjunct (the final item)
- proper-noun conjuncts are rejected (avoids "my friends, John and Mary"
  appositive false positives)
- only the region immediately before the conjunction is ever rewritten
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

_CONJUNCTIONS = {"and", "or", "nor"}

_METADATA = RuleMetadata(
    rule_id="serial_comma",
    safety_tier=SafetyTier.BALANCED,
    semantic_risk=0.15,
    style_impact=0.4,
    normalization_robustness=0.8,
    edit_robustness=0.8,
    description="Presence vs absence of the comma before a list conjunction.",
)


class SerialCommaRule(TransformRule):
    rule_id = "serial_comma"
    safety_tier = SafetyTier.BALANCED
    metadata = _METADATA

    def find_opportunities(
        self,
        text: str,
        doc: spacy.tokens.Doc,
        protected_ranges: list[TextRange],
    ) -> list[WatermarkOpportunity]:
        results: list[WatermarkOpportunity] = []
        per_sentence: dict[int, int] = {}
        for sent in doc.sents:
            tokens = list(sent)
            for tok in tokens:
                if tok.pos_ != "CCONJ" or tok.lower_ not in _CONJUNCTIONS:
                    continue
                if tok.dep_ != "cc":
                    continue
                result = self._analyze_conjunction(tok, tokens)
                if result is None:
                    continue
                first, comma_at, prev = result
                span_start = (
                    comma_at.idx if comma_at is not None else prev.idx + len(prev.text)
                )
                span_end = tok.idx + len(tok.text)
                if span_start < span_end and is_protected(
                    protected_ranges, span_start, span_end
                ):
                    continue
                sent_idx = sentence_index(doc, span_start)
                occurrence = per_sentence.get(sent_idx, 0)
                per_sentence[sent_idx] = occurrence + 1
                conjunction_word = tok.text
                results.append(
                    WatermarkOpportunity(
                        rule_id=self.rule_id,
                        start=span_start,
                        end=span_end,
                        original=text[span_start:span_end],
                        variant_0=" " + conjunction_word,
                        variant_1=", " + conjunction_word,
                        canonical_target=" " + tok.lower_,
                        canonical_context=canonical_context_for(doc, span_start),
                        safety_tier=self.safety_tier.value,
                        confidence=0.85,
                        occurrence_index=occurrence,
                    )
                )
        return results

    def _analyze_conjunction(
        self,
        tok: spacy.tokens.Token,
        tokens: list[spacy.tokens.Token],
    ) -> tuple[spacy.tokens.Token, spacy.tokens.Token | None, spacy.tokens.Token] | None:
        """Return (first_conjunct, comma_directly_before, prev_word)."""
        head = tok.head

        # Right-hand conjunct must exist (a real multi-item list).
        right_items = [
            c for c in head.children if c.dep_ == "conj" and c.i > tok.i
        ]
        if not right_items:
            return None

        if head.dep_ == "conj":
            # Chained coordination: "red, white and blue" (white.conj -> red).
            first = head.head
        else:
            # Flat coordination sharing a verb head:
            # "the budget, the schedule and the risks are..." (all nsubj).
            siblings = [t for t in tokens if t.head == head.head and t.i < head.i]
            if not siblings:
                return None
            first = siblings[0]
        if first == head or first.i >= tok.i:
            return None

        # Reject proper-noun conjuncts: avoids "friends, John and Mary".
        if first.pos_ == "PROPN" or head.pos_ == "PROPN" or right_items[0].pos_ == "PROPN":
            return None

        # Reject clause coordination: a conjunct with its own subject means
        # these are separate clauses, not a serial-comma list.
        # ("The dog barked, the cat slept and the bird sang.")
        if any(c.dep_ == "nsubj" for c in head.children):
            return None
        if any(c.dep_ == "nsubj" for c in right_items[0].children):
            return None

        # There must be at least one separator comma before the conjunction.
        comma_positions = [
            t
            for t in tokens
            if first.i < t.i < tok.i and t.is_punct and t.text == ","
        ]
        if not comma_positions:
            return None

        # The token immediately before the conjunction (skipping a directly
        # adjacent comma) must be the conjunct head.
        prev_idx = tokens.index(tok) - 1
        comma_at: spacy.tokens.Token | None = None
        if prev_idx >= 0 and tokens[prev_idx].text == ",":
            comma_at = tokens[prev_idx]
            prev_idx -= 1
        if prev_idx < 0 or tokens[prev_idx] != head:
            return None

        return first, comma_at, tokens[prev_idx]

    def normalize_variants(self, text: str) -> str:
        return re.sub(
            r",\s+(\b(?:and|or|nor)\b)",
            r" \1",
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
        if not chunk:
            return None
        lower = chunk.lower().lstrip(" ,")
        stripped = lower.strip()
        if stripped in _CONJUNCTIONS and "," in chunk:
            return 1
        if stripped in _CONJUNCTIONS:
            return 0
        return None


rule = SerialCommaRule()
register(rule)
