#!/usr/bin/env python3
"""Structural/contract validation for the lab-only Envelope v9 portability donor."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDERER_PATH = HERE / "render_portable_surface.py"
OPAQUE_SAFE = ROOT / "design-lab" / "profile-envelope-config.example.json"
TRANSPARENT_SAFE = ROOT / "design-lab" / "profile-envelope-config.transparent.example.json"


def load_renderer():
    spec = importlib.util.spec_from_file_location("envelope_v9_renderer", RENDERER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load v9 renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = load_renderer()


def write_config(root: Path, name: str, *, background: str, text: str, motion: str, mounted: str = "inherit", density: str = "auto") -> Path:
    path = root / f"{name}.json"
    path.write_text(
        json.dumps(
            {
                "contract_version": 1,
                "target_adapter": "github-profile-readme",
                "profile": {"theme": "seasonal-dark", "background": background, "text": text, "motion": motion},
                "surface": {"mounted_source_background": mounted},
                "frame": {"mode": "rail", "caps": "outer-only"},
                "labels": {"density": density},
                "packing": {"mode": "auto"},
                "external_media": {"mode": "reference-only"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def texts(path: Path) -> int:
    return R.VECTOR.visible_text_count(path.read_text(encoding="utf-8"))


def assert_xml(root: Path) -> None:
    for rel in R.asset_paths():
        ET.parse(root / rel)


def assert_markers(root: Path, *, background: str, text: str, motion: str, contract_fingerprint: str, render_target: str) -> None:
    for rel in R.asset_paths():
        svg = (root / rel).read_text(encoding="utf-8")
        assert 'data-envelope-presentation="v9-portable-surface"' in svg, rel
        assert f'data-profile-contract-sha256="{contract_fingerprint}"' in svg, rel
        assert f'data-profile-render-target-sha256="{render_target}"' in svg, rel
        assert f'data-profile-background="{background}"' in svg, rel
        assert f'data-profile-text="{text}"' in svg, rel
        assert f'data-profile-motion="{motion}"' in svg, rel
        assert "data-profile-envelope-surface-base=" not in svg, rel
        assert "data-profile-envelope-frame=" not in svg, rel
        assert "data-profile-envelope-mounted-background=" not in svg, rel


def render_case(work: Path, name: str, config: Path) -> tuple[Path, dict, dict]:
    out = work / name
    out.mkdir()
    contract, resolved = R.render(config, season="summer", output_root=out)
    assert_xml(out)
    assert_markers(
        out,
        background=contract["profile"]["background"],
        text=contract["profile"]["text"],
        motion=contract["profile"]["motion"],
        contract_fingerprint=resolved["normalized_contract_sha256"],
        render_target=resolved["render_target_sha256"],
    )
    return out, contract, resolved


def assert_donor_boundary_equivalence(work: Path, expected: Path) -> None:
    """Generic marker normalization must preserve the accepted inherit output bytes."""
    contract, resolved = R.CONTRACT.load_and_resolve(OPAQUE_SAFE)
    stripped_donor = work / "donor-default-stripped"
    preserved_donor = work / "donor-preserved"
    legacy_equivalent = work / "legacy-boundary-output"
    decoupled = work / "decoupled-boundary-output"
    for path in (stripped_donor, preserved_donor, legacy_equivalent, decoupled):
        path.mkdir()

    R.V8.render("summer", stripped_donor)
    R.normalize_donor_bundle(stripped_donor)

    original_strip = R.V8._strip_mounted_source_backgrounds
    R.V8._strip_mounted_source_backgrounds = lambda text: text
    try:
        R.V8.render("summer", preserved_donor)
    finally:
        R.V8._strip_mounted_source_backgrounds = original_strip
    R.normalize_donor_bundle(preserved_donor)

    legacy_receipt = R.TRANSFORM.transform_bundle(
        stripped_donor,
        legacy_equivalent,
        contract=contract,
        resolved=resolved,
        season="summer",
    )
    decoupled_receipt = R.TRANSFORM.transform_bundle(
        preserved_donor,
        decoupled,
        contract=contract,
        resolved=resolved,
        season="summer",
    )
    assert legacy_receipt["render_target_sha256"] == decoupled_receipt["render_target_sha256"]
    for rel in R.asset_paths():
        legacy_bytes = (legacy_equivalent / rel).read_bytes()
        decoupled_bytes = (decoupled / rel).read_bytes()
        current_bytes = (expected / rel).read_bytes()
        assert legacy_bytes == decoupled_bytes == current_bytes, rel


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        opaque, opaque_contract, opaque_resolved = render_case(work, "opaque-safe", OPAQUE_SAFE)
        transparent, transparent_contract, transparent_resolved = render_case(work, "transparent-safe", TRANSPARENT_SAFE)
        transparent_repeat, _, transparent_repeat_resolved = render_case(work, "transparent-safe-repeat", TRANSPARENT_SAFE)
        native_cfg = write_config(work, "native", background="opaque", text="native", motion="on")
        native, _, native_resolved = render_case(work, "opaque-native", native_cfg)
        minimal_cfg = write_config(work, "minimal", background="transparent", text="minimal", motion="off", density="minimal")
        minimal, _, minimal_resolved = render_case(work, "transparent-minimal", minimal_cfg)
        preserve_cfg = write_config(work, "preserve", background="transparent", text="native", motion="off", mounted="preserve")
        preserve, _, preserve_resolved = render_case(work, "transparent-preserve", preserve_cfg)

        assert_donor_boundary_equivalence(work, opaque)
        assert transparent_resolved["render_target_sha256"] == transparent_repeat_resolved["render_target_sha256"]
        target_ids = {
            opaque_resolved["render_target_sha256"],
            transparent_resolved["render_target_sha256"],
            native_resolved["render_target_sha256"],
            minimal_resolved["render_target_sha256"],
            preserve_resolved["render_target_sha256"],
        }
        assert len(target_ids) == 5

        assert all(texts(opaque / rel) == 0 for rel in R.asset_paths())
        assert all(texts(transparent / rel) == 0 for rel in R.asset_paths())
        assert sum((opaque / rel).read_text().count('data-vector-text="v1"') for rel in R.asset_paths()) > 0

        transparent_hero = (transparent / "assets/profile-hero.svg").read_text(encoding="utf-8")
        assert 'data-v9-adaptive-vector-text-style="v1"' in transparent_hero
        assert 'class="v9-adaptive-vector-text"' in transparent_hero
        assert 'prefers-color-scheme: light' in transparent_hero
        assert 'prefers-color-scheme: dark' in transparent_hero
        assert 'stroke="currentColor"' in transparent_hero

        assert sum(texts(native / rel) for rel in R.asset_paths()) > 0
        assert opaque_resolved["verification"]["text_pass_mode"] == "font-independent"
        native_contract, native_contract_resolved = R.CONTRACT.load_and_resolve(native_cfg)
        assert native_contract["profile"]["text"] == "native"
        assert native_contract_resolved["verification"]["text_pass_mode"] == "host-dependent-only"

        for rel in R.DYNAMIC_VISIBLE_TEXT:
            svg = (minimal / rel).read_text(encoding="utf-8")
            assert '<text' not in svg
            assert 'data-vector-text="v1"' not in svg
            assert '<title' in svg or '<desc' in svg
        assert (minimal / "assets/profile-hero.svg").read_text().count('data-vector-text="v1"') >= 1
        assert all('<animate' not in (minimal / rel).read_text().lower() for rel in R.asset_paths())

        assert all('surface-base"' in (opaque / rel).read_text() for rel in R.asset_paths())
        assert all('surface-base"' not in (transparent / rel).read_text() for rel in R.asset_paths())
        inherited_projects = (transparent / "assets/profile-projects-canvas.svg").read_text()
        preserved_projects = (preserve / "assets/profile-projects-canvas.svg").read_text()
        assert 'fill="url(#galaxy-family-bg)"' not in inherited_projects
        assert 'fill="url(#galaxy-family-bg)"' in preserved_projects

        assert len(opaque_resolved["verification"]["target_cases"]) == 2
        assert len(transparent_resolved["verification"]["target_cases"]) == 4
        assert {case["appearance"] for case in transparent_resolved["verification"]["target_cases"]} == {"dark", "light"}
        assert opaque_contract["profile"]["background"] == "opaque"
        assert transparent_contract["profile"]["background"] == "transparent"

    print("ENVELOPE_V9_PORTABLE_STRUCTURE_PASS cases=5 text=safe/native/minimal background=opaque/transparent mounted=inherit/preserve")
    print("DONOR_BOUNDARY_EQUIVALENCE=PASS legacy_prestripped_vs_preserve_first=true")
    print("GENERIC_DONOR_MARKER_BOUNDARY=PASS portable_transformer_v8_identity=false")
    print("RENDER_TARGET_FINGERPRINT=PASS deterministic=true target_sensitive=true")
    print("TARGET_LAYOUT=NOT_RUN TEXT_RENDER=NOT_RUN PLAYBACK=NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
