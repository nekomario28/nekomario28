#!/usr/bin/env python3
"""Validate and optionally promote the seasonal profile hero.

The live README always references assets/profile-hero.svg. This script changes only
that stable asset plus design-lab/live-theme.json, so seasonal switching does not
rewrite README structure.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent
MANIFEST = LAB / "theme-manifest.json"
LIVE_STATE = LAB / "live-theme.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(data: dict) -> None:
    seen: dict[int, str] = {}
    for name, cfg in data["seasons"].items():
        for month in cfg["months"]:
            if not 1 <= month <= 12:
                raise SystemExit(f"invalid month {month} for {name}")
            if month in seen:
                raise SystemExit(f"month {month} is assigned to both {seen[month]} and {name}")
            seen[month] = name
    if set(seen) != set(range(1, 13)):
        raise SystemExit(f"season mapping must cover months 1..12 exactly once; got {sorted(seen)}")


def resolve_day(value: str | None, timezone: str) -> dt.date:
    if value:
        return dt.date.fromisoformat(value)
    return dt.datetime.now(ZoneInfo(timezone)).date()


def resolve_season(data: dict, day: dt.date, explicit: str | None) -> tuple[str, dict]:
    if explicit:
        if explicit not in data["seasons"]:
            raise SystemExit(f"unknown season: {explicit}")
        return explicit, data["seasons"][explicit]
    matches = [(name, cfg) for name, cfg in data["seasons"].items() if day.month in cfg["months"]]
    if len(matches) != 1:
        raise SystemExit(f"expected one season for month {day.month}, got {len(matches)}")
    return matches[0]


def validate_hero(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"hero not found: {path}")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise SystemExit(f"invalid SVG XML: {path}: {exc}") from exc
    if not root.tag.endswith("svg"):
        raise SystemExit(f"not an SVG root: {path}")
    if root.attrib.get("viewBox") != "0 0 900 260":
        raise SystemExit(f"unexpected hero viewBox in {path}: {root.attrib.get('viewBox')!r}")
    if root.attrib.get("width") != "900" or root.attrib.get("height") != "260":
        raise SystemExit(f"unexpected hero geometry in {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="ISO date in the manifest timezone; defaults to now")
    parser.add_argument("--season", choices=["spring", "summer", "autumn", "winter"])
    parser.add_argument("--apply", action="store_true", help="copy the approved candidate to the stable live asset")
    parser.add_argument("--force", action="store_true", help="allow explicit manual promotion even when auto_promote is false")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args()

    manifest = load_json(MANIFEST)
    validate_manifest(manifest)
    day = resolve_day(args.date, manifest.get("timezone", "Asia/Tokyo"))
    season, cfg = resolve_season(manifest, day, args.season)

    hero = LAB / cfg["hero"]
    validate_hero(hero)
    if cfg.get("static_render") != "PASS":
        raise SystemExit(f"{season} is not statically render-approved")
    if not cfg.get("auto_promote", False) and not (args.force and args.season):
        raise SystemExit(f"{season} is not approved for automatic promotion")

    live = load_json(LIVE_STATE)
    live_asset = ROOT / manifest["live_asset"]
    changed = live.get("active_season") != season or live_asset.read_bytes() != hero.read_bytes()

    result = {
        "date": day.isoformat(),
        "timezone": manifest.get("timezone", "Asia/Tokyo"),
        "season": season,
        "theme": f"{season}-dark",
        "source": str(hero.relative_to(ROOT)),
        "live_asset": str(live_asset.relative_to(ROOT)),
        "changed": changed,
        "apply": args.apply,
    }

    if args.apply and changed:
        shutil.copyfile(hero, live_asset)
        next_state = {
            "version": 1,
            "active_season": season,
            "active_theme": f"{season}-dark",
            "source": str(hero.relative_to(ROOT)),
            "live_asset": str(live_asset.relative_to(ROOT)),
            "timezone": manifest.get("timezone", "Asia/Tokyo"),
            "promoted_at": day.isoformat(),
            "promotion_mode": "automatic" if args.season is None else "manual",
        }
        LIVE_STATE.write_text(json.dumps(next_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        action = "promoted" if args.apply and changed else "no-change" if not changed else "would-promote"
        print(f"{action}: {season} -> {live_asset.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
