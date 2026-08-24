"""Shared low-level text scanning helpers for rules."""

from __future__ import annotations

from dataclasses import dataclass

DOUBLE_OPENS = {'"', "\u201c"}
DOUBLE_CLOSES = {'"', "\u201d"}
SINGLE_OPENS = {"'", "\u2018"}
SINGLE_CLOSES = {"'", "\u2019"}

DOUBLE_CHARS = DOUBLE_OPENS | DOUBLE_CLOSES
SINGLE_CHARS = SINGLE_OPENS | SINGLE_CLOSES


@dataclass(frozen=True)
class QuotePair:
    start: int
    end: int
    kind: str  # "double" or "single"
    open_char: str
    close_char: str

    def canonical(self) -> tuple[str, str]:
        if self.kind == "double":
            return ('"', '"')
        return ("'", "'")

    def curly(self) -> tuple[str, str]:
        if self.kind == "double":
            return ("\u201c", "\u201d")
        return ("\u2018", "\u2019")

    def is_straight(self) -> bool:
        return self.open_char in ('"', "'") and self.close_char in ('"', "'")

    def decode_bit(self) -> int | None:
        if self.open_char in DOUBLE_OPENS or self.open_char in SINGLE_OPENS:
            return 0
        if self.open_char in {"\u201c", "\u2018"}:
            return 1
        return None


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def scan_quote_pairs(text: str) -> list[QuotePair]:
    """Find balanced quote pairs that enclose ordinary text.

    Apostrophes (a quote between two word characters, e.g. "don't") are not
    treated as quote delimiters. An opening quote must be preceded by a
    non-word character; a closing quote must be followed by a non-word
    character.
    """
    pairs: list[QuotePair] = []
    n = len(text)

    def match_pair(i: int, opens: set[str], closes: set[str]) -> tuple[int, str, str] | None:
        open_char = text[i]
        prev = text[i - 1] if i > 0 else ""
        if prev and _is_word_char(prev):
            return None
        # The content must not contain another same-kind quote character.
        j = i + 1
        while j < n:
            ch = text[j]
            if ch in opens or ch in closes:
                if ch in closes:
                    nxt = text[j + 1] if j + 1 < n else ""
                    if not nxt or not _is_word_char(nxt):
                        return j, open_char, ch
                return None
            j += 1
        return None

    i = 0
    while i < n:
        ch = text[i]
        if ch in DOUBLE_CHARS:
            result = match_pair(i, DOUBLE_OPENS, DOUBLE_CLOSES)
            if result is not None:
                close, open_char, close_char = result
                pairs.append(QuotePair(i, close + 1, "double", open_char, close_char))
                i = close + 1
                continue
        elif ch in SINGLE_CHARS:
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt and _is_word_char(nxt):
                result = match_pair(i, SINGLE_OPENS, SINGLE_CLOSES)
                if result is not None:
                    close, open_char, close_char = result
                    pairs.append(QuotePair(i, close + 1, "single", open_char, close_char))
                    i = close + 1
                    continue
        i += 1
    return pairs


def find_enclosing_quote_range(pairs: list[QuotePair], start: int, end: int) -> QuotePair | None:
    for pair in pairs:
        if pair.start <= start and end <= pair.end:
            return pair
    return None


def sentence_index(doc, pos: int) -> int:
    for idx, sent in enumerate(doc.sents):
        if sent.start_char <= pos < sent.end_char:
            return idx
    return -1
