#!/usr/bin/env python3
"""Render Envelope v6 from one logical motion space into clipped SVG windows.

Every participating SVG receives the same global particle trajectories. A local asset
only subtracts its own global window start and clips the result to its viewport.
Objects therefore continue beyond a segment boundary instead of being locally deleted
or faded when their center touches an edge.

GitHub still loads each README image as an independent SVG document. Matching global
coordinates, velocity and phase offsets improve perceptual continuity, but this module
does not claim a shared runtime clock or frame-perfect cross-document synchronization.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent
MANIFEST = LAB / "theme-manifest.json"
SPACE = LAB / "envelope-v6" / "global-motion-space.json"
BASE_RENDERER = Path(__file__).with_name("render_envelope_chrome.py")
V7_VALIDATOR = LAB / "envelope-v7" / "validate.py"
_V7_VALIDATED = False


def load_base_renderer():
    spec = importlib.util.spec_from_file_location("render_envelope_chrome", BASE_RENDERER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load base envelope renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_experimental_v7_if_present() -> None:
    global _V7_VALIDATED
    if _V7_VALIDATED or not V7_VALIDATOR.is_file():
        return
    spec = importlib.util.spec_from_file_location("envelope_v7_validate", V7_VALIDATOR)
    if spec is None or spec.loader is None:
        raise ValueError("unable to load Envelope v7 validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.main()
    if result not in (None, 0):
        raise ValueError(f"Envelope v7 validator returned {result}")
    _V7_VALIDATED = True


def validate_space(space: dict) -> None:
    if space.get("version") != 1:
        raise ValueError("Envelope v6 global motion space version must be 1")
    if space.get("coordinate_system") != "profile-envelope-logical-y-v1":
        raise ValueError("unexpected Envelope v6 coordinate system")
    if space.get("width") != 900 or space.get("rail_x") != [18, 882]:
        raise ValueError("unexpected Envelope v6 width/rail contract")
    if space.get("cross_document_hard_sync") is not False:
        raise ValueError("cross-document hard sync must not be claimed")
    if space.get("render_model") != "shared-global-field-clipped-by-local-window":
        raise ValueError("unexpected Envelope v6 render model")
    extent = int(space["global_extent"])
    windows = space["windows"]
    cursor = 0
    for name, window in windows.items():
        start, end, height = int(window["start"]), int(window["end"]), int(window["height"])
        if start != cursor or end <= start or end - start != height:
            raise ValueError(f"non-contiguous or invalid global window: {name}")
        cursor = end
        if window.get("rendered") and not window.get("asset_key"):
            raise ValueError(f"rendered window lacks asset_key: {name}")
    if cursor != extent:
        raise ValueError("global windows must cover the complete logical extent")
    phases = [float(p["phase_seconds"]) for p in space["particles"]]
    if len(phases) != len(set(phases)):
        raise ValueError("particle phases must be unique")
    validate_experimental_v7_if_present()


def cap_markup(height: int, accent: str, accent2: str, *, top: bool, bottom: bool) -> str:
    out: list[str] = []
    if top:
        out.append(
            f'<path d="M18 30V18Q18 7 30 7H76 M882 30V18Q882 7 870 7H824" '
            f'fill="none" stroke="{accent}" stroke-opacity=".34" stroke-width="1.8" stroke-linecap="round"/>'
        )
        out.append(
            f'<path d="M31 13H62 M838 13H869" fill="none" stroke="{accent2}" '
            f'stroke-opacity=".20" stroke-width=".8"/>'
        )
    if bottom:
        y1, y2 = height - 28, height - 18
        qy = height - 7
        out.append(
            f'<path d="M18 {y1}V{y2}Q18 {qy} 30 {qy}H76 M882 {y1}V{y2}Q882 {qy} 870 {qy}H824" '
            f'fill="none" stroke="{accent}" stroke-opacity=".34" stroke-width="1.8" stroke-linecap="round"/>'
        )
    return "".join(out)


def particle_markup(particle: dict, *, window_start: int, global_extent: int, bleed: int,
                    duration: float, rail_x: list[int], accent: str, accent2: str) -> str:
    x = rail_x[0] if particle["rail"] == "left" else rail_x[1]
    color = accent if particle["color"] == "accent" else accent2
    radius = float(particle["radius"])
    tail = float(particle["tail"])
    opacity = float(particle["opacity"])
    phase = float(particle["phase_seconds"])
    global_from = -bleed
    global_to = global_extent + bleed
    local_from = global_from - window_start
    local_to = global_to - window_start
    begin = "0s" if phase == 0 else f"-{phase:g}s"
    return f'''<g id="v6-particle-{particle['id']}" opacity="{opacity:g}">
      <line x1="{x}" y1="{-tail:g}" x2="{x}" y2="0" stroke="{color}" stroke-opacity=".34" stroke-width="1.2" stroke-linecap="round"/>
      <circle cx="{x}" cy="0" r="{radius:g}" fill="{color}"/>
      <animateTransform attributeName="transform" type="translate" values="0 {local_from};0 {local_to}" dur="{duration:g}s" begin="{begin}" repeatCount="indefinite"/>
    </g>'''


def global_motion_layer(window_name: str, space: dict, accent: str, accent2: str,
                        *, top_cap: bool = False, bottom_cap: bool = False) -> str:
    window = space["windows"][window_name]
    if not window.get("rendered"):
        raise ValueError(f"cannot render invisible global window: {window_name}")
    start, end, height = int(window["start"]), int(window["end"]), int(window["height"])
    extent = int(space["global_extent"])
    bleed = int(space["bleed"])
    duration = float(space["duration_seconds"])
    rails = list(space["rail_x"])
    particles = "\n    ".join(
        particle_markup(
            p,
            window_start=start,
            global_extent=extent,
            bleed=bleed,
            duration=duration,
            rail_x=rails,
            accent=accent,
            accent2=accent2,
        )
        for p in space["particles"]
    )
    caps = cap_markup(height, accent, accent2, top=top_cap, bottom=bottom_cap)
    return f'''<defs><clipPath id="v6-window"><rect x="0" y="0" width="900" height="{height}"/></clipPath></defs>
<style>@media (prefers-reduced-motion: reduce) {{ .v6-motion {{ display:none }} }}</style>
<g id="v6-global-window" data-window="{window_name}" data-global-start="{start}" data-global-end="{end}" data-global-extent="{extent}" pointer-events="none">
  {caps}
  <path d="M18 0V{height} M882 0V{height}" fill="none" stroke="{accent}" stroke-opacity=".16" stroke-width="1.8"/>
  <path d="M22 0V{height} M878 0V{height}" fill="none" stroke="{accent2}" stroke-opacity=".08" stroke-width=".7"/>
  <g class="v6-motion" clip-path="url(#v6-window)">
    {particles}
  </g>
</g>'''


def inject(svg_text: str, layer: str) -> str:
    if "</svg>" not in svg_text:
        raise ValueError("missing closing svg tag")
    if 'id="v6-global-window"' in svg_text:
        raise ValueError("v6 layer already present in source")
    if 'id="v5-frame"' in svg_text:
        raise ValueError("v5 layer must not be used as a v6 base")
    return svg_text.replace("</svg>", layer + "\n</svg>", 1)


def render(season: str, out_root: Path = ROOT) -> list[Path]:
    manifest = load_json(MANIFEST)
    space = load_json(SPACE)
    validate_space(space)
    cfg = manifest["seasons"][season]
    accent = cfg["accent"]
    accent2 = cfg["chrome"]["accent2"]
    assets = manifest["live_assets"]
    base = load_base_renderer()

    hero_src = LAB / cfg["hero"]
    hero_dst = out_root / assets["hero"]
    hero_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(hero_src, hero_dst)

    static_outputs = {
        "bridge_character_projects": base.frame_bridge(cfg),
        "projects": base.section_band(cfg, "プロジェクト", "プロジェクト セクション"),
        "bridge_projects_activity": base.frame_bridge(cfg),
        "activity": base.section_band(cfg, "活動", "活動 セクション"),
        "bridge_activity_footer": base.frame_bridge(cfg),
        "footer": base.footer(cfg),
    }
    for key, text in static_outputs.items():
        path = out_root / assets[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")

    render_windows = {
        "hero": ("hero", True, False),
        "bridge_character_projects": ("bridge_character_projects", False, False),
        "projects": ("projects", False, False),
        "bridge_projects_activity": ("bridge_projects_activity", False, False),
        "activity": ("activity", False, False),
        "bridge_activity_footer": ("bridge_activity_footer", False, False),
        "footer": ("footer", False, True),
    }
    written: list[Path] = []
    for key, (window_name, top_cap, bottom_cap) in render_windows.items():
        path = out_root / assets[key]
        text = path.read_text(encoding="utf-8")
        layer = global_motion_layer(
            window_name, space, accent, accent2, top_cap=top_cap, bottom_cap=bottom_cap
        )
        path.write_text(inject(text, layer) + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--season", required=True, choices=["spring", "summer", "autumn", "winter"])
    p.add_argument("--out-root", type=Path, default=ROOT)
    args = p.parse_args()
    for path in render(args.season, args.out_root):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
