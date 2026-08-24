"""Statistical scoring for fingerprint detection.

Under the null hypothesis each observed linguistic choice matches the
candidate's expected bit with probability ~0.5. With ``n`` independent
opportunities and ``k`` matches the raw p-value is the binomial tail
probability P(X >= k) for X ~ Binomial(n, 0.5).

For prototype-sized documents exact integer arithmetic is used; a normal
approximation backs off for very large documents.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from tracemark.watermark.policy import WatermarkPolicy


def binomial_tail_probability(*, matches: int, total: int) -> float:
    """P(X >= matches) for X ~ Binomial(total, 0.5)."""
    if total <= 0:
        return 1.0
    matches = max(0, min(matches, total))
    if matches == 0:
        return 1.0
    if matches > total / 2:
        # Symmetry: P(X >= matches) with p=0.5.
        pass
    if total <= 2000:
        return _exact_tail(matches, total)
    return _normal_tail(matches, total)


def _exact_tail(matches: int, total: int) -> float:
    tail = sum(math.comb(total, k) for k in range(matches, total + 1))
    return tail / (1 << total)


def _normal_tail(matches: int, total: int) -> float:
    mean = total / 2.0
    std = math.sqrt(total / 4.0)
    z = (matches - 0.5 - mean) / std
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def evidence_score(p_value: float) -> float:
    """-log10(p_value); higher is stronger evidence."""
    if p_value <= 0.0:
        return float("inf")
    return -math.log10(p_value)


def bonferroni_adjust(p_value: float, candidate_count: int) -> float:
    if candidate_count <= 1:
        return p_value
    return min(1.0, p_value * candidate_count)


@dataclass(frozen=True)
class ScoreInput:
    matches: int
    total: int


def score_candidate(
    score: ScoreInput,
    candidate_count: int,
    policy: WatermarkPolicy,
) -> float:
    """Combine raw p-value, multiple-testing correction and separation into
    a single evidence figure used for ranking."""
    p = binomial_tail_probability(matches=score.matches, total=score.total)
    adjusted = bonferroni_adjust(p, candidate_count)
    return evidence_score(adjusted)
