#!/usr/bin/env python3
"""Validate and normalize the portable profile-envelope contract without third-party dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

CONTRACT_VERSION = 1
TARGET_ADAPTER = "github-profile-readme"

DEFAULTS: dict[str, dict[str, Any]] = {
    "surface": {"mounted_source_background": "inherit"},
    "frame": {"mode": "rail", "caps": "outer-only"},
    "labels": {"density": "auto"},
    "packing": {"mode": "auto"},
    "external_media": {"mode": "reference-only"},
}

ALLOWED = {
    ("profile", "background"): {"opaque", "transparent"},
    ("profile", "text"): {"safe", "native", "minimal"},
    ("profile", "motion"): {"on", "off"},
    ("surface", "mounted_source_background"): {"inherit", "preserve"},
    ("frame", "mode"): {"rail", "none"},
    ("frame", "caps"): {"outer-only", "none"},
    ("labels", "density"): {"auto", "full", "minimal"},
    ("packing", "mode"): {"auto", "off"},
    ("external_media", "mode"): {"reference-only", "none"},
}

TOP_KEYS = {
    "contract_version",
    "target_adapter",
    "profile",
    "surface",
    "frame",
    "labels",
    "packing",
    "external_media",
}
GROUP_KEYS = {
    "profile": {"theme", "background", "text", "motion"},
    "surface": {"mounted_source_background"},
    "frame": {"mode", "caps"},
    "labels": {"density"},
    "packing": {"mode"},
    "external_media": {"mode"},
}


class ContractError(ValueError):
    pass


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{path} must be an object")
    return dict(value)


def _reject_unknown(obj: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ContractError(f"{path} has unsupported keys: {', '.join(unknown)}")


def _enum(group: str, key: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{group}.{key} must be a string")
    allowed = ALLOWED[(group, key)]
    if value not in allowed:
        raise ContractError(
            f"{group}.{key} must be one of {', '.join(sorted(allowed))}; got {value!r}"
        )
    return value


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    root = _object(raw, "$")
    _reject_unknown(root, TOP_KEYS, "$")

    if root.get("contract_version") != CONTRACT_VERSION:
        raise ContractError(f"contract_version must be {CONTRACT_VERSION}")
    if root.get("target_adapter") != TARGET_ADAPTER:
        raise ContractError(f"target_adapter must be {TARGET_ADAPTER!r}")

    profile = _object(root.get("profile"), "profile")
    _reject_unknown(profile, GROUP_KEYS["profile"], "profile")
    missing = [key for key in ("theme", "background", "text", "motion") if key not in profile]
    if missing:
        raise ContractError(f"profile is missing required keys: {', '.join(missing)}")

    theme = profile["theme"]
    if not isinstance(theme, str) or not (1 <= len(theme) <= 64):
        raise ContractError("profile.theme must be a non-empty string up to 64 characters")

    normalized: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "target_adapter": TARGET_ADAPTER,
        "profile": {
            "theme": theme,
            "background": _enum("profile", "background", profile["background"]),
            "text": _enum("profile", "text", profile["text"]),
            "motion": _enum("profile", "motion", profile["motion"]),
        },
    }

    for group, defaults in DEFAULTS.items():
        supplied = _object(root.get(group, {}), group)
        _reject_unknown(supplied, GROUP_KEYS[group], group)
        merged = {**defaults, **supplied}
        for key in merged:
            merged[key] = _enum(group, key, merged[key])
        normalized[group] = merged

    if normalized["frame"]["mode"] == "none" and normalized["frame"]["caps"] != "none":
        raise ContractError("frame.caps must be 'none' when frame.mode is 'none'")

    return normalized


def _text_roles(mode: str) -> dict[str, Any]:
    accessibility = {
        "representation": "text-metadata",
        "visible": False,
        "required": True,
        "host_font_dependency": False,
    }
    if mode == "safe":
        fixed = {
            "representation": "deterministic-outline",
            "host_font_dependency": False,
            "fallback": "fail-closed if essential glyph coverage is unavailable",
        }
        dynamic = {
            "representation": "deterministic-vector-or-bounded-density-fallback",
            "host_font_dependency": False,
            "fallback": "reduce visible label density without deleting semantic data",
        }
    elif mode == "native":
        fixed = {
            "representation": "svg-text",
            "host_font_dependency": True,
            "fallback": "target-render warning; no font-independent TEXT PASS claim",
        }
        dynamic = {
            "representation": "svg-text",
            "host_font_dependency": True,
            "fallback": "target-render warning; density policy still applies",
        }
    else:
        fixed = {
            "representation": "deterministic-outline",
            "host_font_dependency": False,
            "fallback": "fail-closed if essential glyph coverage is unavailable",
        }
        dynamic = {
            "representation": "suppressed-visible-labels",
            "host_font_dependency": False,
            "fallback": "semantic data and accessibility metadata remain present",
        }
    return {
        "essential_fixed_visible": fixed,
        "dynamic_data_visible": dynamic,
        "accessibility_metadata": accessibility,
    }


def resolve(normalized: dict[str, Any]) -> dict[str, Any]:
    profile = normalized["profile"]
    surface = normalized["surface"]
    labels = normalized["labels"]
    packing = normalized["packing"]

    appearances = ["dark"]
    warnings: list[dict[str, str]] = []
    if profile["background"] == "transparent":
        appearances = ["dark", "light"]
        warnings.append(
            {
                "code": "TRANSPARENT_HOST_PARTICIPATES",
                "message": "Transparent output must be target-rendered on both light and dark host appearances.",
            }
        )
    if profile["text"] == "native":
        warnings.append(
            {
                "code": "HOST_FONT_DEPENDENT_TEXT",
                "message": "Native text is intentionally host-font-dependent and cannot earn a font-independent TEXT PASS.",
            }
        )
    if profile["background"] == "transparent" and surface["mounted_source_background"] == "preserve":
        warnings.append(
            {
                "code": "MIXED_SURFACE_OPACITY",
                "message": "Transparent envelope plus preserved mounted-source backgrounds may create opaque islands.",
            }
        )
    if packing["mode"] == "off":
        warnings.append(
            {
                "code": "GITHUB_MOBILE_SEAM_RISK",
                "message": "Packing is disabled; short SVG rows require an explicit mobile line-box/seam proof.",
            }
        )
    if labels["density"] == "full" and profile["text"] == "safe":
        warnings.append(
            {
                "code": "DENSE_SAFE_TEXT_STRESS_REQUIRED",
                "message": "Full safe labels require a dense-fixture readability/overflow proof.",
            }
        )

    target_cases = [
        {"viewport": viewport, "appearance": appearance}
        for appearance in appearances
        for viewport in ("desktop", "mobile")
    ]
    checks = ["structure", "source-sync", "target-layout", "text"]
    if profile["motion"] == "on":
        checks += ["playback", "reduced-motion-static-fallback"]
    else:
        checks += ["static-completeness"]

    canonical = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    fingerprint = hashlib.sha256(canonical).hexdigest()

    return {
        "normalized_contract_sha256": fingerprint,
        "text_roles": _text_roles(profile["text"]),
        "verification": {
            "target_cases": target_cases,
            "checks": checks,
            "text_pass_mode": (
                "font-independent"
                if profile["text"] in {"safe", "minimal"}
                else "host-dependent-only"
            ),
            "transparent_requires_light_dark": profile["background"] == "transparent",
            "motion_proof_required": profile["motion"] == "on",
        },
        "publication": {
            "generator_authority": "read-only",
            "writer_separation_required": True,
            "atomic_generated_artifact_set_required": True,
            "source_fingerprint_required": True,
        },
        "warnings": warnings,
    }


def load_and_resolve(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"config does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON in {path}: {exc}") from exc
    normalized = normalize(raw)
    return normalized, resolve(normalized)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument(
        "--resolved-json",
        action="store_true",
        help="print normalized contract plus derived policy/verification data as JSON",
    )
    args = parser.parse_args()

    try:
        normalized, derived = load_and_resolve(args.config)
    except ContractError as exc:
        print(f"PROFILE_ENVELOPE_CONTRACT_FAIL {exc}")
        return 1

    if args.resolved_json:
        print(
            json.dumps(
                {"contract": normalized, "resolved": derived},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        cases = len(derived["verification"]["target_cases"])
        warnings = len(derived["warnings"])
        print(
            "PROFILE_ENVELOPE_CONTRACT_PASS "
            f"sha256={derived['normalized_contract_sha256']} "
            f"target_cases={cases} warnings={warnings}"
        )
        for warning in derived["warnings"]:
            print(f"WARN {warning['code']}: {warning['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
