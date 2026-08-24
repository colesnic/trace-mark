"""Watermark encoding engine."""

from __future__ import annotations

from dataclasses import dataclass, field

import spacy

from tracemark.crypto.fingerprint import expected_bit
from tracemark.watermark.opportunities import opportunity_id
from tracemark.watermark.policy import WatermarkPolicy
from tracemark.watermark.protection import detect_protected_ranges
from tracemark.watermark.rules.base import (
    WatermarkOpportunity,
    get_registry,
)

_nlp: spacy.Language | None = None


def get_nlp() -> spacy.Language:
    """Load the shared, lightweight spaCy pipeline (no NER)."""
    global _nlp
    if _nlp is None:
        import en_core_web_sm

        _nlp = en_core_web_sm.load(disable=["ner"])
    return _nlp


@dataclass
class AppliedTransformation:
    rule_id: str
    original: str
    replacement: str
    bit: int
    start: int
    end: int


@dataclass
class WatermarkResult:
    text: str
    opportunities_found: int
    transformations_applied: int
    transformations: list[AppliedTransformation] = field(default_factory=list)


def find_opportunities(
    text: str,
    doc: spacy.tokens.Doc,
    policy: WatermarkPolicy,
) -> list[WatermarkOpportunity]:
    """Collect all candidate opportunities across the policy's enabled rules."""
    protected = detect_protected_ranges(text)
    registry = get_registry()
    opportunities: list[WatermarkOpportunity] = []
    for rule in registry.enabled(policy):
        opportunities.extend(rule.find_opportunities(text, doc, protected))
    return opportunities


def select_non_overlapping_opportunities(
    opportunities: list[WatermarkOpportunity],
    policy: WatermarkPolicy,
) -> list[WatermarkOpportunity]:
    """Choose a non-overlapping set, deterministic priorities first.

    Priority order: rule priority (policy order), higher confidence, then
    deterministic rule-id / position tie-breakers.
    """
    priority = policy.priority

    def key(opp: WatermarkOpportunity):
        return (
            priority.get(opp.rule_id, len(priority)),
            -opp.confidence,
            opp.start,
            opp.rule_id,
        )

    ordered = sorted(opportunities, key=key)
    chosen: list[WatermarkOpportunity] = []
    for opp in ordered:
        overlaps = any(opp.start < other.end and other.start < opp.end for other in chosen)
        if not overlaps:
            chosen.append(opp)
    return chosen


def apply_watermark(
    *,
    text: str,
    fingerprint_key: bytes,
    policy: WatermarkPolicy,
    canonicalizer=None,
) -> WatermarkResult:
    """Apply a cryptographically keyed linguistic fingerprint.

    1. Detect protected spans.
    2. Parse text with spaCy.
    3. Find eligible opportunities across enabled rules.
    4. Remove unsafe and overlapping opportunities.
    5. Compute deterministic opportunity IDs and expected bits.
    6. Select the variant for each expected bit.
    7. Apply replacements right-to-left to preserve offsets.
    """
    if canonicalizer is None:
        from tracemark.watermark.canonicalizers import CASE_SENSITIVE

        canonicalizer = CASE_SENSITIVE
    if not text:
        return WatermarkResult(text=text, opportunities_found=0, transformations_applied=0)

    doc = get_nlp()(text)
    opportunities = select_non_overlapping_opportunities(
        find_opportunities(text, doc, policy), policy
    )

    selected: list[tuple[WatermarkOpportunity, str, int]] = []
    for opp in opportunities:
        ident = opportunity_id(
            rule_id=opp.rule_id,
            canonical_sentence=opp.canonical_context,
            canonical_target=opp.canonical_target,
            occurrence_index=opp.occurrence_index,
            casefold=canonicalizer.casefold,
        )
        bit = expected_bit(fingerprint_key, ident)
        selected.append((opp, opp.encode_variant(bit), bit))

    applied: list[AppliedTransformation] = []
    buffer = text
    for opp, replacement, bit in sorted(
        selected, key=lambda item: item[0].start, reverse=True
    ):
        original = buffer[opp.start : opp.end]
        buffer = buffer[: opp.start] + replacement + buffer[opp.end :]
        if replacement != original:
            applied.append(
                AppliedTransformation(
                    rule_id=opp.rule_id,
                    original=original,
                    replacement=replacement,
                    bit=bit,
                    start=opp.start,
                    end=opp.end,
                )
            )

    return WatermarkResult(
        text=buffer,
        opportunities_found=len(opportunities),
        transformations_applied=len(applied),
        transformations=applied,
    )
