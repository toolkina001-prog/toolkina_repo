"""Line-oriented JSON bridge used by the JavaScript desktop UI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .campaign import LevelDefinition, generate_campaign, load_campaign
from .engine import apply_pour, is_solved, legal_moves
from .solver import solve_level


ROOT_DIR = Path(__file__).resolve().parents[1]


class GameBridge:
    def __init__(self, campaign: list[LevelDefinition] | None = None):
        campaign_path = ROOT_DIR / "campaign" / "levels.json"
        self.campaign = campaign if campaign is not None else (
            load_campaign(campaign_path) if campaign_path.exists() else generate_campaign(12)
        )

    def handle(self, command: str, payload: dict[str, Any] | None = None) -> Any:
        payload = payload or {}
        if command == "get_campaign":
            return [
                {**level.to_dict(), "capacities": list(level.capacities)}
                for level in self.campaign
            ]

        level_index = payload.get("level_index")
        if not isinstance(level_index, int) or not 0 <= level_index < len(self.campaign):
            raise ValueError("Invalid campaign level.")
        level = self.campaign[level_index]
        state = payload.get("state", level.state)
        if not isinstance(state, list | tuple) or any(
            not isinstance(bottle, list | tuple)
            or any(not isinstance(color, str) for color in bottle)
            for bottle in state
        ):
            raise ValueError("Invalid bottle state.")

        if command == "legal_moves":
            return [list(move) for move in legal_moves(
                state, level.capacities, level.mechanics_config
            )]
        if command == "move":
            source = payload.get("source")
            target = payload.get("target")
            if not isinstance(source, int) or not isinstance(target, int):
                raise ValueError("Move indices must be integers.")
            next_state = apply_pour(
                state, source, target, level.capacities, level.mechanics_config
            )
            return {
                "state": [list(bottle) for bottle in next_state],
                "solved": is_solved(next_state, level.capacities),
                "legal_moves": [list(move) for move in legal_moves(
                    next_state, level.capacities, level.mechanics_config
                )],
            }
        if command == "solve":
            try:
                solution = solve_level(
                    state,
                    level.capacities,
                    mechanics=level.mechanics_config,
                    raise_on_timeout=True,
                )
            except TimeoutError:
                return {"solution": None, "timed_out": True}
            return {
                "solution": [list(move) for move in solution] if solution is not None else None,
                "timed_out": False,
            }
        raise ValueError(f"Unknown command: {command}")


def main() -> None:
    bridge = GameBridge()
    for line in sys.stdin:
        request = None
        try:
            request = json.loads(line)
            result = bridge.handle(request["command"], request.get("payload"))
            response = {"id": request.get("id"), "ok": True, "result": result}
        except Exception as error:
            response = {
                "id": request.get("id") if isinstance(request, dict) else None,
                "ok": False,
                "error": str(error),
            }
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
