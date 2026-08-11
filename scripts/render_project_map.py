#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import math
import random
from pathlib import Path
from typing import Any

WIDTH = 760
HEIGHT = 560
OWNER_X = 380.0
OWNER_Y = 275.0
Y_FLATTEN = 0.63
SAFE_LEFT = 16.0
SAFE_RIGHT = 744.0
SAFE_TOP = 64.0
SAFE_BOTTOM = 492.0


def display_label(label: str, maximum: int = 28) -> str:
    return label if len(label) <= maximum else f"{label[: maximum - 1]}…"


def node_radius(node: dict[str, Any]) -> float:
    node_type = str(node.get("type", "repository"))
    if node_type == "owner":
        return 13.0
    if node_type == "group":
        return 6.0
    return 9.0 + min(3.0, float(node.get("stars", 0) or 0))


def label_width(node: dict[str, Any]) -> float:
    label = display_label(str(node.get("label", "")))
    multiplier = 6.2 if node.get("type") == "group" else 5.9
    return max(48.0, min(176.0, 14.0 + len(label) * multiplier))


def collision_size(node: dict[str, Any]) -> tuple[float, float]:
    radius = node_radius(node)
    return max(radius * 2 + 12, label_width(node)), radius * 2 + 27


def stable_hash(value: str) -> int:
    result = 2166136261
    for character in value:
        result ^= ord(character)
        result = (result * 16777619) & 0xFFFFFFFF
    return result


def membership(project_map: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    repositories = {
        str(node["id"]): node
        for node in project_map.get("nodes", [])
        if node.get("type") == "repository"
    }
    members: dict[str, list[dict[str, Any]]] = {}
    grouped: set[str] = set()
    for link in project_map.get("links", []):
        if link.get("type") != "member":
            continue
        group_id = str(link.get("source", ""))
        repository_id = str(link.get("target", ""))
        repository = repositories.get(repository_id)
        if repository is None:
            continue
        members.setdefault(group_id, []).append(repository)
        grouped.add(repository_id)
    for values in members.values():
        values.sort(key=lambda node: str(node.get("id", "")))
    return members, grouped


def group_geometry(project_map: dict[str, Any]) -> list[tuple[dict[str, Any], float]]:
    groups = sorted(
        (node for node in project_map.get("nodes", []) if node.get("type") == "group"),
        key=lambda node: str(node.get("id", "")),
    )
    count = max(1, len(groups))
    return [
        (group, -math.pi / 2 + index * 2 * math.pi / count)
        for index, group in enumerate(groups)
    ]


def planned_radius(repository: dict[str, Any], slot_index: int) -> float:
    lane = slot_index % 3
    tier = slot_index // 3
    jitter = stable_hash(f"{repository.get('id')}:preview-radius") % 15 - 7
    return max(118.0, min(276.0, 128.0 + lane * 61.0 + tier * 23.0 + jitter))


def clamp_position(value: list[Any]) -> None:
    width, height = collision_size(value[2])
    value[0] = max(SAFE_LEFT + width / 2, min(SAFE_RIGHT - width / 2, value[0]))
    value[1] = max(SAFE_TOP + height / 2, min(SAFE_BOTTOM - height / 2, value[1]))


def mobility(node: dict[str, Any]) -> float:
    if node.get("type") == "owner":
        return 0.0
    if node.get("type") == "group":
        return 0.28
    return 1.0


def separate_pair(first: list[Any], second: list[Any]) -> bool:
    a_width, a_height = collision_size(first[2])
    b_width, b_height = collision_size(second[2])
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    overlap_x = (a_width + b_width) / 2 + 11 - abs(dx)
    overlap_y = (a_height + b_height) / 2 + 9 - abs(dy)
    if overlap_x <= 0 or overlap_y <= 0:
        return False

    a_mobility = mobility(first[2])
    b_mobility = mobility(second[2])
    total = a_mobility + b_mobility
    if total <= 0:
        return False
    a_share = a_mobility / total
    b_share = b_mobility / total

    # Use whichever axis resolves the overlap with less movement. This is only the
    # finite README layout solver; the interactive animation uses orbital spacing.
    if overlap_x <= overlap_y:
        direction = 1 if dx >= 0 else -1
        push = overlap_x + 0.6
        first[0] -= direction * push * a_share
        second[0] += direction * push * b_share
    else:
        direction = 1 if dy >= 0 else -1
        push = overlap_y + 0.6
        first[1] -= direction * push * a_share
        second[1] += direction * push * b_share
    clamp_position(first)
    clamp_position(second)
    return True


def relax_positions(values: dict[str, list[Any]], iterations: int, pull: bool) -> None:
    entries = list(values.values())
    for _ in range(iterations):
        moved = False
        for first_index in range(len(entries)):
            for second_index in range(first_index + 1, len(entries)):
                moved = separate_pair(entries[first_index], entries[second_index]) or moved

        if pull:
            for value in entries:
                node = value[2]
                if node.get("type") == "owner":
                    value[0], value[1] = OWNER_X, OWNER_Y
                    continue
                strength = 0.065 if node.get("type") == "group" else 0.018
                value[0] += (value[3] - value[0]) * strength
                value[1] += (value[4] - value[1]) * strength
                clamp_position(value)
        if not moved and not pull:
            break


def preview_positions(project_map: dict[str, Any]) -> dict[str, tuple[float, float, dict[str, Any]]]:
    nodes = project_map.get("nodes", [])
    owner = next(node for node in nodes if node.get("type") == "owner")
    groups = group_geometry(project_map)
    members_by_group, grouped_ids = membership(project_map)
    positions: dict[str, list[Any]] = {
        str(owner["id"]): [OWNER_X, OWNER_Y, owner, OWNER_X, OWNER_Y]
    }

    group_centers: dict[str, tuple[float, float]] = {}
    for group, base_phase in groups:
        group_id = str(group["id"])
        members = members_by_group.get(group_id, [])
        sector_width = min(0.86, (2 * math.pi / max(1, len(groups))) * 0.54)
        member_points: list[tuple[float, float]] = []
        for slot_index, repository in enumerate(members):
            radius = planned_radius(repository, slot_index)
            slot_center = 0.0 if len(members) <= 1 else slot_index / (len(members) - 1) - 0.5
            spiral = ((radius - 128.0) / 148.0) * 0.38
            angle = base_phase + slot_center * sector_width + spiral
            x = OWNER_X + math.cos(angle) * radius
            y = OWNER_Y + math.sin(angle) * radius * Y_FLATTEN
            node_id = str(repository["id"])
            positions[node_id] = [x, y, repository, x, y]
            member_points.append((x, y))

        if member_points:
            centroid_x = sum(point[0] for point in member_points) / len(member_points)
            centroid_y = sum(point[1] for point in member_points) / len(member_points)
            # Pull the semantic label slightly toward the nucleus so it does not read
            # as a parent planet sitting on top of one repository.
            group_x = OWNER_X + (centroid_x - OWNER_X) * 0.78
            group_y = OWNER_Y + (centroid_y - OWNER_Y) * 0.78
        else:
            group_x = OWNER_X + math.cos(base_phase) * 155
            group_y = OWNER_Y + math.sin(base_phase) * 155 * Y_FLATTEN
        group_centers[group_id] = (group_x, group_y)
        positions[group_id] = [group_x, group_y, group, group_x, group_y]

    ungrouped = sorted(
        (
            node
            for node in nodes
            if node.get("type") == "repository" and str(node.get("id")) not in grouped_ids
        ),
        key=lambda node: str(node.get("id", "")),
    )
    for index, repository in enumerate(ungrouped):
        angle = -math.pi / 4 + index * 2 * math.pi / max(1, len(ungrouped))
        radius = 272
        x = OWNER_X + math.cos(angle) * radius
        y = OWNER_Y + math.sin(angle) * radius * Y_FLATTEN
        node_id = str(repository["id"])
        positions[node_id] = [x, y, repository, x, y]

    relax_positions(positions, 220, pull=True)
    relax_positions(positions, 180, pull=False)
    return {
        node_id: (float(value[0]), float(value[1]), value[2])
        for node_id, value in positions.items()
    }


def svg_path_for_arm(base_phase: float) -> str:
    points: list[tuple[float, float]] = []
    for radius in range(92, 294, 8):
        angle = base_phase + ((radius - 128.0) / 148.0) * 0.38
        points.append(
            (
                OWNER_X + math.cos(angle) * radius,
                OWNER_Y + math.sin(angle) * radius * Y_FLATTEN,
            )
        )
    if not points:
        return ""
    commands = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    commands.extend(f"L {x:.1f} {y:.1f}" for x, y in points[1:])
    return " ".join(commands)


def render(project_map: dict[str, Any], path: Path, theme: str) -> None:
    dark = theme == "dark"
    colors = {
        "bg": "#0d1117" if dark else "#f6f8fa",
        "panel": "#161b22" if dark else "#ffffff",
        "text": "#f0f6fc" if dark else "#24292f",
        "muted": "#8b949e" if dark else "#57606a",
        "border": "#30363d" if dark else "#d0d7de",
        "owner": "#58a6ff" if dark else "#54aeff",
        "group": "#1f6feb" if dark else "#0969da",
        "repo": "#3fb950" if dark else "#2da44e",
        "fork": "#8b949e",
        "relation": "#f0883e" if dark else "#bc4c00",
    }
    positions = preview_positions(project_map)
    groups = group_geometry(project_map)
    rng = random.Random(280828)

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="560" viewBox="0 0 760 560" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">Interactive Project Map preview</title>",
        "<desc id=\"desc\">A common-center galaxy of public GitHub projects grouped into spiral sectors.</desc>",
        "<defs>",
        f'<radialGradient id="nucleus" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="{colors["owner"]}" stop-opacity="0.20"/><stop offset="45%" stop-color="{colors["owner"]}" stop-opacity="0.045"/><stop offset="100%" stop-color="{colors["owner"]}" stop-opacity="0"/></radialGradient>',
        "</defs>",
        "<style>",
        ".label{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;text-anchor:middle;paint-order:stroke;stroke-width:3px;stroke-linejoin:round}",
        ".repository{stroke-width:1}.category{fill:none;stroke-width:1.2}.structural{stroke-width:.7}.relation{stroke-width:1.4}",
        "</style>",
        f'<rect x="1" y="1" width="758" height="558" rx="10" fill="{colors["bg"]}" stroke="{colors["border"]}"/>',
        '<g id="cosmic-preview" pointer-events="none">',
    ]

    # A sparse stellar disk follows the same spiral sectors instead of acting as an
    # unrelated screen-space starfield.
    for index in range(92):
        group, base_phase = groups[index % max(1, len(groups))] if groups else ({}, 0.0)
        radius = 70 + math.sqrt(rng.random()) * 242
        angle = base_phase + ((radius - 128.0) / 148.0) * 0.38 + rng.uniform(-0.34, 0.34)
        x = OWNER_X + math.cos(angle) * radius
        y = OWNER_Y + math.sin(angle) * radius * Y_FLATTEN
        r = rng.choice((0.45, 0.6, 0.75, 0.95))
        opacity = rng.uniform(0.07 if not dark else 0.10, 0.22 if not dark else 0.30)
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{colors["text"]}" opacity="{opacity:.3f}"/>')

    for ring_index, radius in enumerate((132, 194, 256)):
        lines.append(
            f'<ellipse id="galaxy-ring-{ring_index}" cx="{OWNER_X}" cy="{OWNER_Y}" rx="{radius}" ry="{radius * Y_FLATTEN:.1f}" fill="none" stroke="{colors["muted"]}" stroke-width="0.55" opacity="{0.075 if dark else 0.050}"/>'
        )

    for index, (_, base_phase) in enumerate(groups):
        arm_path = svg_path_for_arm(base_phase)
        lines.append(
            f'<path id="spiral-sector-{index}" d="{arm_path}" fill="none" stroke="{colors["group"]}" stroke-width="18" stroke-linecap="round" opacity="{0.025 if dark else 0.015}"/>'
        )
        lines.append(
            f'<path d="{arm_path}" fill="none" stroke="{colors["group"]}" stroke-width="0.75" stroke-linecap="round" opacity="{0.14 if dark else 0.085}"/>'
        )

    lines.extend(
        [
            f'<circle class="halo" cx="{OWNER_X}" cy="{OWNER_Y}" r="92" fill="url(#nucleus)"/>',
            "</g>",
        ]
    )

    for link in project_map.get("links", []):
        source = positions.get(str(link.get("source", "")))
        target = positions.get(str(link.get("target", "")))
        if not source or not target:
            continue
        relation = link.get("type") not in {"contains", "member", "owns"}
        color = colors["relation"] if relation else colors["muted"]
        opacity = 0.72 if relation else 0.075
        css_class = "relation" if relation else "structural"
        lines.append(
            f'<line class="{css_class}" x1="{source[0]:.1f}" y1="{source[1]:.1f}" x2="{target[0]:.1f}" y2="{target[1]:.1f}" stroke="{color}" opacity="{opacity}"/>'
        )

    for node_id, (x, y, node) in positions.items():
        node_type = str(node.get("type", "repository"))
        label = html.escape(display_label(str(node.get("label", ""))))
        if node_type == "owner":
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{colors["owner"]}"/>')
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="none" stroke="{colors["owner"]}" stroke-width="1" opacity="0.62"/>')
            label_y = y + 25
            font_size = 13
        elif node_type == "group":
            lines.append(f'<circle class="category" cx="{x:.1f}" cy="{y:.1f}" r="5" stroke="{colors["group"]}"/>')
            label_y = y + 18
            font_size = 11
        else:
            fill = colors["fork"] if node.get("fork") else colors["repo"]
            lines.append(f'<circle class="repository" cx="{x:.1f}" cy="{y:.1f}" r="{node_radius(node):.1f}" fill="{fill}" stroke="{colors["bg"]}"/>')
            label_y = y + node_radius(node) + 14
            font_size = 10.5
        lines.append(
            f'<text class="label" x="{x:.1f}" y="{label_y:.1f}" fill="{colors["text"]}" stroke="{colors["bg"]}" font-size="{font_size}">{label}</text>'
        )

    lines.extend(
        [
            f'<text x="24" y="31" fill="{colors["text"]}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="18" font-weight="600">Interactive Project Map</text>',
            f'<text x="24" y="49" fill="{colors["muted"]}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="10.5">A common-center galaxy of public projects</text>',
            '<a href="https://nekomario28.github.io/nekomario28/" target="_blank">',
            f'<text x="380" y="535" fill="{colors["muted"]}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="11" text-anchor="middle">Open the interactive map →</text>',
            "</a>",
            "</svg>",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render common-center galaxy project map previews")
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--light", type=Path, required=True)
    parser.add_argument("--dark", type=Path, required=True)
    args = parser.parse_args()
    project_map = json.loads(args.json.read_text(encoding="utf-8"))
    render(project_map, args.light, "light")
    render(project_map, args.dark, "dark")


if __name__ == "__main__":
    main()
