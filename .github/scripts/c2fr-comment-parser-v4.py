#!/usr/bin/env python3
import json
import pathlib
import re
import sys

if len(sys.argv) != 4:
    raise SystemExit("usage: parser RUN_ID PAYLOAD_OUT KEY_OUT")

run_id, payload_out, key_out = sys.argv[1:]
pages = json.load(sys.stdin)
comments = []
for page in pages:
    if isinstance(page, list):
        comments.extend(page)
    elif isinstance(page, dict):
        comments.append(page)

pattern = re.compile(
    r"^C2FR_PAYLOAD_V4 "
    r"run_id=(\d+) "
    r"kind=(payload|key) "
    r"index=(\d{3}) "
    r"total=(\d{3}) "
    r"data=([A-Za-z0-9+/=]+)$"
)

parts = {"payload": {}, "key": {}}
totals = {}
for comment in comments:
    body = comment.get("body", "")
    match = pattern.fullmatch(body.strip())
    if not match or match.group(1) != run_id:
        continue
    kind = match.group(2)
    index = int(match.group(3))
    total = int(match.group(4))
    data = match.group(5)
    if total < 1 or index >= total:
        raise SystemExit("invalid chunk bounds")
    if kind in totals and totals[kind] != total:
        raise SystemExit("inconsistent chunk total")
    totals[kind] = total
    if index in parts[kind] and parts[kind][index] != data:
        raise SystemExit("conflicting duplicate chunk")
    parts[kind][index] = data

for kind, output in (("payload", payload_out), ("key", key_out)):
    total = totals.get(kind)
    if total is None or len(parts[kind]) != total:
        raise SystemExit(2)
    expected = list(range(total))
    observed = sorted(parts[kind])
    if observed != expected:
        raise SystemExit("missing or non-contiguous chunks")
    joined = "".join(parts[kind][index] for index in expected)
    pathlib.Path(output).write_text(joined + "\n", encoding="ascii")
