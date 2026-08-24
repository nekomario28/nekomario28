#!/usr/bin/env python3
"""Render experimental Envelope v4 segmented-frame bridges from the seasonal manifest."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
MANIFEST = LAB / "theme-manifest.json"
OUT = HERE / "assets"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def motif(kind: str, accent: str, accent2: str) -> str:
    if kind == "petal":
        return f'<g fill="{esc(accent)}" fill-opacity=".22"><ellipse cx="430" cy="15" rx="4" ry="2" transform="rotate(-24 430 15)"/><ellipse cx="470" cy="18" rx="3.4" ry="1.8" transform="rotate(28 470 18)"/></g>'
    if kind == "water":
        return f'<path d="M338 22 C390 10 443 27 494 17 C544 8 590 22 637 13" fill="none" stroke="{esc(accent)}" stroke-opacity=".10" stroke-width="1.4"/>'
    if kind == "leaf":
        return f'<g fill="{esc(accent)}" fill-opacity=".22"><path d="M0,-6 2,-2 6,-4 4,0 7,2 3,3 4,7 0,4 -2,8 -2,4 -7,5 -4,1 -7,-2 -3,-2 -3,-6 0,-3Z" transform="translate(450 16) rotate(18)"/></g>'
    if kind == "snow":
        return f'<g fill="{esc(accent2)}" fill-opacity=".25"><circle cx="430" cy="14" r="1.4"/><circle cx="450" cy="19" r="1"/><circle cx="472" cy="13" r="1.2"/></g>'
    raise ValueError(f"unknown motif: {kind}")


def bridge(cfg: dict) -> str:
    c = cfg["chrome"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="32" viewBox="0 0 900 32" role="img" aria-label="seasonal envelope frame bridge">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{esc(c['bg0'])}"/><stop offset=".5" stop-color="{esc(c['bg1'])}"/><stop offset="1" stop-color="{esc(c['bg0'])}"/></linearGradient>
    <linearGradient id="rail" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{esc(cfg['accent'])}" stop-opacity=".12"/><stop offset=".5" stop-color="{esc(c['accent2'])}" stop-opacity=".34"/><stop offset="1" stop-color="{esc(cfg['accent'])}" stop-opacity=".12"/></linearGradient>
  </defs>
  <rect width="900" height="32" fill="url(#bg)"/>
  <path d="M18 0V32 M882 0V32" stroke="url(#rail)" stroke-width="1.2"/>
  <path d="M18 15H64 M836 15H882" stroke="#dce8e4" stroke-opacity=".07"/>
  {motif(c['motif'], cfg['accent'], c['accent2'])}
  <circle cx="450" cy="16" r="2" fill="{esc(c['accent2'])}" fill-opacity=".30"/>
</svg>'''


def render(season: str) -> Path:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cfg = data["seasons"][season]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"rail-bridge-{season}.svg"
    path.write_text(bridge(cfg) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", choices=["spring", "summer", "autumn", "winter"])
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    seasons = ["spring", "summer", "autumn", "winter"] if args.all else [args.season]
    if not seasons[0]:
        parser.error("provide --season or --all")
    for season in seasons:
        print(render(season).relative_to(LAB))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
