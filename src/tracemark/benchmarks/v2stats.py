"""Statistical helpers for V2 research benchmarks.

Includes exact binomial computation, Clopper-Pearson confidence intervals and
normal-approximation fallbacks. SciPy is optional (eval group); the code
degrades gracefully to math-only implementations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def exact_binomial_tail(matches: int, total: int) -> float:
    """P(X >= matches) for X ~ Binomial(total, 0.5), exact."""
    if total <= 0:
        return 1.0
    if matches > total:
        return 0.0
    matches = max(0, matches)
    if matches == 0:
        return 1.0
    tail = sum(math.comb(total, k) for k in range(matches, total + 1))
    return tail / (1 << total)


def normal_tail(matches: int, total: int, p: float = 0.5) -> float:
    mean = total * p
    std = math.sqrt(total * p * (1 - p))
    z = (matches - 0.5 - mean) / std
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def binom_tail(matches: int, total: int, p: float = 0.5) -> float:
    """P(X >= matches) for X ~ Binomial(total, p) — exact for small n."""
    if p != 0.5 or total > 2000:
        if p == 0.5:
            return normal_tail(matches, total, p)
        # General p via incomplete beta (no scipy dependency guaranteed).
        return _general_binom_tail(matches, total, p)
    return exact_binomial_tail(matches, total)


def _general_binom_tail(matches: int, total: int, p: float) -> float:
    """P(X >= matches) using the regularized incomplete beta via continued
    fraction (mirrors scipy's betainc for small inputs)."""
    if matches <= 0:
        return 1.0
    if matches > total:
        return 0.0
    a = matches
    b = total - matches + 1
    ibeta = _betainc(a, b, p)
    return ibeta


def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function (continued-fraction, Lentz)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1 - x)
    )
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b


def _betacf(a: float, b: float, x: float, itmax: int = 200) -> float:
    """Continued fraction for incomplete beta (Lentz's algorithm)."""
    tiny = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-10:
            break
    return h


def min_matches_for_pvalue(n: int, target_p: float, p: float = 0.5) -> int:
    """Smallest k such that P(X >= k | Binomial(n, p)) <= target_p."""
    for k in range(n + 1):
        if binom_tail(k, n, p) <= target_p:
            return k
    return n + 1


def clopper_pearson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """Upper one-sided Clopper-Pearson confidence bound for a binomial
    proportion (k successes / n trials)."""
    if k >= n:
        return 1.0
    if k == 0:
        return 1 - alpha ** (1.0 / n)
    # Solve for p_upper such that P(X <= k | Binomial(n, p_upper)) = alpha.
    lo, hi = (k / n), 1.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        p_le = sum(
            math.comb(n, i) * (mid**i) * ((1 - mid) ** (n - i))
            for i in range(k + 1)
        )
        if p_le > alpha:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


@dataclass(frozen=True)
class TheoreticalLimit:
    opportunities: int
    candidates: int
    min_matches: int
    required_match_rate: float
    target_alpha: float


def theoretical_detection_limits(
    opportunity_counts: list[int],
    candidate_counts: list[int],
    target_alpha: float = 0.05,
) -> list[TheoreticalLimit]:
    """Minimum matches needed so the Bonferroni-adjusted p < target_alpha."""
    rows: list[TheoreticalLimit] = []
    for n in opportunity_counts:
        for n_cand in candidate_counts:
            adjusted_target = target_alpha / max(n_cand, 1)
            k = min_matches_for_pvalue(n, adjusted_target)
            rows.append(
                TheoreticalLimit(
                    opportunities=n,
                    candidates=n_cand,
                    min_matches=k,
                    required_match_rate=k / max(n, 1),
                    target_alpha=target_alpha,
                )
            )
    return rows
