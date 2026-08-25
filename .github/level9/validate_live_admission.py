#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
EVALUATOR = ROOT / "experiments/execution-admission-observation/evaluate_v01.py"


def load_evaluator():
    spec = importlib.util.spec_from_file_location("level9_admission_eval", EVALUATOR)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load pinned Level 9 evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def outcome(ok: bool) -> str:
    return "PASS" if ok else "BLOCKED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True)
    parser.add_argument("--mem-kib", type=int, required=True)
    parser.add_argument("--free-disk-kib", type=int, required=True)
    parser.add_argument("--load1", type=float, required=True)
    parser.add_argument("--cpus", type=int, required=True)
    parser.add_argument("--min-mem-kib", type=int, required=True)
    parser.add_argument("--min-free-disk-kib", type=int, required=True)
    parser.add_argument("--max-load-per-cpu", type=float, required=True)
    parser.add_argument("--carrier-head", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--authority-ref", required=True)
    parser.add_argument("--track-a-ref", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if args.cpus <= 0:
        raise SystemExit("cpus must be positive")

    load_per_cpu = args.load1 / args.cpus
    checks = [
        {
            "id": "available-ram",
            "required": True,
            "criterion": f"MemAvailable >= {args.min_mem_kib} KiB",
            "observed": args.mem_kib,
            "unit": "KiB",
            "outcome": outcome(args.mem_kib >= args.min_mem_kib),
        },
        {
            "id": "free-disk",
            "required": True,
            "criterion": f"free disk >= {args.min_free_disk_kib} KiB",
            "observed": args.free_disk_kib,
            "unit": "KiB",
            "outcome": outcome(args.free_disk_kib >= args.min_free_disk_kib),
        },
        {
            "id": "normalized-load",
            "required": True,
            "criterion": f"load1 / nproc <= {args.max_load_per_cpu}",
            "observed": load_per_cpu,
            "unit": "ratio",
            "outcome": outcome(load_per_cpu <= args.max_load_per_cpu),
        },
    ]

    native_decision = "PASS" if all(item["outcome"] == "PASS" for item in checks) else "BLOCKED"
    payload = {
        "schemaVersion": 1,
        "observationId": f"rerobot-hosted-{os.environ.get('GITHUB_RUN_ID', 'unknown')}-{os.environ.get('GITHUB_RUN_ATTEMPT', 'unknown')}-{args.phase}",
        "mode": "LIVE",
        "target": {
            "owner": "nekomario28/nekomario28#87",
            "resource": "github-hosted-ubuntu-latest",
            "revision": args.carrier_head,
            "workload": f"Rerobot-vs-LeRobot Phase43 {args.phase}",
            "executionRef": args.run_url,
        },
        "gate": {
            "gateId": "phase43-hosted-resource-admission",
            "phase": "PRE_PAYLOAD",
            "authorityRef": args.authority_ref,
        },
        "checks": checks,
        "decision": native_decision,
        "payloadState": "NOT_STARTED",
        "evidence": [
            {"route": "RUN_URL", "locator": args.run_url},
            {"route": "WORKFLOW_DEFINITION", "locator": ".github/workflows/temp-rerobot-paired-cpu-hosted-track-a.yml"},
            {"route": "RESEARCH_RECEIPT", "locator": args.track_a_ref},
        ],
        "claimBoundary": {
            "proves": [
                "the frozen Phase43 host admission facts were observed before this payload boundary",
                "the shared decision matches the independently frozen native decision for the same facts",
            ],
            "doesNotProve": [
                "pairing warmup success",
                "measured benchmark success",
                "performance or speed ratio",
                "authority to change thresholds, rerun, cleanup, or execute physical hardware",
            ],
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    evaluator = load_evaluator()
    schema = evaluator.load(evaluator.SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = evaluator.schema_errors(validator, payload)
    semantic_errors = evaluator.semantic_errors(payload)
    shared_decision = evaluator.derive_decision(payload)

    if schema_errors:
        for err in schema_errors:
            print(f"LEVEL9_ADMISSION_SCHEMA_FAIL path={'/'.join(map(str, err.absolute_path))} message={err.message}")
        return 2
    if semantic_errors:
        for err in semantic_errors:
            print(f"LEVEL9_ADMISSION_SEMANTIC_FAIL {err}")
        return 2
    if shared_decision != native_decision:
        print(f"LEVEL9_ADMISSION_DECISION_MISMATCH native={native_decision} shared={shared_decision}")
        return 2

    print(
        "LEVEL9_EXECUTION_ADMISSION_OBSERVATION_PASS "
        f"phase={args.phase} native={native_decision} shared={shared_decision} "
        f"mem_kib={args.mem_kib} free_disk_kib={args.free_disk_kib} "
        f"load1={args.load1} cpus={args.cpus} receipt={out}"
    )
    if native_decision == "BLOCKED":
        print("LEVEL9_OWNER_NATIVE_BLOCKED payload_not_started=true")
        return 42
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
