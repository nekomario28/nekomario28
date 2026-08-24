#!/usr/bin/env python3
"""Render Envelope v7 full-width stages from authoritative checked-in SVG sources.

Repository-owned source SVG bodies are copied into a nested same-document viewport inside
a 900px stage. Side/background chrome is derived from the approved seasonal manifest.
The generator deliberately does not copy or nest the third-party character image.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent
MANIFEST = ROOT / "design-lab" / "theme-manifest.json"
HOST_DARK = "#0d1117"


def svg_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"<svg\b[^>]*>(.*)</svg>\s*$", text, flags=re.S)
    if not match:
        raise ValueError(f"unable to extract SVG body: {path}")
    return match.group(1).strip()


def season_config(season: str) -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cfg = data["seasons"][season]
    if not cfg.get("auto_promote") or cfg.get("static_render") != "PASS":
        raise ValueError(f"season is not approved for v7 rendering: {season}")
    return cfg


def rails(height: int, accent: str, accent2: str) -> str:
    return (
        f'<path d="M18 0V{height} M882 0V{height}" fill="none" stroke="{accent}" '
        'stroke-opacity=".18" stroke-width="1.6"/>'
        f'<path d="M22 0V{height} M878 0V{height}" fill="none" stroke="{accent2}" '
        'stroke-opacity=".08" stroke-width=".7"/>'
    )


def projects_panel(cfg: dict) -> str:
    inner = svg_body(ROOT / "project-map" / "galaxy.svg")
    accent = cfg["accent"]
    c = cfg["chrome"]
    bg0 = c["bg0"]
    accent2 = c["accent2"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420" role="img" aria-label="nekomario28 の公開プロジェクトマップを背景surface上に配置した projects stage">
  <defs><linearGradient id="v7-projects-bg" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{HOST_DARK}"/><stop offset=".11" stop-color="{bg0}"/><stop offset=".18" stop-color="#070a12"/><stop offset=".82" stop-color="#070a12"/><stop offset=".89" stop-color="{bg0}"/><stop offset="1" stop-color="{HOST_DARK}"/></linearGradient></defs>
  <rect width="900" height="420" fill="url(#v7-projects-bg)"/>
  <g fill="#e8edf7"><circle cx="36" cy="54" r="1" opacity=".22"/><circle cx="62" cy="114" r=".7" opacity=".18"/><circle cx="44" cy="220" r="1.1" opacity=".15"/><circle cx="858" cy="78" r=".8" opacity=".20"/><circle cx="838" cy="188" r="1.1" opacity=".16"/><circle cx="864" cy="328" r=".7" opacity=".19"/></g>
  <svg x="80" y="0" width="740" height="420" viewBox="0 0 740 420">{inner}</svg>
  <path d="M80 0V420 M820 0V420" stroke="#eef2f6" stroke-opacity=".08"/>
  {rails(420, accent, accent2)}
</svg>'''


def activity_panel(cfg: dict) -> str:
    inner = svg_body(ROOT / "assets" / "github-contributions-dark.svg")
    accent = cfg["accent"]
    c = cfg["chrome"]
    bg0 = c["bg0"]
    accent2 = c["accent2"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="220" viewBox="0 0 900 220" role="img" aria-label="直近31日間の GitHub コントリビューションを背景surface上に配置した activity stage">
  <defs><linearGradient id="v7-activity-bg" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{HOST_DARK}"/><stop offset=".12" stop-color="{bg0}"/><stop offset=".18" stop-color="{HOST_DARK}"/><stop offset=".82" stop-color="{HOST_DARK}"/><stop offset=".88" stop-color="{bg0}"/><stop offset="1" stop-color="{HOST_DARK}"/></linearGradient></defs>
  <rect width="900" height="220" fill="url(#v7-activity-bg)"/>
  <g opacity=".10" fill="{accent}"><rect x="32" y="184" width="5" height="12" rx="1"/><rect x="44" y="176" width="5" height="20" rx="1"/><rect x="56" y="188" width="5" height="8" rx="1"/><rect x="839" y="180" width="5" height="16" rx="1"/><rect x="851" y="172" width="5" height="24" rx="1"/><rect x="863" y="186" width="5" height="10" rx="1"/></g>
  <svg x="70" y="0" width="760" height="220" viewBox="0 0 760 220">{inner}</svg>
  <path d="M70 0V220 M830 0V220" stroke="#eef2f6" stroke-opacity=".08"/>
  {rails(220, accent, accent2)}
</svg>'''


def render(season: str, out_root: Path = LAB) -> list[Path]:
    cfg = season_config(season)
    outputs = {
        out_root / "projects-panel.svg": projects_panel(cfg),
        out_root / "activity-panel.svg": activity_panel(cfg),
    }
    written: list[Path] = []
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", choices=["spring", "summer", "autumn", "winter"], default="summer")
    parser.add_argument("--out-root", type=Path, default=LAB)
    args = parser.parse_args()
    for path in render(args.season, args.out_root):
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
