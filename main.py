"""Entry point for Bottle Sort."""

from __future__ import annotations

import argparse
import tkinter as tk

from bottle_game.app import play_console
from bottle_game.gui import BottleSortApp


def main() -> None:
    parser = argparse.ArgumentParser(description="Bottle Sort game")
    parser.add_argument("--console", action="store_true", help="Run the console prototype instead of the GUI.")
    args = parser.parse_args()

    if args.console:
        play_console(color_count=3, capacity=4, empty_bottles=2)
        return

    try:
        app = BottleSortApp()
        app.mainloop()
    except tk.TclError as error:
        raise SystemExit(f"Could not start the desktop UI: {error}") from error


if __name__ == "__main__":
    main()
