"""Advanced rule mechanics for Bottle Sort levels."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class BottleMechanics:
    stone_bottles: set[int] = field(default_factory=set)
    decoy_bottles: set[int] = field(default_factory=set)
    frozen_bottles: set[int] = field(default_factory=set)
    hidden_bottles: set[int] = field(default_factory=set)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "BottleMechanics":
        if not payload:
            return cls()
        return cls(
            stone_bottles=set(payload.get("stone_bottles", [])),
            decoy_bottles=set(payload.get("decoy_bottles", [])),
            frozen_bottles=set(payload.get("frozen_bottles", [])),
            hidden_bottles=set(payload.get("hidden_bottles", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stone_bottles": sorted(self.stone_bottles),
            "decoy_bottles": sorted(self.decoy_bottles),
            "frozen_bottles": sorted(self.frozen_bottles),
            "hidden_bottles": sorted(self.hidden_bottles),
        }


def build_mechanics(level_index: int) -> BottleMechanics:
    mechanics = BottleMechanics()
    if level_index >= 25:
        mechanics.decoy_bottles.add(max(0, (level_index - 25) % 3))
    if level_index >= 90:
        mechanics.hidden_bottles.add(max(0, (level_index - 90) % 2))
    return mechanics


def normalize_mechanics(mechanics: BottleMechanics | dict[str, Any] | None) -> BottleMechanics:
    if isinstance(mechanics, BottleMechanics):
        return mechanics
    if isinstance(mechanics, dict):
        return BottleMechanics.from_dict(mechanics)
    return BottleMechanics()
