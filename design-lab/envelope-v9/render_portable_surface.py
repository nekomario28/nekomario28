#!/usr/bin/env python3
"""Envelope v9 donor renderer: portable policy over the frozen v8 visual/motion donor.

v9 is Design-Lab-only. It consumes the normalized portable contract and applies
text/background/frame/motion policy without changing the live direct-IPM profile.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
V8_PATH = ROOT / "design-lab" / "envelope-v8" / "render_continuous_canvas.py"
CONTRACT_PATH = ROOT / "design-lab" / "scripts" / "profile_envelope_contract.py"
VECTOR_PATH = HERE / "vector_text.py"

ADAPTIVE_TEXT_STYLE = """<style data-v9-adaptive-vector-text-style=\"v1\">
.v9-adaptive-vector-text { color: #f0f6fc; }
@media (prefers-color-scheme: light) { .v9-adaptive-vector-text { color: #1f2328; } }
@media (prefers-color-scheme: dark) { .v9-adaptive-vector-text { color: #f0f6fc; } }
</style>"""


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V8 = _load("envelope_v8_renderer", V8_PATH)
CONTRACT = _load("profile_envelope_contract", CONTRACT_PATH)
VECTOR = _load("envelope_v9_vector_text", VECTOR_PATH)

DYNAMIC_VISIBLE_TEXT = {
    "assets/profile-projects-canvas.svg",
    "assets/profile-activity-canvas.svg",
}


def asset_paths() -> list[str]:
    paths = set(V8.LIVE_ASSETS.values()) | set(V8.PRESENTATION_ASSETS.values())
    return sorted(paths)


def _clean_output(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n"


def _strip_surface_base(svg: str) -> str:
    return re.sub(
        r'\s*<rect\b(?=[^>]*\bid="v8-[^"]+-surface-base")[^>]*/>\s*',
        "\n",
        svg,
    )


def _strip_frame(svg: str) -> str:
    return re.sub(r'\s*<g\b[^>]*\bid="v8-frame"[^>]*>.*?</g>\s*', "\n", svg, flags=re.S)


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

    return re.sub(r'<g\b[^>]*\bid="v8-frame"[^>]*>.*?</g>', rewrite, svg, flags=re.S)


def _disable_motion(svg: str) -> str:
    svg = re.sub(r'\s*<animate(?:Transform|Motion)?\b[^>]*/>\s*', "\n", svg, flags=re.I)
    svg = re.sub(r'\s*<set\b[^>]*/>\s*', "\n", svg, flags=re.I)
    return svg


def _insert_after_root_open(svg: str, markup: str) -> str:
    return re.sub(r'(<svg\b[^>]*>)', lambda m: m.group(1) + "\n" + markup, svg, count=1)


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
    return re.sub(
        r'<svg\b',
        f'<svg data-profile-render-target-sha256="{fingerprint}"',
        svg,
        count=1,
    )


def _apply_text(svg: str, *, rel: str, contract: dict) -> str:
    text_mode = contract["profile"]["text"]
    density = contract["labels"]["density"]
    dynamic = rel in DYNAMIC_VISIBLE_TEXT
    suppress_dynamic = dynamic and (text_mode == "minimal" or density == "minimal")

    if suppress_dynamic:
        svg, _ = VECTOR.suppress_visible_text(svg)
        return svg
    if text_mode in {"safe", "minimal"}:
        adaptive = contract["profile"]["background"] == "transparent"
        svg, count = VECTOR.vectorize_visible_text(svg, adaptive=adaptive)
        if adaptive and count:
            svg = _add_adaptive_text_style(svg)
    return svg


def render(config_path: Path, *, season: str, output_root: Path) -> tuple[dict, dict]:
    contract, resolved = CONTRACT.load_and_resolve(config_path)
    preserve_source_bg = contract["surface"]["mounted_source_background"] == "preserve"

    original_strip = V8._strip_mounted_source_backgrounds
    if preserve_source_bg:
        V8._strip_mounted_source_backgrounds = lambda text: text
    try:
        V8.render(season, output_root)
    finally:
        V8._strip_mounted_source_backgrounds = original_strip

    rendered: dict[str, str] = {}
    for rel in asset_paths():
        path = output_root / rel
        svg = path.read_text(encoding="utf-8")

        if contract["profile"]["background"] == "transparent":
            svg = _strip_surface_base(svg)
        if contract["frame"]["mode"] == "none":
            svg = _strip_frame(svg)
        elif contract["frame"]["caps"] == "none":
            svg = _through_rails(svg, rel=rel)
        if contract["profile"]["motion"] == "off":
            svg = _disable_motion(svg)

        svg = _apply_text(svg, rel=rel, contract=contract)
        svg = _mark_root_base(svg, contract=contract, resolved=resolved)
        rendered[rel] = _clean_output(svg)

    render_target = _render_target_fingerprint(
        rendered,
        contract_sha256=resolved["normalized_contract_sha256"],
        season=season,
    )
    resolved["render_target_sha256"] = render_target

    for rel, svg in rendered.items():
        path = output_root / rel
        path.write_text(_clean_output(_add_render_target_marker(svg, render_target)), encoding="utf-8")

    return contract, resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--season", choices=["spring", "summer", "autumn", "winter"], default="summer")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    contract, resolved = render(args.config, season=args.season, output_root=args.output_root)
    if args.json:
        print(json.dumps({"contract": contract, "resolved": resolved}, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "ENVELOPE_V9_RENDER_PASS "
            f"season={args.season} "
            f"background={contract['profile']['background']} "
            f"text={contract['profile']['text']} "
            f"motion={contract['profile']['motion']} "
            f"contract_sha256={resolved['normalized_contract_sha256']} "
            f"render_target_sha256={resolved['render_target_sha256']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
