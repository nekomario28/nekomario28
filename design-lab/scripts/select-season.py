#!/usr/bin/env python3
"""Resolve the design-lab seasonal hero without mutating the live profile."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "theme-manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="ISO date (YYYY-MM-DD); defaults to now in the manifest timezone")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args()

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    timezone = data.get("timezone", "Asia/Tokyo")
    day = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(ZoneInfo(timezone)).date()
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
        "timezone": timezone,
        "month": day.month,
        "season": name,
        "hero": cfg["hero"],
        "accent": cfg["accent"],
        "auto_promote": bool(cfg.get("auto_promote", False)),
        "static_render": cfg.get("static_render"),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True) if args.json else f"{name}: {cfg['hero']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
