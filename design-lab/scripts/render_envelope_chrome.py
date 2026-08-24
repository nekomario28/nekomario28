#!/usr/bin/env python3
"""Render stable README visual-envelope chrome for one approved season."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent
MANIFEST = LAB / "theme-manifest.json"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def motif_svg(kind: str, accent: str, accent2: str) -> str:
    if kind == "petal":
        return f'''<g fill="{esc(accent)}" opacity=".48">
  <path d="M0,-5 C4,-6 7,-2 5,2 C3,6 -2,7 -5,4 C-7,1 -5,-4 0,-5Z" transform="translate(760 23) rotate(18)"/>
  <path d="M0,-5 C4,-6 7,-2 5,2 C3,6 -2,7 -5,4 C-7,1 -5,-4 0,-5Z" transform="translate(788 17) rotate(-28) scale(.72)"/>
</g>'''
    if kind == "water":
        return f'''<g fill="none" stroke-linecap="round">
  <path d="M704 29 C748 11 796 39 842 20" stroke="{esc(accent)}" stroke-opacity=".34" stroke-width="2"/>
  <path d="M723 35 C764 22 806 42 858 27" stroke="{esc(accent2)}" stroke-opacity=".22" stroke-width="1"/>
</g>'''
    if kind == "leaf":
        return f'''<g fill="{esc(accent)}" opacity=".46">
  <path d="M0,-8 3,-3 8,-5 5,0 10,2 4,4 6,9 1,5 -2,10 -3,5 -9,6 -5,1 -9,-2 -4,-3 -4,-8 0,-4Z" transform="translate(782 23) rotate(16)"/>
  <path d="M0,-8 3,-3 8,-5 5,0 10,2 4,4 6,9 1,5 -2,10 -3,5 -9,6 -5,1 -9,-2 -4,-3 -4,-8 0,-4Z" transform="translate(820 18) rotate(-20) scale(.72)"/>
</g>'''
    if kind == "snow":
        return f'''<g fill="{esc(accent2)}" opacity=".48">
  <circle cx="772" cy="17" r="2"/><circle cx="803" cy="29" r="1.5"/><circle cx="835" cy="16" r="1.2"/>
</g>'''
    raise ValueError(f"unknown motif: {kind}")


def bridge_motif(kind: str, accent: str, accent2: str) -> str:
    if kind == "petal":
        return f'<g fill="{esc(accent)}" fill-opacity=".22"><ellipse cx="430" cy="15" rx="4" ry="2" transform="rotate(-24 430 15)"/><ellipse cx="470" cy="18" rx="3.4" ry="1.8" transform="rotate(28 470 18)"/></g>'
    if kind == "water":
        return f'<path d="M338 22 C390 10 443 27 494 17 C544 8 590 22 637 13" fill="none" stroke="{esc(accent)}" stroke-opacity=".10" stroke-width="1.4"/>'
    if kind == "leaf":
        return f'<g fill="{esc(accent)}" fill-opacity=".22"><path d="M0,-6 2,-2 6,-4 4,0 7,2 3,3 4,7 0,4 -2,8 -2,4 -7,5 -4,1 -7,-2 -3,-2 -3,-6 0,-3Z" transform="translate(450 16) rotate(18)"/></g>'
    if kind == "snow":
        return f'<g fill="{esc(accent2)}" fill-opacity=".25"><circle cx="430" cy="14" r="1.4"/><circle cx="450" cy="19" r="1"/><circle cx="472" cy="13" r="1.2"/></g>'
    raise ValueError(f"unknown motif: {kind}")


def background_defs(bg0: str, bg1: str) -> str:
    return f'''<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{esc(bg0)}"/><stop offset=".52" stop-color="{esc(bg1)}"/><stop offset="1" stop-color="{esc(bg0)}"/></linearGradient></defs>'''


def section_band(cfg: dict, label: str, aria: str) -> str:
    c = cfg["chrome"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="68" viewBox="0 0 900 68" role="img" aria-label="{esc(aria)}">
  {background_defs(c['bg0'], c['bg1'])}
  <rect width="900" height="68" rx="14" fill="url(#bg)"/>
  <path d="M56 34 H318 M582 34 H844" stroke="#eef2f6" stroke-opacity=".10"/>
  <circle cx="336" cy="34" r="2.5" fill="{esc(cfg['accent'])}"/>
  <circle cx="564" cy="34" r="2.5" fill="{esc(c['accent2'])}"/>
  <text x="450" y="41" text-anchor="middle" font-family="'Hiragino Kaku Gothic ProN','Yu Gothic','Noto Sans CJK JP',sans-serif" font-size="22" font-weight="600" letter-spacing="4" fill="#eef1f4">{esc(label)}</text>
  {motif_svg(c['motif'], cfg['accent'], c['accent2'])}
</svg>'''


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
  {bridge_motif(c['motif'], cfg['accent'], c['accent2'])}
  <circle cx="450" cy="16" r="2" fill="{esc(c['accent2'])}" fill-opacity=".30"/>
</svg>'''


def footer(cfg: dict) -> str:
    c = cfg["chrome"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="92" viewBox="0 0 900 92" role="img" aria-label="季節ダークプロフィール終端">
  {background_defs(c['bg0'], c['bg1'])}
  <rect width="900" height="92" rx="16" fill="url(#bg)"/>
  <path d="M0 68 C132 46 236 82 356 63 C482 43 582 77 704 53 C788 37 842 42 900 29" fill="none" stroke="{esc(cfg['accent'])}" stroke-opacity=".08" stroke-width="15"/>
  <path d="M322 46 H420 M480 46 H578" stroke="#eef2f6" stroke-opacity=".14"/>
  <circle cx="450" cy="46" r="3" fill="{esc(cfg['accent'])}"/><circle cx="450" cy="46" r="10" fill="none" stroke="{esc(c['accent2'])}" stroke-opacity=".24"/>
  {motif_svg(c['motif'], cfg['accent'], c['accent2'])}
</svg>'''


def render(season: str, out_root: Path = ROOT) -> list[Path]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cfg = data["seasons"][season]
    assets = data["live_assets"]
    outputs = {
        "bridge": bridge(cfg),
        "projects": section_band(cfg, "プロジェクト", "プロジェクト セクション"),
        "activity": section_band(cfg, "活動", "活動 セクション"),
        "footer": footer(cfg),
    }
    written: list[Path] = []
    for key, content in outputs.items():
        path = out_root / assets[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True, choices=["spring", "summer", "autumn", "winter"])
    args = parser.parse_args()
    for path in render(args.season):
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
