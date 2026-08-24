"""Rule B — apostrophes: recognition, canonicalization, protection."""

from __future__ import annotations

import pytest

from tests.helpers import decode, find, unique_opp


@pytest.fixture(scope="module")
def rule(registry):
    return registry.get("apostrophes")


def test_straight_apostrophe_found(nlp, rule):
    opp = unique_opp(rule, "The company's revenue grew.", nlp)
    assert opp.original == "'"
    assert opp.variant_0 == "'"
    assert opp.variant_1 == "\u2019"
    assert decode(rule, "The company's revenue grew.", nlp) == 0
    assert decode(rule, "The company\u2019s revenue grew.", nlp) == 1


def test_curly_apostrophe_found(nlp, rule):
    opp = unique_opp(rule, "The company\u2019s revenue grew.", nlp)
    assert opp.original == "\u2019"
    assert decode(rule, "The company's revenue grew.", nlp) == 0
    assert decode(rule, "The company\u2019s revenue grew.", nlp) == 1


def test_trailing_possessive_found(nlp, rule):
    assert len(find(rule, "The dogs' owner arrived.", nlp)) >= 1


def test_single_quote_pair_delimiters_not_apostrophes(nlp, rule):
    opps = find(rule, "'quoted' text", nlp)
    assert len(opps) == 0


def test_contraction_inner_apostrophe_is_apostrophe(nlp, rule):
    opps = find(rule, "don't stop", nlp)
    assert len(opps) == 1
    assert opps[0].start == 3


def test_canonicalization_curly_to_straight(rule):
    assert rule.normalize_variants("company\u2019s") == "company's"


def test_no_apostrophe_leading(nlp, rule):
    assert len(find(rule, "'tis the season", nlp)) == 0


def test_unicode_apostrophe_in_word(nlp, rule):
    opp = unique_opp(rule, "Na\u00efve isn\u2019t here.", nlp)
    assert opp.variant_1 == "\u2019"
