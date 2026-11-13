"""Level generation helpers for a solvable puzzle campaign."""

from __future__ import annotations

import random
from typing import List, Tuple

from .engine import BottleState, apply_pour, can_pour, is_bottle_complete, is_solved


def solved_state(
    color_count: int,
    capacity: int,
    empty_bottles: int = 0,
    bottle_capacities: tuple[int, ...] | None = None,
) -> BottleState:
    """Create a solved board with one full bottle per color plus empty bottles."""
    capacities = bottle_capacities or (capacity,) * (color_count + empty_bottles)
    if len(capacities) != color_count + empty_bottles:
        raise ValueError("bottle_capacities must match the number of bottles.")
    bottles: List[Tuple[str, ...]] = []
    for index in range(color_count):
        color = f"C{index}"
        bottles.append(tuple([color] * capacities[index]))
    bottles.extend([tuple() for _ in range(empty_bottles)])
    return tuple(bottles)


def generate_level(
    color_count: int,
    capacity: int,
    empty_bottles: int = 2,
    shuffle_steps: int = 18,
    *,
    rng: random.Random | None = None,
    max_attempts: int = 200,
    mechanics: dict | None = None,
    bottle_capacities: tuple[int, ...] | None = None,
    require_full_bottles: tuple[int, ...] = (),
) -> BottleState:
    """Create a solvable board by reversing legal pours from a solved state."""
    state, _ = generate_level_with_solution(
        color_count,
        capacity,
        empty_bottles,
        shuffle_steps,
        rng=rng,
        max_attempts=max_attempts,
        mechanics=mechanics,
        bottle_capacities=bottle_capacities,
        require_full_bottles=require_full_bottles,
    )
    return state


def generate_level_with_solution(
    color_count: int,
    capacity: int,
    empty_bottles: int = 2,
    shuffle_steps: int = 18,
    *,
    rng: random.Random | None = None,
    max_attempts: int = 200,
    mechanics: dict | None = None,
    bottle_capacities: tuple[int, ...] | None = None,
    require_full_bottles: tuple[int, ...] = (),
) -> tuple[BottleState, tuple[tuple[int, int], ...]]:
    """Return a reverse-shuffled board and its proven forward solution."""
    if color_count < 1 or capacity < 1 or empty_bottles < 1:
        raise ValueError("A level requires at least one color, one layer per bottle, and one empty bottle.")
    if shuffle_steps < 1 or max_attempts < 1:
        raise ValueError("shuffle_steps and max_attempts must be positive.")
    capacities = bottle_capacities or (capacity,) * (color_count + empty_bottles)
    if len(capacities) != color_count + empty_bottles or any(value < capacity for value in capacities[:color_count]):
        raise ValueError("bottle_capacities must provide sufficient capacity for every color bottle.")
    if any(not 0 <= index < len(capacities) for index in require_full_bottles):
        raise ValueError("require_full_bottles must contain valid bottle indices.")
    rng = rng or random.Random()

    for _ in range(max_attempts):
        bottles = [
            list(bottle)
            for bottle in solved_state(
                color_count, capacity, empty_bottles, tuple(capacities)
            )
        ]
        reverse_moves: list[tuple[int, int]] = []
        for _ in range(shuffle_steps):
            state = tuple(tuple(bottle) for bottle in bottles)
            candidates: list[tuple[list[list[str]], tuple[int, int]]] = []
            for target_index, target in enumerate(bottles):
                if not target:
                    continue
                color = target[-1]
                top_run = 1
                for layer in reversed(target[:-1]):
                    if layer != color:
                        break
                    top_run += 1
                for source_index, source in enumerate(bottles):
                    source_capacity = capacities[source_index]
                    if (
                        source_index == target_index
                        or len(source) >= source_capacity
                    ):
                        continue
                    max_amount = min(top_run, source_capacity - len(source))
                    for amount in range(1, max_amount + 1):
                        if amount == top_run and top_run < len(target):
                            continue
                        candidate = [list(bottle) for bottle in bottles]
                        candidate[source_index].extend(candidate[target_index][-amount:])
                        del candidate[target_index][-amount:]
                        candidate_state = tuple(tuple(bottle) for bottle in candidate)
                        if not can_pour(candidate_state, source_index, target_index, capacities, mechanics):
                            continue
                        if apply_pour(candidate_state, source_index, target_index, capacities, mechanics) == state:
                            candidates.append((candidate, (source_index, target_index)))
            if not candidates:
                break
            bottles, move = rng.choice(candidates)
            reverse_moves.append(move)

        state = tuple(tuple(bottle) for bottle in bottles)
        if not is_solved(state, capacities) and not any(
            is_bottle_complete(bottle, bottle_capacity)
            for bottle, bottle_capacity in zip(state, capacities)
        ) and all(len(state[index]) == capacities[index] for index in require_full_bottles):
            solution = tuple(reversed(reverse_moves))
            check_state = state
            for source, target in solution:
                check_state = apply_pour(check_state, source, target, capacities, mechanics)
            if not is_solved(check_state, capacities):
                raise RuntimeError("Reverse-generated solution did not solve its level.")
            return state, solution

    raise ValueError("Could not generate a solvable level with the requested parameters.")
