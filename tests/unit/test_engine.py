from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.conftest import MASTER_KEY, TENANT
from tracemark.crypto.fingerprint import derive_fingerprint
from tracemark.watermark.engine import (
    apply_watermark,
    find_opportunities,
    select_non_overlapping_opportunities,
)
from tracemark.watermark.opportunities import canonicalize_for_fingerprinting
from tracemark.watermark.policy import WatermarkPolicy

_TEST_KEY = derive_fingerprint(
    master_key=MASTER_KEY, tenant_id=TENANT, subject_external_ref="alice"
).key
_TEST_POLICY = WatermarkPolicy.from_name("balanced")


def test_empty_text():
    res = apply_watermark(text="", fingerprint_key=_TEST_KEY, policy=_TEST_POLICY)
    assert res.text == ""
    assert res.opportunities_found == 0


def test_watermark_output_valid_unicode():
    text = "We don't believe it's fair, and we will not accept the plan."
    res = apply_watermark(text=text, fingerprint_key=_TEST_KEY, policy=_TEST_POLICY)
    res.text.encode("utf-8")  # must not raise
    assert isinstance(res.text, str)


def test_no_byte_loss_or_gain_outside_opportunities():
    text = "A plain sentence with no opportunities at all here."
    res = apply_watermark(text=text, fingerprint_key=_TEST_KEY, policy=_TEST_POLICY)
    assert res.text == text


def test_deterministic_watermark():
    text = "The report covers sales, marketing and operations; we do not accept delays."
    r1 = apply_watermark(text=text, fingerprint_key=_TEST_KEY, policy=_TEST_POLICY)
    r2 = apply_watermark(text=text, fingerprint_key=_TEST_KEY, policy=_TEST_POLICY)
    assert r1.text == r2.text
    assert [t.bit for t in r1.transformations] == [t.bit for t in r2.transformations]


def test_non_overlapping_selection(nlp):
    text = "We don't think the plan, and we will not accept it."
    doc = nlp(text)
    opps = find_opportunities(text, doc, _TEST_POLICY)
    chosen = select_non_overlapping_opportunities(opps, _TEST_POLICY)
    for i in range(len(chosen)):
        for j in range(i + 1, len(chosen)):
            a, b = chosen[i], chosen[j]
            assert not (a.start < b.end and b.start < a.end)


def test_watermark_preserves_non_opportunity_text():
    text = "The quick brown fox jumps over the lazy dog."
    res = apply_watermark(text=text, fingerprint_key=_TEST_KEY, policy=_TEST_POLICY)
    assert res.text == text
    assert res.opportunities_found == 0


@given(st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=0x2500), max_size=300))
@settings(max_examples=40, deadline=None)
def test_hypothesis_no_crash_offsets_valid(text):
    res = apply_watermark(text=text, fingerprint_key=_TEST_KEY, policy=_TEST_POLICY)
    assert len(res.text) >= 0
    assert res.text.encode("utf-8").decode("utf-8") == res.text


@given(st.text(min_size=1, max_size=200))
@settings(max_examples=30, deadline=None)
def test_hypothesis_canonicalization_idempotent(text):
    once = canonicalize_for_fingerprinting(text)
    twice = canonicalize_for_fingerprinting(once)
    assert once == twice


def test_watermark_roundtrip_preserves_offsets():
    # Each recorded transformation must reference the correct original span,
    # and transforms must be applied right-to-left (descending start).
    text = "One do not change. Two do not change. Three we will not allow."
    res = apply_watermark(text=text, fingerprint_key=_TEST_KEY, policy=_TEST_POLICY)
    starts = [t.start for t in res.transformations]
    assert starts == sorted(starts, reverse=True)
    for t in res.transformations:
        assert t.original == text[t.start : t.end]


def test_strict_policy_excludes_contractions():
    text = "We do not think it is fair, and we will not accept."
    strict = WatermarkPolicy.from_name("strict")
    res = apply_watermark(text=text, fingerprint_key=_TEST_KEY, policy=strict)
    assert all(t.rule_id != "contractions" for t in res.transformations)
