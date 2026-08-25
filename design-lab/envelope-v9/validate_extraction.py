#!/usr/bin/env python3
"""Validate the copyable Envelope v9 core and GitHub-profile transformer."""
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


def expected_repository_creation(readiness: dict[str, str]) -> str:
    technical = readiness["technical_copy_set"] == "PASS"
    external_demand = (
        readiness["independent_consumer"] == "ESTABLISHED"
        or readiness["concrete_reuse_request"] == "ESTABLISHED"
    )
    license_selected = readiness["license_selection"] == "SELECTED"
    return "READY" if technical and external_demand and license_selected else "DEFERRED"


def assert_publication_readiness(manifest: dict) -> None:
    readiness = manifest["publication_readiness"]
    assert readiness["technical_copy_set"] in {"PASS", "NOT_PASS"}
    assert readiness["independent_consumer"] in {"ESTABLISHED", "NOT_ESTABLISHED"}
    assert readiness["concrete_reuse_request"] in {"ESTABLISHED", "NOT_ESTABLISHED"}
    assert readiness["license_selection"] in {"SELECTED", "UNSELECTED"}
    assert readiness["repository_creation"] in {"READY", "DEFERRED"}
    assert readiness["repository_creation"] == expected_repository_creation(readiness)

    # Discriminating state checks: technical copyability alone must never authorize publication.
    assert expected_repository_creation({
        "technical_copy_set": "PASS",
        "independent_consumer": "NOT_ESTABLISHED",
        "concrete_reuse_request": "NOT_ESTABLISHED",
        "license_selection": "SELECTED",
    }) == "DEFERRED"
    assert expected_repository_creation({
        "technical_copy_set": "PASS",
        "independent_consumer": "ESTABLISHED",
        "concrete_reuse_request": "NOT_ESTABLISHED",
        "license_selection": "UNSELECTED",
    }) == "DEFERRED"
    assert expected_repository_creation({
        "technical_copy_set": "PASS",
        "independent_consumer": "NOT_ESTABLISHED",
        "concrete_reuse_request": "ESTABLISHED",
        "license_selection": "SELECTED",
    }) == "READY"
    assert expected_repository_creation({
        "technical_copy_set": "NOT_PASS",
        "independent_consumer": "ESTABLISHED",
        "concrete_reuse_request": "ESTABLISHED",
        "license_selection": "SELECTED",
    }) == "DEFERRED"


def second_consumer_svg(rel: str) -> str:
    """A structurally different donor using only the portable marker contract."""
    if rel.endswith("profile-character-side-left.svg") or rel.endswith("profile-character-side-right.svg"):
        width, height = 120, 360
    elif rel.endswith("profile-projects-canvas.svg"):
        width, height = 900, 360
    elif rel.endswith("profile-activity-canvas.svg"):
        width, height = 900, 180
    else:
        width, height = 900, 64

    mounted = ""
    defs = ""
    if rel.endswith("profile-projects-canvas.svg"):
        defs = '<defs><linearGradient id="consumer-b-surface"><stop stop-color="#123456"/></linearGradient></defs>'
        mounted = '<rect data-profile-envelope-mounted-background="presentation" width="100%" height="100%" fill="url(#consumer-b-surface)"/>'
    elif rel.endswith("profile-activity-canvas.svg"):
        mounted = '<rect data-profile-envelope-mounted-background="presentation" width="810" height="180" fill="#112233"/>'

    frame_path = f"M7 0V{height} M{max(8, width - 7)} 0V{height}"
    frame = f'<g data-profile-envelope-frame="rail"><path d="{frame_path}"/></g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'{defs}<rect data-profile-envelope-surface-base="outer" id="consumer-b-base" width="{width}" height="100%" fill="#223344"/>{mounted}'
        '<text x="20" y="44" font-size="22" fill="#f0f6fc">SECOND 28 &amp; SAFE</text>'
        f'{frame}</svg>\n'
    )


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    assert manifest["public_repo_creation"] == "defer-until-external-demand-and-license"
    assert manifest["readiness_claim"] == "standalone-core-and-marker-github-transformer"
    assert_publication_readiness(manifest)

    core = manifest["layers"]["portable_core"]
    adapters = manifest["layers"]["portable_adapters"]
    donor = manifest["layers"]["donor_producer"]
    assert len(core) == 5
    assert len(adapters) == 1 and adapters[0]["status"] == "standalone-copyable"
    assert len(donor) == 1 and donor[0]["status"] == "donor-bound"

    copy_items = core + adapters
    sources = [item["source"] for item in copy_items]
    destinations = [item["destination"] for item in copy_items]
    assert len(sources) == len(set(sources))
    assert len(destinations) == len(set(destinations))
    assert all(not destination.startswith("design-lab/") for destination in destinations)

    forbidden = tuple(manifest["portable_forbidden_tokens"])
    for item in copy_items:
        source = ROOT / item["source"]
        assert source.is_file(), source
        text = source.read_text(encoding="utf-8")
        hits = [token for token in forbidden if token in text]
        assert not hits, (item["source"], hits)

    for item in copy_items:
        if not item["source"].endswith(".py"):
            continue
        source = ROOT / item["source"]
        allowed_internal = {"profile_envelope"}
        non_stdlib = sorted(
            module for module in imported_roots(source)
            if module != "__future__" and module not in sys.stdlib_module_names and module not in allowed_internal
        )
        assert not non_stdlib, (source, non_stdlib)

    with tempfile.TemporaryDirectory() as tmp:
        extracted = Path(tmp) / "profile-envelope"
        for item in copy_items:
            source = ROOT / item["source"]
            destination = extracted / item["destination"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        contract_path = extracted / "src/profile_envelope/contract.py"
        vector_path = extracted / "src/profile_envelope/vector_text.py"
        transform_path = extracted / "src/profile_envelope/github_profile_transform.py"
        schema_path = extracted / "schema/profile-envelope-config.schema.json"
        opaque_path = extracted / "examples/opaque-safe.json"
        transparent_path = extracted / "examples/transparent-safe.json"

        for path in (contract_path, vector_path, transform_path):
            py_compile.compile(str(path), doraise=True)

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
        transform = load_module("extracted_profile_envelope_transform", transform_path)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assert_schema_alignment(schema, contract)

        sample = '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="80"><text x="20" y="48" font-size="24" fill="#f0f6fc">HELLO 28 &amp; SAFE</text></svg>'
        rendered, count = vector.vectorize_visible_text(sample)
        assert count == 1 and "<text" not in rendered
        assert 'data-vector-text="v1"' in rendered
        assert 'aria-label="HELLO 28 &amp; SAFE"' in rendered

        donor_root = extracted / "second-consumer-donor"
        for rel in transform.asset_paths():
            path = donor_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(second_consumer_svg(rel), encoding="utf-8")

        transparent_contract, transparent_resolved = contract.load_and_resolve(transparent_path)
        transformed_root = extracted / "second-consumer-transformed"
        transformed = transform.transform_bundle(
            donor_root,
            transformed_root,
            contract=transparent_contract,
            resolved=transparent_resolved,
            season="summer",
        )
        assert len(transformed["render_target_sha256"]) == 64
        assert len(transform.asset_paths()) == 15
        for rel in transform.asset_paths():
            svg = (transformed_root / rel).read_text(encoding="utf-8")
            assert 'data-envelope-presentation="v9-portable-surface"' in svg
            assert f'data-profile-render-target-sha256="{transformed["render_target_sha256"]}"' in svg
            assert "consumer-b-base" not in svg
            assert "<text" not in svg
            assert 'data-v9-adaptive-vector-text-style="v1"' in svg
            assert "data-profile-envelope-surface-base=" not in svg
            assert "data-profile-envelope-frame=" not in svg
            assert "data-profile-envelope-mounted-background=" not in svg
        assert 'fill="url(#consumer-b-surface)"' not in (transformed_root / "assets/profile-projects-canvas.svg").read_text()
        assert '#112233' not in (transformed_root / "assets/profile-activity-canvas.svg").read_text()

    assert (ROOT / donor[0]["source"]).is_file()
    gates = manifest["promotion_gates"]
    assert gates["create_public_repository"] and gates["create_new_skill"]

    readiness = manifest["publication_readiness"]
    print(
        "ENVELOPE_V9_EXTRACTION_TRANSFORM_PASS "
        f"core_files={len(core)} adapter_files={len(adapters)} python_stdlib_only=true personalized_tokens=0 "
        "standalone_contract=PASS standalone_vector_text=PASS standalone_github_transform=PASS schema_alignment=PASS"
    )
    print("SECOND_CONSUMER_FIXTURE_PASS donor_identity=v8-independent geometry=heterogeneous generic_markers=3")
    print(
        "PUBLICATION_GATE=PASS "
        f"technical_copy_set={readiness['technical_copy_set']} "
        f"independent_consumer={readiness['independent_consumer']} "
        f"concrete_reuse_request={readiness['concrete_reuse_request']} "
        f"license_selection={readiness['license_selection']} "
        f"repository_creation={readiness['repository_creation']}"
    )
    print(
        "PUBLIC_REPO_CREATE=DEFERRED donor_producer=donor-bound "
        "second_consumer=FIXTURE_ONLY independent_consumer=NOT_ESTABLISHED "
        "concrete_reuse_request=NOT_ESTABLISHED license_selection=UNSELECTED new_skill=DEFERRED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
