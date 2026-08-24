#!/usr/bin/env python3
"""Render Envelope v7 as a continuous dark canvas with clipped global motion.

Repository-owned foreground SVGs are composed into 900px canvas stages. Third-party
character media is never copied or nested here; the renderer only generates its left
and right background surfaces. Every generated SVG is a clipping window into one
logical global Y field. Separate SVG documents still do not share a proven runtime
clock, so this module never claims frame-perfect hard synchronization.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
V7 = Path(__file__).resolve().parent
ROOT = LAB.parent
MANIFEST = LAB / "theme-manifest.json"
SPACE = V7 / "global-motion-space.json"
BASE_RENDERER = LAB / "scripts" / "render_envelope_chrome.py"
PANEL_RENDERER = V7 / "render_panels.py"
ATTRIBUTION_TEMPLATE = V7 / "attribution-band.svg"

LIVE_ASSETS = {
    "hero": "assets/profile-hero.svg",
    "character_left": "assets/profile-character-side-left.svg",
    "character_right": "assets/profile-character-side-right.svg",
    "attribution": "assets/profile-attribution.svg",
    "bridge_character_projects": "assets/profile-frame-bridge-character-projects.svg",
    "projects": "assets/profile-section-projects.svg",
    "projects_canvas": "assets/profile-projects-canvas.svg",
    "bridge_projects_activity": "assets/profile-frame-bridge-projects-activity.svg",
    "activity": "assets/profile-section-activity.svg",
    "activity_canvas": "assets/profile-activity-canvas.svg",
    "bridge_activity_footer": "assets/profile-frame-bridge-activity-footer.svg",
    "footer": "assets/profile-footer.svg",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_space(space: dict) -> None:
    if space.get("version") != 1:
        raise ValueError("Envelope v7 global motion space version must be 1")
    if space.get("coordinate_system") != "profile-envelope-continuous-canvas-y-v1":
        raise ValueError("unexpected Envelope v7 coordinate system")
    if space.get("width") != 900 or space.get("rail_x") != [18, 882]:
        raise ValueError("unexpected Envelope v7 canvas/rail contract")
    if space.get("global_extent") != 1662:
        raise ValueError("unexpected Envelope v7 global extent")
    if space.get("cross_document_hard_sync") is not False:
        raise ValueError("cross-document hard synchronization must not be claimed")
    if space.get("render_model") != "shared-global-field-clipped-by-rendered-canvas-windows":
        raise ValueError("unexpected Envelope v7 render model")

    cursor = 0
    for name, window in space["windows"].items():
        start = int(window["start"])
        end = int(window["end"])
        height = int(window["height"])
        if not window.get("rendered"):
            raise ValueError(f"v7 must not retain invisible gap windows: {name}")
        if start != cursor or end <= start or end - start != height:
            raise ValueError(f"invalid or non-contiguous v7 window: {name}")
        cursor = end
    if cursor != int(space["global_extent"]):
        raise ValueError("v7 windows do not cover the full logical canvas")

    phases = [float(p["phase_seconds"]) for p in space["particles"]]
    if len(phases) != len(set(phases)):
        raise ValueError("v7 particle phases must be unique")


def inject(svg_text: str, layer: str) -> str:
    if "</svg>" not in svg_text:
        raise ValueError("missing closing svg tag")
    if 'id="v7-global-window"' in svg_text:
        raise ValueError("v7 global layer already exists")
    return svg_text.replace("</svg>", layer + "\n</svg>", 1)


def particle_markup(
    particle: dict,
    *,
    window_start: int,
    global_extent: int,
    bleed: int,
    duration: float,
    global_rail_x: list[int],
    global_x_offset: int,
    allowed_rails: set[str],
    accent: str,
    accent2: str,
) -> str:
    rail = particle["rail"]
    if rail not in allowed_rails:
        return ""
    global_x = global_rail_x[0] if rail == "left" else global_rail_x[1]
    local_x = global_x - global_x_offset
    color = accent if particle["color"] == "accent" else accent2
    radius = float(particle["radius"])
    tail = float(particle["tail"])
    opacity = float(particle["opacity"])
    phase = float(particle["phase_seconds"])
    local_from = -bleed - window_start
    local_to = global_extent + bleed - window_start
    begin = "0s" if phase == 0 else f"-{phase:g}s"
    return f'''<g id="v7-particle-{particle['id']}" opacity="{opacity:g}">
      <line x1="{local_x:g}" y1="{-tail:g}" x2="{local_x:g}" y2="0" stroke="{color}" stroke-opacity=".34" stroke-width="1.2" stroke-linecap="round"/>
      <circle cx="{local_x:g}" cy="0" r="{radius:g}" fill="{color}"/>
      <animateTransform attributeName="transform" type="translate" values="0 {local_from};0 {local_to}" dur="{duration:g}s" begin="{begin}" repeatCount="indefinite"/>
    </g>'''


def cap_markup(width: int, height: int, accent: str, accent2: str, *, top: bool, bottom: bool) -> str:
    if width != 900:
        return ""
    out: list[str] = []
    if top:
        out.append(
            f'<path d="M18 30V18Q18 7 30 7H76 M882 30V18Q882 7 870 7H824" fill="none" '
            f'stroke="{accent}" stroke-opacity=".34" stroke-width="1.8" stroke-linecap="round"/>'
        )
        out.append(
            f'<path d="M31 13H62 M838 13H869" fill="none" stroke="{accent2}" stroke-opacity=".20" stroke-width=".8"/>'
        )
    if bottom:
        y1, y2, qy = height - 28, height - 18, height - 7
        out.append(
            f'<path d="M18 {y1}V{y2}Q18 {qy} 30 {qy}H76 M882 {y1}V{y2}Q882 {qy} 870 {qy}H824" fill="none" '
            f'stroke="{accent}" stroke-opacity=".34" stroke-width="1.8" stroke-linecap="round"/>'
        )
    return "".join(out)


def global_motion_layer(
    window_name: str,
    space: dict,
    accent: str,
    accent2: str,
    *,
    physical_width: int = 900,
    global_x_offset: int = 0,
    allowed_rails: set[str] | None = None,
    top_cap: bool = False,
    bottom_cap: bool = False,
) -> str:
    window = space["windows"][window_name]
    start = int(window["start"])
    end = int(window["end"])
    height = int(window["height"])
    extent = int(space["global_extent"])
    bleed = int(space["bleed"])
    duration = float(space["duration_seconds"])
    rails = list(space["rail_x"])
    permitted = allowed_rails or {"left", "right"}

    particles = "\n    ".join(
        p
        for p in (
            particle_markup(
                particle,
                window_start=start,
                global_extent=extent,
                bleed=bleed,
                duration=duration,
                global_rail_x=rails,
                global_x_offset=global_x_offset,
                allowed_rails=permitted,
                accent=accent,
                accent2=accent2,
            )
            for particle in space["particles"]
        )
        if p
    )
    caps = cap_markup(physical_width, height, accent, accent2, top=top_cap, bottom=bottom_cap)
    return f'''<defs><clipPath id="v7-window"><rect x="0" y="0" width="{physical_width}" height="{height}"/></clipPath></defs>
<style>@media (prefers-reduced-motion: reduce) {{ .v7-motion {{ display:none }} }}</style>
<g id="v7-global-window" data-window="{window_name}" data-global-start="{start}" data-global-end="{end}" data-global-extent="{extent}" data-global-x-offset="{global_x_offset}" pointer-events="none">
  {caps}
  <g class="v7-motion" clip-path="url(#v7-window)">
    {particles}
  </g>
</g>'''


def character_side(cfg: dict, side: str) -> str:
    if side not in {"left", "right"}:
        raise ValueError(side)
    accent = cfg["accent"]
    c = cfg["chrome"]
    bg0, bg1, accent2 = c["bg0"], c["bg1"], c["accent2"]
    if side == "left":
        gradient = f'<stop stop-color="#0d1117"/><stop offset=".38" stop-color="{bg0}"/><stop offset="1" stop-color="{bg1}"/>'
        inner_x, rail_x, rail2_x = 99, 18, 22
        motif = '<path d="M0 307 C30 276 55 351 100 292"'
    else:
        gradient = f'<stop stop-color="{bg1}"/><stop offset=".62" stop-color="{bg0}"/><stop offset="1" stop-color="#0d1117"/>'
        inner_x, rail_x, rail2_x = 1, 82, 78
        motif = '<path d="M0 292 C45 351 70 276 100 307"'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="394" viewBox="0 0 100 394" role="img" aria-label="Envelope v7 character {side} background surface">
  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="0">{gradient}</linearGradient></defs>
  <rect width="100" height="394" fill="url(#bg)"/>
  {motif} fill="none" stroke="{accent}" stroke-opacity=".10" stroke-width="18"/>
  <path d="M{rail_x} 0V394" fill="none" stroke="{accent}" stroke-opacity=".18" stroke-width="1.6"/>
  <path d="M{rail2_x} 0V394" fill="none" stroke="{accent2}" stroke-opacity=".08" stroke-width=".7"/>
  <path d="M{inner_x} 0V394" fill="none" stroke="#eef2f6" stroke-opacity=".07"/>
</svg>'''


def attribution_base(cfg: dict) -> str:
    text = ATTRIBUTION_TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "#06101a": cfg["chrome"]["bg0"],
        "#0c2d3b": cfg["chrome"]["bg1"],
        "#86aa94": cfg["accent"],
        "#c7b06c": cfg["chrome"]["accent2"],
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if "<text" in text:
        raise ValueError("v7 attribution must remain font-independent vector geometry")
    return text


def render(season: str, out_root: Path = ROOT) -> list[Path]:
    manifest = load_json(MANIFEST)
    space = load_json(SPACE)
    validate_space(space)
    cfg = manifest["seasons"][season]
    if not cfg.get("auto_promote") or cfg.get("static_render") != "PASS":
        raise ValueError(f"season not approved: {season}")
    accent = cfg["accent"]
    accent2 = cfg["chrome"]["accent2"]

    base = load_module("v7_base_chrome", BASE_RENDERER)
    panels = load_module("v7_panels", PANEL_RENDERER)

    static: dict[str, str] = {
        "character_left": character_side(cfg, "left"),
        "character_right": character_side(cfg, "right"),
        "attribution": attribution_base(cfg),
        "bridge_character_projects": base.frame_bridge(cfg),
        "projects": base.section_band(cfg, "プロジェクト", "プロジェクト セクション"),
        "projects_canvas": panels.projects_panel(cfg),
        "bridge_projects_activity": base.frame_bridge(cfg),
        "activity": base.section_band(cfg, "活動", "活動 セクション"),
        "activity_canvas": panels.activity_panel(cfg),
        "bridge_activity_footer": base.frame_bridge(cfg),
        "footer": base.footer(cfg),
    }

    hero_src = LAB / cfg["hero"]
    static["hero"] = hero_src.read_text(encoding="utf-8")

    render_windows = {
        "hero": ("hero", 900, 0, {"left", "right"}, True, False),
        "character_left": ("character", 100, 0, {"left"}, False, False),
        "character_right": ("character", 100, 800, {"right"}, False, False),
        "attribution": ("attribution", 900, 0, {"left", "right"}, False, False),
        "bridge_character_projects": ("bridge_character_projects", 900, 0, {"left", "right"}, False, False),
        "projects": ("projects", 900, 0, {"left", "right"}, False, False),
        "projects_canvas": ("projects_canvas", 900, 0, {"left", "right"}, False, False),
        "bridge_projects_activity": ("bridge_projects_activity", 900, 0, {"left", "right"}, False, False),
        "activity": ("activity", 900, 0, {"left", "right"}, False, False),
        "activity_canvas": ("activity_canvas", 900, 0, {"left", "right"}, False, False),
        "bridge_activity_footer": ("bridge_activity_footer", 900, 0, {"left", "right"}, False, False),
        "footer": ("footer", 900, 0, {"left", "right"}, False, True),
    }

    written: list[Path] = []
    for key, (window, width, x_offset, allowed, top, bottom) in render_windows.items():
        layer = global_motion_layer(
            window,
            space,
            accent,
            accent2,
            physical_width=width,
            global_x_offset=x_offset,
            allowed_rails=allowed,
            top_cap=top,
            bottom_cap=bottom,
        )
        text = inject(static[key], layer)
        path = out_root / LIVE_ASSETS[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True, choices=["spring", "summer", "autumn", "winter"])
    parser.add_argument("--out-root", type=Path, default=ROOT)
    args = parser.parse_args()
    for path in render(args.season, args.out_root):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
