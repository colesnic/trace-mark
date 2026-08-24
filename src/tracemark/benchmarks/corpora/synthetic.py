"""Synthetic corpus — deterministic, offline, dependency-free.

Used for unit tests, CI, and null-model cross-checks when public corpora are
not available. Generation is seeded and repeatable.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from pathlib import Path

from tracemark.benchmarks.corpora.base import CorpusDocument

_SENTENCES = [
    "The committee reviewed the annual report, the budget and the forecast.",
    "We do not believe the new policy is fair, and we will not accept it.",
    "The manager said... \u201cThis is a great opportunity, isn\u2019t it?\u201d",
    "It was a red, white and blue flag \u2014 it really was a sight to behold.",
    "The plan covers revenue, expenses and liabilities for the coming year.",
    "We do not think the deadline is realistic, and we cannot meet it.",
    "The report included sales, marketing and operations data.",
    "She was tired, hungry and frustrated after the long meeting.",
    "The board will not approve the merger, and it will not reverse course.",
    "Our system supports Linux, macOS and Windows without issue.",
    "The vendor said... \u201cThis version is stable, and it is not ready.\u201d",
    "The team analyzed cost, quality and timing trade-offs.",
    "We do not expect growth this quarter, and we will not raise guidance.",
    "The flag had red, white and blue stripes.",
    "It was a difficult, complex and risky decision \u2014 we knew it.",
    "The paper reviews methods, results and limitations.",
    "They were not ready for the launch, and they did not have a backup.",
    "The proposal includes scope, schedule and budget.",
    "We do not see a path forward, and we will not pretend otherwise.",
    "The menu offered soup, salad and sandwiches for lunch.",
]

_CATEGORIES = ["business email", "financial", "technical", "general prose", "legal"]


class SyntheticSource:
    """Deterministic synthetic corpus (no download)."""

    name = "synthetic"

    def fetch(self, cache_dir: Path) -> None:
        return

    def iter_documents(self, cache_dir: Path) -> Iterable[CorpusDocument]:
        rng = random.Random(2024)
        for i in range(200):
            category = _CATEGORIES[i % len(_CATEGORIES)]
            n_sentences = rng.randint(3, 10)
            text = " ".join(rng.choice(_SENTENCES) for _ in range(n_sentences))
            yield CorpusDocument(
                corpus=self.name,
                document_id=f"synthetic-{i:04d}",
                text=text,
                category=category,
                author_id=f"auth-{i % 12}",
                human_or_machine="human",
                generator=None,
                word_count=len(text.split()),
            )
