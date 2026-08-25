#!/usr/bin/env python3
"""Portable GitHub-profile SVG bundle transformer for Envelope v9.

The transformer consumes a complete pre-rendered SVG bundle plus three bounded
input markers. It does not know how donor artwork is produced and contains no
Envelope v7/v8 or Project Map implementation knowledge.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load_local_vector_text():
    try:
        from profile_envelope import vector_text  # type: ignore
        return vector_text
    except ImportError:
        path = HERE / "vector_text.py"
        spec = importlib.util.spec_from_file_location("profile_envelope_vector_text", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


VECTOR = _load_local_vector_text()

ASSET_PATHS = (
    "assets/profile-activity-canvas.svg",
    "assets/profile-activity-header.svg",
    "assets/profile-attribution-projects-transition.svg",
    "assets/profile-attribution.svg",
    "assets/profile-character-side-left.svg",
    "assets/profile-character-side-right.svg",
    "assets/profile-footer-transition.svg",
    "assets/profile-footer.svg",
    "assets/profile-frame-bridge-activity-footer.svg",
    "assets/profile-frame-bridge-character-projects.svg",
    "assets/profile-frame-bridge-projects-activity.svg",
    "assets/profile-hero.svg",
    "assets/profile-projects-canvas.svg",
    "assets/profile-section-activity.svg",
    "assets/profile-section-projects.svg",
)

DYNAMIC_VISIBLE_TEXT = {
    "assets/profile-projects-canvas.svg",
    "assets/profile-activity-canvas.svg",
}

SURFACE_MARKER = 'data-profile-envelope-surface-base="outer"'
FRAME_MARKER = 'data-profile-envelope-frame="rail"'
MOUNTED_BACKGROUND_MARKER = 'data-profile-envelope-mounted-background="presentation"'
_INTERNAL_MARKER_RE = re.compile(
    r'\sdata-profile-envelope-(?:surface-base|frame|mounted-background)="[^"]*"'
)

ADAPTIVE_TEXT_STYLE = """<style data-v9-adaptive-vector-text-style=\"v1\">
.v9-adaptive-vector-text { color: #f0f6fc; }
@media (prefers-color-scheme: light) { .v9-adaptive-vector-text { color: #1f2328; } }
@media (prefers-color-scheme: dark) { .v9-adaptive-vector-text { color: #f0f6fc; } }
</style>"""


def asset_paths() -> list[str]:
    return list(ASSET_PATHS)


def _clean_output(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n"


def _strip_marked_empty_element(svg: str, marker: str) -> str:
    name, value = marker.split("=", 1)
    value = value.strip('"')
    pattern = rf'\s*<rect\b(?=[^>]*\b{re.escape(name)}="{re.escape(value)}")[^>]*/>\s*'
    return re.sub(pattern, "\n", svg)


def _strip_mounted_source_backgrounds(svg: str) -> str:
    return _strip_marked_empty_element(svg, MOUNTED_BACKGROUND_MARKER)


def _strip_surface_base(svg: str) -> str:
    return _strip_marked_empty_element(svg, SURFACE_MARKER)


def _frame_pattern() -> str:
    return r'<g\b(?=[^>]*\bdata-profile-envelope-frame="rail")[^>]*>.*?</g>'


def _strip_frame(svg: str) -> str:
    return re.sub(r'\s*' + _frame_pattern() + r'\s*', "\n", svg, flags=re.S)


def _through_rails(svg: str, *, rel: str) -> str:
    width_match = re.search(r'<svg\b[^>]*\bwidth="(\d+)"', svg)
    height_match = re.search(r'<svg\b[^>]*\bheight="(\d+)"', svg)
    if not width_match or not height_match:
        raise ValueError(f"unable to resolve frame geometry for {rel}")
    width = int(width_match.group(1))
    height = int(height_match.group(1))
    if width == 900:
        d = f"M18 0V{height} M882 0V{height}"
    elif rel.endswith("profile-character-side-left.svg"):
        d = f"M18 0V{height}"
    elif rel.endswith("profile-character-side-right.svg"):
        d = f"M82 0V{height}"
    else:
        return svg

    def rewrite(match: re.Match[str]) -> str:
        group = match.group(0)
        return re.sub(r'(<path\b[^>]*\bd=")[^"]+("[^>]*?/?>)', rf'\1{d}\2', group, count=1)

    return re.sub(_frame_pattern(), rewrite, svg, flags=re.S)


def _disable_motion(svg: str) -> str:
    svg = re.sub(r'\s*<animate(?:Transform|Motion)?\b[^>]*/>\s*', "\n", svg, flags=re.I)
    return re.sub(r'\s*<set\b[^>]*/>\s*', "\n", svg, flags=re.I)


def _insert_after_root_open(svg: str, markup: str) -> str:
    return re.sub(r'(<svg\b[^>]*>)', lambda match: match.group(1) + "\n" + markup, svg, count=1)


def _add_adaptive_text_style(svg: str) -> str:
    if 'data-v9-adaptive-vector-text-style="v1"' in svg:
        return svg
    return _insert_after_root_open(svg, ADAPTIVE_TEXT_STYLE)


def _mark_root_base(svg: str, *, contract: dict, resolved: dict) -> str:
    contract_fingerprint = resolved["normalized_contract_sha256"]
    profile = contract["profile"]
    surface = contract["surface"]
    font_independent = "true" if profile["text"] in {"safe", "minimal"} else "false"
    attrs = (
        'data-envelope-presentation="v9-portable-surface" '
        f'data-profile-contract-sha256="{contract_fingerprint}" '
        f'data-profile-background="{profile["background"]}" '
        f'data-profile-text="{profile["text"]}" '
        f'data-profile-motion="{profile["motion"]}" '
        f'data-mounted-source-background="{surface["mounted_source_background"]}" '
        f'data-host-font-independent="{font_independent}"'
    )
    svg = re.sub(r'\sdata-envelope-presentation="[^"]*"', "", svg, count=1)
    svg = re.sub(r'\sdata-profile-render-target-sha256="[^"]*"', "", svg, count=1)
    return re.sub(r'<svg\b', f'<svg {attrs}', svg, count=1)


def _render_target_fingerprint(rendered: dict[str, str], *, contract_sha256: str, season: str) -> str:
    payload = {
        "contract_sha256": contract_sha256,
        "season": season,
        "assets": {
            rel: hashlib.sha256(svg.encode("utf-8")).hexdigest()
            for rel, svg in sorted(rendered.items())
        },
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _add_render_target_marker(svg: str, fingerprint: str) -> str:
    return re.sub(r'<svg\b', f'<svg data-profile-render-target-sha256="{fingerprint}"', svg, count=1)


def _apply_text(svg: str, *, rel: str, contract: dict) -> str:
    text_mode = contract["profile"]["text"]
    density = contract["labels"]["density"]
    suppress_dynamic = rel in DYNAMIC_VISIBLE_TEXT and (text_mode == "minimal" or density == "minimal")
    if suppress_dynamic:
        svg, _ = VECTOR.suppress_visible_text(svg)
        return svg
    if text_mode in {"safe", "minimal"}:
        adaptive = contract["profile"]["background"] == "transparent"
        svg, count = VECTOR.vectorize_visible_text(svg, adaptive=adaptive)
        if adaptive and count:
            svg = _add_adaptive_text_style(svg)
    return svg


def _drop_internal_markers(svg: str) -> str:
    return _INTERNAL_MARKER_RE.sub("", svg)


def transform_bundle(
    input_root: Path,
    output_root: Path,
    *,
    contract: dict,
    resolved: dict,
    season: str,
) -> dict:
    """Apply portable policy to a complete marked donor bundle."""
    resolved_out = dict(resolved)
    source: dict[str, str] = {}
    for rel in ASSET_PATHS:
        path = input_root / rel
        if not path.is_file():
            raise FileNotFoundError(f"missing donor bundle asset: {rel}")
        source[rel] = path.read_text(encoding="utf-8")

    rendered: dict[str, str] = {}
    for rel, svg in source.items():
        if contract["surface"]["mounted_source_background"] == "inherit" and rel in DYNAMIC_VISIBLE_TEXT:
            svg = _strip_mounted_source_backgrounds(svg)
        if contract["profile"]["background"] == "transparent":
            svg = _strip_surface_base(svg)
        if contract["frame"]["mode"] == "none":
            svg = _strip_frame(svg)
        elif contract["frame"]["caps"] == "none":
            svg = _through_rails(svg, rel=rel)
        if contract["profile"]["motion"] == "off":
            svg = _disable_motion(svg)
        svg = _apply_text(svg, rel=rel, contract=contract)
        svg = _drop_internal_markers(svg)
        svg = _mark_root_base(svg, contract=contract, resolved=resolved_out)
        rendered[rel] = _clean_output(svg)

    render_target = _render_target_fingerprint(
        rendered,
        contract_sha256=resolved_out["normalized_contract_sha256"],
        season=season,
    )
    resolved_out["render_target_sha256"] = render_target

    for rel, svg in rendered.items():
        path = output_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_clean_output(_add_render_target_marker(svg, render_target)), encoding="utf-8")

    return resolved_out
