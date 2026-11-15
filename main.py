"""Entry point for Bottle Sort."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from bottle_game.app import play_console


def main() -> None:
    parser = argparse.ArgumentParser(description="Bottle Sort game")
    parser.add_argument("--console", action="store_true", help="Run the console prototype instead of the GUI.")
    args = parser.parse_args()

    if args.console:
        play_console(color_count=3, capacity=4, empty_bottles=2)
        return

    command = ["cmd", "/c", "npm", "start"] if os.name == "nt" else ["npm", "start"]
    try:
        result = subprocess.run(command, cwd=Path(__file__).resolve().parent, check=False)
    except FileNotFoundError as error:
        raise SystemExit("Node.js and npm are required to start the JavaScript desktop UI.") from error
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
