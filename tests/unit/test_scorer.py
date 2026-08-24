"""Statistical scorer tests."""

from __future__ import annotations

import pytest

from tracemark.watermark.scorer import (
    binomial_tail_probability,
    bonferroni_adjust,
    evidence_score,
)


def test_no_opportunities_returns_one():
    assert binomial_tail_probability(matches=0, total=0) == 1.0
    assert binomial_tail_probability(matches=5, total=0) == 1.0


def test_all_match_small_n():
    # P(X >= 4 | X ~ Binomial(4, .5)) = 1/16
    assert binomial_tail_probability(matches=4, total=4) == pytest.approx(1 / 16)


def test_half_match_large_p():
    assert binomial_tail_probability(matches=2, total=4) == pytest.approx(11 / 16)


def test_zero_matches():
    assert binomial_tail_probability(matches=0, total=10) == 1.0


def test_known_binomial():
    # Binomial(10, 0.5): P(X>=8) = (C(10,8)+C(10,9)+C(10,10))/1024 = 56/1024
    assert binomial_tail_probability(matches=8, total=10) == pytest.approx(56 / 1024)


def test_normal_approximation_close_to_exact_for_large():
    p_norm = binomial_tail_probability(matches=1200, total=2500)
    assert 0 < p_norm < 1


def test_evidence_score_ordering():
    assert evidence_score(1e-10) > evidence_score(1e-5) > evidence_score(0.1)


def test_evidence_infinite_for_zero():
    assert evidence_score(0.0) == float("inf")


def test_bonferroni_single_candidate():
    assert bonferroni_adjust(0.01, 1) == pytest.approx(0.01)


def test_bonferroni_caps_at_one():
    assert bonferroni_adjust(0.5, 10) == 1.0


def test_bonferroni_multiplies():
    assert bonferroni_adjust(0.01, 5) == pytest.approx(0.05)
