"""Benchmark harness.

No external LLM calls. Results are written to ``benchmarks/results/`` as JSON
plus a rendered Markdown summary.

Runs on the local machine (M3 Pro target):
- opportunity density over the bundled corpus
- attribution (correct subject ranks first)
- adversarial edit survival
- false-positive rate on unwatermarked text
- watermark/detection latency
"""

from __future__ import annotations

import json
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from tracemark.benchmarks.attacks import ATTACKS
from tracemark.benchmarks.report import render_markdown, save_metrics
from tracemark.crypto.fingerprint import derive_fingerprint
from tracemark.watermark.detector import (
    FingerprintCandidate,
    detect_fingerprint,
)
from tracemark.watermark.engine import apply_watermark, get_nlp
from tracemark.watermark.policy import WatermarkPolicy

TENANT = UUID("11111111-1111-1111-1111-111111111111")
MASTER = b"\x42" * 32

RESULTS_DIR = Path("benchmarks/results")
CORPUS_DIR = Path("benchmarks/corpus")


@dataclass
class CorpusDoc:
    id: str
    category: str
    text: str


def load_corpus() -> list[CorpusDoc]:
    docs: list[CorpusDoc] = []
    for path in sorted(CORPUS_DIR.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            docs.append(CorpusDoc(record["id"], record["category"], record["text"]))
    return docs


def _fingerprint(external_ref: str):
    return derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT, subject_external_ref=external_ref
    )


def _decoys(alice, bob, n_randoms: int = 5, seed: int = 42) -> list[FingerprintCandidate]:
    rng = random.Random(seed)
    candidates = [
        FingerprintCandidate(alice.subject_tag, None, alice.key),
        FingerprintCandidate(bob.subject_tag, None, bob.key),
    ]
    for i in range(n_randoms):
        candidates.append(FingerprintCandidate(f"rand-{i}", None, rng.randbytes(32)))
    return candidates


def _measure(fn, n: int = 10) -> list[float]:
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    return times


def _percentiles(times: list[float]) -> tuple[float, float, float]:
    return times[len(times) // 2], times[int(len(times) * 0.95)], statistics.mean(times)


def run_benchmark() -> str:
    alice = _fingerprint("alice")
    bob = _fingerprint("bob")
    policy = WatermarkPolicy.from_name("balanced")
    nlp = get_nlp()

    docs = load_corpus()
    nlp("warmup")

    corpus_rows: list[dict] = []
    attribution_rows: list[dict] = []
    rule_distribution: Counter = Counter()

    for doc in docs:
        result = apply_watermark(text=doc.text, fingerprint_key=alice.key, policy=policy)
        words = len(doc.text.split())
        per_100 = result.opportunities_found / max(words, 1) * 100
        for t in result.transformations:
            rule_distribution[t.rule_id] += 1

        candidates = _decoys(alice, bob)
        det = detect_fingerprint(text=result.text, candidates=candidates, policy=policy)
        correct = next(
            c for c in det.scores if c.subject_tag == alice.subject_tag
        )
        best = det.scores[0]
        attribution_rows.append(
            {
                "id": doc.id,
                "correct_ranked_first": best.subject_tag == alice.subject_tag,
                "correct_rate": correct.match_rate,
                "best_rate": best.match_rate,
                "opportunities": det.usable_opportunities,
            }
        )
        corpus_rows.append(
            {
                "category": doc.category,
                "docs": 1,
                "words": words,
                "opportunities": result.opportunities_found,
                "per_100_words": per_100,
                "transforms": result.transformations_applied,
            }
        )

    # Aggregate corpus by category.
    agg: dict[str, dict] = {}
    for row in corpus_rows:
        key = row["category"]
        target = agg.setdefault(
            key,
            {"category": key, "docs": 0, "words": 0, "opportunities": 0, "transforms": 0},
        )
        target["docs"] += 1
        target["words"] += row["words"]
        target["opportunities"] += row["opportunities"]
        target["transforms"] += row["transforms"]
    for target in agg.values():
        target["per_100_words"] = (
            target["opportunities"] / max(target["words"], 1) * 100
        )
    corpus_rows = list(agg.values())

    # ---- Attack survival ----
    # Build composite documents long enough to exceed the attribution
    # threshold (~20 opportunities) so survival can be measured end-to-end.
    attack_docs: list[str] = []
    chunk = []
    for doc in docs:
        chunk.append(doc.text)
        if len(" ".join(chunk).split()) >= 350:
            attack_docs.append(" ".join(chunk))
            chunk = []
    if chunk:
        attack_docs.append(" ".join(chunk))

    watermarked = [
        apply_watermark(text=text, fingerprint_key=alice.key, policy=policy).text
        for text in attack_docs
    ]
    attack_results: dict[str, dict] = {}
    rng = random.Random(11)
    for name, attack_fn in ATTACKS.items():
        rates: list[float] = []
        evidences: list[float] = []
        detected = 0
        for wm in watermarked:
            attacked = attack_fn(wm, rng)
            det = detect_fingerprint(
                text=attacked, candidates=_decoys(alice, bob), policy=policy
            )
            correct = next(
                c for c in det.scores if c.subject_tag == alice.subject_tag
            )
            rates.append(correct.match_rate)
            if det.best_candidate is not None:
                evidences.append(det.best_candidate.evidence_score)
            if (
                det.detected
                and det.best_candidate is not None
                and det.best_candidate.subject_tag == alice.subject_tag
            ):
                detected += 1
        attack_results[name] = {
            "attack": name,
            "docs": len(watermarked),
            "mean_match_rate": statistics.mean(rates),
            "detected_fraction": detected / max(len(watermarked), 1),
            "median_evidence": statistics.median(evidences) if evidences else 0.0,
        }
    attacks_rows = list(attack_results.values())

    # ---- False positives: unwatermarked corpus vs many random candidates ----
    fp = _false_positive_benchmark(docs, policy)

    # ---- Latency ----
    latency_rows: list[dict] = []
    sample = " ".join(d.text for d in docs[:4])
    for label, size in (("100w", 100), ("500w", 500), ("1000w", 1000), ("5000w", 5000)):
        token_list = sample.split() * (max(1, size // max(len(sample.split()), 1)) + 1)
        text = " ".join(token_list[:size])
        times = _measure(
            lambda text=text: apply_watermark(
                text=text, fingerprint_key=alice.key, policy=policy
            ),
            n=10,
        )
        p50, p95, mean = _percentiles(times)
        latency_rows.append({"name": f"watermark {label}", "p50": p50, "p95": p95, "mean": mean})
    for label, size in (("500w", 500), ("1000w", 1000)):
        token_list = sample.split() * (max(1, size // max(len(sample.split()), 1)) + 1)
        text = " ".join(token_list[:size])
        wm = apply_watermark(text=text, fingerprint_key=alice.key, policy=policy).text
        times = _measure(
            lambda wm=wm: detect_fingerprint(
                text=wm, candidates=_decoys(alice, bob), policy=policy
            ),
            n=10,
        )
        p50, p95, mean = _percentiles(times)
        latency_rows.append({"name": f"detect {label}", "p50": p50, "p95": p95, "mean": mean})

    metrics = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_documents": len(docs),
        "corpus": corpus_rows,
        "attribution": attribution_rows,
        "attacks": attacks_rows,
        "false_positive": fp,
        "latency": latency_rows,
        "rule_distribution": dict(rule_distribution),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    save_metrics(metrics, str(RESULTS_DIR / "metrics.json"))
    markdown = render_markdown(metrics)
    (RESULTS_DIR / "report.md").write_text(markdown, encoding="utf-8")

    return _summary(metrics)


def _false_positive_benchmark(docs: list[CorpusDoc], policy: WatermarkPolicy) -> dict:
    rng = random.Random(99)
    candidates = [
        FingerprintCandidate(f"rand-{i}", None, rng.randbytes(32)) for i in range(20)
    ]
    raw_sig = 0
    adj_sig = 0
    top_rates: list[float] = []
    for doc in docs:
        det = detect_fingerprint(text=doc.text, candidates=candidates, policy=policy)
        if det.usable_opportunities >= 20 and det.scores:
            best = det.scores[0]
            top_rates.append(best.match_rate)
            if best.p_value < 0.05:
                raw_sig += 1
            if best.adjusted_p_value < 0.05:
                adj_sig += 1
    n = len(docs)
    return {
        "candidates_per_doc": len(candidates),
        "raw_significant_fraction": raw_sig / max(n, 1),
        "adjusted_significant_fraction": adj_sig / max(n, 1),
        "top_candidate_match_rate_mean": statistics.mean(top_rates) if top_rates else 0.0,
    }


def _summary(metrics: dict) -> str:
    lines = ["TraceMark benchmark report", "=========================="]
    lines.append(f"corpus documents: {metrics['n_documents']}")
    lines.append("")
    lines.append("Attribution (correct subject ranked first):")
    correct = sum(1 for r in metrics["attribution"] if r["correct_ranked_first"])
    lines.append(f"  {correct}/{len(metrics['attribution'])} documents")
    lines.append("")
    lines.append("Attack survival (mean match rate):")
    for row in metrics["attacks"]:
        lines.append(f"  {row['attack']:24} {row['mean_match_rate']:.3f}")
    fp = metrics["false_positive"]
    lines.append("")
    lines.append(
        f"False positives: raw={fp['raw_significant_fraction']:.3f} "
        f"Bonferroni={fp['adjusted_significant_fraction']:.3f}"
    )
    for row in metrics["latency"]:
        lines.append(f"  {row['name']:16} p50={row['p50']:.1f}ms p95={row['p95']:.1f}ms")
    lines.append("")
    lines.append("Full report: benchmarks/results/report.md")
    return "\n".join(lines)
