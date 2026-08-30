#!/usr/bin/env python3
"""Bounded source refresh bridge for the sealed v1.4 presentation payload.

This does not generate or redesign the Profile Envelope world. It validates the
740x420 Project Map reference and refreshes only the source-bound receipt fields
and embedded adapted contribution SVG inside the already validated overlay
wrapper. Consumer-owned source SVGs are never mutated.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
PM_REL = "project-map/galaxy.svg"
ACT_REL = "assets/github-contributions-dark.svg"
WRAP_REL = "assets/profile-v16-overlay-00.svg"
MAX_BYTES = 512 * 1024
BG = {"width": "760", "height": "220", "rx": "8", "fill": "#0d1117"}
MOTION = {"animate", "animateTransform", "animateMotion", "set"}
ACTIVE = {"script", "foreignObject"}
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
ROOT_EXPECT = {
    "width": "900",
    "height": "261",
    "viewBox": "0 1226 900 261",
    "data-profile-envelope-world-overlay": "v1",
    "data-overlay-index": "0",
    "data-global-start": "1226",
    "data-global-end": "1487",
    "data-global-extent": "1677",
    "data-source-policy": "embedded-adapted-copy-static-self-contained",
    "data-adaptation-policy": "exact-direct-root-rect-removal-v1",
    "data-transparency-preflight": "no-obvious-opaque-canvas",
}
VOLATILE = (
    "data-source-sha256",
    "data-adapted-source-sha256",
    "data-source-bytes",
)


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_svg(payload: bytes, label: str) -> ET.Element:
    if len(payload) > MAX_BYTES:
        raise ValueError(f"{label} exceeds byte limit")
    try:
        root = ET.fromstring(payload.decode("utf-8"))
    except (UnicodeDecodeError, ET.ParseError) as exc:
        raise ValueError(f"{label} must be UTF-8 SVG") from exc
    if local(root.tag) != "svg":
        raise ValueError(f"{label} root must be svg")
    return root


def numeric(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(?:px)?\s*", value)
    return float(match.group(1)) if match else None


def require_geometry(root: ET.Element, width: int, height: int, label: str) -> None:
    actual_w = numeric(root.attrib.get("width"))
    actual_h = numeric(root.attrib.get("height"))
    if actual_w is None or actual_h is None:
        raise ValueError(f"{label} requires numeric width/height")
    if abs(actual_w - width) > 1e-6 or abs(actual_h - height) > 1e-6:
        raise ValueError(f"{label} dimensions drifted")
    view_box = root.attrib.get("viewBox")
    if view_box is not None:
        parts = view_box.replace(",", " ").split()
        if len(parts) != 4:
            raise ValueError(f"{label} viewBox malformed")
        try:
            _, _, view_w, view_h = map(float, parts)
        except ValueError as exc:
            raise ValueError(f"{label} viewBox malformed") from exc
        if abs(view_w - width) > 1e-6 or abs(view_h - height) > 1e-6:
            raise ValueError(f"{label} viewBox dimensions drifted")


def reject_activity_unsafe(root: ET.Element) -> None:
    for elem in root.iter():
        name = local(elem.tag)
        if name in MOTION:
            raise ValueError("activity motion drifted; private regeneration required")
        if name in ACTIVE:
            raise ValueError("activity active content unsupported")
        if name == "style":
            css = elem.text or ""
            lowered = css.lower()
            if "@import" in lowered or "@keyframes" in lowered or re.search(
                r"(?:^|[;{\s])animation(?:-name)?\s*:", css, re.IGNORECASE
            ):
                raise ValueError("activity CSS motion/resource unsupported")
            if any(not target.strip().startswith("#") for _, target in CSS_URL.findall(css)):
                raise ValueError("activity external CSS resource unsupported")
        if re.search(
            r"(?:^|;)\s*animation(?:-name)?\s*:", elem.attrib.get("style", ""), re.IGNORECASE
        ):
            raise ValueError("activity CSS motion unsupported")
        for raw_name, value in elem.attrib.items():
            attr = local(raw_name)
            if attr.lower().startswith("on"):
                raise ValueError("activity event handler unsupported")
            if attr == "href" and value and not value.strip().startswith("#"):
                raise ValueError("activity external href unsupported")
            if any(not target.strip().startswith("#") for _, target in CSS_URL.findall(value)):
                raise ValueError("activity external resource unsupported")


def adapt_activity(payload: bytes) -> bytes:
    root = parse_svg(payload, "activity")
    require_geometry(root, 760, 220, "activity")
    reject_activity_unsafe(root)
    matches = []
    for child in list(root):
        if local(child.tag) != "rect":
            continue
        actual = {local(key): value for key, value in child.attrib.items()}
        if actual == BG:
            matches.append(child)
    if len(matches) != 1:
        raise ValueError(
            f"activity exact background contract drifted: found {len(matches)}"
        )
    root.remove(matches[0])
    # Explicit registration reproduces the sealed build's canonical SVG bytes.
    ET.register_namespace("", SVG_NS)
    return (ET.tostring(root, encoding="unicode").rstrip() + "\n").encode("utf-8")


def validate_project(repo: Path) -> str:
    path = repo / PM_REL
    payload = path.read_bytes()
    root = parse_svg(payload, "project map")
    require_geometry(root, 740, 420, "project map")
    return hashlib.sha256(payload).hexdigest()


def skeleton(text: str) -> str:
    normalized = text
    for key in VOLATILE:
        normalized = re.sub(
            rf'{re.escape(key)}="[^"]*"',
            f'{key}="<volatile>"',
            normalized,
            count=1,
        )
    normalized = re.sub(
        r'href="data:image/svg\+xml;base64,[^"]*"',
        'href="data:image/svg+xml;base64,<payload>"',
        normalized,
        count=1,
    )
    return normalized


def sync(repo: Path) -> dict[str, object]:
    project_sha = validate_project(repo)
    source_path = repo / ACT_REL
    source = source_path.read_bytes()
    original_sha = hashlib.sha256(source).hexdigest()
    adapted = adapt_activity(source)
    adapted_sha = hashlib.sha256(adapted).hexdigest()

    wrapper_path = repo / WRAP_REL
    before = wrapper_path.read_text(encoding="utf-8")
    root = parse_svg(before.encode("utf-8"), "v1.4 wrapper")
    for key, expected in ROOT_EXPECT.items():
        if root.attrib.get(key) != expected:
            raise ValueError(f"wrapper invariant drifted: {key}")
    images = [elem for elem in root.iter() if local(elem.tag) == "image"]
    if len(images) != 1:
        raise ValueError("wrapper must contain exactly one image")
    image = images[0]
    expected_image = {
        "x": "0",
        "y": "1226",
        "width": "900",
        "height": "261",
        "preserveAspectRatio": "xMidYMid meet",
    }
    for key, expected in expected_image.items():
        if image.attrib.get(key) != expected:
            raise ValueError(f"wrapper image geometry drifted: {key}")

    href = "data:image/svg+xml;base64," + base64.b64encode(adapted).decode("ascii")
    after = before
    replacements = {
        "data-source-sha256": original_sha,
        "data-adapted-source-sha256": adapted_sha,
        # This field belongs to the embedded adapted payload, not the original.
        "data-source-bytes": str(len(adapted)),
    }
    for key, value in replacements.items():
        pattern = rf'{re.escape(key)}="[^"]*"'
        after, count = re.subn(pattern, f'{key}="{value}"', after, count=1)
        if count != 1:
            raise ValueError(f"wrapper missing receipt field: {key}")
    after, count = re.subn(
        r'href="data:image/svg\+xml;base64,[^"]*"',
        f'href="{href}"',
        after,
        count=1,
    )
    if count != 1:
        raise ValueError("wrapper embedded image receipt drifted")
    if skeleton(before) != skeleton(after):
        raise ValueError("wrapper frame skeleton changed")

    wrapper_path.write_text(after, encoding="utf-8")
    return {
        "project_sha256": project_sha,
        "activity_sha256": original_sha,
        "adapted_activity_sha256": adapted_sha,
        "adapted_activity_bytes": len(adapted),
        "wrapper_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
        "changed": after != before,
        "source_mutation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = sync(args.repo_root.resolve())
    print(
        "PROFILE_V14_SOURCE_SYNC_PASS "
        + " ".join(f"{key}={value}" for key, value in result.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
