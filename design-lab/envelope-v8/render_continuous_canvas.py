#!/usr/bin/env python3
"""Render Envelope v8 as one visually unified surface on top of the proven v7 motion engine.

Envelope v8 keeps the v7 1662px global coordinate field, source fingerprints, mounted
foreground media, and phase-tolerant cross-document motion. The presentation layer owns
one background grammar and one frame grammar across every physical SVG document:
- one canonical horizontal surface gradient,
- one canonical side rail per edge (no parallel legacy rail),
- crisp outer-end L caps only (no curved frame corners),
- no independent rounded-card borders,
- source-local opaque backgrounds removed from mounted Project Map / Activity content.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V8 = Path(__file__).resolve().parent
V7_RENDERER = ROOT / "design-lab" / "envelope-v7" / "render_continuous_canvas.py"
HOST_DARK = "#0d1117"
SKIN = "unified-v1"


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

X_OFFSET_FOR_KEY = {"character_left": 0, "character_right": 800}


def _clean_output(text: str) -> str:
    """Canonicalize generated SVG whitespace so deterministic diffs stay clean."""
    return "\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n"


def _strip_full_canvas_rounding(text: str, width: int, height: int) -> str:
    """Remove rx/ry only from rects that cover the complete local SVG window."""
    def replace_rect(match: re.Match[str]) -> str:
        tag = match.group(0)
        full_width = f'width="{width}"' in tag or 'width="100%"' in tag
        full_height = f'height="{height}"' in tag or 'height="100%"' in tag
        if not (full_width and full_height):
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


def _remove_root_surface_background(text: str, width: int, height: int) -> str:
    """Remove only the opaque/base full-canvas background; keep decorative full-size overlays."""
    patterns = [
        rf'\s*<rect\b(?=[^>]*\bwidth="{width}")(?=[^>]*\bheight="{height}")(?=[^>]*\bfill="url\(#bg\)")[^>]*/>\s*',
        rf'\s*<rect\b(?=[^>]*\bwidth="{width}")(?=[^>]*\bheight="{height}")(?=[^>]*\bfill="url\(#v7-[^"]*-bg\)")[^>]*/>\s*',
        rf'\s*<rect\b(?=[^>]*\bwidth="100%")(?=[^>]*\bheight="100%")(?=[^>]*\bfill="url\(#bg\)")[^>]*/>\s*',
    ]
    for pattern in patterns:
        text = re.sub(pattern, "\n", text, count=1)
    return text


def _strip_mounted_source_backgrounds(text: str) -> str:
    """Let authoritative mounted data render on the shared envelope surface."""
    text = re.sub(
        r'\s*<rect\b(?=[^>]*\bwidth="100%")(?=[^>]*\bheight="100%")'
        r'(?=[^>]*\bfill="url\(#galaxy-family-bg\)")[^>]*/>\s*',
        "\n",
        text,
        count=1,
    )
    text = re.sub(
        r'\s*<rect\b(?=[^>]*\bwidth="760")(?=[^>]*\bheight="220")'
        r'(?=[^>]*\bfill="#0d1117")[^>]*/>\s*',
        "\n",
        text,
        count=1,
    )
    return text


def _strip_legacy_frame(text: str, *, key: str) -> str:
    """Remove v4/v7 static rails, inner borders, edge ticks and v7 cap paths."""
    def keep_path(match: re.Match[str]) -> str:
        tag = match.group(0)
        dmatch = re.search(r'\bd="([^"]+)"', tag)
        if not dmatch:
            return tag
        d = dmatch.group(1)
        if (
            (d.startswith("M18 ") and "M882 " in d)
            or (d.startswith("M22 ") and "M878 " in d)
            or d.startswith("M18 30V18Q18 ")
            or (d.startswith("M18 ") and "Q18 " in d and "H76 M882 " in d)
        ):
            return ""
        if (d.startswith("M80 0V") and "M820 " in d) or (d.startswith("M70 0V") and "M830 " in d):
            return ""
        if d.startswith("M18 7H58 ") and "M842 7H882" in d:
            return ""
        if key == "character_left" and d in {"M18 0V394", "M22 0V394", "M99 0V394"}:
            return ""
        if key == "character_right" and d in {"M82 0V394", "M78 0V394", "M1 0V394"}:
            return ""
        return tag

    return re.sub(r'<path\b[^>]*?/?>', keep_path, text)


def _surface_defs(cfg: dict, *, width: int, global_x_offset: int, prefix: str) -> str:
    """One horizontal palette sampled in common 900px X coordinates."""
    c = cfg["chrome"]
    x1 = -global_x_offset
    x2 = 900 - global_x_offset
    return f'''<defs id="{prefix}-surface-defs">
  <linearGradient id="{prefix}-surface" gradientUnits="userSpaceOnUse" x1="{x1}" y1="0" x2="{x2}" y2="0">
    <stop offset="0" stop-color="{HOST_DARK}"/>
    <stop offset=".08" stop-color="{c['bg0']}"/>
    <stop offset=".24" stop-color="{c['bg1']}"/>
    <stop offset=".50" stop-color="{c['bg0']}"/>
    <stop offset=".76" stop-color="{c['bg1']}"/>
    <stop offset=".92" stop-color="{c['bg0']}"/>
    <stop offset="1" stop-color="{HOST_DARK}"/>
  </linearGradient>
</defs>
<rect id="{prefix}-surface-base" width="{width}" height="100%" fill="url(#{prefix}-surface)"/>'''


def _frame_path(width: int, height: int, *, global_x_offset: int, top_cap: bool, bottom_cap: bool) -> str:
    """Return one crisp frame path for this document; no curved/parallel duplicate rail."""
    if width == 900 and global_x_offset == 0:
        lx, rx = 18, 882
        if top_cap:
            return f"M{lx} {height}V8H72 M{rx} {height}V8H828"
        if bottom_cap:
            y = height - 8
            return f"M{lx} 0V{y}H72 M{rx} 0V{y}H828"
        return f"M{lx} 0V{height} M{rx} 0V{height}"
    rail_global = 18 if global_x_offset == 0 else 882
    rail_local = rail_global - global_x_offset
    return f"M{rail_local} 0V{height}"


def _frame_layer(
    cfg: dict,
    *,
    width: int,
    height: int,
    global_x_offset: int = 0,
    top_cap: bool = False,
    bottom_cap: bool = False,
) -> str:
    d = _frame_path(
        width,
        height,
        global_x_offset=global_x_offset,
        top_cap=top_cap,
        bottom_cap=bottom_cap,
    )
    return (
        f'<g id="v8-frame" data-frame-grammar="{SKIN}" fill="none">'
        f'<path d="{d}" stroke="{cfg["accent"]}" stroke-opacity=".22" stroke-width="1.2"/>'
        "</g>"
    )


def _insert_after_root_open(text: str, markup: str) -> str:
    return re.sub(r'(<svg\b[^>]*>)', lambda m: m.group(1) + "\n" + markup, text, count=1)


def _insert_before_root_close(text: str, markup: str) -> str:
    head, closing, tail = text.rpartition("</svg>")
    if not closing or tail.strip():
        raise ValueError("root closing svg tag must be the final element")
    return head + "\n" + markup + "\n</svg>" + tail


def unified_surface(
    text: str,
    *,
    key: str,
    cfg: dict,
    width: int,
    height: int,
    global_x_offset: int,
    top_cap: bool,
    bottom_cap: bool,
) -> str:
    text = _strip_full_canvas_rounding(text, width, height)
    if key == "hero":
        text = _remove_hero_card_border(text, width, height)
    text = _remove_root_surface_background(text, width, height)
    if key in {"projects_canvas", "activity_canvas"}:
        text = _strip_mounted_source_backgrounds(text)
    text = _strip_legacy_frame(text, key=key)

    if 'data-envelope-presentation="v8-seamless-surface"' not in text:
        text, count = re.subn(
            r'<svg\b',
            '<svg data-envelope-presentation="v8-seamless-surface"',
            text,
            count=1,
        )
        if count != 1:
            raise ValueError(f"unable to mark Envelope v8 root for {key}")
    if f'data-envelope-skin="{SKIN}"' not in text:
        text = re.sub(r'<svg\b', f'<svg data-envelope-skin="{SKIN}"', text, count=1)

    surface = _surface_defs(cfg, width=width, global_x_offset=global_x_offset, prefix=f"v8-{key}")
    text = _insert_after_root_open(text, surface)
    frame = _frame_layer(
        cfg,
        width=width,
        height=height,
        global_x_offset=global_x_offset,
        top_cap=top_cap,
        bottom_cap=bottom_cap,
    )
    text = _insert_before_root_close(text, frame)
    return text


def _body(text: str) -> str:
    match = re.search(r'<svg\b[^>]*>(.*)</svg>\s*$', text, flags=re.S)
    if not match:
        raise ValueError("unable to extract SVG body")
    return match.group(1).strip()


def _namespace_defs(text: str, prefix: str) -> str:
    """Namespace common ids in nested legacy components before composition."""
    ids = re.findall(r'\bid="([^"]+)"', text)
    for old in dict.fromkeys(ids):
        if old in {"v7-window", "v7-global-window", "v8-frame"}:
            continue
        new = f"{prefix}-{old}"
        text = text.replace(f'id="{old}"', f'id="{new}"')
        text = text.replace(f'url(#{old})', f'url(#{new})')
        text = text.replace(f'href="#{old}"', f'href="#{new}"')
    return text


def _component_content(
    text: str,
    *,
    key: str,
    prefix: str,
    y: int,
    width: int,
    height: int,
) -> str:
    text = _strip_full_canvas_rounding(text, width, height)
    text = _remove_root_surface_background(text, width, height)
    text = _strip_legacy_frame(text, key=key)
    text = _namespace_defs(text, prefix)
    return f'<svg x="0" y="{y}" width="{width}" height="{height}" viewBox="0 0 {width} {height}">{_body(text)}</svg>'


def _combined_motion_layer(
    *,
    name: str,
    start: int,
    end: int,
    space: dict,
    accent: str,
    accent2: str,
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
    return f'''<defs><clipPath id="v7-window"><rect x="0" y="0" width="900" height="{height}"/></clipPath></defs>
<style>@media (prefers-reduced-motion: reduce) {{ .v7-motion {{ display:none }} }}</style>
<g id="v7-global-window" data-window="{name}" data-global-start="{start}" data-global-end="{end}" data-global-extent="{extent}" data-global-x-offset="0" pointer-events="none">
  <g class="v7-motion" clip-path="url(#v7-window)">
    {particles}
  </g>
</g>'''


def _composite(
    *,
    name: str,
    start: int,
    end: int,
    components: list[tuple[str, str, int, int]],
    cfg: dict,
    space: dict,
    bottom_cap: bool = False,
) -> str:
    height = end - start
    body = "\n  ".join(
        _component_content(
            text,
            key=key,
            prefix=f"v8-{name}-{index}",
            y=y,
            width=900,
            height=component_height,
        )
        for index, (key, text, y, component_height) in enumerate(components)
    )
    surface = _surface_defs(cfg, width=900, global_x_offset=0, prefix=f"v8-{name}")
    motion = _combined_motion_layer(
        name=name,
        start=start,
        end=end,
        space=space,
        accent=cfg["accent"],
        accent2=cfg["chrome"]["accent2"],
    )
    frame = _frame_layer(cfg, width=900, height=height, top_cap=False, bottom_cap=bottom_cap)
    return f'''<svg data-envelope-skin="{SKIN}" data-envelope-presentation="v8-seamless-surface" xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}" role="img" aria-label="Envelope v8 unified profile transition">
  {surface}
  {body}
  {motion}
  {frame}
</svg>'''


def _render_presentation_composites(season: str, out_root: Path) -> None:
    manifest = _V7.load_json(_V7.MANIFEST)
    space = _V7.load_json(_V7.SPACE)
    cfg = manifest["seasons"][season]
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
            components=[
                ("attribution", attribution, 0, 44),
                ("bridge_character_projects", bridge1, 44, 32),
            ],
            cfg=cfg,
            space=space,
        ),
        "activity_header": _composite(
            name="activity-header",
            start=1218,
            end=1318,
            components=[
                ("bridge_projects_activity", bridge2, 0, 32),
                ("activity", activity, 32, 68),
            ],
            cfg=cfg,
            space=space,
        ),
        "footer_transition": _composite(
            name="footer-transition",
            start=1538,
            end=1662,
            components=[
                ("bridge_activity_footer", bridge3, 0, 32),
                ("footer", footer, 32, 92),
            ],
            cfg=cfg,
            space=space,
            bottom_cap=True,
        ),
    }
    for key, text in composites.items():
        path = out_root / PRESENTATION_ASSETS[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_clean_output(text), encoding="utf-8")


def render(season: str, out_root: Path = ROOT) -> list[Path]:
    written = _V7.render(season, out_root)
    manifest = _V7.load_json(_V7.MANIFEST)
    cfg = manifest["seasons"][season]

    for key, rel in LIVE_ASSETS.items():
        path = out_root / rel
        text = path.read_text(encoding="utf-8")
        match = re.search(r'<svg\b[^>]*\bwidth="(\d+)"[^>]*\bheight="(\d+)"', text)
        if not match:
            raise ValueError(f"unable to read root geometry for {key}")
        width, height = map(int, match.groups())
        global_x_offset = X_OFFSET_FOR_KEY.get(key, 0)
        text = unified_surface(
            text,
            key=key,
            cfg=cfg,
            width=width,
            height=height,
            global_x_offset=global_x_offset,
            top_cap=(key == "hero"),
            bottom_cap=(key == "footer"),
        )
        path.write_text(_clean_output(text), encoding="utf-8")

    _render_presentation_composites(season, out_root)
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
