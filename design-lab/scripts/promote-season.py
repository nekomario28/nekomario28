#!/usr/bin/env python3
"""Validate and optionally promote the complete seasonal profile envelope v5."""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent
MANIFEST = LAB / "theme-manifest.json"
LIVE_STATE = LAB / "live-theme.json"
RENDERER = Path(__file__).with_name("render_continuous_flow.py")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(data: dict) -> None:
    seen: dict[int, str] = {}
    required_assets = {"hero", "bridge", "projects", "activity", "footer"}
    if data.get("version") != 6:
        raise SystemExit("Envelope v5 requires manifest version 6")
    if set(data.get("live_assets", {})) != required_assets:
        raise SystemExit(f"live_assets must be exactly {sorted(required_assets)}")
    flow = data.get("envelope_motion", {})
    if flow.get("mode") != "phase-tolerant-segmented-handoff":
        raise SystemExit("unexpected envelope motion mode")
    if flow.get("cross_document_hard_sync") is not False:
        raise SystemExit("cross-document hard sync must not be claimed")
    if flow.get("rail_x") != [18, 882] or flow.get("duration_seconds") != 12:
        raise SystemExit("unexpected v5 rail motion contract")
    for name, cfg in data["seasons"].items():
        for month in cfg["months"]:
            if not 1 <= month <= 12 or month in seen:
                raise SystemExit(f"invalid or duplicate month {month} for {name}")
            seen[month] = name
        for field in ("bg0", "bg1", "accent2", "motif"):
            if not cfg.get("chrome", {}).get(field):
                raise SystemExit(f"missing chrome.{field} for {name}")
        motion = cfg.get("motion", {})
        if motion.get("implementation") != "embedded-smil" or motion.get("static_fallback") is not True:
            raise SystemExit(f"invalid motion contract for {name}")
    if set(seen) != set(range(1, 13)):
        raise SystemExit("season mapping must cover months 1..12 exactly once")


def resolve_day(value: str | None, timezone: str) -> dt.date:
    if value:
        return dt.date.fromisoformat(value)
    return dt.datetime.now(ZoneInfo(timezone)).date()


def resolve_season(data: dict, day: dt.date, explicit: str | None) -> tuple[str, dict]:
    if explicit:
        return explicit, data["seasons"][explicit]
    matches = [(name, cfg) for name, cfg in data["seasons"].items() if day.month in cfg["months"]]
    if len(matches) != 1:
        raise SystemExit(f"expected one season for month {day.month}, got {len(matches)}")
    return matches[0]


def validate_svg(path: Path, geometry: tuple[str, str, str], *, require_v5: bool = True) -> None:
    try:
        root = ET.parse(path).getroot()
    except (FileNotFoundError, ET.ParseError) as exc:
        raise SystemExit(f"invalid SVG {path}: {exc}") from exc
    if (root.attrib.get("width"), root.attrib.get("height"), root.attrib.get("viewBox")) != geometry:
        raise SystemExit(f"unexpected geometry in {path}")
    text = path.read_text(encoding="utf-8")
    if require_v5:
        if 'id="v5-frame"' not in text or "prefers-reduced-motion" not in text or "<animate" not in text:
            raise SystemExit(f"missing v5 motion/frame contract in {path}")
        if "<script" in text.lower() or "javascript:" in text.lower():
            raise SystemExit(f"scripted animation is not allowed in {path}")


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_continuous_flow", RENDERER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load v5 renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_assets(renderer, season: str, live_assets: dict[str, str]) -> dict[str, bytes]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        renderer.render(season, root)
        return {key: (root / rel).read_bytes() for key, rel in live_assets.items()}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date")
    p.add_argument("--season", choices=["spring", "summer", "autumn", "winter"])
    p.add_argument("--apply", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    manifest = load_json(MANIFEST)
    validate_manifest(manifest)
    day = resolve_day(args.date, manifest.get("timezone", "Asia/Tokyo"))
    season, cfg = resolve_season(manifest, day, args.season)
    source_hero = LAB / cfg["hero"]
    validate_svg(source_hero, ("900", "260", "0 0 900 260"), require_v5=False)
    source_text = source_hero.read_text(encoding="utf-8")
    if "prefers-reduced-motion" not in source_text or "<animate" not in source_text or "<script" in source_text.lower():
        raise SystemExit(f"invalid seasonal hero motion source: {season}")
    if cfg.get("static_render") != "PASS":
        raise SystemExit(f"{season} is not statically render-approved")
    if not cfg.get("auto_promote", False) and not (args.force and args.season):
        raise SystemExit(f"{season} is not approved for automatic promotion")

    renderer = load_renderer()
    expected = expected_assets(renderer, season, manifest["live_assets"])
    assets = {key: ROOT / rel for key, rel in manifest["live_assets"].items()}
    live = load_json(LIVE_STATE)
    changed = (
        live.get("active_season") != season
        or live.get("envelope_version") != 5
        or any(not assets[key].is_file() or assets[key].read_bytes() != expected[key] for key in expected)
    )

    result = {
        "date": day.isoformat(), "timezone": manifest.get("timezone", "Asia/Tokyo"),
        "season": season, "theme": f"{season}-dark", "changed": changed,
        "apply": args.apply, "envelope_version": 5,
        "motion_mode": manifest["envelope_motion"]["mode"],
        "cross_document_hard_sync": False,
    }

    if args.apply:
        renderer.render(season, ROOT)
        specs = {
            "hero": ("900", "260", "0 0 900 260"),
            "bridge": ("900", "32", "0 0 900 32"),
            "projects": ("900", "68", "0 0 900 68"),
            "activity": ("900", "68", "0 0 900 68"),
            "footer": ("900", "92", "0 0 900 92"),
        }
        for key, geom in specs.items():
            validate_svg(assets[key], geom)
        next_state = {
            "version": 5,
            "envelope_version": 5,
            "active_season": season,
            "active_theme": f"{season}-dark",
            "source": str(source_hero.relative_to(ROOT)),
            "live_assets": {key: str(path.relative_to(ROOT)) for key, path in assets.items()},
            "timezone": manifest.get("timezone", "Asia/Tokyo"),
            "motion": cfg["motion"],
            "frame": {
                "mode": "continuous-segmented-flow",
                "background_illusion": True,
                "shared_edge_rails": True,
                "top_cap": True,
                "bottom_cap": True,
                "phase_tolerant_handoff": True,
                "cross_document_hard_sync": False,
                "true_overlay": False
            },
            "promoted_at": day.isoformat(),
            "promotion_mode": "automatic" if args.season is None else "manual"
        }
        LIVE_STATE.write_text(json.dumps(next_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        action = "promoted" if args.apply and changed else "refreshed" if args.apply else "no-change" if not changed else "would-promote"
        print(f"{action}: {season} envelope v5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
