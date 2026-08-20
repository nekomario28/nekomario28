#!/usr/bin/env python3
"""Render an output-oriented GitHub profile card.

The card intentionally avoids commit / PR / review totals. It summarizes stable
recent project focus, public releases, and explicitly allowlisted upstream merges.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

API = "https://api.github.com"
USER_AGENT = "nekomario28-profile-recent-work"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--relations", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--light", required=True)
    parser.add_argument("--dark", required=True)
    parser.add_argument("--days", type=int)
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


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def validate_policy(policy: dict, days_override: int | None) -> tuple[int, dict, dict, dict]:
    window_days = int(days_override or policy.get("windowDays", 90))
    if window_days < 30 or window_days > 365:
        raise ValueError("windowDays / --days must be between 30 and 365")

    focus = policy.get("focus", {})
    releases = policy.get("releases", {})
    upstream = policy.get("upstream", {})

    max_groups = int(focus.get("maxGroups", 3))
    max_repos = int(focus.get("maxRepositoriesPerGroup", 2))
    buckets = [int(value) for value in focus.get("recencyBucketsDays", [7, 30, window_days])]
    if not (1 <= max_groups <= 5 and 1 <= max_repos <= 3):
        raise ValueError("focus caps are outside supported bounds")
    if not buckets or buckets != sorted(set(buckets)) or buckets[-1] != window_days:
        raise ValueError("focus recency buckets must be sorted, unique, and end at windowDays")

    max_releases = int(releases.get("maxItems", 2))
    max_upstream = int(upstream.get("maxItems", 2))
    if not (0 <= max_releases <= 3 and 0 <= max_upstream <= 3):
        raise ValueError("release/upstream caps are outside supported bounds")

    return window_days, focus, releases, upstream


def bucket_for_age(age_days: float, buckets: list[int]) -> int | None:
    for index, limit in enumerate(buckets):
        if age_days <= limit:
            return index
    return None


def recent_focus(groups, repo_by_name, now: datetime, cutoff: datetime, focus_policy: dict):
    max_groups = int(focus_policy.get("maxGroups", 3))
    max_repos = int(focus_policy.get("maxRepositoriesPerGroup", 2))
    buckets = [int(value) for value in focus_policy.get("recencyBucketsDays", [7, 30, 90])]

    focus = []
    for group_index, group in enumerate(groups):
        active_members = []
        for repo_index, name in enumerate(group.get("repositories", [])):
            repo = repo_by_name.get(name.casefold())
            if not repo:
                continue
            pushed = parse_time(repo.get("pushed_at"))
            if not pushed or pushed < cutoff:
                continue
            age_days = max(0.0, (now - pushed).total_seconds() / 86400.0)
            bucket = bucket_for_age(age_days, buckets)
            if bucket is None:
                continue
            active_members.append(
                {
                    "name": repo["name"],
                    "bucket": bucket,
                    "repo_index": repo_index,
                }
            )

        if not active_members:
            continue

        group_bucket = min(item["bucket"] for item in active_members)
        selected = sorted(active_members, key=lambda item: item["repo_index"])[:max_repos]
        focus.append(
            {
                "label": group.get("label", group.get("id", "Projects")),
                "repos": [item["name"] for item in selected],
                "bucket": group_bucket,
                "group_index": group_index,
            }
        )

    focus.sort(key=lambda item: (item["bucket"], item["group_index"]))
    return focus[:max_groups]


def recent_releases(repositories, token: str, cutoff: datetime, max_items: int):
    if max_items <= 0:
        return []

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
    return unique[:max_items]


def normalized_repo_set(values) -> set[str]:
    return {
        str(value).strip().casefold()
        for value in values or []
        if isinstance(value, str) and "/" in value and str(value).strip()
    }


def external_merges(
    username: str,
    token: str,
    cutoff: datetime,
    allowed_repositories: set[str],
    max_items: int,
):
    if max_items <= 0 or not allowed_repositories:
        return []

    date_text = cutoff.date().isoformat()
    q = f"author:{username} is:pr is:merged merged:>={date_text}"
    params = urllib.parse.urlencode(
        {"q": q, "sort": "updated", "order": "desc", "per_page": 100}
    )
    payload = api_json(f"/search/issues?{params}", token)
    merges = []

    for item in payload.get("items", []):
        repository_url = item.get("repository_url", "")
        parts = repository_url.rstrip("/").split("/")
        if len(parts) < 2:
            continue
        owner, repo = parts[-2], parts[-1]
        full_name = f"{owner}/{repo}"
        if owner.casefold() == username.casefold():
            continue
        if full_name.casefold() not in allowed_repositories:
            continue
        merged_at = parse_time(item.get("closed_at")) or cutoff
        merges.append(
            {
                "repository": full_name,
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
    return unique[:max_items]


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def build_rows(focus, releases, merges):
    rows = []
    for item in focus:
        rows.append(("FOCUS", item["label"], " · ".join(item["repos"])))
    if releases:
        release_text = " · ".join(f"{item['repo']} {item['tag']}" for item in releases)
        rows.append(("SHIPPED", "Public releases", release_text))
    if merges:
        merge_text = " · ".join(f"{item['repository']} #{item['number']}" for item in merges)
        rows.append(("UPSTREAM", "Verified upstream merges", merge_text))
    return rows[:7]


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
                lines.append(
                    f'<line x1="28" y1="{y - 8}" x2="732" y2="{y - 8}" stroke="{rule}" stroke-width="1"/>'
                )
            lines.extend(
                [
                    f'<text x="28" y="{y + 11}" fill="{accent}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="9" font-weight="600" letter-spacing="0.7">{escape(kind)}</text>',
                    f'<text x="116" y="{y + 11}" fill="{text}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12.5" font-weight="600">{escape(truncate(label, 34))}</text>',
                    f'<text x="116" y="{y + 29}" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="11.5">{escape(truncate(detail, 78))}</text>',
                ]
            )

    lines.append(
        f'<text x="732" y="{height - 10}" text-anchor="end" fill="{muted}" opacity="0.72" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="9">public GitHub data · stable caps</text>'
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2

    try:
        relations = load_json(args.relations)
        policy = load_json(args.policy)
        days, focus_policy, release_policy, upstream_policy = validate_policy(
            policy, args.days
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    groups = relations.get("groups", [])
    repositories = fetch_owned_repositories(args.username, token)
    repo_by_name = {repo["name"].casefold(): repo for repo in repositories}

    focus = recent_focus(groups, repo_by_name, now, cutoff, focus_policy)
    releases = recent_releases(
        repositories, token, cutoff, int(release_policy.get("maxItems", 2))
    )
    allowed_repositories = normalized_repo_set(
        upstream_policy.get("allowedRepositories", [])
    )
    merges = external_merges(
        args.username,
        token,
        cutoff,
        allowed_repositories,
        int(upstream_policy.get("maxItems", 2)),
    )
    rows = build_rows(focus, releases, merges)

    Path(args.light).parent.mkdir(parents=True, exist_ok=True)
    Path(args.dark).parent.mkdir(parents=True, exist_ok=True)
    Path(args.light).write_text(render_svg(rows, days, False), encoding="utf-8")
    Path(args.dark).write_text(render_svg(rows, days, True), encoding="utf-8")

    print(
        json.dumps(
            {
                "windowDays": days,
                "focus": [
                    {"label": item["label"], "repos": item["repos"], "bucket": item["bucket"]}
                    for item in focus
                ],
                "releases": [
                    {"repo": item["repo"], "tag": item["tag"]} for item in releases
                ],
                "externalMerges": [
                    {"repository": item["repository"], "number": item["number"]}
                    for item in merges
                ],
                "caps": {
                    "focusGroups": int(focus_policy.get("maxGroups", 3)),
                    "focusReposPerGroup": int(
                        focus_policy.get("maxRepositoriesPerGroup", 2)
                    ),
                    "releases": int(release_policy.get("maxItems", 2)),
                    "upstream": int(upstream_policy.get("maxItems", 2)),
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
