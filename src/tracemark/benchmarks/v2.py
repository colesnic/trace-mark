"""V2 research benchmarks.

The goal is to find out exactly where TraceMark works, where it stops
working, and why. Nothing in here tunes results to look good.
"""

from __future__ import annotations

import math
import random
import re
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from tracemark.benchmarks.corpora.base import CorpusDocument, load_processed_jsonl
from tracemark.benchmarks.v2stats import (
    clopper_pearson_upper,
    exact_binomial_tail,
    min_matches_for_pvalue,
)
from tracemark.crypto.fingerprint import derive_fingerprint, expected_bit
from tracemark.watermark.detector import (
    DecodedDocument,
    FingerprintCandidate,
    decode_document,
    detect_fingerprint,
    score_candidates,
)
from tracemark.watermark.engine import apply_watermark
from tracemark.watermark.policy import WatermarkPolicy

PROCESSED = Path(".data/processed")
RESULTS_V2 = Path("benchmarks/results/v2")

_TENANT = "11111111-1111-1111-1111-111111111111"
_MASTER = b"\x42" * 32


def make_fingerprint(external_ref: str, model_scope: str | None = None):
    import uuid

    return derive_fingerprint(
        master_key=_MASTER,
        tenant_id=uuid.UUID(_TENANT),
        subject_external_ref=external_ref,
        model_scope=model_scope,
    )


def load_corpus(name: str) -> list[CorpusDocument]:
    path = PROCESSED / f"{name}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"run prepare_corpora first: {path}")
    return load_processed_jsonl(path)


# --------------------------------------------------------------------------
# Document windows (Milestone 6)
# --------------------------------------------------------------------------


def make_sentence_preserving_window(
    text: str,
    target_words: int,
    tolerance: float = 0.10,
) -> str | None:
    """Return a sentence-preserving window of ~target_words words.

    Walks sentence boundaries so the window never cuts mid-sentence. Returns
    None when the text is too short to provide a window within tolerance.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return None
    best: str | None = None
    best_diff = float("inf")
    lo = 0
    total = 0
    for hi in range(len(sentences)):
        total += len(sentences[hi].split())
        while total > target_words * (1 + tolerance) and lo <= hi:
            total -= len(sentences[lo].split())
            lo += 1
        if lo > hi:
            continue
        words = sum(len(s.split()) for s in sentences[lo : hi + 1])
        if target_words * (1 - tolerance) <= words <= target_words * (1 + tolerance):
            diff = abs(words - target_words)
            if diff < best_diff:
                best_diff = diff
                best = " ".join(sentences[lo : hi + 1]).strip()
    return best


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def make_nonoverlapping_windows(text: str, target_words: int) -> list[str]:
    """Multiple non-overlapping sentence-preserving windows of ~target_words."""
    sentences = _split_sentences(text)
    windows: list[str] = []
    current: list[str] = []
    words = 0
    for sent in sentences:
        current.append(sent)
        words += len(sent.split())
        if words >= target_words:
            windows.append(" ".join(current).strip())
            current = []
            words = 0
    if words >= max(4, target_words // 2):
        windows.append(" ".join(current).strip())
    return windows


# --------------------------------------------------------------------------
# Corpus statistics (Milestone 2)
# --------------------------------------------------------------------------


@dataclass
class CorpusStats:
    corpus: str
    documents: int
    total_words: int
    median_words: float
    p10_words: float
    p90_words: float
    opportunity_stats: dict[str, float]  # median/p10/p90 density per 100 words
    median_opportunities: float
    eligible_20: float  # fraction with >= 20 opportunities
    rule_distribution: dict[str, int]
    human_fraction: float
    machine_fraction: float


def corpus_statistics(documents: Sequence[CorpusDocument], policy: WatermarkPolicy) -> CorpusStats:
    from collections import Counter

    word_counts: list[int] = []
    densities: list[float] = []
    opp_counts: list[int] = []
    rule_dist: Counter = Counter()
    eligible = 0
    human = machine = 0
    for doc in documents:
        if doc.human_or_machine == "human":
            human += 1
        elif doc.human_or_machine == "machine":
            machine += 1
        word_counts.append(doc.word_count)
        if doc.word_count >= 15:
            decoded = decode_document(doc.text, policy)
            n = decoded.usable_opportunities
            opp_counts.append(n)
            densities.append(n / max(doc.word_count, 1) * 100)
            for d in decoded.opportunities:
                rule_dist[d.rule_id] += 1
            if n >= 20:
                eligible += 1
    return CorpusStats(
        corpus=documents[0].corpus if documents else "",
        documents=len(documents),
        total_words=sum(word_counts),
        median_words=_median(word_counts),
        p10_words=_pct(word_counts, 0.10),
        p90_words=_pct(word_counts, 0.90),
        opportunity_stats={
            "median_per_100": _median(densities) if densities else 0.0,
            "p10_per_100": _pct(densities, 0.10) if densities else 0.0,
            "p90_per_100": _pct(densities, 0.90) if densities else 0.0,
        },
        median_opportunities=_median(opp_counts) if opp_counts else 0.0,
        eligible_20=eligible / max(len(documents), 1),
        rule_distribution=dict(rule_dist),
        human_fraction=human / max(len(documents), 1),
        machine_fraction=machine / max(len(documents), 1),
    )


# --------------------------------------------------------------------------
# Author-style bias (Milestone 5, Enron)
# --------------------------------------------------------------------------


@dataclass
class AuthorBiasResult:
    corpus_author_id: str
    documents: int
    opportunities: int
    best_random_candidate: str
    mean_match_rate: float
    max_match_rate: float
    combined_evidence: float


def benchmark_author_style_bias(
    *,
    documents: Sequence[CorpusDocument],
    candidate_keys: Sequence[bytes],
    policy: WatermarkPolicy,
) -> list[AuthorBiasResult]:
    """Test many unrelated random fingerprints against a real human author's
    unwatermarked writing to check for persistent stylistic false matches."""
    by_author: dict[str, list[CorpusDocument]] = {}
    for doc in documents:
        if doc.author_id:
            by_author.setdefault(doc.author_id, []).append(doc)

    results: list[AuthorBiasResult] = []
    for author, docs in by_author.items():
        if len(docs) < 10:
            continue
        decoded = [decode_document(d.text, policy) for d in docs]
        opps = sum(d.usable_opportunities for d in decoded)
        if opps < 5:
            continue
        # For each random key, count total matches across the author's docs.
        scored: list[tuple[bytes, int, int]] = []
        for key in candidate_keys:
            matches = 0
            total = 0
            for d in decoded:
                for opp in d.opportunities:
                    total += 1
                    if expected_bit(key, opp.ident) == opp.observed_bit:
                        matches += 1
            scored.append((key, matches, total))
        best_key, best_matches, best_total = max(scored, key=lambda t: t[1])
        rates = [m / max(t, 1) for _k, m, t in scored]
        max_rate = best_matches / max(best_total, 1)
        # Adjusted binomial evidence for the best key over the candidate pool.
        p = exact_binomial_tail(best_matches, best_total)
        adjusted = min(1.0, p * max(len(candidate_keys), 1))
        evidence = -math.log10(adjusted) if adjusted > 0 else float("inf")
        results.append(
            AuthorBiasResult(
                corpus_author_id=author,
                documents=len(docs),
                opportunities=opps,
                best_random_candidate=best_key.hex()[:8],
                mean_match_rate=statistics.mean(rates),
                max_match_rate=max_rate,
                combined_evidence=evidence,
            )
        )
    return results


# --------------------------------------------------------------------------
# Candidate scale (Milestone 6)
# --------------------------------------------------------------------------


@dataclass
class CandidateScaleResult:
    document_id: str
    word_count: int
    opportunity_count: int
    candidate_count: int
    correct_rank: int
    correct_match_rate: float
    strongest_false_match_rate: float
    correct_adjusted_p: float
    detected: bool


def benchmark_candidate_scale(
    *,
    documents: Sequence[CorpusDocument],
    candidate_counts: Sequence[int],
    repetitions: int,
    seed: int = 7,
) -> list[CandidateScaleResult]:
    alice = make_fingerprint("alice")
    policy = WatermarkPolicy.from_name("balanced")
    rng = random.Random(seed)

    # Pre-decode once per document.
    prepared: list[tuple[str, int, DecodedDocument]] = []
    for doc in documents:
        wm = apply_watermark(text=doc.text, fingerprint_key=alice.key, policy=policy)
        decoded = decode_document(wm.text, policy)
        prepared.append((doc.document_id, doc.word_count, decoded))

    results: list[CandidateScaleResult] = []
    for doc_id, words, decoded in prepared:
        for n_cand in candidate_counts:
            for _rep in range(repetitions):
                decoys = [
                    (f"decoy-{i}", rng.randbytes(32)) for i in range(n_cand - 1)
                ]
                candidates = [
                    FingerprintCandidate("alice", None, alice.key),
                    *[FingerprintCandidate(tag, None, key) for tag, key in decoys],
                ]
                scores = score_candidates(decoded, candidates)
                ranked = sorted(
                    scores, key=lambda s: (-s.matches, -s.evidence_score, s.subject_tag)
                )
                correct_rank = next(
                    i for i, s in enumerate(ranked) if s.subject_tag == "alice"
                )
                correct = next(s for s in scores if s.subject_tag == "alice")
                strongest_false = max(
                    (s for s in scores if s.subject_tag != "alice"),
                    key=lambda s: s.match_rate,
                    default=None,
                )
                results.append(
                    CandidateScaleResult(
                        document_id=doc_id,
                        word_count=words,
                        opportunity_count=decoded.usable_opportunities,
                        candidate_count=n_cand,
                        correct_rank=correct_rank,
                        correct_match_rate=correct.match_rate,
                        strongest_false_match_rate=(
                            strongest_false.match_rate if strongest_false else 0.0
                        ),
                        correct_adjusted_p=correct.adjusted_p_value,
                        detected=(
                            correct_rank == 0
                            and correct.adjusted_p_value < 0.05
                        ),
                    )
                )
    return results


# --------------------------------------------------------------------------
# Null calibration (Milestone 4)
# --------------------------------------------------------------------------


@dataclass
class NullCalibration:
    opportunities: int
    candidate_count: int
    trials: int
    theoretical_mean: float
    empirical_mean: float
    theoretical_variance: float
    empirical_variance: float
    empirical_fwer: float


def calibrate_null_model(
    *,
    opportunity_counts: Sequence[int],
    candidate_counts: Sequence[int],
    trials: int,
) -> list[NullCalibration]:
    """Simulate null match counts (Binomial(0.5)) without any NLP.

    ``empirical_mean``/``empirical_variance`` describe the *single-candidate*
    match distribution and are compared to Binomial(n, 0.5) theory.
    ``empirical_fwer`` is the family-wise error rate: the fraction of trials
    where the best of N candidates passes the Bonferroni threshold.
    """
    rows: list[NullCalibration] = []
    for n in opportunity_counts:
        for n_cand in candidate_counts:
            rng = random.Random(0)
            single_matches: list[int] = []
            fwer_hits = 0
            target = min_matches_for_pvalue(n, 0.05 / max(n_cand, 1))
            for _ in range(trials):
                per_candidate = [
                    sum(1 for _i in range(n) if rng.random() < 0.5)
                    for _c in range(n_cand)
                ]
                single_matches.extend(per_candidate)
                if max(per_candidate) >= target:
                    fwer_hits += 1
            rows.append(
                NullCalibration(
                    opportunities=n,
                    candidate_count=n_cand,
                    trials=trials,
                    theoretical_mean=n / 2.0,
                    empirical_mean=statistics.mean(single_matches),
                    theoretical_variance=n / 4.0,
                    empirical_variance=statistics.variance(single_matches),
                    empirical_fwer=fwer_hits / trials,
                )
            )
    return rows


# --------------------------------------------------------------------------
# Match independence / dependence (Milestone 4)
# --------------------------------------------------------------------------


@dataclass
class DependenceReport:
    documents: int
    opportunity_pairs: int
    mean_pairwise_correlation: float
    within_rule_correlation: dict[str, float]
    duplicate_ids: int
    expected_bit_imbalance: float
    per_rule_bit_frequency: dict[str, float]


def analyze_match_dependence(
    decoded_documents: Sequence[DecodedDocument],
    candidate_keys: Sequence[bytes],
    sample_pairs: int = 20_000,
) -> DependenceReport:
    """Check whether match indicators across opportunities are independent."""
    rng = random.Random(1)
    docs = [d for d in decoded_documents if d.usable_opportunities >= 2]
    if not docs:
        return DependenceReport(0, 0, 0.0, {}, 0, 0.0, {})

    # Key 0 determines the match indicator for every opportunity.
    key = candidate_keys[0]
    indicators: list[tuple[int, str]] = []  # (match(0/1), rule_id)
    id_set: set[bytes] = set()
    dup = 0
    for doc in docs:
        for opp in doc.opportunities:
            if opp.ident in id_set:
                dup += 1
            id_set.add(opp.ident)
            m = 1 if expected_bit(key, opp.ident) == opp.observed_bit else 0
            indicators.append((m, opp.rule_id))

    # Pairwise correlation over a sampled set of opportunity pairs.
    correlations: list[float] = []
    n = len(indicators)
    for _ in range(min(sample_pairs, n * n // 2)):
        i, j = rng.sample(range(n), 2)
        mi, mj = indicators[i][0], indicators[j][0]
        if mi == mj:
            correlations.append(1.0)
        else:
            correlations.append(0.0)
    mean_corr = statistics.mean(correlations) if correlations else 0.0

    # Within-rule bit frequency (should be ~0.5 if balanced).
    by_rule: dict[str, list[int]] = {}
    for m, rule in indicators:
        by_rule.setdefault(rule, []).append(m)
    per_rule_freq = {r: statistics.mean(v) for r, v in by_rule.items()}
    within_rule_corr: dict[str, float] = {}
    for rule, vals in by_rule.items():
        if len(vals) >= 20:
            mean = statistics.mean(vals)
            # Correlation of indicator with itself is 1; instead report the
            # per-rule mean deviation from 0.5 as a bias measure.
            within_rule_corr[rule] = abs(mean - 0.5)

    all_m = [m for m, _ in indicators]
    imbalance = statistics.mean(all_m) if all_m else 0.0
    return DependenceReport(
        documents=len(docs),
        opportunity_pairs=n,
        mean_pairwise_correlation=mean_corr,
        within_rule_correlation=within_rule_corr,
        duplicate_ids=dup,
        expected_bit_imbalance=imbalance,
        per_rule_bit_frequency=per_rule_freq,
    )


# --------------------------------------------------------------------------
# Opportunity-ID collisions (Milestone 4)
# --------------------------------------------------------------------------


@dataclass
class CollisionReport:
    total_ids: int
    unique_ids: int
    duplicate_ids: int
    duplicate_fraction: float
    top_repeated: list[tuple[bytes, int]]


def analyze_opportunity_id_collisions(
    corpus: Iterable[CorpusDocument],
    policy: WatermarkPolicy,
    limit: int | None = None,
) -> CollisionReport:
    counts: dict[bytes, int] = {}
    for idx, doc in enumerate(corpus):
        if limit is not None and idx >= limit:
            break
        decoded = decode_document(doc.text, policy)
        for opp in decoded.opportunities:
            counts[opp.ident] = counts.get(opp.ident, 0) + 1
    total = sum(counts.values())
    unique = len(counts)
    dup = total - unique
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return CollisionReport(
        total_ids=total,
        unique_ids=unique,
        duplicate_ids=dup,
        duplicate_fraction=dup / max(total, 1),
        top_repeated=top,
    )


# --------------------------------------------------------------------------
# False positives (Milestone 5)
# --------------------------------------------------------------------------


@dataclass
class FalsePositiveResult:
    documents: int
    candidates_per_doc: int
    trials: int
    raw_significant: int
    adjusted_significant: int
    raw_significant_fraction: float
    adjusted_significant_fraction: float
    adjusted_upper_95: float
    eligible_documents: int


def benchmark_false_positives(
    *,
    documents: Sequence[CorpusDocument],
    candidate_counts: Sequence[int],
    policy: WatermarkPolicy,
    seed: int = 99,
) -> list[FalsePositiveResult]:
    rng = random.Random(seed)
    results: list[FalsePositiveResult] = []
    for n_cand in candidate_counts:
        candidates = [
            FingerprintCandidate(f"rand-{i}", None, rng.randbytes(32))
            for i in range(n_cand)
        ]
        raw_sig = 0
        adj_sig = 0
        eligible = 0
        for doc in documents:
            decoded = decode_document(doc.text, policy)
            if decoded.usable_opportunities >= policy.minimum_opportunities:
                eligible += 1
            scores = score_candidates(decoded, candidates)
            best = max(scores, key=lambda s: s.match_rate, default=None)
            if best is None:
                continue
            if best.p_value < 0.05:
                raw_sig += 1
            if best.adjusted_p_value < 0.05:
                adj_sig += 1
        trials = max(len(documents), 1)
        results.append(
            FalsePositiveResult(
                documents=len(documents),
                candidates_per_doc=n_cand,
                trials=trials,
                raw_significant=raw_sig,
                adjusted_significant=adj_sig,
                raw_significant_fraction=raw_sig / trials,
                adjusted_significant_fraction=adj_sig / trials,
                adjusted_upper_95=clopper_pearson_upper(adj_sig, trials),
                eligible_documents=eligible,
            )
        )
    return results


# --------------------------------------------------------------------------
# Length × candidate grid (Milestone 6)
# --------------------------------------------------------------------------


@dataclass
class GridCell:
    words: int
    candidates: int
    windows: int
    attributed: int
    attributed_fraction: float
    insufficient: int
    insufficient_fraction: float
    false_attribution: int
    false_attribution_fraction: float
    median_evidence: float


def attribution_grid(
    *,
    documents: Sequence[CorpusDocument],
    word_buckets: Sequence[int],
    candidate_counts: Sequence[int],
    policy: WatermarkPolicy,
    seed: int = 21,
    max_windows_per_doc: int = 3,
) -> list[GridCell]:
    alice = make_fingerprint("alice")
    rng = random.Random(seed)

    cells: list[GridCell] = []
    for words in word_buckets:
        windows: list[tuple[str, str]] = []  # (doc_id, text)
        for doc in documents:
            for w in make_nonoverlapping_windows(doc.text, words):
                if len(w.split()) >= int(words * 0.8):
                    windows.append((doc.document_id, w))
                if len([x for x in windows if x[0] == doc.document_id]) >= max_windows_per_doc:
                    break
        if not windows:
            continue
        rng.shuffle(windows)
        windows = windows[:400]

        # Watermark + decode ONCE per window; candidate counts only change
        # the scoring population.
        prepared: list[tuple[str, DecodedDocument]] = []
        for _doc_id, text in windows:
            wm = apply_watermark(text=text, fingerprint_key=alice.key, policy=policy)
            prepared.append((text, decode_document(wm.text, policy)))

        for n_cand in candidate_counts:
            attributed = 0
            insufficient = 0
            false_attr = 0
            evidences: list[float] = []
            for _text, decoded in prepared:
                candidates = [
                    FingerprintCandidate("alice", None, alice.key),
                    *[
                        FingerprintCandidate(f"decoy-{i}", None, rng.randbytes(32))
                        for i in range(n_cand - 1)
                    ],
                ]
                scores = score_candidates(decoded, candidates)
                ranked = sorted(
                    scores, key=lambda s: (-s.matches, -s.evidence_score, s.subject_tag)
                )
                best = ranked[0]
                evidences.append(best.evidence_score if decoded.usable_opportunities else 0.0)
                if decoded.usable_opportunities < policy.minimum_opportunities:
                    insufficient += 1
                    continue
                if best.subject_tag == "alice" and best.adjusted_p_value < 0.05:
                    attributed += 1
                else:
                    false_attr += 1
            n = len(prepared)
            cells.append(
                GridCell(
                    words=words,
                    candidates=n_cand,
                    windows=n,
                    attributed=attributed,
                    attributed_fraction=attributed / max(n, 1),
                    insufficient=insufficient,
                    insufficient_fraction=insufficient / max(n, 1),
                    false_attribution=false_attr,
                    false_attribution_fraction=false_attr / max(n, 1),
                    median_evidence=statistics.median(evidences) if evidences else 0.0,
                )
            )
    return cells


# --------------------------------------------------------------------------
# Channel ablation (Milestone 7)
# --------------------------------------------------------------------------


@dataclass
class AblationRow:
    rules: tuple[str, ...]
    documents: int
    median_opportunities: float
    mean_opportunities: float
    attributed_fraction: float


def channel_ablation(
    *,
    documents: Sequence[CorpusDocument],
    policy: WatermarkPolicy,
    max_documents: int = 200,
) -> list[AblationRow]:
    from tracemark.watermark.policy import BALANCED_RULES

    alice = make_fingerprint("alice")
    rules = list(BALANCED_RULES)
    subsets: list[tuple[str, ...]] = [
        tuple(rules),
        tuple(r for r in rules if r != "contractions"),
        tuple(r for r in rules if r != "serial_comma"),
        ("quotes", "apostrophes", "ellipsis", "dash_style"),
        ("serial_comma", "contractions"),
    ]
    for r in rules:
        subsets.append((r,))

    docs = documents[:max_documents]
    rows: list[AblationRow] = []
    for subset in subsets:
        subset_policy = WatermarkPolicy(
            name="ablation",
            tier=policy.tier,
            enabled_rules=subset,
            minimum_opportunities=20,
            minimum_separation=2.0,
        )
        opps: list[int] = []
        attributed = 0
        for doc in docs:
            wm = apply_watermark(text=doc.text, fingerprint_key=alice.key, policy=subset_policy)
            decoded = decode_document(wm.text, subset_policy)
            opps.append(decoded.usable_opportunities)
            if decoded.usable_opportunities >= 20:
                det = detect_fingerprint(
                    text=wm.text,
                    candidates=[FingerprintCandidate("alice", None, alice.key)],
                    policy=subset_policy,
                )
                if det.detected:
                    attributed += 1
        rows.append(
            AblationRow(
                rules=subset,
                documents=len(docs),
                median_opportunities=_median(opps),
                mean_opportunities=statistics.mean(opps) if opps else 0.0,
                attributed_fraction=attributed / max(len(docs), 1),
            )
        )
    return rows


# --------------------------------------------------------------------------
# Pattern inventory (Milestone 7)
# --------------------------------------------------------------------------


@dataclass
class PatternInventory:
    numeric_ranges: int
    dates: int
    percentages: int
    times: int
    em_dashes: int
    hyphens: int
    abbreviations: int
    markdown_bold: int
    markdown_bullets: int
    documents: int
    words: int


_MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
_PATTERNS = {
    "numeric_ranges": re.compile(r"\b\d+\s*[-–]\s*\d+\b"),
    "dates": re.compile(
        rf"\b{_MONTHS}[a-z]*\.?\s+\d{{1,2}},?\s+\d{{4}}\b", re.IGNORECASE
    ),
    "percentages": re.compile(r"\b\d+(?:\.\d+)?\s*%\b"),
    "times": re.compile(
        r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b|\b\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)\b",
        re.IGNORECASE,
    ),
    "em_dashes": re.compile(r"\u2014"),
    "hyphens": re.compile(r"\b\w+-\w+\b"),
    "abbreviations": re.compile(r"\b(?:e\.g\.|i\.e\.|etc\.|vs\.|approx\.)\b", re.IGNORECASE),
    "markdown_bold": re.compile(r"\*\*[^*]+\*\*|__[^_]+__"),
    "markdown_bullets": re.compile(r"(?m)^\s*[-*]\s+"),
}


def find_candidate_linguistic_patterns(
    corpus: Iterable[CorpusDocument],
    limit: int | None = None,
) -> PatternInventory:
    counts = dict.fromkeys(_PATTERNS, 0)
    docs = 0
    words = 0
    for idx, doc in enumerate(corpus):
        if limit is not None and idx >= limit:
            break
        docs += 1
        words += doc.word_count
        for name, pattern in _PATTERNS.items():
            counts[name] += len(pattern.findall(doc.text))
    return PatternInventory(
        numeric_ranges=counts["numeric_ranges"],
        dates=counts["dates"],
        percentages=counts["percentages"],
        times=counts["times"],
        em_dashes=counts["em_dashes"],
        hyphens=counts["hyphens"],
        abbreviations=counts["abbreviations"],
        markdown_bold=counts["markdown_bold"],
        markdown_bullets=counts["markdown_bullets"],
        documents=docs,
        words=words,
    )


def _median(values: list) -> float:
    return statistics.median(values) if values else 0.0


@dataclass
class SourceDensity:
    corpus: str
    source: str
    documents: int
    median_words: float
    density_per_100: float
    median_opportunities: float
    eligible_20: float


def density_by_source(
    documents: Sequence[CorpusDocument],
    policy: WatermarkPolicy,
) -> list[SourceDensity]:
    """Compare watermark capacity on human vs machine source text (HC3)."""
    groups: dict[str, list[CorpusDocument]] = {}
    for doc in documents:
        key = doc.human_or_machine or "unknown"
        groups.setdefault(key, []).append(doc)
    rows: list[SourceDensity] = []
    for source, docs in sorted(groups.items()):
        densities: list[float] = []
        opp_counts: list[int] = []
        words: list[int] = []
        eligible = 0
        for doc in docs:
            if doc.word_count < 15:
                continue
            decoded = decode_document(doc.text, policy)
            densities.append(decoded.usable_opportunities / max(doc.word_count, 1) * 100)
            opp_counts.append(decoded.usable_opportunities)
            words.append(doc.word_count)
            if decoded.usable_opportunities >= 20:
                eligible += 1
        rows.append(
            SourceDensity(
                corpus=documents[0].corpus if documents else "",
                source=source,
                documents=len(docs),
                median_words=_median(words),
                density_per_100=_median(densities),
                median_opportunities=_median(opp_counts),
                eligible_20=eligible / max(len(docs), 1),
            )
        )
    return rows


# --------------------------------------------------------------------------
# Canonicalization mode experiment (Milestone 8)
# --------------------------------------------------------------------------


@dataclass
class CanonicalizationModeResult:
    mode: str
    documents: int
    unedited_match_rate: float
    lowercase_match_rate: float
    unedited_detected: float
    lowercase_detected: float
    collision_duplicate_fraction: float
    total_ids: int
    unique_ids: int


def benchmark_canonicalization_modes(
    *,
    documents: Sequence[CorpusDocument],
    policy: WatermarkPolicy,
    max_documents: int = 300,
    seed: int = 4,
) -> list[CanonicalizationModeResult]:
    from tracemark.watermark.canonicalizers import CASE_SENSITIVE, CASEFOLDED
    from tracemark.watermark.detector import FingerprintCandidate, detect_fingerprint

    docs = documents[:max_documents]
    alice = make_fingerprint("alice")
    results: list[CanonicalizationModeResult] = []

    for canonicalizer in (CASE_SENSITIVE, CASEFOLDED):
        rates_clean: list[float] = []
        rates_lower: list[float] = []
        detected_clean = 0
        detected_lower = 0
        for doc in docs:
            wm = apply_watermark(
                text=doc.text,
                fingerprint_key=alice.key,
                policy=policy,
                canonicalizer=canonicalizer,
            )
            # Clean attribution.
            det = detect_fingerprint(
                text=wm.text,
                candidates=[FingerprintCandidate("alice", None, alice.key)],
                policy=policy,
            )
            if det.detected:
                detected_clean += 1
            alice_score = next(
                s for s in det.scores if s.subject_tag == "alice"
            )
            rates_clean.append(alice_score.match_rate)

            # Lowercase attack.
            lowered = wm.text.lower()
            det_low = detect_fingerprint(
                text=lowered,
                candidates=[FingerprintCandidate("alice", None, alice.key)],
                policy=policy,
            )
            if det_low.detected:
                detected_lower += 1
            alice_low = next(
                s for s in det_low.scores if s.subject_tag == "alice"
            )
            rates_lower.append(alice_low.match_rate)

        # Collisions across the sample.
        counts: dict[bytes, int] = {}
        for doc in docs:
            decoded = decode_document(doc.text, policy, canonicalizer=canonicalizer)
            for opp in decoded.opportunities:
                counts[opp.ident] = counts.get(opp.ident, 0) + 1
        total = sum(counts.values())
        unique = len(counts)

        results.append(
            CanonicalizationModeResult(
                mode=canonicalizer.version,
                documents=len(docs),
                unedited_match_rate=statistics.mean(rates_clean),
                lowercase_match_rate=statistics.mean(rates_lower),
                unedited_detected=detected_clean / max(len(docs), 1),
                lowercase_detected=detected_lower / max(len(docs), 1),
                collision_duplicate_fraction=(total - unique) / max(total, 1),
                total_ids=total,
                unique_ids=unique,
            )
        )
    return results


def _pct(values: list, p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    return values[min(len(values) - 1, int(p * len(values)))]
