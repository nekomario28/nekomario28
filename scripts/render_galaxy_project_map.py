#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
from typing import Any

WIDTH = 760
HEIGHT = 560
OWNER_X = WIDTH / 2
OWNER_Y = 275.0
SAFE_LEFT = 18.0
SAFE_RIGHT = WIDTH - 18.0
SAFE_TOP = 64.0
SAFE_BOTTOM = 486.0


def fnv1a(value: str) -> int:
    result = 2166136261
    for character in value:
        result ^= ord(character)
        result = (result * 16777619) & 0xFFFFFFFF
    return result


def display_label(label: str, maximum: int = 28) -> str:
    return label if len(label) <= maximum else f"{label[: maximum - 1]}…"


def node_radius(node: dict[str, Any]) -> float:
    node_type = str(node.get("type", "repository"))
    if node_type == "owner":
        return 35.0
    if node_type == "group":
        return 24.0
    return 11.0 + min(3.0, float(node.get("stars", 0) or 0))


def label_width(node: dict[str, Any]) -> float:
    label = display_label(str(node.get("label", "")))
    node_type = str(node.get("type", "repository"))
    multiplier = 6.8 if node_type == "group" else 7.0 if node_type == "owner" else 6.2
    maximum = 150.0 if node_type == "owner" else 194.0
    return max(58.0, min(maximum, 18.0 + len(label) * multiplier))


def collision_size(node: dict[str, Any]) -> tuple[float, float]:
    radius = node_radius(node)
    width = max(radius * 2 + 18, label_width(node))
    height = radius * 2 + (34 if node.get("type") == "group" else 31)
    return width, height


def mobility(node: dict[str, Any]) -> float:
    if node.get("type") == "owner":
        return 0.0
    if node.get("type") == "group":
        return 0.24
    return 1.0


def sorted_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(nodes, key=lambda node: (fnv1a(str(node.get("id", ""))), str(node.get("id", ""))))


def build_world_layout(project_map: dict[str, Any]) -> tuple[dict[str, list[Any]], dict[str, str]]:
    nodes = project_map["nodes"]
    groups = [node for node in nodes if node.get("type") == "group"]
    repositories = [node for node in nodes if node.get("type") == "repository"]
    repository_by_id = {str(node["id"]): node for node in repositories}
    members_by_group: dict[str, list[dict[str, Any]]] = {}
    parent_by_repository: dict[str, str] = {}

    for link in project_map["links"]:
        if link.get("type") != "member":
            continue
        group_id = str(link["source"])
        repository_id = str(link["target"])
        repository = repository_by_id.get(repository_id)
        if repository is None:
            continue
        members_by_group.setdefault(group_id, []).append(repository)
        parent_by_repository.setdefault(repository_id, group_id)

    world: dict[str, list[Any]] = {}
    owner = next(node for node in nodes if node.get("type") == "owner")
    world[str(owner["id"])] = [0.0, 0.0, owner, 0.0, 0.0]

    group_anchors: dict[str, tuple[float, float, float]] = {}
    group_count = max(1, len(groups))
    for index, group in enumerate(groups):
        ring = index // 6
        index_in_ring = index % 6
        ring_count = min(6, group_count - ring * 6)
        angle = -math.pi / 2 + index_in_ring * 2 * math.pi / max(1, ring_count)
        rx = 235 + ring * 155
        ry = 178 + ring * 118
        x = math.cos(angle) * rx
        y = math.sin(angle) * ry
        group_id = str(group["id"])
        group_anchors[group_id] = (x, y, angle)
        world[group_id] = [x, y, group, x, y]

    for group in groups:
        group_id = str(group["id"])
        gx, gy, outward_angle = group_anchors[group_id]
        members = sorted_nodes(members_by_group.get(group_id, []))
        cursor = 0
        orbit = 0
        while cursor < len(members):
            capacity = 4 + orbit * 2
            batch = members[cursor : cursor + capacity]
            radius = 112 + orbit * 82
            span = 0.0 if len(batch) <= 1 else min(1.82, 0.72 + len(batch) * 0.21)
            for slot, repository in enumerate(batch):
                fraction = 0.5 if len(batch) <= 1 else slot / (len(batch) - 1)
                jitter = ((fnv1a(str(repository["id"])) % 1000) / 1000 - 0.5) * 0.11
                angle = outward_angle - span / 2 + span * fraction + jitter
                x = gx + math.cos(angle) * radius
                y = gy + math.sin(angle) * radius
                repository_id = str(repository["id"])
                world[repository_id] = [x, y, repository, x, y]
            cursor += len(batch)
            orbit += 1

    ungrouped = sorted_nodes(
        [node for node in repositories if str(node["id"]) not in parent_by_repository]
    )
    for index, repository in enumerate(ungrouped):
        angle = -math.pi / 2 + index * 2 * math.pi / max(1, len(ungrouped))
        ring = index // 10
        x = math.cos(angle) * (445 + ring * 120)
        y = math.sin(angle) * (325 + ring * 90)
        repository_id = str(repository["id"])
        world[repository_id] = [x, y, repository, x, y]

    return world, parent_by_repository


def separate_pair(first: list[Any], second: list[Any], padding_x: float, padding_y: float, strength: float) -> bool:
    ax, ay, a_node = first[0], first[1], first[2]
    bx, by, b_node = second[0], second[1], second[2]
    a_width, a_height = collision_size(a_node)
    b_width, b_height = collision_size(b_node)
    dx, dy = bx - ax, by - ay
    if abs(dx) < 0.001 and abs(dy) < 0.001:
        dx = 0.01 if fnv1a(str(a_node["id"]) + str(b_node["id"])) % 2 else -0.01
        dy = 0.01
    overlap_x = (a_width + b_width) / 2 + padding_x - abs(dx)
    overlap_y = (a_height + b_height) / 2 + padding_y - abs(dy)
    if overlap_x <= 0 or overlap_y <= 0:
        return False

    use_x = overlap_x < overlap_y
    overlap = (overlap_x if use_x else overlap_y) * strength
    direction = 1 if (dx if use_x else dy) >= 0 else -1
    a_mobility = mobility(a_node)
    b_mobility = mobility(b_node)
    total = a_mobility + b_mobility
    if total <= 0:
        return False
    a_share = a_mobility / total
    b_share = b_mobility / total
    if use_x:
        first[0] -= direction * overlap * a_share
        second[0] += direction * overlap * b_share
    else:
        first[1] -= direction * overlap * a_share
        second[1] += direction * overlap * b_share
    return True


def relax_layout(positions: dict[str, list[Any]], iterations: int, pull: bool, screen: bool = False) -> None:
    values = list(positions.values())
    for _ in range(iterations):
        moved = False
        for first_index in range(len(values)):
            for second_index in range(first_index + 1, len(values)):
                moved = separate_pair(
                    values[first_index],
                    values[second_index],
                    26 if screen else 30,
                    22 if screen else 25,
                    0.56 if screen else 0.58,
                ) or moved

        if pull:
            for value in values:
                node = value[2]
                if node.get("type") == "owner":
                    continue
                strength = 0.07 if node.get("type") == "group" else 0.022
                value[0] += (value[3] - value[0]) * strength
                value[1] += (value[4] - value[1]) * strength

        if screen:
            for value in values:
                width, height = collision_size(value[2])
                value[0] = max(SAFE_LEFT + width / 2, min(SAFE_RIGHT - width / 2, value[0]))
                value[1] = max(SAFE_TOP + height / 2, min(SAFE_BOTTOM - height / 2, value[1]))

        if not moved:
            break


def fit_world_to_preview(world: dict[str, list[Any]]) -> dict[str, list[Any]]:
    relax_layout(world, 260, pull=True, screen=False)
    relax_layout(world, 110, pull=False, screen=False)

    min_x = min(value[0] for value in world.values())
    max_x = max(value[0] for value in world.values())
    min_y = min(value[1] for value in world.values())
    max_y = max(value[1] for value in world.values())
    available_width = SAFE_RIGHT - SAFE_LEFT - 150
    available_height = SAFE_BOTTOM - SAFE_TOP - 110
    scale = min(
        1.0,
        available_width / max(1.0, max_x - min_x),
        available_height / max(1.0, max_y - min_y),
    )
    world_cx = (min_x + max_x) / 2
    world_cy = (min_y + max_y) / 2

    screen: dict[str, list[Any]] = {}
    for node_id, value in world.items():
        x = OWNER_X + (value[0] - world_cx) * scale
        y = OWNER_Y + (value[1] - world_cy) * scale
        screen[node_id] = [x, y, value[2], x, y]

    owner_id = next(node_id for node_id, value in screen.items() if value[2].get("type") == "owner")
    owner_dx = OWNER_X - screen[owner_id][0]
    owner_dy = OWNER_Y - screen[owner_id][1]
    for value in screen.values():
        value[0] += owner_dx
        value[1] += owner_dy
        value[3] += owner_dx
        value[4] += owner_dy

    relax_layout(screen, 240, pull=True, screen=True)
    relax_layout(screen, 160, pull=False, screen=True)
    return screen


def preview_positions(project_map: dict[str, Any]) -> dict[str, tuple[float, float, dict[str, Any]]]:
    world, _ = build_world_layout(project_map)
    screen = fit_world_to_preview(world)
    return {
        node_id: (value[0], value[1], value[2])
        for node_id, value in screen.items()
    }


def theme_colors(theme: str) -> dict[str, str]:
    if theme == "dark":
        return {
            "background": "#0d1117",
            "panel": "#161b22",
            "border": "#30363d",
            "edge": "#484f58",
            "relation": "#f0883e",
            "text": "#f0f6fc",
            "muted": "#8b949e",
            "fork": "#8b949e",
            "repository": "#3fb950",
            "group": "#1f6feb",
            "owner": "#58a6ff",
        }
    return {
        "background": "#f6f8fa",
        "panel": "#ffffff",
        "border": "#d0d7de",
        "edge": "#afb8c1",
        "relation": "#bc4c00",
        "text": "#24292f",
        "muted": "#57606a",
        "fork": "#8c959f",
        "repository": "#2da44e",
        "group": "#0969da",
        "owner": "#54aeff",
    }


def render(project_map: dict[str, Any], output: Path, theme: str) -> None:
    colors = theme_colors(theme)
    positions = preview_positions(project_map)
    owner_id = f"user:{project_map['owner']}"
    owner_x, owner_y, owner_node = positions[owner_id]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Animated galaxy-style preview of the interactive public project map">',
        "<defs>",
        f'<radialGradient id="background" cx="50%" cy="46%" r="75%"><stop offset="0" stop-color="{colors["panel"]}"/><stop offset="1" stop-color="{colors["background"]}"/></radialGradient>',
        '<filter id="glow" x="-120%" y="-120%" width="340%" height="340%"><feGaussianBlur stdDeviation="4" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        "</defs>",
        "<style>",
        ".flow{stroke-dasharray:4 9;animation:flow 7s linear infinite}",
        ".halo{transform-origin:center;animation:pulse 3.2s ease-in-out infinite}",
        ".category{animation:breathe 4.8s ease-in-out infinite}",
        ".orbit{stroke-dasharray:2 8;opacity:.12}",
        ".cta{animation:lift 2.4s ease-in-out infinite}",
        ".arrow{animation:nudge 1.6s ease-in-out infinite}",
        "@keyframes flow{to{stroke-dashoffset:-52}}",
        "@keyframes pulse{0%,100%{opacity:.2;transform:scale(.92)}50%{opacity:.05;transform:scale(1.18)}}",
        "@keyframes breathe{0%,100%{opacity:1}50%{opacity:.82}}",
        "@keyframes lift{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}",
        "@keyframes nudge{0%,100%{transform:translateX(0)}50%{transform:translateX(4px)}}",
        "@media(prefers-reduced-motion:reduce){*{animation:none!important}}",
        "</style>",
        f'<rect x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}" rx="16" fill="url(#background)" stroke="{colors["border"]}"/>',
        f'<text x="{WIDTH / 2:.1f}" y="31" text-anchor="middle" fill="{colors["text"]}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="19" font-weight="650">Interactive Project Map</text>',
        f'<text x="{WIDTH / 2:.1f}" y="51" text-anchor="middle" fill="{colors["muted"]}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="11.5">A galaxy-style constellation of public projects</text>',
    ]

    members_by_group: dict[str, int] = {}
    for link in project_map["links"]:
        if link.get("type") == "member":
            members_by_group[str(link["source"])] = members_by_group.get(str(link["source"]), 0) + 1

    for node_id, (x, y, node) in positions.items():
        if node.get("type") != "group":
            continue
        count = members_by_group.get(node_id, 0)
        if count <= 0:
            continue
        radius = 42 + min(38, count * 5)
        parts.append(
            f'<ellipse class="orbit" cx="{x:.1f}" cy="{y:.1f}" rx="{radius:.1f}" ry="{radius * 0.58:.1f}" fill="none" stroke="{colors["group"]}" stroke-width="1"/>'
        )

    structural_types = {"owns", "contains", "member"}
    for index, link in enumerate(project_map["links"]):
        source = positions.get(str(link["source"]))
        target = positions.get(str(link["target"]))
        if source is None or target is None:
            continue
        structural = link.get("type") in structural_types
        stroke = colors["edge"] if structural else colors["relation"]
        stroke_width = 1.15 if structural else 2.2
        opacity = 0.55 if structural else 0.9
        parts.append(
            f'<line class="flow" style="animation-delay:-{index * 0.31:.2f}s" x1="{source[0]:.1f}" y1="{source[1]:.1f}" x2="{target[0]:.1f}" y2="{target[1]:.1f}" stroke="{stroke}" stroke-width="{stroke_width}" opacity="{opacity}"/>'
        )

    parts.append(f'<circle class="halo" cx="{owner_x:.1f}" cy="{owner_y:.1f}" r="56" fill="{colors["owner"]}" opacity="0.14"/>')
    parts.append(f'<circle cx="{owner_x:.1f}" cy="{owner_y:.1f}" r="35" fill="{colors["owner"]}" stroke="{colors["panel"]}" stroke-width="3" filter="url(#glow)"/>')
    parts.append(f'<text x="{owner_x:.1f}" y="{owner_y + 5:.1f}" text-anchor="middle" fill="#ffffff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="15" font-weight="750">N</text>')
    parts.append(f'<text x="{owner_x:.1f}" y="{owner_y + 56:.1f}" text-anchor="middle" fill="{colors["text"]}" stroke="{colors["background"]}" stroke-width="4" paint-order="stroke" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="11.5" font-weight="650">{html.escape(str(owner_node["label"]))}</text>')

    ordered = sorted(
        ((node_id, value) for node_id, value in positions.items() if node_id != owner_id),
        key=lambda item: (0 if item[1][2].get("type") == "group" else 1, fnv1a(item[0])),
    )
    for index, (_, (x, y, node)) in enumerate(ordered):
        node_type = str(node.get("type", "repository"))
        radius = node_radius(node)
        fill = colors["group"] if node_type == "group" else colors["fork"] if node.get("fork") else colors["repository"]
        category_class = ' class="category"' if node_type == "group" else ""
        delay = f' style="animation-delay:-{index * 0.23:.2f}s"' if node_type == "group" else ""
        parts.append(f'<circle{category_class}{delay} cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" stroke="{colors["panel"]}" stroke-width="{2.2 if node_type == "group" else 1.5}"/>')
        if node_type == "group":
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius + 6:.1f}" fill="none" stroke="{fill}" stroke-width="1" opacity="0.26"/>')
        label = html.escape(display_label(str(node.get("label", ""))))
        label_y = y + radius + (17 if node_type == "group" else 15)
        parts.append(f'<text x="{x:.1f}" y="{label_y:.1f}" text-anchor="middle" fill="{colors["text"]}" stroke="{colors["background"]}" stroke-width="4" paint-order="stroke" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="{11 if node_type == "group" else 10.2}" font-weight="{650 if node_type == "group" else 500}">{label}</text>')

    parts.extend(
        [
            '<g class="cta">',
            f'<rect x="246" y="503" width="268" height="40" rx="20" fill="{colors["group"]}"/>',
            '<text x="372" y="528" text-anchor="middle" fill="#ffffff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="12.5" font-weight="650">Open the interactive map</text>',
            '<text class="arrow" x="481" y="528" text-anchor="middle" fill="#ffffff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="16" font-weight="700">→</text>',
            "</g>",
            f'<text x="24" y="543" fill="{colors["muted"]}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="10.5">{project_map.get("repositoryCount", 0)} public projects · {project_map.get("groupCount", 0)} curated areas</text>',
            "</svg>",
        ]
    )
    output.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render deterministic galaxy-style project map previews")
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--light", type=Path, required=True)
    parser.add_argument("--dark", type=Path, required=True)
    args = parser.parse_args()
    project_map = json.loads(args.json.read_text(encoding="utf-8"))
    render(project_map, args.light, "light")
    render(project_map, args.dark, "dark")


if __name__ == "__main__":
    main()
