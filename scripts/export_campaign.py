#!/usr/bin/env python3
"""Generate and export the campaign JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bottle_game.campaign import export_campaign, generate_campaign, verify_campaign


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Bottle Sort campaign data.")
    parser.add_argument("--levels", type=int, default=120, help="Number of levels to generate.")
    parser.add_argument("--out", type=str, default="campaign/levels.json", help="Destination JSON path.")
    args = parser.parse_args()
    levels = generate_campaign(args.levels)
    verify_campaign(levels)
    path = export_campaign(args.out, levels)
    print(f"Campaign exported to {path}")


if __name__ == "__main__":
    main()
