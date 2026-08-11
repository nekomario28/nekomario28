#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from render_project_map import collision_size, preview_positions


def fail(message: str) -> None:
    raise AssertionError(message)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail(f"{path}: top-level JSON value must be an object")
    return data


def validate_graph(data: dict[str, Any]) -> None:
    nodes = data.get("nodes")
    links = data.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        fail("graph-data.json must contain nodes and links arrays")

    ids = [str(node.get("id", "")) for node in nodes if isinstance(node, dict)]
    if len(ids) != len(nodes) or any(not node_id for node_id in ids):
        fail("every node must be an object with a non-empty id")
    if len(ids) != len(set(ids)):
        fail("node ids must be unique")
    known = set(ids)

    owners = [node for node in nodes if node.get("type") == "owner"]
    repositories = [node for node in nodes if node.get("type") == "repository"]
    groups = [node for node in nodes if node.get("type") == "group"]
    if len(owners) != 1:
        fail(f"expected exactly one owner node, found {len(owners)}")
    expected_owner = f"user:{data.get('owner', '')}"
    if owners[0].get("id") != expected_owner:
        fail("owner node id does not match graph owner")
    if len(repositories) != int(data.get("repositoryCount", -1)):
        fail("repositoryCount does not match repository nodes")
    if len(groups) != int(data.get("groupCount", -1)):
        fail("groupCount does not match group nodes")

    link_keys: set[tuple[str, str, str]] = set()
    members_by_group: dict[str, set[str]] = {}
    for link in links:
        if not isinstance(link, dict):
            fail("every link must be an object")
        source = str(link.get("source", ""))
        target = str(link.get("target", ""))
        link_type = str(link.get("type", ""))
        if source not in known or target not in known:
            fail(f"link references unknown node: {source} -> {target}")
        if source == target:
            fail(f"self-link is not allowed: {source}")
        key = (source, target, link_type)
        if key in link_keys:
            fail(f"duplicate link: {key}")
        link_keys.add(key)
        if link_type == "member":
            members_by_group.setdefault(source, set()).add(target)

    for group in groups:
        group_id = str(group["id"])
        actual = len(members_by_group.get(group_id, set()))
        declared = int(group.get("repositoryCount", -1))
        if actual != declared:
            fail(f"{group_id}: repositoryCount={declared}, membership links={actual}")


def validate_public_config(data: dict[str, Any], config_path: Path) -> None:
    config = load_json(config_path)
    public_names = {
        str(node.get("label", ""))
        for node in data.get("nodes", [])
        if isinstance(node, dict) and node.get("type") == "repository"
    }
    public_casefold = {name.casefold(): name for name in public_names}
    group_ids: set[str] = set()

    groups = config.get("groups", [])
    relations = config.get("relations", [])
    if not isinstance(groups, list) or not isinstance(relations, list):
        fail(f"{config_path}: groups and relations must be arrays")

    def require_public_repository(name: str, location: str) -> None:
        if name in public_names:
            return
        canonical = public_casefold.get(name.casefold())
        if canonical:
            fail(
                f"{config_path}: {location} uses {name!r}, but the public repository is "
                f"{canonical!r}; update the exact spelling/case"
            )
        fail(
            f"{config_path}: {location} references {name!r}, which is not in the generated "
            "public repository set; public profile config must not retain private/stale names"
        )

    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            fail(f"{config_path}: groups[{index}] must be an object")
        group_id = str(group.get("id", "")).strip()
        label = str(group.get("label", "")).strip()
        if not group_id or not label:
            fail(f"{config_path}: groups[{index}] needs non-empty id and label")
        if group_id in group_ids:
            fail(f"{config_path}: duplicate group id {group_id!r}")
        group_ids.add(group_id)
        repositories = group.get("repositories", [])
        if not isinstance(repositories, list) or not repositories:
            fail(f"{config_path}: group {group_id!r} must list at least one repository")
        seen: set[str] = set()
        for repo_index, raw_name in enumerate(repositories):
            name = str(raw_name)
            if name in seen:
                fail(f"{config_path}: group {group_id!r} contains duplicate repository {name!r}")
            seen.add(name)
            require_public_repository(name, f"group {group_id!r} repositories[{repo_index}]")

    for index, relation in enumerate(relations):
        if not isinstance(relation, dict):
            fail(f"{config_path}: relations[{index}] must be an object")
        source = str(relation.get("source", "")).strip()
        target = str(relation.get("target", "")).strip()
        if not source or not target:
            fail(f"{config_path}: relations[{index}] needs source and target")
        require_public_repository(source, f"relations[{index}].source")
        require_public_repository(target, f"relations[{index}].target")


def rect_for(node: dict[str, Any], x: float, y: float) -> tuple[float, float, float, float]:
    width, height = collision_size(node)
    return (x - width / 2, y - height / 2, x + width / 2, y + height / 2)


def overlap_amount(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> tuple[float, float]:
    return (
        min(first[2], second[2]) - max(first[0], second[0]),
        min(first[3], second[3]) - max(first[1], second[1]),
    )


def validate_preview_layout(data: dict[str, Any], width: int = 760, height: int = 560) -> None:
    first = preview_positions(data)
    second = preview_positions(data)
    signature_a = [(key, round(value[0], 4), round(value[1], 4)) for key, value in sorted(first.items())]
    signature_b = [(key, round(value[0], 4), round(value[1], 4)) for key, value in sorted(second.items())]
    if signature_a != signature_b:
        fail("preview layout must be deterministic")

    placed = [(node_id, x, y, node) for node_id, (x, y, node) in first.items()]
    if len(placed) != len(data["nodes"]):
        fail("preview layout must place every graph node exactly once")

    left_limit, right_limit = 12.0, width - 12.0
    top_limit, bottom_limit = 60.0, 490.0
    for node_id, x, y, node in placed:
        if not math.isfinite(x) or not math.isfinite(y):
            fail(f"{node_id}: non-finite preview coordinate")
        rect = rect_for(node, x, y)
        if rect[0] < left_limit or rect[2] > right_limit or rect[1] < top_limit or rect[3] > bottom_limit:
            fail(f"{node_id}: preview node/label leaves the safe drawing area: {rect}")

    overlaps: list[str] = []
    for first_index in range(len(placed)):
        a_id, ax, ay, a_node = placed[first_index]
        a_rect = rect_for(a_node, ax, ay)
        for second_index in range(first_index + 1, len(placed)):
            b_id, bx, by, b_node = placed[second_index]
            b_rect = rect_for(b_node, bx, by)
            overlap_x, overlap_y = overlap_amount(a_rect, b_rect)
            if overlap_x > 0.75 and overlap_y > 0.75:
                overlaps.append(f"{a_id} <-> {b_id} ({overlap_x:.1f} x {overlap_y:.1f})")
    if overlaps:
        fail("preview node/label overlaps remain: " + "; ".join(overlaps[:8]))


def validate_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    required_ids = ["graph", "search", "reset", "details", "interaction-hint"]
    for element_id in required_ids:
        if f'id="{element_id}"' not in text:
            fail(f"{path}: missing required element id={element_id}")

    scripts = ["graph.js", "obsidian-controls.js", "orbital-spacing.js", "galaxy-structure.js", "cosmic.js"]
    positions = [text.find(f'src="{script}"') for script in scripts]
    if any(position < 0 for position in positions):
        fail(f"{path}: missing required map script")
    if positions != sorted(positions):
        fail(
            f"{path}: scripts must load in order "
            "graph.js -> obsidian-controls.js -> orbital-spacing.js -> galaxy-structure.js -> cosmic.js"
        )

    forbidden = [
        "natural-motion.js",
        "galaxy-orbits.js",
        "galaxy-layout.js",
        "galaxy-motion.js",
        "galaxy-controls.js",
    ]
    for script in forbidden:
        if f'src="{script}"' in text:
            fail(f"{path}: obsolete galaxy behavior script must not be loaded: {script}")

    if "?plain=1" not in text:
        fail(f"{path}: plain force-graph comparison route must remain documented")


def validate_svg(path: Path, expected_groups: int) -> None:
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    if "nan" in lowered or "infinity" in lowered:
        fail(f"{path}: SVG contains a non-finite number")
    root = ET.fromstring(text)
    if root.tag.split("}")[-1] != "svg":
        fail(f"{path}: root element is not svg")
    if root.attrib.get("viewBox") != "0 0 760 560":
        fail(f"{path}: unexpected viewBox {root.attrib.get('viewBox')!r}")
    if 'id="cosmic-preview"' not in text:
        fail(f"{path}: cosmic preview layer is missing")
    sector_count = text.count('id="spiral-sector-')
    if sector_count != expected_groups:
        fail(f"{path}: expected {expected_groups} spiral sectors, found {sector_count}")
    if "A common-center galaxy of public projects" not in text:
        fail(f"{path}: common-center galaxy preview subtitle is missing")
    if "Open the interactive map" not in text:
        fail(f"{path}: CTA is missing")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated interactive project map artifacts")
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--light", type=Path, required=True)
    parser.add_argument("--dark", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_json(args.json)
    validate_graph(data)
    validate_public_config(data, args.config)
    validate_preview_layout(data)
    validate_html(args.html)
    expected_groups = int(data.get("groupCount", 0))
    validate_svg(args.light, expected_groups)
    validate_svg(args.dark, expected_groups)
    print(
        "project map validation passed: "
        f"{data.get('repositoryCount', 0)} repositories, "
        f"{expected_groups} categories, no preview overlaps, public config clean"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, json.JSONDecodeError, ET.ParseError) as error:
        print(f"project map validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
