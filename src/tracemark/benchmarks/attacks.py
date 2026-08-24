"""Adversarial edit attacks against watermarked text.

These quantify fingerprint survival under realistic editing. Heavy
paraphrasing and translation are intentionally NOT included: they require an
external LLM and would be dishonest to fake.
"""

from __future__ import annotations

import random
import re


def _sentences(text: str) -> list[str]:
    stripped = text.rstrip()
    if stripped.endswith("."):
        stripped = stripped[:-1]
    return [s.strip() for s in stripped.split(". ") if s.strip()]


def delete_sentences(text: str, rate: float, rng: random.Random) -> str:
    """Delete a fraction of sentences (never producing double periods)."""
    sentences = _sentences(text)
    if not sentences:
        return text
    keep = max(1, int(len(sentences) * (1 - rate)))
    selected = rng.sample(sentences, keep)
    return ". ".join(selected) + "."


def normalize_typography(text: str) -> str:
    """Replace all curly punctuation with straight equivalents."""
    out = text.replace("\u201c", '"').replace("\u201d", '"')
    out = out.replace("\u2018", "'").replace("\u2019", "'")
    out = out.replace("\u2026", "...")
    out = re.sub(r"[ \t]*\u2014[ \t]*", " \u2014 ", out)
    return out


def expand_all_contractions(text: str) -> str:
    from tracemark.watermark.rules.contractions import expand_contractions

    return expand_contractions(text)


def remove_serial_commas(text: str) -> str:
    """Remove every comma directly before and/or/nor."""
    return re.sub(r",\s+(\b(?:and|or|nor)\b)", r" \1", text, flags=re.IGNORECASE)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def lowercase_text(text: str) -> str:
    return text.lower()


def sentence_reorder(text: str, rng: random.Random) -> str:
    sentences = _sentences(text)
    if len(sentences) < 2:
        return text
    rng.shuffle(sentences)
    return ". ".join(sentences) + "."


ATTACKS = {
    "original": lambda text, rng: text,
    "delete_10pct": lambda text, rng: delete_sentences(text, 0.10, rng),
    "delete_20pct": lambda text, rng: delete_sentences(text, 0.20, rng),
    "delete_30pct": lambda text, rng: delete_sentences(text, 0.30, rng),
    "typography_normalize": lambda text, rng: normalize_typography(text),
    "contraction_normalize": lambda text, rng: expand_all_contractions(text),
    "serial_comma_normalize": lambda text, rng: remove_serial_commas(text),
    "whitespace_normalize": lambda text, rng: normalize_whitespace(text),
    "lowercase": lambda text, rng: lowercase_text(text),
    "sentence_reorder": lambda text, rng: sentence_reorder(text, rng),
}
