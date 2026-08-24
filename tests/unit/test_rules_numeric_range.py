"""Rule E — numeric range typography tests."""

from __future__ import annotations

import pytest

from tests.helpers import decode, find, unique_opp


@pytest.fixture(scope="module")
def rule(registry):
    return registry.get("numeric_range")


def test_clear_range_found(nlp, rule):
    opp = unique_opp(rule, "The years 1980-1995 were busy.", nlp)
    assert opp.variant_0 == "1980-1995"
    assert opp.variant_1 == "1980\u20131995"
    assert decode(rule, "The years 1980-1995 were busy.", nlp) == 0
    assert decode(rule, "The years 1980\u20131995 were busy.", nlp) == 1


def test_large_first_number(nlp, rule):
    assert len(find(rule, "chapters 15-30", nlp)) == 1


def test_en_dash_form_found(nlp, rule):
    opp = unique_opp(rule, "pages 40\u201360", nlp)
    assert opp.original == "40\u201360"
    assert opp.variant_0 == "40-60"


def test_date_like_rejected(nlp, rule):
    assert len(find(rule, "pages 10-12", nlp)) == 0
    assert len(find(rule, "12-25 discount", nlp)) == 0
    assert len(find(rule, "on 5-8 items", nlp)) == 0


def test_descending_rejected(nlp, rule):
    assert len(find(rule, "version 1-2", nlp)) == 0
    assert len(find(rule, "10-5", nlp)) == 0


def test_phone_number_rejected(nlp, rule):
    assert len(find(rule, "call 555-123-4567", nlp)) == 0


def test_negative_number_rejected(nlp, rule):
    assert len(find(rule, "temperature -5", nlp)) == 0


def test_normalization(nlp, rule):
    assert rule.normalize_variants("40\u201360") == "40-60"
    assert rule.normalize_variants("40-60") == "40-60"


def test_watermark_roundtrip(nlp, rule):
    text = "The period 1980-1995 saw major change."
    opp = unique_opp(rule, text, nlp)
    assert opp.canonical_target == "1980-1995"
