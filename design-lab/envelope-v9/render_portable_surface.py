#!/usr/bin/env python3
"""Envelope v9 donor adapter over the standalone GitHub-profile transformer.

This file is intentionally repository-bound: it creates the current v8 donor bundle.
Portable presentation policy lives in `github_profile_transform.py`, which does not
import v7/v8 or repository-local Project Map / Activity source modules.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
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


def render(config_path: Path, *, season: str, output_root: Path) -> tuple[dict, dict]:
    contract, resolved = CONTRACT.load_and_resolve(config_path)

    # Normalize the donor boundary: always retain mounted-source presentation
    # backgrounds in the v8 bundle. The standalone transformer alone decides
    # `inherit | preserve`, so its behavior can be extracted without v8 imports.
    original_strip = V8._strip_mounted_source_backgrounds
    V8._strip_mounted_source_backgrounds = lambda text: text
    try:
        V8.render(season, output_root)
    finally:
        V8._strip_mounted_source_backgrounds = original_strip

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
