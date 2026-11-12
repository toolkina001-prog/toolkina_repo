"""Core rules for the bottle-pouring puzzle."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

BottleState = Tuple[Tuple[str, ...], ...]


def _normalize_state(state: Sequence[Sequence[str]]) -> BottleState:
    return tuple(tuple(bottle) for bottle in state)


def _mechanic_set(mechanics: dict | None, key: str) -> set[int]:
    if not mechanics:
        return set()
    value = mechanics.get(key, [])
    if isinstance(value, set):
        return value
    return set(value)


def _top_color(bottle: Sequence[str]) -> str | None:
    return bottle[-1] if bottle else None


def _top_run_length(bottle: Sequence[str]) -> int:
    if not bottle:
        return 0
    color = bottle[-1]
    count = 1
    for idx in range(len(bottle) - 2, -1, -1):
        if bottle[idx] == color:
            count += 1
        else:
            break
    return count


def can_pour(
    state: Sequence[Sequence[str]],
    source_index: int,
    target_index: int,
    capacity: int,
    mechanics: dict | None = None,
) -> bool:
    """Return whether a pour from source to target is legal."""
    if source_index == target_index:
        return False

    bottles = _normalize_state(state)
    if not (0 <= source_index < len(bottles) and 0 <= target_index < len(bottles)):
        return False

    if mechanics:
        if source_index in _mechanic_set(mechanics, "stone_bottles"):
            return False
        if target_index in _mechanic_set(mechanics, "stone_bottles"):
            return False
        if target_index in _mechanic_set(mechanics, "decoy_bottles"):
            return False
        if source_index in _mechanic_set(mechanics, "frozen_bottles"):
            return False

    source = bottles[source_index]
    target = bottles[target_index]

    if not source:
        return False
    if len(target) >= capacity:
        return False

    source_top = _top_color(source)
    if source_top is None:
        return False

    if not target:
        return True

    target_top = _top_color(target)
    return source_top == target_top


def apply_pour(
    state: Sequence[Sequence[str]],
    source_index: int,
    target_index: int,
    capacity: int,
    mechanics: dict | None = None,
) -> BottleState:
    """Apply one valid pour and return the resulting state."""
    bottles = _normalize_state(state)

    if not can_pour(bottles, source_index, target_index, capacity, mechanics):
        raise ValueError(f"Illegal move: {source_index} -> {target_index}")

    source = list(bottles[source_index])
    target = list(bottles[target_index])

    source_top = source[-1]
    source_run = _top_run_length(source)
    available_space = capacity - len(target)
    transfer_count = min(source_run, available_space)

    if not target:
        moved = source[-transfer_count:]
        source = source[:-transfer_count]
        target = moved
    else:
        moved = source[-transfer_count:]
        source = source[:-transfer_count]
        target.extend(moved)

    next_state = [list(bottle) for bottle in bottles]
    next_state[source_index] = source
    next_state[target_index] = target
    return tuple(tuple(bottle) for bottle in next_state)


def is_solved(state: Sequence[Sequence[str]], capacity: int) -> bool:
    """A state is solved when every non-empty bottle is full and monochrome."""
    for bottle in state:
        if not bottle:
            continue
        if len(bottle) != capacity:
            return False
        if any(color != bottle[0] for color in bottle):
            return False
    return True


def legal_moves(
    state: Sequence[Sequence[str]],
    capacity: int,
    mechanics: dict | None = None,
) -> Iterable[Tuple[int, int]]:
    """Yield all legal moves for the current state."""
    bottles = _normalize_state(state)
    for source_index, source in enumerate(bottles):
        if not source:
            continue
        for target_index, target in enumerate(bottles):
            if source_index == target_index:
                continue
            if can_pour(bottles, source_index, target_index, capacity, mechanics):
                yield source_index, target_index
