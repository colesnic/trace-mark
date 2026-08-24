"""Rule C — ellipsis and Rule D — dash typography tests."""

from __future__ import annotations

import pytest

from tests.helpers import decode, find, unique_opp
from tracemark.watermark.protection import TextRange


@pytest.fixture(scope="module")
def ellipsis(registry):
    return registry.get("ellipsis")


@pytest.fixture(scope="module")
def dash(registry):
    return registry.get("dash_style")


def test_ellipsis_three_dots_found(nlp, ellipsis):
    opp = unique_opp(ellipsis, "He paused... then spoke.", nlp)
    assert opp.variant_0 == "..."
    assert opp.variant_1 == "\u2026"
    assert decode(ellipsis, "He paused... then spoke.", nlp) == 0
    assert decode(ellipsis, "He paused\u2026 then spoke.", nlp) == 1


def test_ellipsis_character_found(nlp, ellipsis):
    opp = unique_opp(ellipsis, "He paused\u2026 then spoke.", nlp)
    assert opp.original == "\u2026"


def test_ellipsis_rejects_long_runs(nlp, ellipsis):
    assert len(find(ellipsis, "He paused.... then spoke.", nlp)) == 0
    assert len(find(ellipsis, "He paused.....", nlp)) == 0


def test_ellipsis_rejects_numeric_ranges(nlp, ellipsis):
    assert len(find(ellipsis, "Range 1...3", nlp)) == 0
    assert len(find(ellipsis, "v1...v3", nlp)) == 0


def test_ellipsis_rejects_letter_both_sides(nlp, ellipsis):
    assert len(find(ellipsis, "ab...cd", nlp)) == 0


def test_ellipsis_canonicalization(ellipsis):
    assert ellipsis.normalize_variants("a\u2026b") == "a...b"


def test_dash_spaced_found(nlp, dash):
    opp = unique_opp(dash, "word \u2014 word", nlp)
    assert opp.variant_0 == " \u2014 "
    assert opp.variant_1 == "\u2014"
    assert decode(dash, "word \u2014 word", nlp) == 0


def test_dash_unspaced_found(nlp, dash):
    opp = unique_opp(dash, "word\u2014word", nlp)
    assert opp.original == "\u2014"
    assert opp.variant_1 == "\u2014"
    assert decode(dash, "word\u2014word", nlp) == 1


def test_dash_half_spaced_found(nlp, dash):
    opp = unique_opp(dash, "word \u2014word", nlp)
    assert opp.original == " \u2014"


def test_dash_requires_words_both_sides(nlp, dash):
    assert len(find(dash, "The \u2014", nlp)) == 0
    assert len(find(dash, "\u2014 end", nlp)) == 0


def test_dash_does_not_touch_hyphens(nlp, dash):
    assert len(find(dash, "well-known compound", nlp)) == 0
    assert len(find(dash, "10-12 range", nlp)) == 0


def test_dash_canonicalization(dash):
    assert dash.normalize_variants("a\u2014b") == "a \u2014 b"
    assert dash.normalize_variants("a \u2014 b") == "a \u2014 b"


def test_dash_protected(nlp, dash):
    text = "word \u2014 word"
    assert len(find(dash, text, nlp, protected=[TextRange(0, len(text), "code")])) == 0
