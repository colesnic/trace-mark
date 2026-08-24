"""Watermark policies and safety tiers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SafetyTier(StrEnum):
    STRICT = "strict"
    BALANCED = "balanced"
    EXPERIMENTAL = "experimental"


STRICT_RULES = ["quotes", "apostrophes", "ellipsis", "dash_style", "numeric_range"]

BALANCED_RULES = [
    "quotes",
    "ellipsis",
    "dash_style",
    "serial_comma",
    "contractions",
    "apostrophes",
]

EXPERIMENTAL_RULES = [
    "quotes",
    "apostrophes",
    "ellipsis",
    "dash_style",
    "serial_comma",
    "contractions",
    "abbreviations",
    "complementizer_that",
    "markdown",
]


@dataclass(frozen=True)
class WatermarkPolicy:
    """A policy selects which transformation rules are enabled.

    Rule IDs appear in this order to define a deterministic priority:
    earlier rules win when opportunities overlap.
    """

    name: str
    tier: SafetyTier
    enabled_rules: tuple[str, ...]

    # Minimum usable opportunities before a detection is reported.
    minimum_opportunities: int = 20

    # Evidence separation required between the best and runner-up candidate.
    minimum_separation: float = 2.0

    def includes(self, rule_id: str) -> bool:
        return rule_id in self.enabled_rules

    @property
    def priority(self) -> dict[str, int]:
        return {rid: idx for idx, rid in enumerate(self.enabled_rules)}

    @staticmethod
    def from_name(name: str) -> WatermarkPolicy:
        normalized = name.strip().lower()
        if normalized in {"strict", "strictest"}:
            return WatermarkPolicy(
                name="strict", tier=SafetyTier.STRICT, enabled_rules=tuple(STRICT_RULES)
            )
        if normalized in {"balanced", "default"}:
            return WatermarkPolicy(
                name="balanced", tier=SafetyTier.BALANCED, enabled_rules=tuple(BALANCED_RULES)
            )
        if normalized in {"experimental"}:
            return WatermarkPolicy(
                name="experimental",
                tier=SafetyTier.EXPERIMENTAL,
                enabled_rules=tuple(EXPERIMENTAL_RULES),
            )
        raise ValueError(f"unknown policy: {name!r}")


class PolicyModel(BaseModel):
    """Pydantic representation of a policy for API input."""

    model_config = ConfigDict(extra="forbid")

    name: str
    tier: SafetyTier | None = None
    enabled_rules: list[str] | None = None
    minimum_opportunities: int | None = None
    minimum_separation: float | None = None

    def to_policy(self) -> WatermarkPolicy:
        if self.enabled_rules is not None:
            return WatermarkPolicy(
                name=self.name,
                tier=self.tier or SafetyTier.BALANCED,
                enabled_rules=tuple(self.enabled_rules),
                minimum_opportunities=self.minimum_opportunities or 20,
                minimum_separation=self.minimum_separation or 2.0,
            )
        base = WatermarkPolicy.from_name(self.name)
        return WatermarkPolicy(
            name=base.name,
            tier=self.tier or base.tier,
            enabled_rules=base.enabled_rules,
            minimum_opportunities=self.minimum_opportunities or base.minimum_opportunities,
            minimum_separation=self.minimum_separation or base.minimum_separation,
        )
