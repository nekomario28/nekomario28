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
from collections import Counter
from pathlib import Path
from typing import Any


EMPTY_RELATIONS: dict[str, Any] = {
    "schemaVersion": 1,
    "groups": [],
    "relations": [],
}


def github_get(url: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nekomario28-profile-graph",
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


def load_relations(path: Path | None) -> dict[str, Any]:
    if path is None:
        return dict(EMPTY_RELATIONS)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("top-level value must be an object")
        groups = raw.get("groups", [])
        relations = raw.get("relations", [])
        if not isinstance(groups, list) or not isinstance(relations, list):
            raise ValueError("groups and relations must be arrays")
        return {
            "schemaVersion": raw.get("schemaVersion", 1),
            "groups": groups,
            "relations": relations,
        }
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(
            f"warning: ignoring project relation config {path}: {error}",
            file=sys.stderr,
        )
        return dict(EMPTY_RELATIONS)


def build_graph(
    username: str,
    repositories: list[dict[str, Any]],
    relation_config: dict[str, Any],
) -> dict[str, Any]:
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
        link: dict[str, str] = {
            "source": source,
            "target": target,
            "type": link_type,
        }
        if label:
            link["label"] = label
        links.append(link)

    language_counts = Counter(
        repository.get("language")
        for repository in repositories
        if repository.get("language")
    )
    topic_counts = Counter(
        topic
        for repository in repositories
        for topic in repository.get("topics", [])
    )

    visible_languages = {language for language, _ in language_counts.most_common(10)}
    visible_topics = {topic for topic, _ in topic_counts.most_common(16)}
    repository_names = {str(repository["name"]) for repository in repositories}

    for language in sorted(visible_languages):
        nodes.append(
            {
                "id": f"language:{language}",
                "label": language,
                "type": "language",
            }
        )

    for topic in sorted(visible_topics):
        nodes.append(
            {
                "id": f"topic:{topic}",
                "label": f"#{topic}",
                "type": "topic",
            }
        )

    valid_groups: list[dict[str, Any]] = []
    for raw_group in relation_config.get("groups", []):
        if not isinstance(raw_group, dict):
            continue
        group_id = str(raw_group.get("id", "")).strip()
        label = str(raw_group.get("label", "")).strip()
        raw_members = raw_group.get("repositories", [])
        if not group_id or not label or not isinstance(raw_members, list):
            continue
        members = [
            str(member)
            for member in raw_members
            if str(member) in repository_names
        ]
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
            add_link(group_node_id, f"repository:{member}", "member")

    for repository in repositories:
        name = str(repository["name"])
        node_id = f"repository:{name}"
        language = repository.get("language")
        topics = [topic for topic in repository.get("topics", []) if topic in visible_topics]
        nodes.append(
            {
                "id": node_id,
                "label": name,
                "type": "repository",
                "url": repository.get("html_url"),
                "description": repository.get("description") or "",
                "language": language,
                "topics": topics,
                "stars": repository.get("stargazers_count", 0),
                "fork": bool(repository.get("fork")),
                "archived": bool(repository.get("archived")),
                "updatedAt": repository.get("updated_at"),
            }
        )
        add_link(f"user:{username}", node_id, "owns")

        if language in visible_languages:
            add_link(node_id, f"language:{language}", "language")

        for topic in topics:
            add_link(node_id, f"topic:{topic}", "topic")

    for raw_relation in relation_config.get("relations", []):
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
    minimum = 126 if node_type == "group" else 76
    maximum = 190 if node_type == "group" else 150
    return max(minimum, min(maximum, 24 + len(label) * 6))


def render_preview(graph: dict[str, Any], output: Path, theme: str) -> None:
    if theme == "dark":
        background = "#0d1117"
        border = "#30363d"
        edge = "#484f58"
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
        node_fill = "#f6f8fa"
        node_text = "#24292f"
        fork_fill = "#eaeef2"
        group_fill = "#0969da"
        center_fill = "#54aeff"
        muted = "#57606a"

    repository_nodes = [
        node for node in graph["nodes"] if node.get("type") == "repository"
    ]
    group_nodes = [node for node in graph["nodes"] if node.get("type") == "group"]
    width, height = 760, 520
    cx, cy = width / 2, 270
    positions: dict[str, tuple[float, float, dict[str, Any]]] = {}

    for index, node in enumerate(group_nodes):
        angle = -math.pi / 2 + index * (2 * math.pi / max(len(group_nodes), 1))
        positions[str(node["id"])] = (
            cx + 110 * math.cos(angle),
            cy + 85 * math.sin(angle),
            node,
        )

    inner_count = min(8, len(repository_nodes))
    outer_nodes = repository_nodes[inner_count:]
    for index, node in enumerate(repository_nodes[:inner_count]):
        angle = -math.pi / 2 + index * (2 * math.pi / max(inner_count, 1))
        positions[str(node["id"])] = (
            cx + 205 * math.cos(angle),
            cy + 155 * math.sin(angle),
            node,
        )

    for index, node in enumerate(outer_nodes):
        angle = -math.pi / 2 + (index + 0.5) * (2 * math.pi / max(len(outer_nodes), 1))
        positions[str(node["id"])] = (
            cx + 295 * math.cos(angle),
            cy + 215 * math.sin(angle),
            node,
        )

    owner_id = f"user:{graph['owner']}"
    owner = html.escape(str(graph["owner"]))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Public project knowledge graph preview">',
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="12" fill="{background}" stroke="{border}"/>',
        f'<text x="{cx}" y="34" text-anchor="middle" fill="{node_text}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="18" font-weight="600">Project Knowledge Graph</text>',
    ]

    for link in graph["links"]:
        source_id = str(link["source"])
        target_id = str(link["target"])
        if source_id == owner_id:
            source = (cx, cy)
        elif source_id in positions:
            source = positions[source_id][:2]
        else:
            continue
        if target_id == owner_id:
            target = (cx, cy)
        elif target_id in positions:
            target = positions[target_id][:2]
        else:
            continue
        opacity = 0.9 if link.get("type") not in {"owns", "contains", "member"} else 0.58
        stroke_width = 2.1 if link.get("type") not in {"owns", "contains", "member"} else 1.15
        parts.append(
            f'<line x1="{source[0]:.1f}" y1="{source[1]:.1f}" x2="{target[0]:.1f}" y2="{target[1]:.1f}" stroke="{edge}" stroke-width="{stroke_width}" opacity="{opacity}"/>'
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

    parts.append(f'<circle cx="{cx}" cy="{cy}" r="50" fill="{center_fill}"/>')
    parts.append(
        f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" fill="#ffffff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="15" font-weight="700">{owner}</text>'
    )
    parts.append(
        f'<text x="{cx}" y="{height - 18}" text-anchor="middle" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="11">{len(repository_nodes)} public projects • {len(group_nodes)} curated group • click to explore</text>'
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
    relation_config = load_relations(args.relations)
    graph = build_graph(args.username, repositories, relation_config)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render_preview(graph, args.light, "light")
    render_preview(graph, args.dark, "dark")


if __name__ == "__main__":
    main()
