#!/usr/bin/env python3
"""Render Envelope v7 full-width stages from authoritative checked-in SVG sources.

The source SVG body is copied into a nested SVG viewport inside a 900px stage so GitHub
only has to load one responsive image per row. This avoids both multi-<img> wrapping and
nested external SVG subresource loading.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent


def svg_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"<svg\b[^>]*>(.*)</svg>\s*$", text, flags=re.S)
    if not match:
        raise ValueError(f"unable to extract SVG body: {path}")
    return match.group(1).strip()


def rails(height: int) -> str:
    return (
        f'<path d="M18 0V{height} M882 0V{height}" fill="none" stroke="#86aa94" '
        'stroke-opacity=".18" stroke-width="1.6"/>'
        f'<path d="M22 0V{height} M878 0V{height}" fill="none" stroke="#c7b06c" '
        'stroke-opacity=".08" stroke-width=".7"/>'
    )


def projects_panel() -> str:
    inner = svg_body(ROOT / "project-map" / "galaxy.svg")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420" role="img" aria-label="nekomario28 の公開プロジェクトマップを背景surface上に配置した projects stage">
  <defs><linearGradient id="v7-projects-bg" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#0d1117"/><stop offset=".11" stop-color="#06101a"/><stop offset=".18" stop-color="#070a12"/><stop offset=".82" stop-color="#070a12"/><stop offset=".89" stop-color="#06101a"/><stop offset="1" stop-color="#0d1117"/></linearGradient></defs>
  <rect width="900" height="420" fill="url(#v7-projects-bg)"/>
  <g fill="#e8edf7"><circle cx="36" cy="54" r="1" opacity=".22"/><circle cx="62" cy="114" r=".7" opacity=".18"/><circle cx="44" cy="220" r="1.1" opacity=".15"/><circle cx="858" cy="78" r=".8" opacity=".20"/><circle cx="838" cy="188" r="1.1" opacity=".16"/><circle cx="864" cy="328" r=".7" opacity=".19"/></g>
  <svg x="80" y="0" width="740" height="420" viewBox="0 0 740 420">{inner}</svg>
  <path d="M80 0V420 M820 0V420" stroke="#eef2f6" stroke-opacity=".08"/>
  {rails(420)}
</svg>'''


def activity_panel() -> str:
    inner = svg_body(ROOT / "assets" / "github-contributions-dark.svg")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="220" viewBox="0 0 900 220" role="img" aria-label="直近31日間の GitHub コントリビューションを背景surface上に配置した activity stage">
  <defs><linearGradient id="v7-activity-bg" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#0d1117"/><stop offset=".12" stop-color="#06101a"/><stop offset=".18" stop-color="#0d1117"/><stop offset=".82" stop-color="#0d1117"/><stop offset=".88" stop-color="#06101a"/><stop offset="1" stop-color="#0d1117"/></linearGradient></defs>
  <rect width="900" height="220" fill="url(#v7-activity-bg)"/>
  <g opacity=".10" fill="#86aa94"><rect x="32" y="184" width="5" height="12" rx="1"/><rect x="44" y="176" width="5" height="20" rx="1"/><rect x="56" y="188" width="5" height="8" rx="1"/><rect x="839" y="180" width="5" height="16" rx="1"/><rect x="851" y="172" width="5" height="24" rx="1"/><rect x="863" y="186" width="5" height="10" rx="1"/></g>
  <svg x="70" y="0" width="760" height="220" viewBox="0 0 760 220">{inner}</svg>
  <path d="M70 0V220 M830 0V220" stroke="#eef2f6" stroke-opacity=".08"/>
  {rails(220)}
</svg>'''


def main() -> int:
    outputs = {
        LAB / "projects-panel.svg": projects_panel(),
        LAB / "activity-panel.svg": activity_panel(),
    }
    for path, content in outputs.items():
        path.write_text(content + "\n", encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
