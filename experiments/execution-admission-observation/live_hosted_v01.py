#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import time
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "registry/active-prospective-gates.json"
SCHEMA_PATH = ROOT / "schemas/agent-engineering/execution-admission-observation.schema.json"
EVALUATOR_PATH = ROOT / "experiments/execution-admission-observation/evaluate_v01.py"
GATE_ID = "level9-execution-admission-first-native-consumer"
SUBSTRATE_SHA = "28577f133fedbc6fee41675b627b7b8f653d8229"
PREREG_SHA = "ab07e597339fe047750984212022463f67acbfea"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_evaluator():
    spec = importlib.util.spec_from_file_location("level9_admission_evaluator", EVALUATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load pinned admission evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def outcome(ok: bool) -> str:
    return "PASS" if ok else "BLOCKED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["pre-warmup", "pre-measurement"], required=True)
    parser.add_argument("--mem-kib", type=int, required=True)
    parser.add_argument("--free-kib", type=int, required=True)
    parser.add_argument("--load1", type=float, required=True)
    parser.add_argument("--cpus", type=int, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    started = time.perf_counter_ns()
    gates = load(GATE_PATH)
    matches = [item for item in gates.get("gates", []) if item.get("gateId") == GATE_ID]
    if len(matches) != 1:
        raise SystemExit(f"active gate lookup expected one match, got {len(matches)}")
    gate = matches[0]
    if gate.get("state") != "ACTIVE" or "PRE_PAYLOAD_ADMISSION" not in gate.get("eventTypes", []):
        raise SystemExit("pinned gate is not ACTIVE for PRE_PAYLOAD_ADMISSION")
    if gate.get("preDecisionRequired") is not True:
        raise SystemExit("pinned gate lost preDecisionRequired=true")
    required_actions = set(gate.get("requiredActions", []))
    expected_actions = {
        "freeze native baseline before shared observation",
        "construct EXECUTION_ADMISSION_OBSERVATION from already-available read-only facts",
        "compare native and shared decisions/costs before promotion",
    }
    if not expected_actions.issubset(required_actions):
        raise SystemExit("pinned gate requiredActions drifted")
    print(f"LEVEL9_ACTIVE_GATE_QUERY_PASS gateId={GATE_ID} phase={args.phase}")

    if args.cpus <= 0:
        raise SystemExit("cpus must be positive")
    mem_ok = args.mem_kib >= 4 * 1024 * 1024
    disk_ok = args.free_kib >= 10 * 1024 * 1024
    load_ratio = args.load1 / args.cpus
    load_ok = load_ratio <= 1.5
    native_decision = "PASS" if mem_ok and disk_ok and load_ok else "BLOCKED"

    checks = [
        {
            "id": "mem-available",
            "required": True,
            "criterion": "MemAvailable >= 4 GiB",
            "observed": args.mem_kib,
            "unit": "KiB",
            "outcome": outcome(mem_ok),
        },
        {
            "id": "free-disk",
            "required": True,
            "criterion": "free disk >= 10 GiB",
            "observed": args.free_kib,
            "unit": "KiB",
            "outcome": outcome(disk_ok),
        },
        {
            "id": "normalized-load",
            "required": True,
            "criterion": "load1 / nproc <= 1.5",
            "observed": f"load1={args.load1} cpus={args.cpus} ratio={load_ratio:.9f}",
            "outcome": outcome(load_ok),
        },
    ]

    run_url = f"https://github.com/nekomario28/nekomario28/actions/runs/{args.run_id}"
    payload = {
        "schemaVersion": 1,
        "observationId": f"rerobot-phase43-{args.phase}-{args.run_id}-attempt-{args.run_attempt}",
        "mode": "LIVE",
        "target": {
            "owner": "nekomario28/nekomario28",
            "resource": "github-hosted-runner",
            "revision": args.revision,
            "workload": f"rerobot-vs-lerobot-phase43-{args.phase}",
            "executionRef": run_url,
        },
        "gate": {
            "gateId": GATE_ID,
            "phase": "PRE_PAYLOAD",
            "authorityRef": f"nekomario28/project-incubator@{SUBSTRATE_SHA}:registry/active-prospective-gates.json",
        },
        "checks": checks,
        "decision": native_decision,
        "payloadState": "NOT_STARTED",
        "evidence": [
            {"route": "RUN_URL", "locator": run_url},
            {
                "route": "WORKFLOW_DEFINITION",
                "locator": f"nekomario28/nekomario28@{args.revision}:.github/workflows/temp-rerobot-paired-cpu-hosted.yml",
            },
            {
                "route": "RESEARCH_RECEIPT",
                "locator": f"nekomario28/project-incubator@{PREREG_SHA}:research/2026-08-25-level-9-rerobot-hosted-track-a-preregistration.md",
            },
        ],
        "claimBoundary": {
            "proves": [
                "the pinned active PRE_PAYLOAD gate was consulted before the owner admission decision",
                "the shared observation used the same frozen RAM/disk/load facts and thresholds as the native admission gate",
                "the shared derived decision agrees with the frozen native decision for this phase",
            ],
            "doesNotProve": [
                "warmup success",
                "measured benchmark success",
                "performance or speed ratio",
                "semantic equivalence beyond the frozen Phase-43 benchmark contract",
            ],
        },
    }

    schema = load(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    evaluator = load_evaluator()
    schema_errors = evaluator.schema_errors(validator, payload)
    semantic_errors = evaluator.semantic_errors(payload)
    if schema_errors or semantic_errors:
        for err in schema_errors:
            print(f"LEVEL9_SCHEMA_FAIL path={'/'.join(map(str, err.absolute_path))} message={err.message}")
        for err in semantic_errors:
            print(f"LEVEL9_SEMANTIC_FAIL {err}")
        return 1

    shared_decision = evaluator.derive_decision(payload)
    if shared_decision != native_decision:
        raise SystemExit(f"native/shared mismatch native={native_decision} shared={shared_decision}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elapsed = time.perf_counter_ns() - started
    print(f"LEVEL9_NATIVE_ADMISSION decision={native_decision} phase={args.phase}")
    print(f"LEVEL9_SHARED_ADMISSION decision={shared_decision} phase={args.phase}")
    print(f"LEVEL9_NATIVE_SHARED_AGREEMENT=PASS phase={args.phase}")
    print(f"LEVEL9_ADMISSION_COMPONENT_OVERHEAD_NS={elapsed} phase={args.phase}")
    print(f"LEVEL9_ADMISSION_OBSERVATION_PATH={args.out}")
    print(f"LEVEL9_DECISION={shared_decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
