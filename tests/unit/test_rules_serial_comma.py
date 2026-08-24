"""Rule G — serial comma: recognition, canonicalization, negative tests."""

from __future__ import annotations

import pytest

from tests.helpers import decode, find, unique_opp


@pytest.fixture(scope="module")
def rule(registry):
    return registry.get("serial_comma")


def test_no_serial_comma_found(nlp, rule):
    opp = unique_opp(rule, "The flag is red, white and blue.", nlp)
    assert opp.variant_0 == " and"
    assert opp.variant_1 == ", and"
    assert decode(rule, "The flag is red, white and blue.", nlp) == 0
    assert decode(rule, "The flag is red, white, and blue.", nlp) == 1


def test_serial_comma_found(nlp, rule):
    opp = unique_opp(rule, "The flag is red, white, and blue.", nlp)
    assert opp.variant_0 == " and"
    assert opp.variant_1 == ", and"
    assert opp.original == ", and"


def test_canonicalization_identical_for_both_variants(rule):
    assert rule.normalize_variants("red, white and blue") == "red, white and blue"
    assert rule.normalize_variants("red, white, and blue") == "red, white and blue"


def test_two_item_list_rejected(nlp, rule):
    assert len(find(rule, "apples and oranges", nlp)) == 0
    assert len(find(rule, "apples, and oranges", nlp)) == 0


def test_appositive_rejected(nlp, rule):
    assert len(find(rule, "My friends, John and Mary, arrived.", nlp)) == 0
    assert len(find(rule, "I invited my friends, John and Mary.", nlp)) == 0


def test_proper_noun_list_rejected_conservatively(nlp, rule):
    assert len(find(rule, "Alice, Bob and Carol met.", nlp)) == 0


def test_clause_conjunction_rejected(nlp, rule):
    assert len(find(rule, "She said no, and walked away.", nlp)) == 0


def test_four_item_list_accepted(nlp, rule):
    assert decode(rule, "Bring plates, cups, forks and spoons.", nlp) == 0


def test_or_conjunction(nlp, rule):
    opp = unique_opp(rule, "Choose tea, coffee or juice.", nlp)
    assert opp.variant_0 == " or"
    assert opp.variant_1 == ", or"
    assert decode(rule, "Choose tea, coffee, or juice.", nlp) == 1


def test_multiple_lists_in_one_sentence(nlp, rule):
    opps = find(rule, "Buy apples, pears and plums; then find knives, forks and spoons.", nlp)
    assert len(opps) == 2
    assert opps[0].occurrence_index == 0
    assert opps[1].occurrence_index == 1


def test_verb_list_accepted(nlp, rule):
    opp = unique_opp(rule, "I ran, jumped and shouted.", nlp)
    assert opp is not None


def test_flat_subject_list_accepted(nlp, rule):
    assert decode(rule, "The budget, the schedule, and the risks are under review.", nlp) == 1


def test_object_list_accepted(nlp, rule):
    assert decode(rule, "He bought apples, oranges, and bananas.", nlp) == 1


def test_clause_list_rejected(nlp, rule):
    assert len(find(rule, "The dog barked, the cat slept and the bird sang.", nlp)) == 0


def test_shared_subject_clause_list_rejected(nlp, rule):
    text = "We planned the launch, we shipped the feature and we celebrated."
    assert len(find(rule, text, nlp)) == 0


def test_no_comma_before_and_required(nlp, rule):
    # Two items with a comma but no genuine third item after "and".
    opps = find(rule, "The team, and the boss arrived.", nlp)
    assert len(opps) == 0
