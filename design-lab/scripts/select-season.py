#!/usr/bin/env python3
"""Resolve the design-lab seasonal hero without mutating the live profile."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "theme-manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="ISO date (YYYY-MM-DD); defaults to today")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args()

    day = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    matches = [
        (name, cfg)
        for name, cfg in data["seasons"].items()
        if day.month in cfg["months"]
    ]
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one season for month {day.month}, got {len(matches)}")
    name, cfg = matches[0]
    result = {
        "date": day.isoformat(),
        "month": day.month,
        "season": name,
        "hero": cfg["hero"],
        "accent": cfg["accent"],
    }
    print(json.dumps(result, ensure_ascii=False) if args.json else f"{name}: {cfg['hero']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
