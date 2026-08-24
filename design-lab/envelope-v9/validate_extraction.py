#!/usr/bin/env python3
"""Validate the copyable Envelope v9 kernel without pretending the donor renderer is standalone."""
from __future__ import annotations

import ast
import importlib.util
import json
import py_compile
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "portable-package-manifest.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def assert_schema_alignment(schema: dict, contract) -> None:
    assert schema["$id"] == "urn:profile-envelope:config:v1"
    props = schema["properties"]
    assert props["contract_version"]["const"] == contract.CONTRACT_VERSION
    assert props["target_adapter"]["const"] == contract.TARGET_ADAPTER
    mapping = {
        ("profile", "background"): props["profile"]["properties"]["background"]["enum"],
        ("profile", "text"): props["profile"]["properties"]["text"]["enum"],
        ("profile", "motion"): props["profile"]["properties"]["motion"]["enum"],
        ("surface", "mounted_source_background"): props["surface"]["properties"]["mounted_source_background"]["enum"],
        ("frame", "mode"): props["frame"]["properties"]["mode"]["enum"],
        ("frame", "caps"): props["frame"]["properties"]["caps"]["enum"],
        ("labels", "density"): props["labels"]["properties"]["density"]["enum"],
        ("packing", "mode"): props["packing"]["properties"]["mode"]["enum"],
        ("external_media", "mode"): props["external_media"]["properties"]["mode"]["enum"],
    }
    for key, values in mapping.items():
        assert set(values) == set(contract.ALLOWED[key]), (key, values, contract.ALLOWED[key])


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    assert manifest["public_repo_creation"] == "defer-until-independent-consumer"
    assert manifest["readiness_claim"] == "standalone-copy-set-only"

    core = manifest["layers"]["portable_core"]
    assert len(core) >= 5
    sources = [item["source"] for item in core]
    destinations = [item["destination"] for item in core]
    assert len(sources) == len(set(sources))
    assert len(destinations) == len(set(destinations))
    assert all(not destination.startswith("design-lab/") for destination in destinations)

    forbidden = tuple(manifest["portable_core_forbidden_tokens"])
    for item in core:
        source = ROOT / item["source"]
        assert source.is_file(), source
        text = source.read_text(encoding="utf-8")
        hits = [token for token in forbidden if token in text]
        assert not hits, (item["source"], hits)

    python_sources = [ROOT / item["source"] for item in core if item["source"].endswith(".py")]
    for source in python_sources:
        third_party = sorted(
            module for module in imported_roots(source)
            if module != "__future__" and module not in sys.stdlib_module_names
        )
        assert not third_party, (source, third_party)

    with tempfile.TemporaryDirectory() as tmp:
        extracted = Path(tmp) / "profile-envelope"
        for item in core:
            source = ROOT / item["source"]
            destination = extracted / item["destination"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        contract_path = extracted / "src/profile_envelope/contract.py"
        vector_path = extracted / "src/profile_envelope/vector_text.py"
        schema_path = extracted / "schema/profile-envelope-config.schema.json"
        opaque_path = extracted / "examples/opaque-safe.json"
        transparent_path = extracted / "examples/transparent-safe.json"

        py_compile.compile(str(contract_path), doraise=True)
        py_compile.compile(str(vector_path), doraise=True)

        for config in (opaque_path, transparent_path):
            completed = subprocess.run(
                [sys.executable, str(contract_path), str(config), "--resolved-json"],
                text=True,
                capture_output=True,
                check=False,
                cwd=extracted,
            )
            assert completed.returncode == 0, completed.stderr or completed.stdout
            receipt = json.loads(completed.stdout)
            assert receipt["contract"]["target_adapter"] == "github-profile-readme"
            assert len(receipt["resolved"]["normalized_contract_sha256"]) == 64

        contract = load_module("extracted_profile_envelope_contract", contract_path)
        vector = load_module("extracted_profile_envelope_vector_text", vector_path)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assert_schema_alignment(schema, contract)

        sample = '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="80"><text x="20" y="48" font-size="24" fill="#f0f6fc">HELLO 28 &amp; SAFE</text></svg>'
        rendered, count = vector.vectorize_visible_text(sample)
        assert count == 1
        assert "<text" not in rendered
        assert 'data-vector-text="v1"' in rendered
        assert 'aria-label="HELLO 28 &amp; SAFE"' in rendered

    adapter = manifest["layers"]["github_adapter_candidate"]
    assert len(adapter) == 1 and adapter[0]["status"] == "donor-bound"
    assert (ROOT / adapter[0]["source"]).is_file()
    gates = manifest["promotion_gates"]
    assert gates["create_public_repository"] and gates["create_new_skill"]

    print(
        "ENVELOPE_V9_EXTRACTION_READINESS_PASS "
        f"core_files={len(core)} python_stdlib_only=true personalized_tokens=0 "
        "standalone_contract=PASS standalone_vector_text=PASS schema_alignment=PASS"
    )
    print(
        "PUBLIC_REPO_CREATE=DEFERRED renderer_adapter=donor-bound "
        "second_consumer=NOT_ESTABLISHED new_skill=DEFERRED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
