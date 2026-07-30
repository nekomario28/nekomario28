#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any


EMPTY_CONFIG: dict[str, Any] = {
    "schemaVersion": 2,
    "groups": [],
    "relations": [],
}


def github_get(url: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nekomario28-profile-map",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_public_repositories(username: str) -> list[dict[str, Any]]:
    repositories: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/users/{username}/repos"
            f"?type=owner&sort=updated&per_page=100&page={page}"
        )
        batch = github_get(url)
        if not isinstance(batch, list):
            raise RuntimeError("GitHub returned an unexpected repository response")
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return [
        repository
        for repository in repositories
        if not repository.get("private") and repository.get("name") != username
    ]


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return dict(EMPTY_CONFIG)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("top-level value must be an object")
        groups = raw.get("groups", [])
        relations = raw.get("relations", [])
        if not isinstance(groups, list) or not isinstance(relations, list):
            raise ValueError("groups and relations must be arrays")
        return {
            "schemaVersion": raw.get("schemaVersion", 2),
            "groups": groups,
            "relations": relations,
        }
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"warning: ignoring project map config {path}: {error}", file=sys.stderr)
        return dict(EMPTY_CONFIG)


def build_map(
    username: str,
    repositories: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    repository_names = {str(repository["name"]) for repository in repositories}
    nodes: list[dict[str, Any]] = [
        {
            "id": f"user:{username}",
            "label": username,
            "type": "owner",
            "url": f"https://github.com/{username}",
        }
    ]
    links: list[dict[str, str]] = []
    link_keys: set[tuple[str, str, str]] = set()

    def add_link(source: str, target: str, link_type: str, label: str = "") -> None:
        key = (source, target, link_type)
        if key in link_keys:
            return
        link_keys.add(key)
        link: dict[str, str] = {"source": source, "target": target, "type": link_type}
        if label:
            link["label"] = label
        links.append(link)

    valid_groups: list[dict[str, Any]] = []
    member_group_ids: dict[str, list[str]] = {name: [] for name in repository_names}
    member_group_labels: dict[str, list[str]] = {name: [] for name in repository_names}

    for raw_group in config.get("groups", []):
        if not isinstance(raw_group, dict):
            continue
        group_id = str(raw_group.get("id", "")).strip()
        label = str(raw_group.get("label", "")).strip()
        raw_members = raw_group.get("repositories", [])
        if not group_id or not label or not isinstance(raw_members, list):
            continue
        members = [str(member) for member in raw_members if str(member) in repository_names]
        if not members:
            continue

        group = {
            "id": group_id,
            "label": label,
            "description": str(raw_group.get("description", "")).strip(),
            "repositories": members,
        }
        valid_groups.append(group)
        group_node_id = f"group:{group_id}"
        nodes.append(
            {
                "id": group_node_id,
                "label": label,
                "type": "group",
                "description": group["description"],
                "repositoryCount": len(members),
            }
        )
        add_link(f"user:{username}", group_node_id, "contains")
        for member in members:
            member_group_ids[member].append(group_id)
            member_group_labels[member].append(label)
            add_link(group_node_id, f"repository:{member}", "member")

    for repository in repositories:
        name = str(repository["name"])
        node_id = f"repository:{name}"
        nodes.append(
            {
                "id": node_id,
                "label": name,
                "type": "repository",
                "url": repository.get("html_url"),
                "description": repository.get("description") or "",
                "language": repository.get("language"),
                "topics": repository.get("topics", []),
                "categories": member_group_labels[name],
                "categoryIds": member_group_ids[name],
                "stars": repository.get("stargazers_count", 0),
                "fork": bool(repository.get("fork")),
                "archived": bool(repository.get("archived")),
                "updatedAt": repository.get("updated_at"),
            }
        )
        if not member_group_ids[name]:
            add_link(f"user:{username}", node_id, "owns")

    for raw_relation in config.get("relations", []):
        if not isinstance(raw_relation, dict):
            continue
        source = str(raw_relation.get("source", "")).strip()
        target = str(raw_relation.get("target", "")).strip()
        relation_type = str(raw_relation.get("type", "related")).strip() or "related"
        label = str(raw_relation.get("label", "")).strip()
        if source not in repository_names or target not in repository_names:
            continue
        add_link(
            f"repository:{source}",
            f"repository:{target}",
            relation_type,
            label,
        )

    return {
        "owner": username,
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repositoryCount": len(repositories),
        "groupCount": len(valid_groups),
        "nodes": nodes,
        "links": links,
    }


def display_label(label: str, maximum: int = 28) -> str:
    if len(label) <= maximum:
        return label
    return f"{label[: maximum - 1]}…"


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
    estimated = 16 + len(label) * (6.4 if node_type == "group" else 6.0)
    return max(54.0, min(178.0, estimated))


def collision_size(node: dict[str, Any]) -> tuple[float, float]:
    radius = node_radius(node)
    width = max(radius * 2 + 16, label_width(node))
    height = radius * 2 + (30 if node.get("type") == "group" else 27)
    return width, height


def preview_positions(
    project_map: dict[str, Any],
    width: int,
    height: int,
) -> dict[str, tuple[float, float, dict[str, Any]]]:
    cx, cy = width / 2, 275
    group_nodes = [node for node in project_map["nodes"] if node.get("type") == "group"]
    repository_nodes = [
        node for node in project_map["nodes"] if node.get("type") == "repository"
    ]
    repository_by_id = {str(node["id"]): node for node in repository_nodes}
    members_by_group: dict[str, list[dict[str, Any]]] = {}
    grouped_repository_ids: set[str] = set()

    for link in project_map["links"]:
        if link.get("type") != "member":
            continue
        group_id = str(link["source"])
        repository_id = str(link["target"])
        repository = repository_by_id.get(repository_id)
        if repository is None:
            continue
        members_by_group.setdefault(group_id, []).append(repository)
        grouped_repository_ids.add(repository_id)

    positions: dict[str, tuple[float, float, dict[str, Any]]] = {}
    anchors: dict[str, tuple[float, float]] = {}
    group_angles: dict[str, float] = {}
    group_count = max(1, len(group_nodes))

    for index, node in enumerate(group_nodes):
        angle = -math.pi / 2 + index * 2 * math.pi / group_count
        x = cx + 175 * math.cos(angle)
        y = cy + 100 * math.sin(angle)
        group_angles[str(node["id"])] = angle
        anchors[str(node["id"])] = (x, y)
        positions[str(node["id"])] = (x, y, node)

    for group in group_nodes:
        group_id = str(group["id"])
        group_x, group_y, _ = positions[group_id]
        angle = group_angles[group_id]
        outward_x, outward_y = math.cos(angle), math.sin(angle)
        tangent_x, tangent_y = -outward_y, outward_x
        members = members_by_group.get(group_id, [])
        columns = min(3, max(1, math.ceil(math.sqrt(len(members)))))
        for index, node in enumerate(members):
            row = index // columns
            column = index % columns
            items_in_row = min(columns, len(members) - row * columns)
            tangent_offset = (column - (items_in_row - 1) / 2) * 112
            if outward_y < -0.7 and row > 0:
                tangent_offset += 56
            if outward_y < -0.7:
                outward_offset = max(58, 94 - row * 32)
            elif outward_y > 0.7:
                outward_offset = 64 + row * 44
            else:
                outward_offset = 110 + row * 48
            x = group_x + outward_x * outward_offset + tangent_x * tangent_offset
            y = group_y + outward_y * outward_offset + tangent_y * tangent_offset
            node_id = str(node["id"])
            anchors[node_id] = (x, y)
            positions[node_id] = (x, y, node)

    ungrouped = [
        node for node in repository_nodes if str(node["id"]) not in grouped_repository_ids
    ]
    for index, node in enumerate(ungrouped):
        angle = -math.pi / 2 + index * 2 * math.pi / max(1, len(ungrouped))
        x = cx + 285 * math.cos(angle)
        y = cy + 190 * math.sin(angle)
        node_id = str(node["id"])
        anchors[node_id] = (x, y)
        positions[node_id] = (x, y, node)

    mutable = {
        node_id: [position[0], position[1], position[2]]
        for node_id, position in positions.items()
    }

    for _ in range(160):
        identifiers = list(mutable)
        moved = False
        for first in range(len(identifiers)):
            first_id = identifiers[first]
            ax, ay, a_node = mutable[first_id]
            a_width, a_height = collision_size(a_node)
            a_fixed = a_node.get("type") == "group"
            for second in range(first + 1, len(identifiers)):
                second_id = identifiers[second]
                bx, by, b_node = mutable[second_id]
                b_width, b_height = collision_size(b_node)
                b_fixed = b_node.get("type") == "group"
                dx, dy = bx - ax, by - ay
                overlap_x = (a_width + b_width) / 2 + 12 - abs(dx)
                overlap_y = (a_height + b_height) / 2 + 12 - abs(dy)
                if overlap_x <= 0 or overlap_y <= 0:
                    continue
                moved = True
                a_share = 0 if a_fixed else (1 if b_fixed else 0.5)
                b_share = 0 if b_fixed else (1 if a_fixed else 0.5)
                if overlap_x < overlap_y:
                    direction = 1 if dx >= 0 else -1
                    push = overlap_x + 0.1
                    mutable[first_id][0] -= direction * push * a_share
                    mutable[second_id][0] += direction * push * b_share
                else:
                    direction = 1 if dy >= 0 else -1
                    push = overlap_y + 0.1
                    mutable[first_id][1] -= direction * push * a_share
                    mutable[second_id][1] += direction * push * b_share
                ax, ay = mutable[first_id][0], mutable[first_id][1]

        for node_id, values in mutable.items():
            node = values[2]
            anchor_x, anchor_y = anchors[node_id]
            if node.get("type") == "group":
                values[0], values[1] = anchor_x, anchor_y
            else:
                values[0] += (anchor_x - values[0]) * 0.018
                values[1] += (anchor_y - values[1]) * 0.018
            node_width, node_height = collision_size(node)
            values[0] = max(20 + node_width / 2, min(width - 20 - node_width / 2, values[0]))
            values[1] = max(67 + node_height / 2, min(height - 91 - node_height / 2, values[1]))

        if not moved:
            break

    for _ in range(100):
        identifiers = list(mutable)
        moved = False
        for first in range(len(identifiers)):
            first_id = identifiers[first]
            ax, ay, a_node = mutable[first_id]
            a_width, a_height = collision_size(a_node)
            a_fixed = a_node.get("type") == "group"
            for second in range(first + 1, len(identifiers)):
                second_id = identifiers[second]
                bx, by, b_node = mutable[second_id]
                b_width, b_height = collision_size(b_node)
                b_fixed = b_node.get("type") == "group"
                dx, dy = bx - ax, by - ay
                overlap_x = (a_width + b_width) / 2 + 12 - abs(dx)
                overlap_y = (a_height + b_height) / 2 + 12 - abs(dy)
                if overlap_x <= 0 or overlap_y <= 0:
                    continue
                moved = True
                a_share = 0 if a_fixed else (1 if b_fixed else 0.5)
                b_share = 0 if b_fixed else (1 if a_fixed else 0.5)
                if overlap_x < overlap_y:
                    direction = 1 if dx >= 0 else -1
                    push = overlap_x + 0.1
                    mutable[first_id][0] -= direction * push * a_share
                    mutable[second_id][0] += direction * push * b_share
                else:
                    direction = 1 if dy >= 0 else -1
                    push = overlap_y + 0.1
                    mutable[first_id][1] -= direction * push * a_share
                    mutable[second_id][1] += direction * push * b_share
                ax, ay = mutable[first_id][0], mutable[first_id][1]

        for values in mutable.values():
            node_width, node_height = collision_size(values[2])
            values[0] = max(20 + node_width / 2, min(width - 20 - node_width / 2, values[0]))
            values[1] = max(67 + node_height / 2, min(height - 91 - node_height / 2, values[1]))
        if not moved:
            break

    return {
        node_id: (values[0], values[1], values[2])
        for node_id, values in mutable.items()
    }


def render_preview(project_map: dict[str, Any], output: Path, theme: str) -> None:
    if theme == "dark":
        background = "#0d1117"
        panel = "#161b22"
        border = "#30363d"
        edge = "#484f58"
        relation = "#f0883e"
        node_text = "#f0f6fc"
        fork = "#8b949e"
        repository = "#3fb950"
        group = "#1f6feb"
        owner_fill = "#58a6ff"
        muted = "#8b949e"
        halo = "#58a6ff"
    else:
        background = "#f6f8fa"
        panel = "#ffffff"
        border = "#d0d7de"
        edge = "#afb8c1"
        relation = "#bc4c00"
        node_text = "#24292f"
        fork = "#8c959f"
        repository = "#2da44e"
        group = "#0969da"
        owner_fill = "#54aeff"
        muted = "#57606a"
        halo = "#0969da"

    width, height = 760, 560
    cx, cy = width / 2, 275
    owner_id = f"user:{project_map['owner']}"
    positions = preview_positions(project_map, width, height)
    owner = html.escape(str(project_map["owner"]))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Animated Obsidian-style preview of the interactive public project map">',
        "<defs>",
        f'<radialGradient id="background" cx="50%" cy="43%" r="74%"><stop offset="0" stop-color="{panel}"/><stop offset="1" stop-color="{background}"/></radialGradient>',
        f'<filter id="glow" x="-120%" y="-120%" width="340%" height="340%"><feGaussianBlur stdDeviation="4" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        "</defs>",
        "<style>",
        ".flow{stroke-dasharray:4 9;animation:flow 7s linear infinite}",
        ".halo{transform-origin:center;animation:pulse 3.2s ease-in-out infinite}",
        ".cta{animation:lift 2.4s ease-in-out infinite}",
        ".arrow{animation:nudge 1.6s ease-in-out infinite}",
        ".category{animation:breathe 4.8s ease-in-out infinite}",
        "@keyframes flow{to{stroke-dashoffset:-52}}",
        "@keyframes pulse{0%,100%{opacity:.2;transform:scale(.92)}50%{opacity:.05;transform:scale(1.18)}}",
        "@keyframes lift{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}",
        "@keyframes nudge{0%,100%{transform:translateX(0)}50%{transform:translateX(4px)}}",
        "@keyframes breathe{0%,100%{opacity:1}50%{opacity:.82}}",
        "@media(prefers-reduced-motion:reduce){*{animation:none!important}}",
        "</style>",
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="16" fill="url(#background)" stroke="{border}"/>',
        f'<text x="{cx}" y="31" text-anchor="middle" fill="{node_text}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="19" font-weight="650">Interactive Project Map</text>',
        f'<text x="{cx}" y="51" text-anchor="middle" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="11.5">An Obsidian-style constellation of public projects</text>',
    ]

    structural_types = {"owns", "contains", "member"}
    for index, link in enumerate(project_map["links"]):
        source_id = str(link["source"])
        target_id = str(link["target"])
        source = (cx, cy) if source_id == owner_id else positions.get(source_id, (None, None, None))[:2]
        target = (cx, cy) if target_id == owner_id else positions.get(target_id, (None, None, None))[:2]
        if source[0] is None or target[0] is None:
            continue
        structural = link.get("type") in structural_types
        stroke = edge if structural else relation
        stroke_width = 1.15 if structural else 2.2
        opacity = 0.55 if structural else 0.9
        parts.append(
            f'<line class="flow" style="animation-delay:-{index * 0.31:.2f}s" x1="{source[0]:.1f}" y1="{source[1]:.1f}" x2="{target[0]:.1f}" y2="{target[1]:.1f}" stroke="{stroke}" stroke-width="{stroke_width}" opacity="{opacity}"/>'
        )

    parts.append(
        f'<circle class="halo" cx="{cx}" cy="{cy}" r="56" fill="{halo}" opacity="0.14"/>'
    )
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="35" fill="{owner_fill}" stroke="{panel}" stroke-width="3" filter="url(#glow)"/>'
    )
    parts.append(
        f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" fill="#ffffff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="15" font-weight="750">N</text>'
    )
    parts.append(
        f'<text x="{cx}" y="{cy + 56}" text-anchor="middle" fill="{node_text}" stroke="{background}" stroke-width="4" paint-order="stroke" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="11.5" font-weight="650">{owner}</text>'
    )

    for index, (x, y, node) in enumerate(positions.values()):
        label = html.escape(display_label(str(node["label"])))
        node_type = str(node.get("type", "repository"))
        radius = node_radius(node)
        fill = group if node_type == "group" else (fork if node.get("fork") else repository)
        class_name = ' class="category"' if node_type == "group" else ""
        delay = f' style="animation-delay:-{index * 0.23:.2f}s"' if node_type == "group" else ""
        stroke_width = 2.2 if node_type == "group" else 1.5
        parts.append(
            f'<circle{class_name}{delay} cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" stroke="{panel}" stroke-width="{stroke_width}"/>'
        )
        if node_type == "group":
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius + 6:.1f}" fill="none" stroke="{fill}" stroke-width="1" opacity="0.26"/>'
            )
        label_y = y + radius + (17 if node_type == "group" else 15)
        parts.append(
            f'<text x="{x:.1f}" y="{label_y:.1f}" text-anchor="middle" fill="{node_text}" stroke="{background}" stroke-width="4" paint-order="stroke" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="{11 if node_type == "group" else 10.2}" font-weight="{650 if node_type == "group" else 500}">{label}</text>'
        )

    cta_x, cta_y, cta_width, cta_height = 246, 503, 268, 40
    parts.extend(
        [
            '<g class="cta">',
            f'<rect x="{cta_x}" y="{cta_y}" width="{cta_width}" height="{cta_height}" rx="20" fill="{group}"/>',
            f'<text x="{cta_x + 126}" y="{cta_y + 25}" text-anchor="middle" fill="#ffffff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="12.5" font-weight="650">Open the interactive map</text>',
            f'<text class="arrow" x="{cta_x + 235}" y="{cta_y + 25}" text-anchor="middle" fill="#ffffff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="16" font-weight="700">→</text>',
            "</g>",
            f'<text x="24" y="{height - 17}" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="10.5">{len([node for node in project_map["nodes"] if node.get("type") == "repository"])} public projects · {len([node for node in project_map["nodes"] if node.get("type") == "group"])} curated areas</text>',
            "</svg>",
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--relations", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--light", type=Path, required=True)
    parser.add_argument("--dark", type=Path, required=True)
    args = parser.parse_args()

    repositories = fetch_public_repositories(args.username)
    config = load_config(args.relations)
    project_map = build_map(args.username, repositories, config)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(project_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    render_preview(project_map, args.light, "light")
    render_preview(project_map, args.dark, "dark")


if __name__ == "__main__":
    main()
