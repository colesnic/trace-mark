"""Rule A — quotes: recognition, canonicalization, protection, edge cases."""

from __future__ import annotations

import pytest

from tests.helpers import decode, find, unique_opp
from tracemark.watermark.protection import TextRange, detect_protected_ranges


@pytest.fixture(scope="module")
def rule(registry):
    return registry.get("quotes")


def test_straight_double_quote_pair_found(nlp, rule):
    opp = unique_opp(rule, 'He said "hello" to me.', nlp)
    assert opp.variant_0 == '"hello"'
    assert opp.variant_1 == "\u201chello\u201d"
    assert decode(rule, 'He said "hello" to me.', nlp) == 0
    assert decode(rule, "He said \u201chello\u201d to me.", nlp) == 1


def test_curly_double_quote_pair_found(nlp, rule):
    opp = unique_opp(rule, "He said \u201chello\u201d to me.", nlp)
    assert opp.variant_0 == '"hello"'
    assert opp.variant_1 == "\u201chello\u201d"


def test_single_quote_pair_found(nlp, rule):
    opp = unique_opp(rule, "He said 'hello' to me.", nlp)
    assert opp.variant_0 == "'hello'"
    assert opp.variant_1 == "\u2018hello\u2019"


def test_apostrophe_is_not_a_quote_pair(nlp, rule):
    assert len(find(rule, "It is John's book.", nlp)) == 0


def test_contraction_apostrophe_not_quote(nlp, rule):
    assert len(find(rule, "I can't do that.", nlp)) == 0


def test_quoted_contraction_is_single_opportunity(nlp, rule):
    opp = unique_opp(rule, 'He said "can\'t do that" to me.', nlp)
    assert opp.variant_0 == '"can\'t do that"'


def test_canonicalization_maps_both_variants_to_straight(nlp, rule):
    assert rule.normalize_variants('"straight"') == '"straight"'
    assert rule.normalize_variants("\u201ccurly\u201d") == '"curly"'
    assert rule.normalize_variants("'single'") == "'single'"
    assert rule.normalize_variants("\u2018single\u2019") == "'single'"


def test_unicode_quotes_normalized(nlp, rule):
    assert rule.normalize_variants("\u201c\u201d\u2018\u2019") == "\"\"''"


def test_protected_inline_code_respected(nlp, rule):
    text = 'Use the `"literal"` argument.'
    protected = [TextRange(8, 17, "inline_code")]
    assert len(find(rule, text, nlp, protected=protected)) == 0


def test_protected_url_respected(nlp, rule):
    text = 'See "quoted" at https://example.com/"foo" now.'
    protected = detect_protected_ranges(text)
    assert any(r.kind == "url" for r in protected)
    opps = find(rule, text, nlp, protected=protected)
    assert len(opps) == 1  # only the outer pair survives
    assert text[opps[0].start : opps[0].end] == '"quoted"'


def test_mixed_straight_pair_still_decodes(nlp, rule):
    assert decode(rule, 'He said "hello" to me.', nlp) == 0
    assert decode(rule, "He said \u201chello\u201d to me.", nlp) == 1
