"""Opportunity identification and canonical context handling."""

from __future__ import annotations

import hashlib

import spacy

from tracemark.watermark.rules.base import WatermarkOpportunity  # noqa: F401

_CANONICAL_ORDER = [
    "contractions",
    "serial_comma",
    "quotes",
    "apostrophes",
    "ellipsis",
    "dash_style",
]


def opportunity_id(
    *,
    rule_id: str,
    canonical_sentence: str,
    canonical_target: str,
    occurrence_index: int,
    casefold: bool = False,
) -> bytes:
    """Deterministic SHA-256 identifier for an opportunity.

    Depends only on canonical (variant-independent) inputs, so it is the
    same whether bit 0 or bit 1 was embedded. When ``casefold`` is set the
    inputs are case-folded before hashing (experimental; see
    ``watermark.canonicalizers``).
    """
    if casefold:
        canonical_sentence = canonical_sentence.casefold()
        canonical_target = canonical_target.casefold()
    hasher = hashlib.sha256()
    hasher.update(rule_id.encode("utf-8"))
    hasher.update(b"\x00")
    hasher.update(len(canonical_sentence).to_bytes(8, "big"))
    hasher.update(canonical_sentence.encode("utf-8"))
    hasher.update(b"\x00")
    hasher.update(len(canonical_target).to_bytes(8, "big"))
    hasher.update(canonical_target.encode("utf-8"))
    hasher.update(occurrence_index.to_bytes(8, "big"))
    return hasher.digest()


def canonicalize_for_fingerprinting(text: str, registry=None) -> str:
    """Normalize every supported watermark variation into a neutral form.

    This function is always applied with the full rule set, independent of
    the active policy, so that IDs computed while encoding and while
    detecting are identical even when a rule was disabled at encode time.
    """
    from tracemark.watermark.rules.base import get_registry

    registry = registry or get_registry()
    out = text
    for rule_id in _CANONICAL_ORDER:
        try:
            out = registry.get(rule_id).normalize_variants(out)
        except KeyError:
            continue
    return out


def sentence_containing(doc: spacy.tokens.Doc, pos: int) -> spacy.tokens.Span | None:
    for sent in doc.sents:
        if sent.start_char <= pos < sent.end_char:
            return sent
    return None


def canonical_context_for(
    doc: spacy.tokens.Doc,
    pos: int,
    registry=None,
) -> str:
    """Canonical sentence text for the sentence containing ``pos``."""
    sent = sentence_containing(doc, pos)
    if sent is None:
        return canonicalize_for_fingerprinting(doc.text, registry=registry)
    return canonicalize_for_fingerprinting(sent.text, registry=registry)
