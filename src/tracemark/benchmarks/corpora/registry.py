"""Corpus source registry."""

from __future__ import annotations

from tracemark.benchmarks.corpora.base import CorpusSource
from tracemark.benchmarks.corpora.enron import EnronSource
from tracemark.benchmarks.corpora.hc3 import HC3Source
from tracemark.benchmarks.corpora.m4 import M4Source
from tracemark.benchmarks.corpora.newsgroups import NewsgroupsSource
from tracemark.benchmarks.corpora.synthetic import SyntheticSource

_SOURCES: dict[str, CorpusSource] = {
    "enron": EnronSource(),
    "hc3": HC3Source(),
    "m4": M4Source(),
    "newsgroups": NewsgroupsSource(),
    "synthetic": SyntheticSource(),
}


def get_source(name: str) -> CorpusSource:
    if name not in _SOURCES:
        raise KeyError(f"unknown corpus source: {name}")
    return _SOURCES[name]


def available_sources() -> list[str]:
    return list(_SOURCES.keys())
