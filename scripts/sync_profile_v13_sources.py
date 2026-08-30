#!/usr/bin/env python3
"""Refresh only source-mounted regions of the v1.3 profile presentation.

The source SVG files remain authoritative and are never modified. This adapter
only updates the two presentation segment files that visibly contain them.
Typography, geometry, styles, and animation inside each source SVG are copied
without transformation; only the known opaque outer background is omitted and
root placement/provenance attributes are attached.
"""
from __future__ import annotations

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

SOURCES = {
    "project-map/galaxy.svg": {
        "segment": "assets/profile-v12-projects.svg",
        "x": "80", "y": "880", "width": "740", "height": "420",
    },
    "assets/github-contributions-dark.svg": {
        "segment": "assets/profile-v12-activity.svg",
        "x": "70", "y": "1570", "width": "760", "height": "220",
    },
}


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text_snapshot(root: ET.Element) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
    return [
        ("".join(e.itertext()), tuple(sorted(e.attrib.items())))
        for e in root.iter() if local(e.tag) == "text"
    ]


def motion_snapshot(root: ET.Element) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
    return [
        (local(e.tag), tuple(sorted(e.attrib.items())))
        for e in root.iter() if local(e.tag) in {"animate", "animateTransform", "animateMotion"}
    ]


def remove_known_background(root: ET.Element, rel: str) -> None:
    for child in list(root):
        if local(child.tag) != "rect":
            continue
        width = child.attrib.get("width")
        height = child.attrib.get("height")
        fill = child.attrib.get("fill", "")
        if rel == "project-map/galaxy.svg" and width == "100%" and height == "100%" and fill == "url(#galaxy-family-bg)":
            root.remove(child)
            return
        if rel == "assets/github-contributions-dark.svg" and width == "760" and height == "220" and fill.lower() == "#0d1117":
            root.remove(child)
            return
    raise ValueError(f"known source background not found: {rel}")


def prepared_source(repo: Path, rel: str) -> ET.Element:
    cfg = SOURCES[rel]
    source = ET.fromstring((repo / rel).read_text(encoding="utf-8"))
    before_text = text_snapshot(source)
    before_motion = motion_snapshot(source)
    remove_known_background(source, rel)
    source.attrib.update({
        "x": cfg["x"], "y": cfg["y"], "width": cfg["width"], "height": cfg["height"],
        "data-supernatural-mounted-source": rel,
        "data-profile-envelope-mounted-background": "presentation",
    })
    if text_snapshot(source) != before_text:
        raise ValueError(f"text changed while preparing source: {rel}")
    if motion_snapshot(source) != before_motion:
        raise ValueError(f"motion changed while preparing source: {rel}")
    return source


def find_with_parent(root: ET.Element, rel: str) -> tuple[ET.Element, ET.Element]:
    for parent in root.iter():
        for child in list(parent):
            if child.attrib.get("data-supernatural-mounted-source") == rel:
                return parent, child
    raise ValueError(f"mounted source not found in presentation segment: {rel}")


def canonical(elem: ET.Element) -> bytes:
    return ET.tostring(elem, encoding="utf-8")


def sync_one(repo: Path, rel: str) -> bool:
    cfg = SOURCES[rel]
    segment_path = repo / cfg["segment"]
    segment = ET.fromstring(segment_path.read_text(encoding="utf-8"))
    parent, current = find_with_parent(segment, rel)
    new = prepared_source(repo, rel)
    if canonical(current) == canonical(new):
        print(f"unchanged {rel}")
        return False
    index = list(parent).index(current)
    parent.remove(current)
    parent.insert(index, new)
    segment_path.write_text(ET.tostring(segment, encoding="unicode").rstrip() + "\n", encoding="utf-8")
    print(f"updated {cfg['segment']} from {rel}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args()
    changed = [rel for rel in SOURCES if sync_one(args.repo, rel)]
    print("PROFILE_ENVELOPE_V13_SOURCE_SYNC_PASS changed=" + str(len(changed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
