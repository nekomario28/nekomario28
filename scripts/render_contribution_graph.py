#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

GRAPHQL_URL = "https://api.github.com/graphql"
DAYS = 31
WIDTH = 760
HEIGHT = 220
MARGIN_LEFT = 38
MARGIN_RIGHT = 18
MARGIN_TOP = 42
MARGIN_BOTTOM = 32


def fetch_contributions(username: str, token: str) -> tuple[list[tuple[date, int]], int]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=DAYS - 1)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps(
        {
            "query": query,
            "variables": {
                "login": username,
                "from": f"{start.isoformat()}T00:00:00Z",
                "to": f"{today.isoformat()}T23:59:59Z",
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "nekomario28-profile-contribution-graph",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub GraphQL request failed: HTTP {error.code}: {detail}") from error

    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL returned errors: {result['errors']}")
    user = result.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user not found: {username}")

    calendar = user["contributionsCollection"]["contributionCalendar"]
    counts: dict[date, int] = {}
    for week in calendar.get("weeks", []):
        for day in week.get("contributionDays", []):
            parsed = date.fromisoformat(day["date"])
            if start <= parsed <= today:
                counts[parsed] = int(day.get("contributionCount", 0))

    series = []
    cursor = start
    while cursor <= today:
        series.append((cursor, counts.get(cursor, 0)))
        cursor += timedelta(days=1)
    return series, sum(count for _, count in series)


def nice_ceiling(value: int) -> int:
    if value <= 1:
        return 1
    magnitude = 10 ** (len(str(value)) - 1)
    normalized = value / magnitude
    if normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10
    return nice * magnitude


def render_svg(username: str, series: list[tuple[date, int]], total: int, dark: bool) -> str:
    bg = "#0d1117" if dark else "#ffffff"
    text = "#8b949e" if dark else "#57606a"
    strong = "#f0f6fc" if dark else "#24292f"
    grid = "#21262d" if dark else "#d8dee4"
    line = "#58a6ff" if dark else "#0969da"
    point = "#79c0ff" if dark else "#54aeff"
    y_max = nice_ceiling(max((count for _, count in series), default=0))

    plot_width = WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    plot_height = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
    step_x = plot_width / max(1, len(series) - 1)

    def x_at(index: int) -> float:
        return MARGIN_LEFT + index * step_x

    def y_at(count: int) -> float:
        return MARGIN_TOP + plot_height - (count / y_max) * plot_height

    points = [(x_at(index), y_at(count)) for index, (_, count) in enumerate(series)]
    line_path = " ".join(
        ("M" if index == 0 else "L") + f" {x:.2f} {y:.2f}"
        for index, (x, y) in enumerate(points)
    )
    baseline = MARGIN_TOP + plot_height
    area_path = f"{line_path} L {points[-1][0]:.2f} {baseline:.2f} L {points[0][0]:.2f} {baseline:.2f} Z"

    grid_lines: list[str] = []
    for tick in range(5):
        fraction = tick / 4
        y = MARGIN_TOP + plot_height * (1 - fraction)
        value = round(y_max * fraction)
        grid_lines.append(
            f'<line x1="{MARGIN_LEFT}" y1="{y:.2f}" x2="{WIDTH - MARGIN_RIGHT}" y2="{y:.2f}" '
            f'stroke="{grid}" stroke-width="1" opacity="0.55"/>'
        )
        grid_lines.append(
            f'<text x="{MARGIN_LEFT - 8}" y="{y + 4:.2f}" text-anchor="end" fill="{text}" font-size="10">{value}</text>'
        )

    label_indices = sorted({0, len(series) // 4, len(series) // 2, (len(series) * 3) // 4, len(series) - 1})
    date_labels = []
    for index in label_indices:
        day = series[index][0]
        date_labels.append(
            f'<text x="{x_at(index):.2f}" y="{HEIGHT - 10}" text-anchor="middle" fill="{text}" font-size="10">'
            f'{html.escape(day.strftime("%b %-d"))}</text>'
        )

    dots = []
    for x, y in points:
        dots.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.15" fill="{point}"/>')

    title = html.escape(f"{username} contributions")
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{title}</title>',
            f'<desc id="desc">Daily GitHub contribution counts for the last {DAYS} days.</desc>',
            "<defs>",
            f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{line}" stop-opacity="0.30"/><stop offset="1" stop-color="{line}" stop-opacity="0.02"/></linearGradient>',
            "</defs>",
            f'<rect width="{WIDTH}" height="{HEIGHT}" rx="8" fill="{bg}"/>',
            f'<text x="{MARGIN_LEFT}" y="24" fill="{strong}" font-family="system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="14" font-weight="600">Contributions · last {DAYS} days</text>',
            f'<text x="{WIDTH - MARGIN_RIGHT}" y="24" text-anchor="end" fill="{text}" font-family="system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="11">{total} contributions</text>',
            f'<g font-family="system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">',
            *grid_lines,
            f'<path d="{area_path}" fill="url(#area)"/>',
            f'<path d="{line_path}" fill="none" stroke="{line}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>',
            *dots,
            *date_labels,
            "</g>",
            "</svg>",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render self-hosted GitHub contribution graphs.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--light", type=Path, required=True)
    parser.add_argument("--dark", type=Path, required=True)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")

    series, total = fetch_contributions(args.username, token)
    args.light.parent.mkdir(parents=True, exist_ok=True)
    args.dark.parent.mkdir(parents=True, exist_ok=True)
    args.light.write_text(render_svg(args.username, series, total, dark=False), encoding="utf-8")
    args.dark.write_text(render_svg(args.username, series, total, dark=True), encoding="utf-8")


if __name__ == "__main__":
    main()
