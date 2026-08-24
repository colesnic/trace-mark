"""Rule H — contractions: recognition, canonicalization, negatives."""

from __future__ import annotations

import pytest

from tests.helpers import decode, find, unique_opp
from tracemark.watermark.rules.contractions import expand_contractions


@pytest.fixture(scope="module")
def rule(registry):
    return registry.get("contractions")


def test_expanded_found(nlp, rule):
    opp = unique_opp(rule, "We do not think so.", nlp)
    assert opp.variant_0 == "do not"
    assert opp.variant_1 == "don't"
    assert decode(rule, "We do not think so.", nlp) == 0
    assert decode(rule, "We don't think so.", nlp) == 1


def test_contracted_found(nlp, rule):
    opp = unique_opp(rule, "We don't think so.", nlp)
    assert opp.variant_1 == "don't"
    assert opp.original == "don't"


def test_capitalized_expansion(nlp, rule):
    opp = unique_opp(rule, "Do not enter.", nlp)
    assert opp.variant_1 == "Don't"


def test_all_caps_expansion(nlp, rule):
    opp = unique_opp(rule, "We DO NOT accept this.", nlp)
    assert opp.variant_1 == "DON'T"


def test_cannot_single_token(nlp, rule):
    opp = unique_opp(rule, "I cannot agree.", nlp)
    assert opp.variant_0 == "cannot"
    assert opp.variant_1 == "can't"


def test_can_not_two_tokens(nlp, rule):
    opp = unique_opp(rule, "I can not agree.", nlp)
    assert opp.variant_0 == "cannot"
    assert opp.variant_1 == "can't"


def test_whitelist_forms_all_mapped(rule):
    pairs = {
        "do not": "don't",
        "does not": "doesn't",
        "did not": "didn't",
        "is not": "isn't",
        "are not": "aren't",
        "was not": "wasn't",
        "were not": "weren't",
        "has not": "hasn't",
        "have not": "haven't",
        "cannot": "can't",
        "will not": "won't",
    }
    for expanded, contracted in pairs.items():
        assert rule.canonicalize_match(contracted) == expanded
        assert rule.normalize_variants(contracted) == expanded


def test_forbidden_modals_untouched(rule):
    for phrase in ["shall not", "may not", "must not"]:
        assert rule.normalize_variants(phrase) == phrase
        assert "not" in phrase


def test_no_contraction_inside_quotes(nlp, rule):
    text = 'He said "it is not ready".'
    assert len(find(rule, text, nlp)) == 0


def test_contraction_inside_curly_quotes_also_skipped(nlp, rule):
    text = "He said \u201cit is not ready\u201d."
    assert len(find(rule, text, nlp)) == 0


def test_expansion_inside_quotes_skipped(nlp, rule):
    text = "He said \"it does not work\"."
    assert len(find(rule, text, nlp)) == 0


def test_no_overly_aggressive_contraction(nlp, rule):
    # "may not" is not whitelisted.
    assert len(find(rule, "It may not be valid.", nlp)) == 0


def test_expand_contractions_helper():
    assert expand_contractions("Don't go, won't return.") == "Do not go, will not return."
