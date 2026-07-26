#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import math
import re
from pathlib import Path


def read_nodes(source: Path) -> list[str]:
    text = source.read_text(encoding="utf-8")
    marker = "初期ノード候補:"
    start = text.find(marker)
    if start < 0:
        raise SystemExit(f"Marker not found: {marker}")

    nodes: list[str] = []
    for line in text[start + len(marker):].splitlines():
        match = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if match:
            nodes.append(match.group(1))
        elif nodes and line.strip():
            break

    if not nodes:
        raise SystemExit("No graph nodes found")
    return nodes


def node_width(label: str) -> int:
    return max(92, min(158, 28 + len(label) * 7))


def render(nodes: list[str], output: Path, theme: str) -> None:
    if theme == "dark":
        background = "#0d1117"
        border = "#30363d"
        edge = "#484f58"
        node_fill = "#161b22"
        node_text = "#f0f6fc"
        center_fill = "#1f6feb"
        center_text = "#ffffff"
        muted = "#8b949e"
    else:
        background = "#ffffff"
        border = "#d0d7de"
        edge = "#afb8c1"
        node_fill = "#f6f8fa"
        node_text = "#24292f"
        center_fill = "#0969da"
        center_text = "#ffffff"
        muted = "#57606a"

    width, height = 760, 470
    cx, cy = width / 2, 245
    center_label = "Civitas"
    surrounding = [node for node in nodes if node != center_label]

    positions: list[tuple[float, float, str]] = []
    inner_count = min(6, len(surrounding))
    outer = surrounding[inner_count:]

    for index, label in enumerate(surrounding[:inner_count]):
        angle = -math.pi / 2 + index * (2 * math.pi / max(inner_count, 1))
        positions.append((cx + 125 * math.cos(angle), cy + 115 * math.sin(angle), label))

    for index, label in enumerate(outer):
        angle = -math.pi / 2 + (index + 0.5) * (2 * math.pi / max(len(outer), 1))
        positions.append((cx + 255 * math.cos(angle), cy + 185 * math.sin(angle), label))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Civitas knowledge graph preview">',
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="12" fill="{background}" stroke="{border}"/>',
        f'<text x="{cx}" y="34" text-anchor="middle" fill="{node_text}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="18" font-weight="600">Knowledge Graph</text>',
    ]

    for x, y, _ in positions:
        parts.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="{edge}" stroke-width="1.5" opacity="0.85"/>')

    for x, y, label in positions:
        escaped = html.escape(label)
        box_width = node_width(label)
        parts.append(
            f'<rect x="{x - box_width / 2:.1f}" y="{y - 17:.1f}" width="{box_width}" height="34" rx="17" fill="{node_fill}" stroke="{border}"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" fill="{node_text}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="11.5">{escaped}</text>'
        )

    parts.append(f'<circle cx="{cx}" cy="{cy}" r="50" fill="{center_fill}"/>')
    parts.append(
        f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" fill="{center_text}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="16" font-weight="700">Civitas</text>'
    )
    parts.append(
        f'<text x="{cx}" y="{height - 18}" text-anchor="middle" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans JP,sans-serif" font-size="11">Generated from the public Civitas knowledge-graph plan</text>'
    )
    parts.append("</svg>")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    args = parser.parse_args()

    render(read_nodes(args.source), args.output, args.theme)


if __name__ == "__main__":
    main()
