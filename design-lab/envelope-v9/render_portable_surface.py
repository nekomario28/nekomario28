#!/usr/bin/env python3
"""Envelope v9 donor adapter over the standalone GitHub-profile transformer.

This file is intentionally repository-bound: it creates the current v8 donor bundle
and annotates donor-specific elements with the small generic marker contract consumed
by `github_profile_transform.py`.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
V8_PATH = ROOT / "design-lab" / "envelope-v8" / "render_continuous_canvas.py"
CONTRACT_PATH = ROOT / "design-lab" / "scripts" / "profile_envelope_contract.py"
TRANSFORM_PATH = HERE / "github_profile_transform.py"


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
TRANSFORM = _load("envelope_v9_github_profile_transform", TRANSFORM_PATH)
VECTOR = TRANSFORM.VECTOR
DYNAMIC_VISIBLE_TEXT = TRANSFORM.DYNAMIC_VISIBLE_TEXT
asset_paths = TRANSFORM.asset_paths


def _add_marker(tag: str, marker: str) -> str:
    if marker in tag:
        return tag
    return re.sub(r'(<[A-Za-z][^\s/>]*)', lambda match: match.group(1) + " " + marker, tag, count=1)


def _annotate_donor_svg(svg: str, *, rel: str) -> str:
    surface = re.compile(r'<rect\b(?=[^>]*\bid="v8-[^"]+-surface-base")[^>]*/>')
    svg = surface.sub(lambda match: _add_marker(match.group(0), TRANSFORM.SURFACE_MARKER), svg)

    frame = re.compile(r'<g\b(?=[^>]*\bid="v8-frame")[^>]*>')
    svg = frame.sub(lambda match: _add_marker(match.group(0), TRANSFORM.FRAME_MARKER), svg)

    if rel == "assets/profile-projects-canvas.svg":
        mounted = re.compile(
            r'<rect\b(?=[^>]*\bwidth="100%")(?=[^>]*\bheight="100%")'
            r'(?=[^>]*\bfill="url\(#galaxy-family-bg\)")[^>]*/>'
        )
        svg = mounted.sub(lambda match: _add_marker(match.group(0), TRANSFORM.MOUNTED_BACKGROUND_MARKER), svg, count=1)
    elif rel == "assets/profile-activity-canvas.svg":
        mounted = re.compile(
            r'<rect\b(?=[^>]*\bwidth="760")(?=[^>]*\bheight="220")'
            r'(?=[^>]*\bfill="#0d1117")[^>]*/>'
        )
        svg = mounted.sub(lambda match: _add_marker(match.group(0), TRANSFORM.MOUNTED_BACKGROUND_MARKER), svg, count=1)
    return svg


def normalize_donor_bundle(root: Path) -> None:
    """Translate donor-specific element identity into portable marker semantics."""
    for rel in asset_paths():
        path = root / rel
        svg = path.read_text(encoding="utf-8")
        path.write_text(_annotate_donor_svg(svg, rel=rel), encoding="utf-8")


def render(config_path: Path, *, season: str, output_root: Path) -> tuple[dict, dict]:
    contract, resolved = CONTRACT.load_and_resolve(config_path)

    original_strip = V8._strip_mounted_source_backgrounds
    V8._strip_mounted_source_backgrounds = lambda text: text
    try:
        V8.render(season, output_root)
    finally:
        V8._strip_mounted_source_backgrounds = original_strip

    normalize_donor_bundle(output_root)
    resolved_out = TRANSFORM.transform_bundle(
        output_root,
        output_root,
        contract=contract,
        resolved=resolved,
        season=season,
    )
    return contract, resolved_out


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
