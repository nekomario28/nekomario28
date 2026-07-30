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


def node_width(label: str, node_type: str) -> int:
    minimum = 132 if node_type == "group" else 76
    maximum = 190 if node_type == "group" else 156
    return max(minimum, min(maximum, 24 + len(label) * 6))


def render_preview(project_map: dict[str, Any], output: Path, theme: str) -> None:
    if theme == "dark":
        background = "#0d1117"
        border = "#30363d"
        edge = "#484f58"
        relation = "#f0883e"
        node_fill = "#161b22"
        node_text = "#f0f6fc"
        fork_fill = "#21262d"
        group_fill = "#1f6feb"
        center_fill = "#58a6ff"
        muted = "#8b949e"
    else:
        background = "#ffffff"
        border = "#d0d7de"
        edge = "#afb8c1"
        relation = "#bc4c00"
        node_fill = "#f6f8fa"
        node_text = "#24292f"
        fork_fill = "#eaeef2"
        group_fill = "#0969da"
        center_fill = "#54aeff"
        muted = "#57606a"

    width, height = 760, 560
    cx, cy = width / 2, 290
    owner_id = f"user:{project_map['owner']}"
    group_nodes = [node for node in project_map["nodes"] if node.get("type") == "group"]
    repository_nodes = [
        node for node in project_map["nodes"] if node.get("type") == "repository"
    ]
    repository_by_id = {str(node["id"]): node for node in repository_nodes}
    member_links = [link for link in project_map["links"] if link.get("type") == "member"]
    members_by_group: dict[str, list[dict[str, Any]]] = {}
    grouped_repository_ids: set[str] = set()
    for link in member_links:
        group_id = str(link["source"])
        repository_id = str(link["target"])
        repository = repository_by_id.get(repository_id)
        if repository is None:
            continue
        members_by_group.setdefault(group_id, []).append(repository)
        grouped_repository_ids.add(repository_id)

    positions: dict[str, tuple[float, float, dict[str, Any]]] = {}
    group_angles: dict[str, float] = {}
    group_count = max(1, len(group_nodes))
    for index, node in enumerate(group_nodes):
        angle = -math.pi / 2 + index * 2 * math.pi / group_count
        group_angles[str(node["id"])] = angle
        positions[str(node["id"])] = (
            cx + 145 * math.cos(angle),
            cy + 120 * math.sin(angle),
            node,
        )

    for group in group_nodes:
        group_id = str(group["id"])
        group_x, group_y, _ = positions[group_id]
        members = members_by_group.get(group_id, [])
        base_angle = group_angles[group_id]
        for index, node in enumerate(members):
            if len(members) == 1:
                angle = base_angle
            else:
                spread = min(math.pi * 1.35, 0.55 * (len(members) - 1))
                angle = base_angle - spread / 2 + spread * index / (len(members) - 1)
            positions[str(node["id"])] = (
                group_x + 112 * math.cos(angle),
                group_y + 92 * math.sin(angle),
                node,
            )

    ungrouped = [node for node in repository_nodes if str(node["id"]) not in grouped_repository_ids]
    for index, node in enumerate(ungrouped):
        angle = -math.pi / 2 + index * 2 * math.pi / max(1, len(ungrouped))
        positions[str(node["id"])] = (
            cx + 285 * math.cos(angle),
            cy + 210 * math.sin(angle),
            node,
        )

    owner = html.escape(str(project_map["owner"]))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Interactive public project map preview">',
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="12" fill="{background}" stroke="{border}"/>',
        f'<text x="{cx}" y="34" text-anchor="middle" fill="{node_text}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="18" font-weight="600">Interactive Project Map</text>',
    ]

    structural_types = {"owns", "contains", "member"}
    for link in project_map["links"]:
        source_id = str(link["source"])
        target_id = str(link["target"])
        source = (cx, cy) if source_id == owner_id else positions.get(source_id, (None, None, None))[:2]
        target = (cx, cy) if target_id == owner_id else positions.get(target_id, (None, None, None))[:2]
        if source[0] is None or target[0] is None:
            continue
        structural = link.get("type") in structural_types
        parts.append(
            f'<line x1="{source[0]:.1f}" y1="{source[1]:.1f}" x2="{target[0]:.1f}" y2="{target[1]:.1f}" stroke="{edge if structural else relation}" stroke-width="{1.15 if structural else 2.2}" opacity="{0.52 if structural else 0.9}"/>'
        )

    for x, y, node in positions.values():
        label = html.escape(str(node["label"]))
        node_type = str(node.get("type", "repository"))
        box_width = node_width(str(node["label"]), node_type)
        if node_type == "group":
            fill = group_fill
            text_fill = "#ffffff"
            height_px = 34
        else:
            fill = fork_fill if node.get("fork") else node_fill
            text_fill = node_text
            height_px = 30
        parts.append(
            f'<rect x="{x - box_width / 2:.1f}" y="{y - height_px / 2:.1f}" width="{box_width}" height="{height_px}" rx="{height_px / 2:.1f}" fill="{fill}" stroke="{border}"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" fill="{text_fill}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="{11.5 if node_type == "group" else 10.5}" font-weight="{600 if node_type == "group" else 400}">{label}</text>'
        )

    parts.append(f'<circle cx="{cx}" cy="{cy}" r="48" fill="{center_fill}"/>')
    parts.append(
        f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" fill="#ffffff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="15" font-weight="700">{owner}</text>'
    )
    parts.append(
        f'<text x="{cx}" y="{height - 18}" text-anchor="middle" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="11">{len(repository_nodes)} public projects • {len(group_nodes)} curated categories • click to explore</text>'
    )
    parts.append("</svg>")

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
