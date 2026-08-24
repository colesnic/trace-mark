"""Tests for V2 statistics helpers."""

from __future__ import annotations

import pytest

from tracemark.benchmarks.v2stats import (
    clopper_pearson_upper,
    exact_binomial_tail,
    min_matches_for_pvalue,
    theoretical_detection_limits,
)


def test_exact_binomial_tail_small():
    assert exact_binomial_tail(4, 4) == pytest.approx(1 / 16)
    assert exact_binomial_tail(0, 10) == 1.0
    assert exact_binomial_tail(11, 10) == 0.0


def test_min_matches_for_pvalue():
    # For n=10, P(X>=9 | Bin(10,.5)) = 11/1024 ≈ 0.0107
    assert min_matches_for_pvalue(10, 0.02) == 9
    assert min_matches_for_pvalue(10, 0.5) == 6


def test_theoretical_limits_monotonic():
    rows = theoretical_detection_limits([20, 30], [10, 1000])
    by = {(r.opportunities, r.candidates): r for r in rows}
    r20_10 = by[(20, 10)]
    r20_1000 = by[(20, 1000)]
    assert r20_1000.min_matches >= r20_10.min_matches
    assert r20_10.required_match_rate <= r20_1000.required_match_rate


def test_clopper_pearson_upper_zero_hits():
    # 0 failures in 100 trials: upper bound must be > 0 but small.
    upper = clopper_pearson_upper(0, 100, alpha=0.05)
    assert 0.0 < upper < 0.05


def test_clopper_pearson_upper_all_hits():
    assert clopper_pearson_upper(100, 100) == 1.0


def test_general_binom_tail_p_not_half():
    from tracemark.benchmarks.v2stats import binom_tail

    # P(X>=8 | Bin(10, 0.9)) should be large.
    assert binom_tail(8, 10, 0.9) > 0.9
    # P(X>=9 | Bin(10, 0.1)) tiny.
    assert binom_tail(9, 10, 0.1) < 1e-6
