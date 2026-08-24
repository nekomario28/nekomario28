#!/usr/bin/env python3
"""Render Envelope v5: continuous segmented rails with phase-tolerant motion.

GitHub renders README images as separate SVG documents, so cross-document clock
synchronization is not guaranteed. v5 therefore uses the same rail coordinates,
duration, direction, and sparse pulse grammar in every participating asset. The
handoff remains visually coherent even when individual image load times drift.
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
BASE_RENDERER = Path(__file__).with_name("render_envelope_chrome.py")


def load_base_renderer():
    spec = importlib.util.spec_from_file_location("render_envelope_chrome", BASE_RENDERER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load base envelope renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def motion_layer(height: int, accent: str, accent2: str, *, top_cap: bool = False, bottom_cap: bool = False) -> str:
    cap = []
    if top_cap:
        cap.append(f'<path d="M18 30V18Q18 7 30 7H76 M882 30V18Q882 7 870 7H824" fill="none" stroke="{accent}" stroke-opacity=".34" stroke-width="1.8" stroke-linecap="round"/>')
        cap.append(f'<path d="M31 13H62 M838 13H869" fill="none" stroke="{accent2}" stroke-opacity=".20" stroke-width=".8"/>')
    if bottom_cap:
        cap.append(f'<path d="M18 {height-28}V{height-18}Q18 {height-7} 30 {height-7}H76 M882 {height-28}V{height-18}Q882 {height-7} 870 {height-7}H824" fill="none" stroke="{accent}" stroke-opacity=".34" stroke-width="1.8" stroke-linecap="round"/>')
    travel = height + 20
    return f'''<style>@media (prefers-reduced-motion: reduce) {{ .v5-motion {{ display:none }} }}</style>
<g id="v5-frame" pointer-events="none">
  {''.join(cap)}
  <path d="M18 0V{height} M882 0V{height}" fill="none" stroke="{accent}" stroke-opacity=".16" stroke-width="1.8"/>
  <path d="M22 0V{height} M878 0V{height}" fill="none" stroke="{accent2}" stroke-opacity=".08" stroke-width=".7"/>
  <g class="v5-motion">
    <circle cx="18" cy="-8" r="2.4" fill="{accent}"><animate attributeName="cy" values="-8;{height+8}" dur="12s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;.8;.8;0" keyTimes="0;.12;.82;1" dur="12s" repeatCount="indefinite"/></circle>
    <circle cx="882" cy="-8" r="2.1" fill="{accent2}"><animate attributeName="cy" values="-8;{height+8}" dur="12s" begin="-3s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;.65;.65;0" keyTimes="0;.12;.82;1" dur="12s" begin="-3s" repeatCount="indefinite"/></circle>
    <circle cx="18" cy="-8" r="1.4" fill="{accent2}"><animate attributeName="cy" values="-8;{height+8}" dur="12s" begin="-6s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;.45;.45;0" keyTimes="0;.12;.82;1" dur="12s" begin="-6s" repeatCount="indefinite"/></circle>
    <circle cx="882" cy="-8" r="1.5" fill="{accent}"><animate attributeName="cy" values="-8;{height+8}" dur="12s" begin="-9s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;.5;.5;0" keyTimes="0;.12;.82;1" dur="12s" begin="-9s" repeatCount="indefinite"/></circle>
  </g>
</g>'''


def inject(svg_text: str, layer: str) -> str:
    if "</svg>" not in svg_text:
        raise ValueError("missing closing svg tag")
    # Idempotent for generated previews.
    if 'id="v5-frame"' in svg_text:
        return svg_text
    return svg_text.replace("</svg>", layer + "\n</svg>", 1)


def render(season: str, out_root: Path = ROOT) -> list[Path]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cfg = data["seasons"][season]
    accent = cfg["accent"]
    accent2 = cfg["chrome"]["accent2"]
    assets = data["live_assets"]

    base = load_base_renderer()
    base.render(season, out_root)

    hero_src = LAB / cfg["hero"]
    hero_dst = out_root / assets["hero"]
    hero_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(hero_src, hero_dst)

    specs = {
        "hero": (260, True, False),
        "bridge": (32, False, False),
        "projects": (68, False, False),
        "activity": (68, False, False),
        "footer": (92, False, True),
    }
    written: list[Path] = []
    for key, (height, top_cap, bottom_cap) in specs.items():
        path = out_root / assets[key]
        text = path.read_text(encoding="utf-8")
        text = inject(text, motion_layer(height, accent, accent2, top_cap=top_cap, bottom_cap=bottom_cap))
        path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
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
