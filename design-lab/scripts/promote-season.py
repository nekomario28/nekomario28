#!/usr/bin/env python3
"""Validate and optionally promote the complete seasonal profile Envelope v6."""
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
GLOBAL_SPACE = LAB / "envelope-v6" / "global-motion-space.json"
RENDERER = Path(__file__).with_name("render_global_motion.py")

REQUIRED_ASSETS = {
    "hero",
    "bridge_character_projects",
    "projects",
    "bridge_projects_activity",
    "activity",
    "bridge_activity_footer",
    "footer",
}

GEOMETRY = {
    "hero": ("900", "260", "0 0 900 260"),
    "bridge_character_projects": ("900", "32", "0 0 900 32"),
    "projects": ("900", "68", "0 0 900 68"),
    "bridge_projects_activity": ("900", "32", "0 0 900 32"),
    "activity": ("900", "68", "0 0 900 68"),
    "bridge_activity_footer": ("900", "32", "0 0 900 32"),
    "footer": ("900", "92", "0 0 900 92"),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_global_motion", RENDERER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load Envelope v6 renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_manifest(data: dict, renderer) -> dict:
    if data.get("version") != 7:
        raise SystemExit("Envelope v6 requires manifest version 7")
    if set(data.get("live_assets", {})) != REQUIRED_ASSETS:
        raise SystemExit(f"live_assets must be exactly {sorted(REQUIRED_ASSETS)}")
    flow = data.get("envelope_motion", {})
    expected_flow = {
        "mode": "global-coordinate-windowed-handoff",
        "coordinate_system": "profile-envelope-logical-y-v1",
        "render_model": "shared-global-field-clipped-by-local-window",
        "rail_x": [18, 882],
        "duration_seconds": 36,
        "global_extent": 1868,
        "bleed": 24,
        "cross_document_hard_sync": False,
        "boundary_fade": False,
        "partial_geometry_clipping": True,
        "static_fallback": True,
        "reduced_motion": True,
    }
    for key, value in expected_flow.items():
        if flow.get(key) != value:
            raise SystemExit(f"unexpected Envelope v6 motion contract: {key}")
    if flow.get("space") != "design-lab/envelope-v6/global-motion-space.json":
        raise SystemExit("unexpected global motion space path")

    space = load_json(GLOBAL_SPACE)
    try:
        renderer.validate_space(space)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    rendered_windows = {
        w["asset_key"]: (name, int(w["start"]), int(w["end"]), int(w["height"]))
        for name, w in space["windows"].items()
        if w.get("rendered")
    }
    if set(rendered_windows) != REQUIRED_ASSETS:
        raise SystemExit("global motion rendered windows must match live_assets exactly")
    for key, (_, _, _, height) in rendered_windows.items():
        if int(GEOMETRY[key][1]) != height:
            raise SystemExit(f"window height does not match asset geometry: {key}")

    bridge_starts = [
        rendered_windows[key][1]
        for key in ("bridge_character_projects", "bridge_projects_activity", "bridge_activity_footer")
    ]
    if len(set(bridge_starts)) != 3:
        raise SystemExit("the three bridge occurrences must have distinct global windows")

    seen: dict[int, str] = {}
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
            raise SystemExit(f"invalid seasonal motion contract for {name}")
        if motion.get("live_verification") not in {"NOT_RUN", "PASS"}:
            raise SystemExit(f"invalid live verification state for {name}")
    if set(seen) != set(range(1, 13)):
        raise SystemExit("season mapping must cover months 1..12 exactly once")
    return space


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


def validate_svg(path: Path, geometry: tuple[str, str, str], *, expected_window: tuple[str, int, int] | None = None) -> None:
    try:
        root = ET.parse(path).getroot()
    except (FileNotFoundError, ET.ParseError) as exc:
        raise SystemExit(f"invalid SVG {path}: {exc}") from exc
    if (root.attrib.get("width"), root.attrib.get("height"), root.attrib.get("viewBox")) != geometry:
        raise SystemExit(f"unexpected geometry in {path}")
    text = path.read_text(encoding="utf-8")
    if 'id="v6-global-window"' not in text:
        raise SystemExit(f"missing v6 global window in {path}")
    if "prefers-reduced-motion" not in text or "<animateTransform" not in text:
        raise SystemExit(f"missing v6 motion/reduced-motion contract in {path}")
    if 'clip-path="url(#v6-window)"' not in text:
        raise SystemExit(f"missing v6 clipped-window rendering in {path}")
    if 'dur="36s"' not in text:
        raise SystemExit(f"unexpected global motion duration in {path}")
    if "<script" in text.lower() or "javascript:" in text.lower():
        raise SystemExit(f"scripted animation is not allowed in {path}")
    v6_tail = text.split('id="v6-global-window"', 1)[1]
    if '<animate attributeName="opacity"' in v6_tail:
        raise SystemExit(f"v6 boundary fade is forbidden in {path}")
    if expected_window:
        name, start, end = expected_window
        if f'data-window="{name}"' not in text:
            raise SystemExit(f"wrong v6 global window name in {path}")
        if f'data-global-start="{start}"' not in text or f'data-global-end="{end}"' not in text:
            raise SystemExit(f"wrong v6 global coordinates in {path}")


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

    renderer = load_renderer()
    manifest = load_json(MANIFEST)
    space = validate_manifest(manifest, renderer)
    day = resolve_day(args.date, manifest.get("timezone", "Asia/Tokyo"))
    season, cfg = resolve_season(manifest, day, args.season)
    source_hero = LAB / cfg["hero"]

    try:
        source_root = ET.parse(source_hero).getroot()
    except (FileNotFoundError, ET.ParseError) as exc:
        raise SystemExit(f"invalid seasonal hero source {source_hero}: {exc}") from exc
    if (source_root.attrib.get("width"), source_root.attrib.get("height"), source_root.attrib.get("viewBox")) != GEOMETRY["hero"]:
        raise SystemExit(f"invalid seasonal hero geometry: {season}")
    source_text = source_hero.read_text(encoding="utf-8")
    if "prefers-reduced-motion" not in source_text or "<animate" not in source_text or "<script" in source_text.lower():
        raise SystemExit(f"invalid seasonal hero motion source: {season}")
    if cfg.get("static_render") != "PASS":
        raise SystemExit(f"{season} is not statically render-approved")
    if not cfg.get("auto_promote", False) and not (args.force and args.season):
        raise SystemExit(f"{season} is not approved for automatic promotion")

    expected = expected_assets(renderer, season, manifest["live_assets"])
    assets = {key: ROOT / rel for key, rel in manifest["live_assets"].items()}
    live = load_json(LIVE_STATE)
    changed = (
        live.get("active_season") != season
        or live.get("envelope_version") != 6
        or any(not assets[key].is_file() or assets[key].read_bytes() != expected[key] for key in expected)
    )

    result = {
        "date": day.isoformat(),
        "timezone": manifest.get("timezone", "Asia/Tokyo"),
        "season": season,
        "theme": f"{season}-dark",
        "changed": changed,
        "apply": args.apply,
        "envelope_version": 6,
        "motion_mode": manifest["envelope_motion"]["mode"],
        "coordinate_system": manifest["envelope_motion"]["coordinate_system"],
        "cross_document_hard_sync": False,
    }

    if args.apply:
        renderer.render(season, ROOT)
        rendered_windows = {
            w["asset_key"]: (name, int(w["start"]), int(w["end"]))
            for name, w in space["windows"].items()
            if w.get("rendered")
        }
        for key, geom in GEOMETRY.items():
            validate_svg(assets[key], geom, expected_window=rendered_windows[key])
        next_state = {
            "version": 6,
            "envelope_version": 6,
            "active_season": season,
            "active_theme": f"{season}-dark",
            "source": str(source_hero.relative_to(ROOT)),
            "live_assets": {key: str(path.relative_to(ROOT)) for key, path in assets.items()},
            "timezone": manifest.get("timezone", "Asia/Tokyo"),
            "motion": cfg["motion"],
            "frame": {
                "mode": "global-windowed-flow",
                "background_illusion": True,
                "shared_edge_rails": True,
                "top_cap": True,
                "bottom_cap": True,
                "global_coordinate_space": True,
                "shared_global_object_field": True,
                "window_clipping": True,
                "boundary_fade": False,
                "partial_geometry_clipping": True,
                "unique_bridge_windows": True,
                "phase_tolerant_handoff": True,
                "cross_document_hard_sync": False,
                "true_overlay": False,
            },
            "global_motion_space": str(GLOBAL_SPACE.relative_to(ROOT)),
            "promoted_at": day.isoformat(),
            "promotion_mode": "automatic" if args.season is None else "manual",
        }
        LIVE_STATE.write_text(json.dumps(next_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        action = "promoted" if args.apply and changed else "refreshed" if args.apply else "no-change" if not changed else "would-promote"
        print(f"{action}: {season} envelope v6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
