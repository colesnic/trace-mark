"""Global canonicalization and protection tests."""

from __future__ import annotations

from tracemark.watermark.opportunities import canonicalize_for_fingerprinting
from tracemark.watermark.protection import TextRange, detect_protected_ranges, is_protected


def test_canonicalization_is_idempotent():
    samples = [
        "We don't think it's fair, and we will not accept it.",
        "The manager said... \u201cThis is great\u201d \u2014 it really was.",
        "red, white, and blue",
        "Use e.g. an example: \u2018quoted\u2019.",
        "I can not believe that is true...",
    ]
    for s in samples:
        once = canonicalize_for_fingerprinting(s)
        twice = canonicalize_for_fingerprinting(once)
        assert once == twice, f"not idempotent for {s!r}"


def test_canonicalization_makes_variants_identical():
    pairs = [
        ("We don't think so.", "We do not think so."),
        ("red, white and blue", "red, white, and blue"),
        ('"quoted"', "\u201cquoted\u201d"),
        ("company's", "company\u2019s"),
        ("...", "\u2026"),
        ("a\u2014b", "a \u2014 b"),
    ]
    for a, b in pairs:
        assert canonicalize_for_fingerprinting(a) == canonicalize_for_fingerprinting(b), (
            f"canonical mismatch: {a!r} vs {b!r}"
        )


def test_canonicalization_stable_across_rules():
    a = canonicalize_for_fingerprinting("We do not think it's fair, and we won't stop.")
    b = canonicalize_for_fingerprinting("We don't think it's fair, and we will not stop.")
    assert a == b


def test_detect_protected_ranges_fences():
    text = "Before\n```python\nx = 1  # a\"b\n```\nafter"
    ranges = detect_protected_ranges(text)
    kinds = {r.kind for r in ranges}
    assert "code_fence" in kinds


def test_detect_protected_ranges_inline_code():
    text = 'Use `code "here"` please.'
    ranges = detect_protected_ranges(text)
    assert any(r.kind == "inline_code" for r in ranges)


def test_detect_protected_ranges_url_email():
    text = "Email me at alice@example.com or visit https://x.com/foo."
    ranges = detect_protected_ranges(text)
    assert any(r.kind == "email" for r in ranges)
    assert any(r.kind == "url" for r in ranges)


def test_detect_protected_ranges_json():
    text = 'config = {"key": "value"}'
    ranges = detect_protected_ranges(text)
    assert any(r.kind == "json" for r in ranges)


def test_is_protected_intersection():
    protected = [TextRange(5, 10, "code")]
    assert is_protected(protected, 6, 8)
    assert is_protected(protected, 0, 6)
    assert not is_protected(protected, 0, 5)
    assert not is_protected(protected, 10, 15)


def test_markdown_link_protected():
    text = "See [docs](https://example.com) for more."
    ranges = detect_protected_ranges(text)
    assert any(r.kind == "markdown_link" for r in ranges)


def test_protection_merges_overlapping():
    text = "http://a.com/<tag>"
    ranges = detect_protected_ranges(text)
    assert len(ranges) == 1
