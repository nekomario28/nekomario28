#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import os
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


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


def build_graph(username: str, repositories: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = [
        {
            "id": f"user:{username}",
            "label": username,
            "type": "owner",
            "url": f"https://github.com/{username}",
        }
    ]
    links: list[dict[str, str]] = []

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

    for repository in repositories:
        name = repository["name"]
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
        links.append({"source": f"user:{username}", "target": node_id, "type": "owns"})

        if language in visible_languages:
            links.append(
                {
                    "source": node_id,
                    "target": f"language:{language}",
                    "type": "language",
                }
            )

        for topic in topics:
            links.append(
                {
                    "source": node_id,
                    "target": f"topic:{topic}",
                    "type": "topic",
                }
            )

    return {
        "owner": username,
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repositoryCount": len(repositories),
        "nodes": nodes,
        "links": links,
    }


def node_width(label: str) -> int:
    return max(76, min(150, 24 + len(label) * 6))


def render_preview(graph: dict[str, Any], output: Path, theme: str) -> None:
    if theme == "dark":
        background = "#0d1117"
        border = "#30363d"
        edge = "#484f58"
        node_fill = "#161b22"
        node_text = "#f0f6fc"
        fork_fill = "#21262d"
        center_fill = "#1f6feb"
        muted = "#8b949e"
    else:
        background = "#ffffff"
        border = "#d0d7de"
        edge = "#afb8c1"
        node_fill = "#f6f8fa"
        node_text = "#24292f"
        fork_fill = "#eaeef2"
        center_fill = "#0969da"
        muted = "#57606a"

    repository_nodes = [
        node for node in graph["nodes"] if node.get("type") == "repository"
    ]
    width, height = 760, 500
    cx, cy = width / 2, 258
    positions: list[tuple[float, float, dict[str, Any]]] = []

    inner_count = min(8, len(repository_nodes))
    outer_nodes = repository_nodes[inner_count:]

    for index, node in enumerate(repository_nodes[:inner_count]):
        angle = -math.pi / 2 + index * (2 * math.pi / max(inner_count, 1))
        positions.append((cx + 150 * math.cos(angle), cy + 125 * math.sin(angle), node))

    for index, node in enumerate(outer_nodes):
        angle = -math.pi / 2 + (index + 0.5) * (2 * math.pi / max(len(outer_nodes), 1))
        positions.append((cx + 285 * math.cos(angle), cy + 205 * math.sin(angle), node))

    owner = html.escape(str(graph["owner"]))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Public project knowledge graph preview">',
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="12" fill="{background}" stroke="{border}"/>',
        f'<text x="{cx}" y="34" text-anchor="middle" fill="{node_text}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="18" font-weight="600">Project Knowledge Graph</text>',
    ]

    for x, y, _ in positions:
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="{edge}" stroke-width="1.25" opacity="0.72"/>'
        )

    for x, y, node in positions:
        label = html.escape(str(node["label"]))
        box_width = node_width(str(node["label"]))
        fill = fork_fill if node.get("fork") else node_fill
        parts.append(
            f'<rect x="{x - box_width / 2:.1f}" y="{y - 15:.1f}" width="{box_width}" height="30" rx="15" fill="{fill}" stroke="{border}"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" fill="{node_text}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="10.5">{label}</text>'
        )

    parts.append(f'<circle cx="{cx}" cy="{cy}" r="53" fill="{center_fill}"/>')
    parts.append(
        f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" fill="#ffffff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="15" font-weight="700">{owner}</text>'
    )
    parts.append(
        f'<text x="{cx}" y="{height - 18}" text-anchor="middle" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="11">{len(repository_nodes)} public projects • click to explore interactively</text>'
    )
    parts.append("</svg>")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--light", type=Path, required=True)
    parser.add_argument("--dark", type=Path, required=True)
    args = parser.parse_args()

    repositories = fetch_public_repositories(args.username)
    graph = build_graph(args.username, repositories)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render_preview(graph, args.light, "light")
    render_preview(graph, args.dark, "dark")


if __name__ == "__main__":
    main()
