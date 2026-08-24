"""Fingerprint detection.

Detection is split into two phases so that candidate scaling is cheap:

1. ``decode_document`` — parse, find and decode opportunities ONCE.
2. ``score_candidate`` — pure cryptographic scoring (one HMAC per
   opportunity), no NLP.

For N candidates this is 1 spaCy parse + N cheap key comparisons instead of
N parses.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from tracemark.crypto.fingerprint import expected_bit
from tracemark.watermark.engine import (
    find_opportunities,
    get_nlp,
    select_non_overlapping_opportunities,
)
from tracemark.watermark.opportunities import opportunity_id
from tracemark.watermark.policy import WatermarkPolicy
from tracemark.watermark.rules.base import (
    get_registry,
)
from tracemark.watermark.scorer import (
    binomial_tail_probability,
    bonferroni_adjust,
    evidence_score,
)


@dataclass(frozen=True)
class FingerprintCandidate:
    subject_tag: str
    model_scope: str | None
    key: bytes


@dataclass(frozen=True)
class DecodedOpportunity:
    ident: bytes
    observed_bit: int
    rule_id: str


@dataclass(frozen=True)
class DecodedDocument:
    """A document decoded once, ready to be scored against many keys."""

    text: str
    opportunities: tuple[DecodedOpportunity, ...] = ()

    @property
    def usable_opportunities(self) -> int:
        return len(self.opportunities)


@dataclass(frozen=True)
class CandidateScore:
    subject_tag: str
    model_scope: str | None
    opportunities: int
    matches: int
    match_rate: float
    p_value: float
    adjusted_p_value: float
    evidence_score: float


@dataclass(frozen=True)
class DetectionResult:
    detected: bool
    usable_opportunities: int
    best_candidate: CandidateScore | None
    runner_up: CandidateScore | None
    candidates_tested: int
    reason: str
    scores: list[CandidateScore] = field(default_factory=list)


def decode_document(
    text: str,
    policy: WatermarkPolicy,
) -> DecodedDocument:
    """Parse, find and decode opportunities in ``text`` exactly once."""
    registry = get_registry()
    doc = get_nlp()(text)
    opportunities = select_non_overlapping_opportunities(
        find_opportunities(text, doc, policy), policy
    )
    decoded: list[DecodedOpportunity] = []
    for opp in opportunities:
        rule = registry.get(opp.rule_id)
        bit = rule.decode_opportunity(text, opp.start, opp.end)
        if bit is None:
            continue
        ident = opportunity_id(
            rule_id=opp.rule_id,
            canonical_sentence=opp.canonical_context,
            canonical_target=opp.canonical_target,
            occurrence_index=opp.occurrence_index,
        )
        decoded.append(
            DecodedOpportunity(ident=ident, observed_bit=bit, rule_id=opp.rule_id)
        )
    return DecodedDocument(text=text, opportunities=tuple(decoded))


def score_candidate(
    document: DecodedDocument,
    fingerprint_key: bytes,
    *,
    subject_tag: str,
    model_scope: str | None = None,
    candidate_count: int,
) -> CandidateScore:
    """Score one candidate against a decoded document. No NLP involved."""
    total = document.usable_opportunities
    matches = 0
    for d in document.opportunities:
        if expected_bit(fingerprint_key, d.ident) == d.observed_bit:
            matches += 1
    p = binomial_tail_probability(matches=matches, total=total)
    adjusted = bonferroni_adjust(p, candidate_count)
    return CandidateScore(
        subject_tag=subject_tag,
        model_scope=model_scope,
        opportunities=total,
        matches=matches,
        match_rate=(matches / total) if total else 0.0,
        p_value=p,
        adjusted_p_value=adjusted,
        evidence_score=evidence_score(adjusted),
    )


def score_candidates(
    document: DecodedDocument,
    candidates: Sequence[FingerprintCandidate],
) -> list[CandidateScore]:
    """Score every candidate against one decoded document."""
    return [
        score_candidate(
            document,
            cand.key,
            subject_tag=cand.subject_tag,
            model_scope=cand.model_scope,
            candidate_count=len(candidates),
        )
        for cand in candidates
    ]


def detect_fingerprint(
    *,
    text: str,
    candidates: Sequence[FingerprintCandidate],
    policy: WatermarkPolicy,
) -> DetectionResult:
    """Detect which candidate fingerprint best explains the observed variants.

    Returns insufficient-evidence results without attributing when the
    document has too few usable opportunities.
    """
    document = decode_document(text, policy)
    total = document.usable_opportunities
    scores = score_candidates(document, candidates)

    if total < policy.minimum_opportunities:
        return DetectionResult(
            detected=False,
            usable_opportunities=total,
            best_candidate=None,
            runner_up=None,
            candidates_tested=len(candidates),
            reason="insufficient_evidence",
            scores=scores,
        )

    ranked = sorted(
        scores,
        key=lambda s: (-s.matches, -s.evidence_score, s.subject_tag),
    )
    best = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None

    separation = 0.0
    if runner_up is not None:
        separation = best.evidence_score - runner_up.evidence_score

    if best.adjusted_p_value >= 0.05:
        return DetectionResult(
            detected=False,
            usable_opportunities=total,
            best_candidate=best,
            runner_up=runner_up,
            candidates_tested=len(candidates),
            reason="not_significant",
            scores=scores,
        )
    if separation < policy.minimum_separation:
        return DetectionResult(
            detected=False,
            usable_opportunities=total,
            best_candidate=best,
            runner_up=runner_up,
            candidates_tested=len(candidates),
            reason="insufficient_separation",
            scores=scores,
        )

    return DetectionResult(
        detected=True,
        usable_opportunities=total,
        best_candidate=best,
        runner_up=runner_up,
        candidates_tested=len(candidates),
        reason="detected",
        scores=scores,
    )
