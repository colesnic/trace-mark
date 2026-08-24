"""Generate all V2 research benchmarks and the final report.

Run with::

    uv run python -m tracemark.benchmarks.report_v2

Writes machine-readable CSVs under ``benchmarks/results/v2/`` and the
research report to ``docs/research-v2-report.md``.
"""

from __future__ import annotations

import random
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path

from tracemark.benchmarks.results_io import write_metrics_json, write_rows_csv
from tracemark.benchmarks.v2 import (
    RESULTS_V2,
    analyze_match_dependence,
    analyze_opportunity_id_collisions,
    attribution_grid,
    benchmark_author_style_bias,
    benchmark_candidate_scale,
    calibrate_null_model,
    channel_ablation,
    corpus_statistics,
    load_corpus,
    make_fingerprint,
    make_sentence_preserving_window,
)
from tracemark.benchmarks.v2stats import (
    theoretical_detection_limits,
)
from tracemark.watermark.detector import (
    FingerprintCandidate,
    decode_document,
    score_candidates,
)
from tracemark.watermark.engine import apply_watermark
from tracemark.watermark.policy import WatermarkPolicy

POLICY = WatermarkPolicy.from_name("balanced")
ALICE = make_fingerprint("alice")

_DOC_DIR = Path("docs")


def _sample(docs, n, seed=1):
    rng = random.Random(seed)
    rng.shuffle(docs)
    return docs[:n]


def run_corpus_stats() -> dict:
    rows = []
    for name, sample_n in [("enron", 3000), ("hc3", 3000), ("synthetic", 200)]:
        try:
            docs = _sample(load_corpus(name), sample_n)
        except FileNotFoundError as exc:
            print(f"[skip] {name}: {exc}")
            continue
        stats = corpus_statistics(docs, POLICY)
        rows.append(
            {
                "corpus": name,
                "documents": stats.documents,
                "median_words": stats.median_words,
                "p10_words": stats.p10_words,
                "p90_words": stats.p90_words,
                "density_per_100_median": stats.opportunity_stats["median_per_100"],
                "density_p10": stats.opportunity_stats["p10_per_100"],
                "density_p90": stats.opportunity_stats["p90_per_100"],
                "median_opportunities": stats.median_opportunities,
                "eligible_20": stats.eligible_20,
                "rule_contractions": stats.rule_distribution.get("contractions", 0),

                "rule_serial_comma": stats.rule_distribution.get("serial_comma", 0),
                "rule_apostrophes": stats.rule_distribution.get("apostrophes", 0),
                "rule_quotes": stats.rule_distribution.get("quotes", 0),
                "rule_ellipsis": stats.rule_distribution.get("ellipsis", 0),
                "human_fraction": stats.human_fraction,
                "machine_fraction": stats.machine_fraction,
            }
        )
    write_rows_csv(RESULTS_V2 / "corpus_stats.csv", rows)
    return {"corpus_stats": rows}


def run_length_experiment() -> dict:
    from contextlib import suppress

    docs = []
    for name in ("enron", "hc3"):
        with suppress(FileNotFoundError):
            docs.extend(_sample(load_corpus(name), 4000, seed=name))
    long_docs = [d for d in docs if d.word_count >= 500]
    buckets = [50, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000]

    rows = []
    for target in buckets:
        windows = []
        for doc in long_docs:
            w = make_sentence_preserving_window(doc.text, target)
            if w is not None:
                windows.append(w)
        windows = _sample(windows, 150, seed=target)
        if not windows:
            continue
        opp_counts = []
        eligible = 0
        for w in windows:
            decoded = decode_document(w, POLICY)
            opp_counts.append(decoded.usable_opportunities)
            if decoded.usable_opportunities >= 20:
                eligible += 1
        rows.append(
            {
                "target_words": target,
                "windows": len(windows),
                "median_opportunities": statistics.median(opp_counts),
                "p10_opportunities": sorted(opp_counts)[int(0.10 * len(opp_counts))],
                "p90_opportunities": sorted(opp_counts)[int(0.90 * len(opp_counts))],
                "eligible_20": eligible / max(len(windows), 1),
            }
        )
    write_rows_csv(RESULTS_V2 / "length_results.csv", rows)
    return {"length": rows}


def run_candidate_scale() -> dict:
    docs = _sample(load_corpus("enron"), 3000, seed=9)
    long_docs = [d for d in docs if d.word_count >= 400]
    candidates_counts = [10, 100, 1000, 5000, 10000]
    results = benchmark_candidate_scale(
        documents=long_docs[:60],
        candidate_counts=candidates_counts,
        repetitions=1,
    )
    write_rows_csv(RESULTS_V2 / "candidate_scale.csv", [asdict(r) for r in results])
    return {"candidate_scale": results}


def run_null_calibration() -> dict:
    rows = calibrate_null_model(
        opportunity_counts=[10, 20, 30, 50, 100],
        candidate_counts=[10, 100, 1000, 10000],
        trials=2000,
    )
    write_rows_csv(RESULTS_V2 / "null_calibration.csv", [asdict(r) for r in rows])
    return {"null_calibration": rows}


def run_false_positives() -> dict:
    docs = _sample(load_corpus("enron"), 4000, seed=42)
    rows = []
    from tracemark.benchmarks.v2 import benchmark_false_positives

    results = benchmark_false_positives(
        documents=docs, candidate_counts=[100, 1000], policy=POLICY
    )
    for r in results:
        rows.append(asdict(r))
    write_rows_csv(RESULTS_V2 / "false_positives.csv", rows)
    return {"false_positives": results}


def run_author_bias() -> dict:
    docs = _sample(load_corpus("enron"), 6000, seed=77)
    rng = random.Random(5)
    candidate_keys = [rng.randbytes(32) for _ in range(200)]
    results = benchmark_author_style_bias(
        documents=docs, candidate_keys=candidate_keys, policy=POLICY
    )
    write_rows_csv(RESULTS_V2 / "author_style.csv", [asdict(r) for r in results])
    return {"author_style": results}


def run_ablation() -> dict:
    docs = _sample(load_corpus("hc3"), 400, seed=13)
    rows = channel_ablation(documents=docs, policy=POLICY, max_documents=300)
    write_rows_csv(RESULTS_V2 / "channel_ablation.csv", [asdict(r) for r in rows])
    return {"ablation": rows}


def run_collisions() -> dict:
    docs = _sample(load_corpus("enron"), 3000, seed=31) + _sample(
        load_corpus("hc3"), 3000, seed=32
    )
    report = analyze_opportunity_id_collisions(docs, POLICY)
    top = [{"id_hex": k.hex()[:16], "count": v} for k, v in report.top_repeated]
    row = {
        "total_ids": report.total_ids,
        "unique_ids": report.unique_ids,
        "duplicate_ids": report.duplicate_ids,
        "duplicate_fraction": report.duplicate_fraction,
    }
    write_rows_csv(RESULTS_V2 / "opportunity_collisions.csv", [row])
    return {"collisions": report, "top_repeated": top}


def run_dependence() -> dict:
    docs = _sample(load_corpus("enron"), 600, seed=55) + _sample(
        load_corpus("hc3"), 600, seed=56
    )
    decoded = [decode_document(d.text, POLICY) for d in docs]
    rng = random.Random(2)
    keys = [rng.randbytes(32) for _ in range(1)]
    report = analyze_match_dependence(decoded, keys)
    write_metrics_json(RESULTS_V2 / "dependence.json", asdict(report))
    return {"dependence": report}


def run_theoretical() -> dict:
    rows = theoretical_detection_limits(
        opportunity_counts=[10, 15, 20, 25, 30, 40, 50, 75, 100],
        candidate_counts=[10, 100, 1000, 10000, 50000],
    )
    csv_rows = [
        {
            "opportunities": r.opportunities,
            "candidates": r.candidates,
            "min_matches": r.min_matches,
            "required_match_rate": r.required_match_rate,
            "target_alpha": r.target_alpha,
        }
        for r in rows
    ]
    write_rows_csv(RESULTS_V2 / "theoretical_detection_limits.csv", csv_rows)
    # Markdown table.
    md = ["# Theoretical detection limits", ""]
    md.append("Minimum matches (and required match rate) for Bonferroni-adjusted p < 0.05:")
    md.append("")
    header = "| opps | " + " | ".join(f"N={c}" for c in [10, 100, 1000, 10000, 50000]) + " |"
    md.append(header)
    md.append("|------" + "|---------" * 5 + "|")
    by_opps: dict[int, dict[int, tuple[int, float]]] = {}
    for r in rows:
        by_opps.setdefault(r.opportunities, {})[r.candidates] = (
            r.min_matches,
            r.required_match_rate,
        )
    for opps, d in sorted(by_opps.items()):
        cells = []
        for c in [10, 100, 1000, 10000, 50000]:
            k, rate = d.get(c, (None, 0.0))
            cells.append(f"{k} ({rate:.2f})")
        md.append(f"| {opps} | " + " | ".join(cells) + " |")
    (RESULTS_V2 / "theoretical_detection_limits.md").write_text("\n".join(md), encoding="utf-8")
    return {"theoretical": csv_rows}


def run_grid() -> dict:
    docs = []
    for name in ("enron", "hc3"):
        docs.extend(_sample(load_corpus(name), 6000, seed=name))
    long_docs = [d for d in docs if d.word_count >= 500]
    cells = attribution_grid(
        documents=long_docs,
        word_buckets=[100, 200, 300, 400, 500, 750, 1000, 1500, 2000],
        candidate_counts=[10, 100, 1000, 10000],
        policy=POLICY,
    )
    write_rows_csv(RESULTS_V2 / "attribution_grid.csv", [asdict(c) for c in cells])
    return {"grid": cells}


def run_partial_copy() -> dict:

    docs = _sample(load_corpus("enron"), 3000, seed=17)
    candidates = [
        FingerprintCandidate("alice", None, ALICE.key),
        *[
            FingerprintCandidate(
                f"decoy-{i}", None, random.Random(i).randbytes(32)
            )
            for i in range(99)
        ],
    ]
    rows = []
    for frac in [0.10, 0.25, 0.50, 0.75]:
        attributed = 0
        insufficient = 0
        total = 0
        rng = random.Random(int(frac * 100))
        for doc in docs:
            if doc.word_count < 400:
                continue
            wm = apply_watermark(text=doc.text, fingerprint_key=ALICE.key, policy=POLICY)
            text = wm.text
            words = text.split()
            take = max(20, int(len(words) * frac))
            start = rng.randint(0, max(0, len(words) - take))
            partial = " ".join(words[start : start + take])
            decoded = decode_document(partial, POLICY)
            total += 1
            if decoded.usable_opportunities < POLICY.minimum_opportunities:
                insufficient += 1
                continue
            scores = score_candidates(decoded, candidates)
            best = max(scores, key=lambda s: s.match_rate)
            if best.subject_tag == "alice" and best.adjusted_p_value < 0.05:
                attributed += 1
        rows.append(
            {
                "fraction": frac,
                "documents": total,
                "attributed_fraction": attributed / max(total, 1),
                "insufficient_fraction": insufficient / max(total, 1),
            }
        )
    write_rows_csv(RESULTS_V2 / "partial_copy.csv", rows)
    return {"partial_copy": rows}


def asdict(o):
    from dataclasses import asdict as _a

    return _a(o)


def run_canonicalization() -> dict:
    from tracemark.benchmarks.v2 import benchmark_canonicalization_modes

    docs = _sample(load_corpus("enron"), 2000, seed=88) + _sample(
        load_corpus("hc3"), 1000, seed=89
    )
    results = benchmark_canonicalization_modes(documents=docs, policy=POLICY, max_documents=250)
    write_rows_csv(RESULTS_V2 / "canonicalization_modes.csv", [asdict(r) for r in results])
    return {"canonicalization": results}


def run_combined_attacks() -> dict:
    from tracemark.benchmarks.attacks import COMBINED_ATTACKS
    from tracemark.watermark.detector import FingerprintCandidate

    docs = _sample(load_corpus("enron"), 2500, seed=61)
    docs = [d for d in docs if d.word_count >= 400][:120]
    candidates = [FingerprintCandidate("alice", None, ALICE.key)]
    rng = random.Random(12)
    rows = []
    for name, fn in COMBINED_ATTACKS.items():
        rates = []
        detected = 0
        for doc in docs:
            wm = apply_watermark(text=doc.text, fingerprint_key=ALICE.key, policy=POLICY)
            attacked = fn(wm.text, rng)
            decoded = decode_document(attacked, POLICY)
            scores = score_candidates(decoded, candidates)
            best = scores[0]
            rates.append(best.match_rate)
            if (
                decoded.usable_opportunities >= POLICY.minimum_opportunities
                and best.adjusted_p_value < 0.05
            ):
                detected += 1
        rows.append(
            {
                "attack": name,
                "documents": len(docs),
                "mean_match_rate": statistics.mean(rates),
                "detected_fraction": detected / max(len(docs), 1),
            }
        )
    write_rows_csv(RESULTS_V2 / "combined_attacks.csv", rows)
    return {"combined_attacks": rows}


def run_human_machine() -> dict:
    from tracemark.benchmarks.v2 import density_by_source

    docs = _sample(load_corpus("hc3"), 2500, seed=91)
    rows = density_by_source(docs, POLICY)
    write_rows_csv(
        RESULTS_V2 / "human_machine_density.csv",
        [
            {
                "corpus": r.corpus,
                "source": r.source,
                "documents": r.documents,
                "median_words": r.median_words,
                "density_per_100": r.density_per_100,
                "median_opportunities": r.median_opportunities,
                "eligible_20": r.eligible_20,
            }
            for r in rows
        ],
    )
    return {"human_machine": rows}


def run_all(only: list[str] | None = None) -> dict:
    import json

    started = time.time()
    print("V2 benchmarks running…")
    results: dict = {}
    existing = RESULTS_V2 / "all_results.json"
    if only is not None and existing.exists():
        # Merge with previously saved results so partial runs accumulate.
        results = json.loads(existing.read_text(encoding="utf-8"))
    steps = _STEPS if only is None else [s for s in _STEPS if s[0] in only]
    for name, fn in steps:
        t0 = time.time()
        print(f"[run] {name} …")
        try:
            results[name] = fn()
        except Exception as exc:  # noqa: BLE001 - keep going, report failures
            print(f"[error] {name}: {exc}")
            results[name] = {"error": str(exc)}
        print(f"[done] {name} ({time.time() - t0:.0f}s)")
    if only is None:
        results["runtime_seconds"] = time.time() - started
    write_metrics_json(RESULTS_V2 / "all_results.json", results)
    _write_report(results)
    print(f"benchmarks complete ({time.time() - started:.0f}s)")
    return results


_STEPS: list[tuple[str, Callable[[], dict]]] = [
    ("corpus_stats", run_corpus_stats),
    ("length", run_length_experiment),
    ("candidate_scale", run_candidate_scale),
    ("null_calibration", run_null_calibration),
    ("false_positives", run_false_positives),
    ("author_bias", run_author_bias),
    ("ablation", run_ablation),
    ("collisions", run_collisions),
    ("dependence", run_dependence),
    ("theoretical", run_theoretical),
    ("grid", run_grid),
    ("partial_copy", run_partial_copy),
    ("canonicalization", run_canonicalization),
    ("combined_attacks", run_combined_attacks),
    ("human_machine", run_human_machine),
]


def render_existing_report() -> None:
    """Re-render the report from the saved all_results.json (no re-running)."""
    import json

    path = RESULTS_V2 / "all_results.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run the benchmarks first")
    results = json.loads(path.read_text(encoding="utf-8"))
    _write_report(results)
    print("report re-rendered from", path)


def _write_report(results: dict) -> None:
    from tracemark.benchmarks.research_report import render_report

    _DOC_DIR.mkdir(parents=True, exist_ok=True)
    report = render_report(results)
    (_DOC_DIR / "research-v2-report.md").write_text(report, encoding="utf-8")
    print("report written to docs/research-v2-report.md")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run TraceMark V2 benchmarks")
    parser.add_argument("--only", default=None, help="comma-separated step names")
    parser.add_argument("--report", action="store_true", help="only re-render the report")
    args = parser.parse_args()

    if args.report:
        render_existing_report()
    else:
        only = args.only.split(",") if args.only else None
        run_all(only=only)
    sys.exit(0)
