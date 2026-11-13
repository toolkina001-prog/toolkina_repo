"""Campaign definition and generation utilities for the bottle puzzle game."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List

from .engine import apply_pour, is_solved
from .generator import generate_level_with_solution


@dataclass
class LevelDefinition:
    id: int
    title: str
    description: str
    state: tuple[tuple[str, ...], ...]
    capacity: int
    color_count: int
    empty_bottles: int
    mechanics: list[str]
    mechanics_config: dict[str, Any] | None = None
    solution: tuple[tuple[int, int], ...] = ()
    tutorial: bool = False
    difficulty: float = 0.0
    bottle_capacities: tuple[int, ...] = ()

    @property
    def capacities(self) -> tuple[int, ...]:
        if self.bottle_capacities:
            return self.bottle_capacities
        return (self.capacity,) * len(self.state)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "state": [list(bottle) for bottle in self.state],
            "capacity": self.capacity,
            "color_count": self.color_count,
            "empty_bottles": self.empty_bottles,
            "mechanics": self.mechanics,
            "mechanics_config": self.mechanics_config or {},
            "solution": [list(move) for move in self.solution],
            "tutorial": self.tutorial,
            "difficulty": self.difficulty,
            "bottle_capacities": list(self.bottle_capacities),
        }


def _geometric_color_count(level_index: int) -> int:
    if level_index <= 10:
        return math.ceil(3 + 2 * (level_index - 1) / 9)
    if level_index <= 25:
        return math.ceil(5 + 3 * (level_index - 10) / 15)
    if level_index <= 45:
        return math.ceil(8 + 4 * (level_index - 25) / 20)
    if level_index <= 70:
        return math.ceil(12 + 6 * (level_index - 45) / 25)
    if level_index <= 100:
        return math.ceil(18 + 8 * (level_index - 70) / 30)
    return 26 + (level_index - 100) // 10


def _determine_mechanics(
    level_index: int,
    capacity: int,
    color_count: int,
    empty_bottles: int,
) -> tuple[list[str], dict[str, Any]]:
    mechanics: list[str] = []
    config: dict[str, Any] = {"decoy_bottles": [], "frozen_bottles": [], "stone_bottles": []}
    empty_indices = list(range(color_count, color_count + empty_bottles))

    if level_index >= 25:
        mechanics.append("decoy_bottle")
        config["decoy_bottles"] = [empty_indices[0]]
    if level_index >= 45:
        mechanics.append("stone_layer")
        config["stone_bottles"] = [empty_indices[1] if len(empty_indices) > 1 else empty_indices[0]]
    if level_index >= 70:
        mechanics.append("frozen_layer")
        config["frozen_bottles"] = [empty_indices[2] if len(empty_indices) > 2 else empty_indices[-1]]
    if capacity >= 5:
        mechanics.append("capacity_5")
    return mechanics, config


def _expected_difficulty(level_index: int, capacity: int, empty_bottles: int, mechanics: Iterable[str]) -> float:
    base = (level_index * capacity * (1 + max(0, 3 - empty_bottles) * 0.25))
    mechanics_factor = 1 + len(list(mechanics)) * 0.25
    return round(base * mechanics_factor, 2)


def generate_level_definition(level_index: int, *, capacity: int | None = None) -> LevelDefinition:
    level_index = max(1, int(level_index))
    if capacity is None:
        capacity = 4 if level_index < 71 else 5

    color_count = _geometric_color_count(level_index)
    empty_bottles = 3 if level_index == 46 else (2 if level_index < 70 else 3)
    generation_empty_bottles = empty_bottles - 1 if level_index == 46 else empty_bottles
    mechanics, mechanics_config = _determine_mechanics(
        level_index, capacity, color_count, generation_empty_bottles
    )
    has_giant_bottle = level_index in {10, 30, 50, 70, 90, 110, 125, 130, 135, 140}
    bottle_capacities = [capacity] * (color_count + empty_bottles)
    giant_bottle_indices: tuple[int, ...] = ()
    if has_giant_bottle:
        giant_index = 0
        bottle_capacities[giant_index] = capacity * 3
        giant_bottle_indices = (giant_index,)
        mechanics.append("giant_bottle_3x")
        mechanics_config["giant_bottles"] = [giant_index]
    if level_index in {90, 110}:
        mechanics.append("hidden_colors")
        mechanics_config["hidden_bottles"] = [min(1, color_count - 1)]
    state, solution = generate_level_with_solution(
        color_count,
        capacity,
        empty_bottles=generation_empty_bottles,
        shuffle_steps=max(
            12,
            6 + level_index // 3,
            color_count + 10 if has_giant_bottle else 0,
            60 if level_index > 120 else 0,
        ),
        rng=random.Random(level_index),
        mechanics=mechanics_config,
        bottle_capacities=tuple(bottle_capacities) if has_giant_bottle else None,
        require_full_bottles=giant_bottle_indices,
    )
    if level_index == 46:
        state += ((),)
    tutorial = level_index in {1, 10, 25, 45, 70}
    title = f"Level {level_index}"
    description = "Solve the board by filling each bottle with one color." if not mechanics else (
        f"Mechanics: {', '.join(mechanics)}"
    )
    difficulty = _expected_difficulty(level_index, capacity, empty_bottles, mechanics)
    return LevelDefinition(
        id=level_index,
        title=title,
        description=description,
        state=state,
        capacity=capacity,
        color_count=color_count,
        empty_bottles=empty_bottles,
        mechanics=mechanics,
        mechanics_config=mechanics_config,
        solution=solution,
        tutorial=tutorial,
        difficulty=difficulty,
        bottle_capacities=tuple(bottle_capacities) if has_giant_bottle else (),
    )


def generate_campaign(level_count: int = 120, *, start_level: int = 1) -> list[LevelDefinition]:
    """Generate a campaign using the README's color-count progression and reverse shuffles."""
    return [generate_level_definition(level_index) for level_index in range(start_level, start_level + level_count)]


def export_campaign(path: str | Path, levels: list[LevelDefinition] | None = None) -> Path:
    payload = {"levels": [level.to_dict() for level in (levels or generate_campaign())]}
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def load_campaign(path: str | Path) -> list[LevelDefinition]:
    source = Path(path)
    if not source.exists():
        return generate_campaign()
    raw = json.loads(source.read_text(encoding="utf-8"))
    levels = []
    for item in raw.get("levels", []):
        levels.append(
            LevelDefinition(
                id=item["id"],
                title=item["title"],
                description=item["description"],
                state=tuple(tuple(bottle) for bottle in item["state"]),
                capacity=item["capacity"],
                color_count=item["color_count"],
                empty_bottles=item["empty_bottles"],
                mechanics=item.get("mechanics", []),
                mechanics_config=item.get("mechanics_config", {}),
                solution=tuple(tuple(move) for move in item.get("solution", [])),
                tutorial=item.get("tutorial", False),
                difficulty=float(item.get("difficulty", 0.0)),
                bottle_capacities=tuple(item.get("bottle_capacities", [])),
            )
        )
    return levels


def verify_campaign(levels: list[LevelDefinition]) -> None:
    """Replay each generation-proven solution and fail on invalid campaign content."""
    for level in levels:
        state = level.state
        for source, target in level.solution:
            state = apply_pour(state, source, target, level.capacities, level.mechanics_config)
        if not is_solved(state, level.capacities):
            raise ValueError(f"Level {level.id} failed solution verification.")
