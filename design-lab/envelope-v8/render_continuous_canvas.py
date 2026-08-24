#!/usr/bin/env python3
"""Render Envelope v8 presentation on top of the proven v7 motion engine.

Envelope v8 keeps the v7 1662px global coordinate field, source fingerprints, mounted
foreground media, and phase-tolerant cross-document motion. It changes presentation
only: intermediate windows are one rectangular surface rather than independent rounded
cards, the name hero no longer carries its own inset card border, and short logical
windows are packed into taller physical SVG documents so GitHub's README line-height
cannot reopen seams after responsive scaling.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V8 = Path(__file__).resolve().parent
V7_RENDERER = ROOT / "design-lab" / "envelope-v7" / "render_continuous_canvas.py"


def load_v7():
    spec = importlib.util.spec_from_file_location("envelope_v7_renderer", V7_RENDERER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Envelope v7 renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_V7 = load_v7()
LIVE_ASSETS = _V7.LIVE_ASSETS
PRESENTATION_ASSETS = {
    "hero": LIVE_ASSETS["hero"],
    "character_left": LIVE_ASSETS["character_left"],
    "character_right": LIVE_ASSETS["character_right"],
    "attribution_projects_transition": "assets/profile-attribution-projects-transition.svg",
    "projects": LIVE_ASSETS["projects"],
    "projects_canvas": LIVE_ASSETS["projects_canvas"],
    "activity_header": "assets/profile-activity-header.svg",
    "activity_canvas": LIVE_ASSETS["activity_canvas"],
    "footer_transition": "assets/profile-footer-transition.svg",
}
validate_space = _V7.validate_space


def _strip_full_canvas_rounding(text: str, width: int, height: int) -> str:
    """Remove rx/ry only from rects that cover the complete local SVG window."""
    def replace_rect(match: re.Match[str]) -> str:
        tag = match.group(0)
        if f'width="{width}"' not in tag or f'height="{height}"' not in tag:
            return tag
        tag = re.sub(r'\s+rx="[^"]*"', "", tag)
        tag = re.sub(r'\s+ry="[^"]*"', "", tag)
        return tag

    return re.sub(r'<rect\b[^>]*>', replace_rect, text)


def _remove_hero_card_border(text: str, width: int, height: int) -> str:
    inset_w = width - 1
    inset_h = height - 1
    pattern = re.compile(
        rf'\s*<rect\b(?=[^>]*\bx="\.5")(?=[^>]*\by="\.5")'
        rf'(?=[^>]*\bwidth="{inset_w}")(?=[^>]*\bheight="{inset_h}")'
        rf'(?=[^>]*\bfill="none")[^>]*/>\s*'
    )
    return pattern.sub("\n", text)


def seamless_surface(text: str, *, key: str, width: int, height: int) -> str:
    text = _strip_full_canvas_rounding(text, width, height)
    if key == "hero":
        text = _remove_hero_card_border(text, width, height)
    if 'data-envelope-presentation="v8-seamless-surface"' not in text:
        text, count = re.subn(
            r'<svg\b',
            '<svg data-envelope-presentation="v8-seamless-surface"',
            text,
            count=1,
        )
        if count != 1:
            raise ValueError(f"unable to mark Envelope v8 root for {key}")
    return text


def _body(text: str) -> str:
    match = re.search(r'<svg\b[^>]*>(.*)</svg>\s*$', text, flags=re.S)
    if not match:
        raise ValueError("unable to extract SVG body")
    return match.group(1).strip()


def _namespace_bg(text: str, prefix: str) -> str:
    return text.replace('id="bg"', f'id="{prefix}-bg"').replace('url(#bg)', f'url(#{prefix}-bg)')


def _nested_component(text: str, *, prefix: str, y: int, width: int, height: int) -> str:
    text = _strip_full_canvas_rounding(text, width, height)
    text = _namespace_bg(text, prefix)
    return (
        f'<svg x="0" y="{y}" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'{_body(text)}</svg>'
    )


def _combined_motion_layer(
    *,
    name: str,
    start: int,
    end: int,
    space: dict,
    accent: str,
    accent2: str,
    bottom_cap: bool = False,
) -> str:
    height = end - start
    extent = int(space["global_extent"])
    bleed = int(space["bleed"])
    duration = float(space["duration_seconds"])
    rails = list(space["rail_x"])
    particles = "\n    ".join(
        _V7.particle_markup(
            particle,
            window_start=start,
            global_extent=extent,
            bleed=bleed,
            duration=duration,
            global_rail_x=rails,
            global_x_offset=0,
            allowed_rails={"left", "right"},
            accent=accent,
            accent2=accent2,
        )
        for particle in space["particles"]
    )
    caps = _V7.cap_markup(900, height, accent, accent2, top=False, bottom=bottom_cap)
    return f'''<defs><clipPath id="v7-window"><rect x="0" y="0" width="900" height="{height}"/></clipPath></defs>
<style>@media (prefers-reduced-motion: reduce) {{ .v7-motion {{ display:none }} }}</style>
<g id="v7-global-window" data-window="{name}" data-global-start="{start}" data-global-end="{end}" data-global-extent="{extent}" data-global-x-offset="0" pointer-events="none">
  {caps}
  <g class="v7-motion" clip-path="url(#v7-window)">
    {particles}
  </g>
</g>'''


def _composite(
    *,
    name: str,
    start: int,
    end: int,
    components: list[tuple[str, int, int]],
    space: dict,
    accent: str,
    accent2: str,
    bottom_cap: bool = False,
) -> str:
    height = end - start
    body = "\n  ".join(
        _nested_component(text, prefix=f"v8-{name}-{index}", y=y, width=900, height=component_height)
        for index, (text, y, component_height) in enumerate(components)
    )
    motion = _combined_motion_layer(
        name=name,
        start=start,
        end=end,
        space=space,
        accent=accent,
        accent2=accent2,
        bottom_cap=bottom_cap,
    )
    return f'''<svg data-envelope-presentation="v8-seamless-surface" xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}" role="img" aria-label="Envelope v8 seamless profile transition">
  {body}
  {motion}
</svg>'''


def _render_presentation_composites(season: str, out_root: Path) -> None:
    manifest = _V7.load_json(_V7.MANIFEST)
    space = _V7.load_json(_V7.SPACE)
    cfg = manifest["seasons"][season]
    accent = cfg["accent"]
    accent2 = cfg["chrome"]["accent2"]
    base = _V7.load_module("v8_base_chrome", _V7.BASE_RENDERER)

    attribution = _V7.attribution_base(cfg)
    bridge1 = base.frame_bridge(cfg)
    bridge2 = base.frame_bridge(cfg)
    activity = base.section_band(cfg, "活動", "活動 セクション")
    bridge3 = base.frame_bridge(cfg)
    footer = base.footer(cfg)

    composites = {
        "attribution_projects_transition": _composite(
            name="attribution-projects-transition",
            start=654,
            end=730,
            components=[(attribution, 0, 44), (bridge1, 44, 32)],
            space=space,
            accent=accent,
            accent2=accent2,
        ),
        "activity_header": _composite(
            name="activity-header",
            start=1218,
            end=1318,
            components=[(bridge2, 0, 32), (activity, 32, 68)],
            space=space,
            accent=accent,
            accent2=accent2,
        ),
        "footer_transition": _composite(
            name="footer-transition",
            start=1538,
            end=1662,
            components=[(bridge3, 0, 32), (footer, 32, 92)],
            space=space,
            accent=accent,
            accent2=accent2,
            bottom_cap=True,
        ),
    }
    for key, text in composites.items():
        path = out_root / PRESENTATION_ASSETS[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")


def render(season: str, out_root: Path = ROOT) -> list[Path]:
    written = _V7.render(season, out_root)
    for key, rel in LIVE_ASSETS.items():
        path = out_root / rel
        text = path.read_text(encoding="utf-8")
        match = re.search(r'<svg\b[^>]*\bwidth="(\d+)"[^>]*\bheight="(\d+)"', text)
        if not match:
            raise ValueError(f"unable to read root geometry for {key}")
        width, height = map(int, match.groups())
        text = seamless_surface(text, key=key, width=width, height=height)
        path.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
    _render_presentation_composites(season, out_root)
    # Preserve the v7 renderer's 12-asset return contract for inherited source/motion validation.
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True, choices=["spring", "summer", "autumn", "winter"])
    parser.add_argument("--out-root", type=Path, default=ROOT)
    args = parser.parse_args()
    render(args.season, args.out_root)
    for rel in dict.fromkeys([*LIVE_ASSETS.values(), *PRESENTATION_ASSETS.values()]):
        print(args.out_root / rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
