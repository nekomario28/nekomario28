#!/usr/bin/env python3
"""Validate and optionally promote the complete seasonal profile envelope.

The live README references stable assets only. Promotion changes the approved hero,
seasonal chrome assets, and design-lab/live-theme.json without restructuring README.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent
MANIFEST = LAB / "theme-manifest.json"
LIVE_STATE = LAB / "live-theme.json"
RENDERER = Path(__file__).with_name("render_envelope_chrome.py")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(data: dict) -> None:
    seen: dict[int, str] = {}
    required_assets = {"hero", "divider", "projects", "activity", "footer"}
    if set(data.get("live_assets", {})) != required_assets:
        raise SystemExit(f"live_assets must be exactly {sorted(required_assets)}")
    for name, cfg in data["seasons"].items():
        for month in cfg["months"]:
            if not 1 <= month <= 12:
                raise SystemExit(f"invalid month {month} for {name}")
            if month in seen:
                raise SystemExit(f"month {month} is assigned to both {seen[month]} and {name}")
            seen[month] = name
        chrome = cfg.get("chrome", {})
        for field in ("bg0", "bg1", "accent2", "motif"):
            if not chrome.get(field):
                raise SystemExit(f"missing chrome.{field} for {name}")
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


def validate_svg(path: Path, width: str, height: str, viewbox: str) -> None:
    if not path.is_file():
        raise SystemExit(f"SVG not found: {path}")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise SystemExit(f"invalid SVG XML: {path}: {exc}") from exc
    if not root.tag.endswith("svg"):
        raise SystemExit(f"not an SVG root: {path}")
    if root.attrib.get("viewBox") != viewbox:
        raise SystemExit(f"unexpected viewBox in {path}: {root.attrib.get('viewBox')!r}")
    if root.attrib.get("width") != width or root.attrib.get("height") != height:
        raise SystemExit(f"unexpected geometry in {path}")


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_envelope_chrome", RENDERER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load envelope chrome renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="ISO date in the manifest timezone; defaults to now")
    parser.add_argument("--season", choices=["spring", "summer", "autumn", "winter"])
    parser.add_argument("--apply", action="store_true", help="promote the approved candidate to all stable live envelope assets")
    parser.add_argument("--force", action="store_true", help="allow explicit manual promotion even when auto_promote is false")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args()

    manifest = load_json(MANIFEST)
    validate_manifest(manifest)
    day = resolve_day(args.date, manifest.get("timezone", "Asia/Tokyo"))
    season, cfg = resolve_season(manifest, day, args.season)

    hero = LAB / cfg["hero"]
    validate_svg(hero, "900", "260", "0 0 900 260")
    if cfg.get("static_render") != "PASS":
        raise SystemExit(f"{season} is not statically render-approved")
    if not cfg.get("auto_promote", False) and not (args.force and args.season):
        raise SystemExit(f"{season} is not approved for automatic promotion")

    assets = {key: ROOT / path for key, path in manifest["live_assets"].items()}
    live = load_json(LIVE_STATE)
    changed = live.get("active_season") != season or assets["hero"].read_bytes() != hero.read_bytes()

    result = {
        "date": day.isoformat(),
        "timezone": manifest.get("timezone", "Asia/Tokyo"),
        "season": season,
        "theme": f"{season}-dark",
        "source": str(hero.relative_to(ROOT)),
        "live_assets": {key: str(path.relative_to(ROOT)) for key, path in assets.items()},
        "changed": changed,
        "apply": args.apply,
        "envelope_version": 2,
    }

    if args.apply:
        shutil.copyfile(hero, assets["hero"])
        renderer = load_renderer()
        renderer.render(season, ROOT)
        validate_svg(assets["divider"], "900", "38", "0 0 900 38")
        validate_svg(assets["projects"], "900", "68", "0 0 900 68")
        validate_svg(assets["activity"], "900", "68", "0 0 900 68")
        validate_svg(assets["footer"], "900", "92", "0 0 900 92")
        next_state = {
            "version": 2,
            "envelope_version": 2,
            "active_season": season,
            "active_theme": f"{season}-dark",
            "source": str(hero.relative_to(ROOT)),
            "live_assets": {key: str(path.relative_to(ROOT)) for key, path in assets.items()},
            "timezone": manifest.get("timezone", "Asia/Tokyo"),
            "promoted_at": day.isoformat(),
            "promotion_mode": "automatic" if args.season is None else "manual",
        }
        LIVE_STATE.write_text(json.dumps(next_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        action = "promoted" if args.apply and changed else "refreshed" if args.apply else "no-change" if not changed else "would-promote"
        print(f"{action}: {season} envelope v2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
