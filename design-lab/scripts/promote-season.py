#!/usr/bin/env python3
"""Validate and optionally promote the complete seasonal profile Envelope v7."""
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
GLOBAL_SPACE = LAB / "envelope-v7" / "global-motion-space.json"
RENDERER = LAB / "envelope-v7" / "render_continuous_canvas.py"

REQUIRED_ASSETS = {
    "hero",
    "character_left",
    "character_right",
    "attribution",
    "bridge_character_projects",
    "projects",
    "projects_canvas",
    "bridge_projects_activity",
    "activity",
    "activity_canvas",
    "bridge_activity_footer",
    "footer",
}

GEOMETRY = {
    "hero": ("900", "260", "0 0 900 260"),
    "character_left": ("100", "394", "0 0 100 394"),
    "character_right": ("100", "394", "0 0 100 394"),
    "attribution": ("900", "44", "0 0 900 44"),
    "bridge_character_projects": ("900", "32", "0 0 900 32"),
    "projects": ("900", "68", "0 0 900 68"),
    "projects_canvas": ("900", "420", "0 0 900 420"),
    "bridge_projects_activity": ("900", "32", "0 0 900 32"),
    "activity": ("900", "68", "0 0 900 68"),
    "activity_canvas": ("900", "220", "0 0 900 220"),
    "bridge_activity_footer": ("900", "32", "0 0 900 32"),
    "footer": ("900", "92", "0 0 900 92"),
}

WINDOW_FOR_ASSET = {
    "hero": "hero",
    "character_left": "character",
    "character_right": "character",
    "attribution": "attribution",
    "bridge_character_projects": "bridge_character_projects",
    "projects": "projects",
    "projects_canvas": "projects_canvas",
    "bridge_projects_activity": "bridge_projects_activity",
    "activity": "activity",
    "activity_canvas": "activity_canvas",
    "bridge_activity_footer": "bridge_activity_footer",
    "footer": "footer",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_continuous_canvas", RENDERER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load Envelope v7 renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_manifest(data: dict, renderer) -> dict:
    if data.get("version") != 8:
        raise SystemExit("Envelope v7 requires manifest version 8")
    if set(data.get("live_assets", {})) != REQUIRED_ASSETS:
        raise SystemExit(f"live_assets must be exactly {sorted(REQUIRED_ASSETS)}")

    flow = data.get("envelope_motion", {})
    expected_flow = {
        "mode": "continuous-canvas-global-windowed-handoff",
        "coordinate_system": "profile-envelope-continuous-canvas-y-v1",
        "render_model": "shared-global-field-clipped-by-rendered-canvas-windows",
        "background_model": "edge-matched-dark-surface-with-mounted-foreground-media",
        "rail_x": [18, 882],
        "duration_seconds": 32,
        "global_extent": 1662,
        "bleed": 24,
        "boundary_fade": False,
        "partial_geometry_clipping": True,
        "all_logical_windows_rendered": True,
        "mounted_foreground_media": True,
        "cross_document_hard_sync": False,
        "static_fallback": True,
        "reduced_motion": True,
    }
    for key, value in expected_flow.items():
        if flow.get(key) != value:
            raise SystemExit(f"unexpected Envelope v7 motion contract: {key}")
    if flow.get("space") != "design-lab/envelope-v7/global-motion-space.json":
        raise SystemExit("unexpected Envelope v7 global motion space path")

    space = load_json(GLOBAL_SPACE)
    try:
        renderer.validate_space(space)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    mapped: dict[str, tuple[str, int, int, int]] = {}
    for name, window in space["windows"].items():
        keys = []
        if window.get("asset_key"):
            keys.append(window["asset_key"])
        keys.extend(window.get("asset_keys", []))
        for key in keys:
            mapped[key] = (name, int(window["start"]), int(window["end"]), int(window["height"]))
    if set(mapped) != REQUIRED_ASSETS:
        raise SystemExit("Envelope v7 rendered windows must map all live assets exactly")
    for key, (_, _, _, height) in mapped.items():
        if int(GEOMETRY[key][1]) != height:
            raise SystemExit(f"window height does not match asset geometry: {key}")

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


def validate_svg(path: Path, geometry: tuple[str, str, str], *, window: tuple[str, int, int] | None = None) -> None:
    try:
        root = ET.parse(path).getroot()
    except (FileNotFoundError, ET.ParseError) as exc:
        raise SystemExit(f"invalid SVG {path}: {exc}") from exc
    if (root.attrib.get("width"), root.attrib.get("height"), root.attrib.get("viewBox")) != geometry:
        raise SystemExit(f"unexpected geometry in {path}")
    text = path.read_text(encoding="utf-8")
    if 'id="v7-global-window"' not in text:
        raise SystemExit(f"missing v7 global window in {path}")
    if "prefers-reduced-motion" not in text or "<animateTransform" not in text:
        raise SystemExit(f"missing v7 motion/reduced-motion contract in {path}")
    if 'clip-path="url(#v7-window)"' not in text:
        raise SystemExit(f"missing v7 clipped-window rendering in {path}")
    if 'dur="32s"' not in text:
        raise SystemExit(f"unexpected v7 global motion duration in {path}")
    if "<script" in text.lower() or "javascript:" in text.lower():
        raise SystemExit(f"scripted animation is not allowed in {path}")
    tail = text.split('id="v7-global-window"', 1)[1]
    if '<animate attributeName="opacity"' in tail:
        raise SystemExit(f"v7 boundary fade is forbidden in {path}")
    if window:
        name, start, end = window
        if f'data-window="{name}"' not in text:
            raise SystemExit(f"wrong v7 global window name in {path}")
        if f'data-global-start="{start}"' not in text or f'data-global-end="{end}"' not in text:
            raise SystemExit(f"wrong v7 global coordinates in {path}")


def asset_windows(space: dict) -> dict[str, tuple[str, int, int]]:
    result: dict[str, tuple[str, int, int]] = {}
    for name, window in space["windows"].items():
        keys = []
        if window.get("asset_key"):
            keys.append(window["asset_key"])
        keys.extend(window.get("asset_keys", []))
        for key in keys:
            result[key] = (name, int(window["start"]), int(window["end"]))
    return result


def expected_assets(renderer, season: str, live_assets: dict[str, str]) -> dict[str, bytes]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        renderer.render(season, root)
        return {key: (root / rel).read_bytes() for key, rel in live_assets.items()}


def same_verification_target(live: dict, *, season: str, source_hero: Path) -> bool:
    """Whether a live playback receipt still describes this exact deployed target.

    Derived Project Map/contribution refreshes do not invalidate representative v7 rail
    playback. A seasonal source, Envelope version, or global-space change does.
    Renderer/layout changes are expected to advance the Envelope version before release.
    """
    return (
        live.get("active_season") == season
        and live.get("envelope_version") == 7
        and live.get("source") == str(source_hero.relative_to(ROOT))
        and live.get("global_motion_space") == str(GLOBAL_SPACE.relative_to(ROOT))
    )


def next_motion_state(live: dict, cfg: dict, *, season: str, source_hero: Path) -> dict:
    next_motion = dict(cfg["motion"])
    current_motion = live.get("motion", {}) if isinstance(live.get("motion"), dict) else {}
    if same_verification_target(live, season=season, source_hero=source_hero) and current_motion.get("live_verification") == "PASS":
        for key, value in current_motion.items():
            if key == "live_verification" or key.startswith("live_verification_"):
                next_motion[key] = value
    else:
        next_motion["live_verification"] = "NOT_RUN"
    return next_motion


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
    try:
        live = load_json(LIVE_STATE)
    except FileNotFoundError:
        live = {}
    changed = (
        live.get("active_season") != season
        or live.get("envelope_version") != 7
        or live.get("global_motion_space") != str(GLOBAL_SPACE.relative_to(ROOT))
        or any(not assets[key].is_file() or assets[key].read_bytes() != expected[key] for key in expected)
    )

    result = {
        "date": day.isoformat(),
        "timezone": manifest.get("timezone", "Asia/Tokyo"),
        "season": season,
        "theme": f"{season}-dark",
        "changed": changed,
        "apply": args.apply,
        "envelope_version": 7,
        "motion_mode": manifest["envelope_motion"]["mode"],
        "coordinate_system": manifest["envelope_motion"]["coordinate_system"],
        "global_extent": manifest["envelope_motion"]["global_extent"],
        "cross_document_hard_sync": False,
    }

    if args.apply:
        renderer.render(season, ROOT)
        windows = asset_windows(space)
        for key, geom in GEOMETRY.items():
            validate_svg(assets[key], geom, window=windows[key])
        next_state = {
            "version": 7,
            "envelope_version": 7,
            "active_season": season,
            "active_theme": f"{season}-dark",
            "source": str(source_hero.relative_to(ROOT)),
            "live_assets": {key: str(path.relative_to(ROOT)) for key, path in assets.items()},
            "timezone": manifest.get("timezone", "Asia/Tokyo"),
            "motion": next_motion_state(live, cfg, season=season, source_hero=source_hero),
            "frame": {
                "mode": "continuous-canvas-global-windowed-flow",
                "background_illusion": True,
                "edge_matched_background": True,
                "mounted_foreground_media": True,
                "all_logical_windows_rendered": True,
                "shared_edge_rails": True,
                "top_cap": True,
                "bottom_cap": True,
                "global_coordinate_space": True,
                "shared_global_object_field": True,
                "window_clipping": True,
                "boundary_fade": False,
                "partial_geometry_clipping": True,
                "split_character_window": True,
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
        print(f"{action}: {season} envelope v7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
