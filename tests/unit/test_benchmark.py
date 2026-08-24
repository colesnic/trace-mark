"""Benchmark harness smoke tests (no external calls)."""

from __future__ import annotations

import random

from tracemark.benchmarks.attacks import (
    delete_sentences,
    expand_all_contractions,
    lowercase_text,
    normalize_typography,
    remove_serial_commas,
    sentence_reorder,
)
from tracemark.benchmarks.benchmark import load_corpus


def test_load_corpus_all_categories():
    docs = load_corpus()
    categories = {d.category for d in docs}
    assert "business email" in categories
    assert "markdown" in categories
    assert "short responses" in categories
    assert len(docs) >= 15


def test_delete_sentences_never_double_period():
    rng = random.Random(0)
    text = "One sentence. Two sentences. Three sentences."
    for rate in (0.1, 0.3, 0.5):
        out = delete_sentences(text, rate, rng)
        assert ".." not in out
        assert out.endswith(".")
        assert out.count(". ") + 1 >= 1


def test_delete_sentences_reduces_length():
    rng = random.Random(0)
    text = "One sentence. Two sentences. Three sentences. Four sentences."
    out = delete_sentences(text, 0.5, rng)
    assert out.count(". ") < text.count(". ")


def test_normalize_typography():
    assert normalize_typography("\u201chello\u201d \u2026") == '"hello" ...'


def test_expand_all_contractions():
    assert expand_all_contractions("Don't go.") == "Do not go."


def test_remove_serial_commas():
    assert remove_serial_commas("red, white, and blue") == "red, white and blue"


def test_sentence_reorder_preserves_sentences():
    rng = random.Random(0)
    text = "First sentence. Second sentence. Third sentence."
    out = sentence_reorder(text, rng)
    for frag in ("First sentence", "Second sentence", "Third sentence"):
        assert frag in out


def test_lowercase():
    assert lowercase_text("We Do Not") == "we do not"


def test_benchmark_runs_and_writes_report(tmp_path):
    import tracemark.benchmarks.benchmark as bm

    # Point results/corpus at the real paths (already on disk).
    markdown = bm.run_benchmark()
    assert "TraceMark" in markdown
    report = bm.RESULTS_DIR / "report.md"
    assert report.exists()
    assert "## Attack survival" in report.read_text(encoding="utf-8")
