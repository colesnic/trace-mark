from __future__ import annotations

from tracemark.watermark.protection import TextRange


def find(rule, text, nlp, protected: list[TextRange] | None = None):
    """Find opportunities for a rule against text."""
    doc = nlp(text)
    return rule.find_opportunities(text, doc, protected or [])


def find_in(rule, text, nlp, predicate) -> list:
    return [o for o in find(rule, text, nlp) if predicate(o)]


def unique_opp(rule, text, nlp, protected=None):
    opps = find(rule, text, nlp, protected)
    assert len(opps) == 1, f"expected exactly 1 opportunity, got {len(opps)}"
    return opps[0]


def decode(rule, text, nlp, protected=None) -> int | None:
    """Decode the observed bit of the single opportunity in ``text``."""
    opps = find(rule, text, nlp, protected)
    assert len(opps) == 1, f"expected exactly 1 opportunity, got {len(opps)}"
    return rule.decode_opportunity(text, opps[0].start, opps[0].end)
