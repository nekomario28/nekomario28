#!/usr/bin/env python3
"""Render a small output-oriented GitHub profile card.

The card intentionally avoids commit / PR / review totals. It summarizes recent
project areas, public releases, and merged pull requests to repositories owned by
other accounts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

API = "https://api.github.com"
USER_AGENT = "nekomario28-profile-recent-work"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--relations", required=True)
    parser.add_argument("--light", required=True)
    parser.add_argument("--dark", required=True)
    parser.add_argument("--days", type=int, default=90)
    return parser.parse_args()


def api_json(path: str, token: str):
    request = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} for {path}: {body[:500]}") from exc


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_groups(path: str):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("groups", [])


def fetch_owned_repositories(username: str, token: str):
    repos = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {
                "type": "owner",
                "sort": "pushed",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            }
        )
        batch = api_json(f"/users/{urllib.parse.quote(username)}/repos?{query}", token)
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [repo for repo in repos if not repo.get("private") and not repo.get("archived")]


def recent_focus(groups, repo_by_name, cutoff: datetime):
    focus = []
    for group in groups:
        members = []
        for name in group.get("repositories", []):
            repo = repo_by_name.get(name.casefold())
            if not repo:
                continue
            pushed = parse_time(repo.get("pushed_at"))
            if pushed and pushed >= cutoff:
                members.append((pushed, repo["name"]))
        if not members:
            continue
        members.sort(reverse=True)
        focus.append(
            {
                "label": group.get("label", group.get("id", "Projects")),
                "repos": [name for _, name in members[:2]],
                "latest": members[0][0],
            }
        )
    focus.sort(key=lambda item: item["latest"], reverse=True)
    return focus[:3]


def recent_releases(repositories, token: str, cutoff: datetime):
    releases = []
    candidates = []
    for repo in repositories:
        pushed = parse_time(repo.get("pushed_at"))
        if pushed and pushed >= cutoff - timedelta(days=60):
            candidates.append(repo)
    for repo in candidates[:40]:
        path = f"/repos/{repo['owner']['login']}/{repo['name']}/releases?per_page=5"
        for release in api_json(path, token):
            if release.get("draft"):
                continue
            published = parse_time(release.get("published_at") or release.get("created_at"))
            if not published or published < cutoff:
                continue
            releases.append(
                {
                    "repo": repo["name"],
                    "tag": release.get("tag_name") or release.get("name") or "release",
                    "published": published,
                }
            )
    releases.sort(key=lambda item: item["published"], reverse=True)
    seen = set()
    unique = []
    for release in releases:
        key = (release["repo"].casefold(), release["tag"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(release)
    return unique[:3]


def external_merges(username: str, token: str, cutoff: datetime):
    date_text = cutoff.date().isoformat()
    q = f"author:{username} is:pr is:merged merged:>={date_text}"
    params = urllib.parse.urlencode({"q": q, "sort": "updated", "order": "desc", "per_page": 100})
    payload = api_json(f"/search/issues?{params}", token)
    merges = []
    for item in payload.get("items", []):
        repository_url = item.get("repository_url", "")
        parts = repository_url.rstrip("/").split("/")
        if len(parts) < 2:
            continue
        owner, repo = parts[-2], parts[-1]
        if owner.casefold() == username.casefold():
            continue
        merged_at = parse_time(item.get("closed_at")) or cutoff
        merges.append(
            {
                "repository": f"{owner}/{repo}",
                "number": item.get("number"),
                "merged": merged_at,
            }
        )
    merges.sort(key=lambda item: item["merged"], reverse=True)
    seen = set()
    unique = []
    for merge in merges:
        key = (merge["repository"].casefold(), merge["number"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(merge)
    return unique[:3]


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def build_rows(focus, releases, merges):
    rows = []
    for item in focus:
        rows.append(("FOCUS", item["label"], " · ".join(item["repos"])))
    if releases:
        release_text = " · ".join(f"{item['repo']} {item['tag']}" for item in releases[:2])
        rows.append(("SHIPPED", "Public releases", release_text))
    if merges:
        merge_text = " · ".join(f"{item['repository']} #{item['number']}" for item in merges[:2])
        rows.append(("UPSTREAM", "Merged outside my repos", merge_text))
    return rows[:5]


def render_svg(rows, days: int, dark: bool) -> str:
    width = 760
    top = 62
    row_height = 42
    footer = 24
    height = top + max(1, len(rows)) * row_height + footer

    if dark:
        bg = "#0d1117"
        title = "#f0f6fc"
        text = "#c9d1d9"
        muted = "#8b949e"
        accent = "#58a6ff"
        rule = "#21262d"
    else:
        bg = "#ffffff"
        title = "#24292f"
        text = "#24292f"
        muted = "#57606a"
        accent = "#0969da"
        rule = "#d8dee4"

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Recent Work</title>',
        f'<desc id="desc">Output-oriented public GitHub activity from the last {days} days. Commit, pull request and review totals are intentionally omitted.</desc>',
        f'<rect width="{width}" height="{height}" rx="8" fill="{bg}"/>',
        f'<text x="28" y="27" fill="{title}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="16" font-weight="600">Recent Work</text>',
        f'<text x="28" y="48" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="11">Last {days} days · outcomes and project areas, not activity volume</text>',
    ]

    if not rows:
        lines.append(
            f'<text x="28" y="88" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="13">No public output signal matched the current filters.</text>'
        )
    else:
        for index, (kind, label, detail) in enumerate(rows):
            y = top + index * row_height
            if index:
                lines.append(f'<line x1="28" y1="{y - 8}" x2="732" y2="{y - 8}" stroke="{rule}" stroke-width="1"/>')
            lines.extend(
                [
                    f'<text x="28" y="{y + 11}" fill="{accent}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="9" font-weight="600" letter-spacing="0.7">{escape(kind)}</text>',
                    f'<text x="116" y="{y + 11}" fill="{text}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12.5" font-weight="600">{escape(truncate(label, 34))}</text>',
                    f'<text x="116" y="{y + 29}" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="11.5">{escape(truncate(detail, 78))}</text>',
                ]
            )

    lines.append(
        f'<text x="732" y="{height - 10}" text-anchor="end" fill="{muted}" opacity="0.72" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="9">public GitHub data</text>'
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2
    if args.days < 30 or args.days > 365:
        print("--days must be between 30 and 365", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.days)
    groups = load_groups(args.relations)
    repositories = fetch_owned_repositories(args.username, token)
    repo_by_name = {repo["name"].casefold(): repo for repo in repositories}

    focus = recent_focus(groups, repo_by_name, cutoff)
    releases = recent_releases(repositories, token, cutoff)
    merges = external_merges(args.username, token, cutoff)
    rows = build_rows(focus, releases, merges)

    Path(args.light).parent.mkdir(parents=True, exist_ok=True)
    Path(args.dark).parent.mkdir(parents=True, exist_ok=True)
    Path(args.light).write_text(render_svg(rows, args.days, False), encoding="utf-8")
    Path(args.dark).write_text(render_svg(rows, args.days, True), encoding="utf-8")

    print(
        json.dumps(
            {
                "focus": [{"label": item["label"], "repos": item["repos"]} for item in focus],
                "releases": [{"repo": item["repo"], "tag": item["tag"]} for item in releases],
                "externalMerges": [
                    {"repository": item["repository"], "number": item["number"]} for item in merges
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
