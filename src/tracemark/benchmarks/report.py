"""Benchmark report rendering (Markdown)."""

from __future__ import annotations

import json


def render_markdown(metrics: dict) -> str:
    lines: list[str] = []
    lines.append("# TraceMark benchmark report")
    lines.append("")
    lines.append(f"Generated: {metrics.get('generated_at', '')}")
    lines.append(f"Corpus documents: {metrics.get('n_documents', 0)}")
    lines.append("")
    lines.append("## Corpus summary")
    lines.append("")
    lines.append("| category | docs | words | opportunities | per 100 words | transforms |")
    lines.append("|----------|------|-------|---------------|---------------|------------|")
    for row in metrics.get("corpus", []):
        lines.append(
            f"| {row['category']} | {row['docs']} | {row['words']} | "
            f"{row['opportunities']} | {row['per_100_words']:.1f} | {row['transforms']} |"
        )
    lines.append("")
    lines.append("## Attribution benchmark")
    lines.append("")
    for row in metrics.get("attribution", []):
        lines.append(
            f"- {row['id']}: correct ranked first={row['correct_ranked_first']}, "
            f"correct rate={row['correct_rate']:.3f}, best rate={row['best_rate']:.3f}"
        )
    lines.append("")
    lines.append("## Attack survival")
    lines.append("")
    lines.append("| attack | docs | mean match rate | detected | evidence (median) |")
    lines.append("|--------|------|-----------------|----------|------------------|")
    for row in metrics.get("attacks", []):
        lines.append(
            f"| {row['attack']} | {row['docs']} | {row['mean_match_rate']:.3f} | "
            f"{row['detected_fraction']:.2f} | {row['median_evidence']:.2f} |"
        )
    lines.append("")
    lines.append("## False positive (unwatermarked corpus vs random candidates)")
    lines.append("")
    fp = metrics.get("false_positive", {})
    lines.append(
        f"- candidates per document: {fp.get('candidates_per_doc', 0)}"
    )
    lines.append(
        f"- docs with any significant attribution (raw p<0.05): "
        f"{fp.get('raw_significant_fraction', 0.0):.3f}"
    )
    lines.append(
        f"- docs with any significant attribution (Bonferroni): "
        f"{fp.get('adjusted_significant_fraction', 0.0):.3f}"
    )
    lines.append("")
    lines.append("## Latency (ms)")
    lines.append("")
    lines.append("| operation | p50 | p95 | mean |")
    lines.append("|-----------|-----|-----|------|")
    for row in metrics.get("latency", []):
        lines.append(
            f"| {row['name']} | {row['p50']:.1f} | {row['p95']:.1f} | {row['mean']:.1f} |"
        )
    lines.append("")
    return "\n".join(lines)


def save_metrics(metrics: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, default=str)
