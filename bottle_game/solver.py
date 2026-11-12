"""A* solver with bottle-symmetry reduction and a bounded result cache."""

from __future__ import annotations

import heapq
import itertools
import time
from collections import OrderedDict
from typing import Sequence

from .engine import BottleState, Capacity, apply_pour, is_solved, legal_moves

_CACHE_LIMIT = 256
_SOLUTION_CACHE: OrderedDict[tuple, tuple[tuple[int, int], ...] | None] = OrderedDict()


def _mechanics_key(mechanics: dict | None) -> tuple:
    if not mechanics:
        return ()
    return tuple(
        (key, tuple(sorted(value)))
        for key, value in sorted(mechanics.items())
        if key in {"stone_bottles", "decoy_bottles", "frozen_bottles"}
    )


def _canonicalize(
    state: Sequence[Sequence[str]], identities: Sequence[int], capacities: Sequence[int]
) -> tuple[BottleState, tuple[int, ...], tuple[int, ...]]:
    ordered = sorted(
        (
            (tuple(bottle), identity, bottle_capacity)
            for bottle, identity, bottle_capacity in zip(state, identities, capacities)
        ),
        key=lambda item: (item[2], len(item[0]), item[0], item[1]),
    )
    return (
        tuple(bottle for bottle, _, _ in ordered),
        tuple(identity for _, identity, _ in ordered),
        tuple(bottle_capacity for _, _, bottle_capacity in ordered),
    )


def _heuristic(state: BottleState, capacity: int) -> int:
    # Each color run beyond the first in a bottle must be separated at least once.
    runs = sum(
        sum(1 for index in range(1, len(bottle)) if bottle[index] != bottle[index - 1])
        for bottle in state
    )
    return runs


def solve_level(
    state: Sequence[Sequence[str]],
    capacity: Capacity,
    *,
    time_limit: float = 2.0,
    mechanics: dict | None = None,
) -> list[tuple[int, int]] | None:
    """Return a path of bottle indices solving the level, or None if not found in time."""
    initial = tuple(tuple(bottle) for bottle in state)
    capacities = (capacity,) * len(initial) if isinstance(capacity, int) else tuple(capacity)
    if (
        len(capacities) != len(initial)
        or any(bottle_capacity < 1 for bottle_capacity in capacities)
        or any(len(bottle) > bottle_capacity for bottle, bottle_capacity in zip(initial, capacities))
    ):
        return None

    mechanic_key = _mechanics_key(mechanics)
    cache_key = (initial, capacities, mechanic_key)
    if cache_key in _SOLUTION_CACHE:
        _SOLUTION_CACHE.move_to_end(cache_key)
        cached = _SOLUTION_CACHE[cache_key]
        return list(cached) if cached is not None else None
    if is_solved(initial, capacities):
        _cache_result(cache_key, ())
        return []

    indexed_mechanics = {
        key: set(values)
        for key, values in mechanic_key
    }

    def search_key(search_state: BottleState, identities: tuple[int, ...]) -> tuple:
        if indexed_mechanics or len(set(capacities)) > 1:
            return search_state, identities
        return search_state

    start_state, start_identities, start_capacities = _canonicalize(
        initial, range(len(initial)), capacities
    )
    deadline = time.monotonic() + max(0.0, time_limit)
    sequence = itertools.count()
    frontier = [
        (
            _heuristic(start_state, capacity),
            0,
            next(sequence),
            start_state,
            start_identities,
            start_capacities,
            (),
        )
    ]
    best_cost = {search_key(start_state, start_identities): 0}

    while frontier:
        if time.monotonic() >= deadline:
            return None
        _, cost, _, current, identities, current_capacities, path = heapq.heappop(frontier)
        if cost != best_cost.get(search_key(current, identities)):
            continue

        identity_to_position = {identity: position for position, identity in enumerate(identities)}
        canonical_mechanics = {
            key: {
                identity_to_position[index]
                for index in original_indices
                if index in identity_to_position
            }
            for key, original_indices in indexed_mechanics.items()
        }

        for source, target in legal_moves(current, current_capacities, canonical_mechanics):
            next_state = apply_pour(current, source, target, current_capacities, canonical_mechanics)
            next_identities = list(identities)
            next_state, next_identities_tuple, next_capacities = _canonicalize(
                next_state,
                next_identities,
                tuple(capacities[identity] for identity in next_identities),
            )
            next_identities = next_identities_tuple
            next_cost = cost + 1
            next_path = path + ((identities[source], identities[target]),)
            if is_solved(next_state, next_capacities):
                _cache_result(cache_key, next_path)
                return list(next_path)

            next_key = search_key(next_state, next_identities)
            if next_cost >= best_cost.get(next_key, float("inf")):
                continue
            best_cost[next_key] = next_cost
            priority = next_cost + _heuristic(next_state, capacity)
            heapq.heappush(
                frontier,
                (
                    priority,
                    next_cost,
                    next(sequence),
                    next_state,
                    next_identities,
                    next_capacities,
                    next_path,
                ),
            )

    _cache_result(cache_key, None)
    return None


def _cache_result(key: tuple, result: tuple[tuple[int, int], ...] | None) -> None:
    _SOLUTION_CACHE[key] = result
    _SOLUTION_CACHE.move_to_end(key)
    if len(_SOLUTION_CACHE) > _CACHE_LIMIT:
        _SOLUTION_CACHE.popitem(last=False)
