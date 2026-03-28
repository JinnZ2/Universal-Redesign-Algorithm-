#!/usr/bin/env python3
"""Run the Universal Redesign Algorithm pipeline.

Usage:
    python -m src.run plans/energy_grid.example.json
    python -m src.run plans/energy_grid.example.json --clone-base /tmp
"""
from __future__ import annotations

import argparse
import pathlib
import sys

# Ensure project root is on the path
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Run the Universal Redesign Algorithm pipeline on a plan."
    )
    parser.add_argument(
        "plan",
        help="Path to a plan JSON file (e.g. plans/energy_grid.example.json)",
    )
    parser.add_argument(
        "--clone-base",
        default="/tmp",
        help="Base directory containing cloned sibling repos (default: /tmp)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON report instead of human-readable text",
    )
    args = parser.parse_args()

    pipeline = Pipeline(clone_base=args.clone_base)
    report = pipeline.run(args.plan)

    if args.json:
        import json
        print(json.dumps(report, indent=2))
    else:
        pipeline.print_report(report)

    # Exit code: 0 if OK, 1 if errors
    sys.exit(0 if report["status"] == "OK" else 1)


if __name__ == "__main__":
    main()
