"""Fingerprint detection integration tests — the core proof of concept."""

from __future__ import annotations

import random

import pytest

from tracemark.watermark.detector import (
    FingerprintCandidate,
    detect_fingerprint,
)
from tracemark.watermark.engine import apply_watermark

SENTENCES = [
    "The committee reviewed the annual report, the budget and the forecast.",
    "We do not believe the new policy is fair, and we will not accept it.",
    "The manager said... \u201cThis is a great opportunity, isn\u2019t it?\u201d",
    "It was a red, white and blue flag \u2014 it really was a sight to behold.",
    "The plan covers revenue, expenses and liabilities for the coming year.",
    "We do not think the deadline is realistic, and we cannot meet it.",
    "The report included sales, marketing and operations data.",
    "She was tired, hungry and frustrated after the long meeting.",
    "The board will not approve the merger, and it will not reverse course.",
    "Our system supports Linux, macOS and Windows without issue.",
    "The vendor said... \u201cThis version is stable, and it is not ready for production.\u201d",
    "The team analyzed cost, quality and timing trade-offs.",
    "We do not expect growth this quarter, and we will not raise guidance.",
    "The flag had red, white and blue stripes.",
    "It was a difficult, complex and risky decision \u2014 we knew it.",
    "The paper reviews methods, results and limitations.",
    "They were not ready for the launch, and they did not have a backup.",
    "The proposal includes scope, schedule and budget.",
    "We do not see a path forward, and we will not pretend otherwise.",
    "The menu offered soup, salad and sandwiches for lunch.",
]

DEFAULT_MASTER = b"\x42" * 32


def _derive(external_ref: str):
    from uuid import UUID

    from tracemark.crypto.fingerprint import derive_fingerprint

    tenant = UUID("11111111-1111-1111-1111-111111111111")
    return derive_fingerprint(
        master_key=DEFAULT_MASTER, tenant_id=tenant, subject_external_ref=external_ref
    )


@pytest.fixture(scope="module")
def rich_document():
    return " ".join(SENTENCES) * 2


@pytest.fixture(scope="module")
def balanced_policy():
    from tracemark.watermark.policy import WatermarkPolicy

    return WatermarkPolicy.from_name("balanced")


def _candidates(alice, bob, n_randoms: int = 5) -> list[FingerprintCandidate]:
    random.seed(1234)
    candidates = [
        FingerprintCandidate(alice.subject_tag, None, alice.key),
        FingerprintCandidate(bob.subject_tag, None, bob.key),
    ]
    for i in range(n_randoms):
        candidates.append(FingerprintCandidate(f"rand-{i}", None, random.randbytes(32)))
    return candidates


def _best(det):
    return det.best_candidate


def test_correct_employee_ranks_first(rich_document, balanced_policy):
    alice = _derive("alice")
    bob = _derive("bob")
    res = apply_watermark(
        text=rich_document, fingerprint_key=alice.key, policy=balanced_policy
    )
    assert res.opportunities_found >= 20

    det = detect_fingerprint(
        text=res.text, candidates=_candidates(alice, bob), policy=balanced_policy
    )
    assert det.detected is True
    assert det.best_candidate is not None
    assert det.best_candidate.subject_tag == alice.subject_tag
    assert det.best_candidate.match_rate >= 0.9
    assert det.best_candidate.adjusted_p_value < 0.05


def test_other_employee_near_chance(rich_document, balanced_policy):
    alice = _derive("alice")
    bob = _derive("bob")
    res = apply_watermark(
        text=rich_document, fingerprint_key=alice.key, policy=balanced_policy
    )
    det = detect_fingerprint(
        text=res.text, candidates=_candidates(alice, bob), policy=balanced_policy
    )
    assert det.best_candidate.subject_tag == alice.subject_tag
    bob_score = next(
        c for c in det.scores if c.subject_tag == bob.subject_tag
    )
    # Unrelated employee should be near 50%, with tolerance.
    assert 0.30 <= bob_score.match_rate <= 0.70


def test_same_document_bob_ranks_above_alice(rich_document, balanced_policy):
    alice = _derive("alice")
    bob = _derive("bob")
    res = apply_watermark(
        text=rich_document, fingerprint_key=bob.key, policy=balanced_policy
    )
    det = detect_fingerprint(
        text=res.text, candidates=_candidates(alice, bob), policy=balanced_policy
    )
    assert det.detected is True
    assert det.best_candidate.subject_tag == bob.subject_tag
    assert det.best_candidate.match_rate >= 0.9


def test_watermarked_as_alice_differs_from_bob_watermark(rich_document, balanced_policy):
    alice = _derive("alice")
    bob = _derive("bob")
    a = apply_watermark(text=rich_document, fingerprint_key=alice.key, policy=balanced_policy)
    b = apply_watermark(text=rich_document, fingerprint_key=bob.key, policy=balanced_policy)
    assert a.text != b.text


def test_unwatermarked_text_not_attributed(rich_document, balanced_policy):
    alice = _derive("alice")
    bob = _derive("bob")
    det = detect_fingerprint(
        text=rich_document, candidates=_candidates(alice, bob), policy=balanced_policy
    )
    # The raw text should not produce a confident, significant attribution.
    assert det.detected is False
    assert det.reason in {"insufficient_evidence", "not_significant", "insufficient_separation"}


def test_short_document_insufficient_evidence(balanced_policy):
    alice = _derive("alice")
    bob = _derive("bob")
    short = "A short note we will not expand into a long document today."
    res = apply_watermark(text=short, fingerprint_key=alice.key, policy=balanced_policy)
    det = detect_fingerprint(
        text=res.text, candidates=_candidates(alice, bob), policy=balanced_policy
    )
    assert det.usable_opportunities < 20
    assert det.detected is False
    assert det.reason == "insufficient_evidence"
    assert det.best_candidate is None


def test_edit_degradation_still_detects(rich_document, balanced_policy):
    alice = _derive("alice")
    bob = _derive("bob")
    res = apply_watermark(
        text=rich_document, fingerprint_key=alice.key, policy=balanced_policy
    )
    sentences = [s for s in res.text.split(". ") if s.strip()]
    # Delete ~20% of sentences.
    random.seed(5)
    random.shuffle(sentences)
    keep = int(len(sentences) * 0.8)
    edited = ". ".join(sentences[:keep]) + "."
    det = detect_fingerprint(
        text=edited, candidates=_candidates(alice, bob), policy=balanced_policy
    )
    assert det.usable_opportunities >= 20
    assert det.detected is True
    assert det.best_candidate.subject_tag == alice.subject_tag


def test_model_scope_fingerprints_distinct(rich_document, balanced_policy):
    alice_gpt = _derive("alice")
    from uuid import UUID

    from tracemark.crypto.fingerprint import derive_fingerprint

    tenant = UUID("11111111-1111-1111-1111-111111111111")
    alice_openai = derive_fingerprint(
        master_key=DEFAULT_MASTER,
        tenant_id=tenant,
        subject_external_ref="alice",
        model_scope="openai",
    )
    assert alice_gpt.key != alice_openai.key

    res = apply_watermark(
        text=rich_document, fingerprint_key=alice_openai.key, policy=balanced_policy
    )
    candidates = [
        FingerprintCandidate(alice_gpt.subject_tag, None, alice_gpt.key),
        FingerprintCandidate(alice_openai.subject_tag, "openai", alice_openai.key),
        FingerprintCandidate(_derive("bob").subject_tag, None, _derive("bob").key),
    ]
    det = detect_fingerprint(text=res.text, candidates=candidates, policy=balanced_policy)
    assert det.detected is True
    assert det.best_candidate.subject_tag == alice_openai.subject_tag
    assert det.best_candidate.model_scope == "openai"
