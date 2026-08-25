#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/agent-engineering/execution-admission-observation.schema.json"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

VALID = [
    "waydroid-blocked-v01.json",
    "waydroid-pass-v01.json",
    "grrc-quiet-host-blocked-v01.json",
    "ornith-q6-resource-blocked-v01.json",
]
INVALID = ["invalid-blocked-after-payload-start-v01.json"]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def schema_errors(validator: Draft202012Validator, payload):
    return sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))


def derive_decision(payload) -> str:
    required = [item for item in payload["checks"] if item["required"]]
    if any(item["outcome"] == "BLOCKED" for item in required):
        return "BLOCKED"
    if any(item["outcome"] == "UNKNOWN" for item in required):
        return "UNKNOWN"
    return "PASS"


def semantic_errors(payload) -> list[str]:
    found: list[str] = []
    derived = derive_decision(payload)
    if payload["decision"] != derived:
        found.append(f"decision={payload['decision']} derived={derived}")
    if payload["payloadState"] == "STARTED" and payload["decision"] != "PASS":
        found.append("payload STARTED requires PASS admission")
    if payload["decision"] in {"BLOCKED", "UNKNOWN"} and payload["payloadState"] == "STARTED":
        found.append(f"{payload['decision']} admission cannot have STARTED payload")
    return found


def main() -> int:
    schema = load(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    for name in VALID:
        payload = load(FIXTURES / name)
        found = schema_errors(validator, payload)
        semantic = semantic_errors(payload)
        if found or semantic:
            for err in found:
                print(f"FAIL valid={name} path={'/'.join(map(str, err.absolute_path))} message={err.message}")
            for err in semantic:
                print(f"FAIL valid={name} semantic={err}")
            return 1
        print(f"PASS valid={name} decision={payload['decision']} payloadState={payload['payloadState']}")

    for name in INVALID:
        payload = load(FIXTURES / name)
        found = schema_errors(validator, payload)
        semantic = semantic_errors(payload)
        if not found and not semantic:
            print(f"FAIL invalid={name} unexpectedly accepted")
            return 1
        print(f"PASS invalid={name} rejected schemaErrors={len(found)} semanticErrors={len(semantic)}")

    print(f"EXECUTION_ADMISSION_OBSERVATION_EVAL PASS valid={len(VALID)} invalid={len(INVALID)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
