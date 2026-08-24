"""Experimental rules: abbreviations, markdown, complementizer that."""

from __future__ import annotations

import pytest

from tests.helpers import find, unique_opp


@pytest.fixture(scope="module")
def abbrev(registry):
    return registry.get("abbreviations")


@pytest.fixture(scope="module")
def markdown(registry):
    return registry.get("markdown")


@pytest.fixture(scope="module")
def complementizer(registry):
    return registry.get("complementizer_that")


def test_for_example_found(nlp, abbrev):
    opp = unique_opp(abbrev, "Use a proxy, for example a gateway.", nlp)
    assert opp.variant_0 == "for example"
    assert opp.variant_1 == "e.g."
    assert abbrev.decode_opportunity("e.g.", 0, 4) == 1


def test_eg_found(nlp, abbrev):
    opp = unique_opp(abbrev, "Use a proxy, e.g. a gateway.", nlp)
    assert opp.variant_0 == "for example"
    assert opp.variant_1 == "e.g."


def test_that_is_with_comma_found(nlp, abbrev):
    opp = unique_opp(abbrev, "That is, the plan failed.", nlp)
    assert opp.variant_1 == "I.e."


def test_that_is_demonstrative_rejected(nlp, abbrev):
    assert len(find(abbrev, "I think that is correct.", nlp)) == 0


def test_canonicalization_long_forms(abbrev):
    assert abbrev.normalize_variants("e.g. example") == "for example example"
    assert abbrev.normalize_variants("i.e. note") == "that is note"


def test_markdown_bold(nlp, markdown):
    opp = unique_opp(markdown, "This is **bold** text.", nlp)
    assert opp.variant_0 == "**bold**"
    assert opp.variant_1 == "__bold__"
    assert markdown.decode_opportunity("__bold__", 0, 8) == 1


def test_markdown_underscore_bold(nlp, markdown):
    opp = unique_opp(markdown, "This is __bold__ text.", nlp)
    assert opp.variant_1 == "__bold__"


def test_markdown_list_marker(nlp, markdown):
    text = "- first item"
    opp = unique_opp(markdown, text, nlp)
    assert opp.variant_0 == "- "
    assert opp.variant_1 == "* "


def test_markdown_canonicalization(markdown):
    assert markdown.normalize_variants("__bold__") == "**bold**"
    assert markdown.normalize_variants("* item") == "- item"


def test_complementizer_with_that(nlp, complementizer):
    opp = unique_opp(complementizer, "We believe that the rule applies.", nlp)
    assert opp.variant_1 == "that"
    assert (
        complementizer.decode_opportunity(
            "We believe that the rule applies.", opp.start, opp.end
        )
        == 1
    )


def test_complementizer_without_that(nlp, complementizer):
    opp = unique_opp(complementizer, "We believe the rule applies.", nlp)
    assert opp.variant_0 == " the rule "
    assert opp.variant_1 == "that the rule "
    assert (
        complementizer.decode_opportunity(
            "We believe the rule applies.", opp.start, opp.end
        )
        == 0
    )
    assert (
        complementizer.decode_opportunity(
            "We believe that the rule applies.", opp.start, opp.end
        )
        == 1
    )


def test_complementizer_nonwhitelisted_verb(nlp, complementizer):
    assert len(find(complementizer, "We hope that it works.", nlp)) == 0


def test_complementizer_canonicalization(complementizer):
    assert complementizer.normalize_variants("We believe that it works.") == "We believe it works."
