"""Base classes and registry for linguistic transformation rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

import spacy

from tracemark.watermark.policy import SafetyTier
from tracemark.watermark.protection import TextRange


@dataclass(frozen=True)
class RuleMetadata:
    rule_id: str
    safety_tier: SafetyTier
    semantic_risk: float
    style_impact: float
    normalization_robustness: float
    edit_robustness: float
    description: str


@dataclass(frozen=True)
class WatermarkOpportunity:
    """A single place where a rule can represent bit 0 or bit 1."""

    rule_id: str
    start: int
    end: int
    original: str
    variant_0: str
    variant_1: str
    canonical_target: str
    canonical_context: str
    safety_tier: str
    confidence: float
    occurrence_index: int = 0
    observed_bit: int | None = None

    def encode_variant(self, bit: int) -> str:
        return self.variant_1 if bit else self.variant_0


class TransformRule(ABC):
    rule_id: ClassVar[str]
    safety_tier: ClassVar[SafetyTier]
    metadata: ClassVar[RuleMetadata]

    @abstractmethod
    def find_opportunities(
        self,
        text: str,
        doc: spacy.tokens.Doc,
        protected_ranges: list[TextRange],
    ) -> list[WatermarkOpportunity]:
        """Find places where this rule can safely represent bit 0 or 1."""

    @abstractmethod
    def normalize_variants(self, text: str) -> str:
        """Map every variant of this rule onto one canonical representation."""

    @abstractmethod
    def canonicalize_match(self, matched: str) -> str:
        """Canonical representation of a single matched span."""

    @abstractmethod
    def decode_opportunity(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        """Return 0 or 1 for the observed variant, or None if unsafe."""


@dataclass
class RuleRegistry:
    _rules: dict[str, TransformRule] = field(default_factory=dict)

    def register(self, rule: TransformRule) -> TransformRule:
        self._rules[rule.rule_id] = rule
        return rule

    def get(self, rule_id: str) -> TransformRule:
        return self._rules[rule_id]

    def enabled(self, policy) -> list[TransformRule]:
        return [self._rules[rid] for rid in policy.enabled_rules if rid in self._rules]

    def all(self) -> list[TransformRule]:
        return list(self._rules.values())


_registry: RuleRegistry | None = None
_pending_rules: list[TransformRule] = []


def register(rule: TransformRule) -> TransformRule:
    """Register a rule into the global registry (used at import time)."""
    if _registry is not None:
        _registry.register(rule)
    else:
        _pending_rules.append(rule)
    return rule


def get_registry() -> RuleRegistry:
    """Return the global rule registry, populating it on first use.

    Rules register themselves at module import time via ``register``; this
    function guarantees those imports have run.
    """
    global _registry
    if _registry is None:
        _registry = RuleRegistry()
        for rule in _pending_rules:
            _registry.register(rule)
        from tracemark.watermark.rules import (
            abbreviations,  # noqa: F401
            apostrophes,  # noqa: F401
            complementizer,  # noqa: F401
            contractions,  # noqa: F401
            dash_style,  # noqa: F401
            ellipsis,  # noqa: F401
            markdown,  # noqa: F401
            numeric_range,  # noqa: F401
            quotes,  # noqa: F401
            serial_comma,  # noqa: F401
        )
        for rule in _pending_rules:
            _registry.register(rule)
    return _registry
