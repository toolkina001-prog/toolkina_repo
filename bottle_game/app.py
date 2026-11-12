"""Small interactive console app for the bottle-pouring puzzle."""

from __future__ import annotations

from typing import Sequence

from .engine import BottleState, apply_pour, can_pour, is_solved
from .generator import generate_level
from .solver import solve_level


def pretty_print(state: Sequence[Sequence[str]], capacity: int) -> str:
    lines: list[str] = []
    for bottle_index, bottle in enumerate(state):
        lines.append(f"Bottle {bottle_index}: {list(bottle)}")
    return "\n".join(lines)


def play_console(color_count: int = 3, capacity: int = 4, empty_bottles: int = 2) -> None:
    state = generate_level(color_count, capacity, empty_bottles)
    print("Generated puzzle:")
    print(pretty_print(state, capacity))

    while not is_solved(state, capacity):
        print("\nChoose move: source target")
        raw = input("> ").strip()
        if raw.lower() in {"hint", "solve", "help"}:
            solution = solve_level(state, capacity)
            if solution is None:
                print("No solution found.")
            else:
                print(f"Hint: {solution[:5]}")
            continue
        parts = raw.split()
        if len(parts) != 2:
            print("Expected two integers.")
            continue
        try:
            source_index, target_index = map(int, parts)
        except ValueError:
            print("Invalid input.")
            continue

        if not can_pour(state, source_index, target_index, capacity):
            print("Illegal move.")
            continue

        state = apply_pour(state, source_index, target_index, capacity)
        print(pretty_print(state, capacity))

    print("You solved the level!")
