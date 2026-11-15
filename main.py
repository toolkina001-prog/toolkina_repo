"""Entry point for Bottle Sort."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from bottle_game.app import play_console


def _npm_command(*arguments: str) -> list[str]:
    if os.name == "nt":
        return ["cmd", "/c", "npm", *arguments]
    return ["npm", *arguments]


def _ensure_electron(project_root: Path) -> None:
    electron_binary = project_root / "node_modules" / "electron" / "dist"
    electron_binary /= "electron.exe" if os.name == "nt" else "electron"
    if electron_binary.is_file():
        return

    print("Electron is missing; installing JavaScript UI dependencies...", file=sys.stderr)
    installation = subprocess.run(
        _npm_command("install"), cwd=project_root, check=False
    )
    if installation.returncode:
        raise SystemExit(installation.returncode)
    if electron_binary.is_file():
        return

    installer = project_root / "node_modules" / "electron" / "install.js"
    if not installer.is_file():
        raise SystemExit("npm install did not install Electron. Check its output and try again.")

    print("Electron's binary is missing; downloading it now...", file=sys.stderr)
    installation = subprocess.run(
        ["node", str(installer)], cwd=project_root, check=False
    )
    if installation.returncode:
        raise SystemExit(installation.returncode)
    if not electron_binary.is_file():
        raise SystemExit("Electron's installer finished, but its executable is still missing.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bottle Sort game")
    parser.add_argument("--console", action="store_true", help="Run the console prototype instead of the GUI.")
    args = parser.parse_args()

    if args.console:
        play_console(color_count=3, capacity=4, empty_bottles=2)
        return

    project_root = Path(__file__).resolve().parent
    try:
        _ensure_electron(project_root)
        result = subprocess.run(
            _npm_command("start"), cwd=project_root, check=False
        )
    except FileNotFoundError as error:
        raise SystemExit("Node.js and npm are required to start the JavaScript desktop UI.") from error
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
