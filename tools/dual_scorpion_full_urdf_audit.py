#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np

FULL_URDF = Path("dual_scorpion_Full_urdf/urdf/dual_scorpion.urdf")
FULL_LAUNCH = Path("dual_scorpion_Full_urdf/launch/dual_scorpion.launch")
FULL_PACKAGE = Path("dual_scorpion_Full_urdf/package.xml")

# Canonical aliases for the two left-side Onshape part names.
LINK_ALIAS = {
    "ds_urdf_v4_1": "left_link_2",
    "ds_urdf_v4": "left_link_5",
}

JOINT_MAP = {
    "revolute_1": ("right", "joint0"),
    "revolute_2": ("right", "joint1"),
    "revolute_3": ("right", "joint2"),
    "revolute_4": ("right", "joint3"),
    "revolute_5": ("right", "joint4"),
    "revolute_6": ("right", "joint5"),
    "revolute_7": ("right", "joint6"),
    "revolute_8": ("right", "gripper"),
    "revolute_9": ("left", "joint0"),
    "revolute_10": ("left", "joint1"),
    "revolute_11": ("left", "joint2"),
    "revolute_12": ("left", "joint3"),
    "revolute_13": ("left", "joint4"),
    "revolute_14": ("left", "joint5"),
    "revolute_15": ("left", "joint6"),
    "revolute_16": ("left", "gripper"),
}

# Existing Dual Scorpion kinematic reference used by downstream tooling.
# Values are copied from the source-derived left/right URDF snapshots, not from
# the approximate MuJoCo collision model.
REFERENCE: dict[tuple[str, str], dict[str, Any]] = {
    ("left", "joint0"): {"xyz": [0.2923, 0.0015, 0.3967], "rpy": [-2.77106e-24, 1.07852e-32, 1.54074e-33], "axis": [-1, 0, 0], "limit": [-1.41372, 1.50098]},
    ("left", "joint1"): {"xyz": [-0.0199967, 2.95597e-15, -0.061], "rpy": [-1.17484e-16, 2.77556e-17, 1.36056e-09], "axis": [0, 0, 1], "limit": [-3.05433, 3.05433]},
    ("left", "joint2"): {"xyz": [-0.0183109, -0.0030748, -0.060508], "rpy": [2.53056e-16, 5.7629e-18, -1.88737e-19], "axis": [-1, 0, 0], "limit": [-1.74533, 2.0944]},
    ("left", "joint3"): {"xyz": [0.0008, -0.00520003, -0.1348], "rpy": [-1.5708, 1.39556e-18, -4.95715e-18], "axis": [1, 0, 0], "limit": [-0.523599, 3.31613]},
    ("left", "joint4"): {"xyz": [0.0202033, 2.95597e-15, -0.061], "rpy": [-1.4286e-18, -1.23156e-16, -2.91434e-16], "axis": [0, 0, 1], "limit": [-2.95511, 2.97901]},
    ("left", "joint5"): {"xyz": [0.018551, -0.00329665, -0.060508], "rpy": [-8.12727e-12, -3.1739e-19, -0.0119469], "axis": [-1, 0, 0], "limit": [-1.74533, 2.0944]},
    ("left", "joint6"): {"xyz": [-0.0199967, 2.98372e-15, -0.061], "rpy": [1.05879e-22, 3.17281e-19, -4.33681e-18], "axis": [0, 0, 1], "limit": [-2.96706, 2.96706]},
    ("left", "gripper"): {"xyz": [-0.0202033, -0.0181, -0.0234], "rpy": [-1.20731e-16, 1.3606e-09, -2.78336e-15], "axis": [0, 1, 0], "limit": [-0.174533, 1.91986]},
    ("right", "joint0"): {"xyz": [-0.277418, 0.00138639, 0.393411], "rpy": [-2.27782e-07, -0.0119469, 2.72121e-09], "axis": [-1, 0, 0], "limit": [-1.41372, 1.50098]},
    ("right", "joint1"): {"xyz": [0.0199967, 2.95597e-15, -0.061], "rpy": [-1.19112e-22, -2.60209e-18, -1.36056e-09], "axis": [0, 0, -1], "limit": [-3.05433, 3.05433]},
    ("right", "joint2"): {"xyz": [0.0183109, -0.00307479, -0.060508], "rpy": [-4.46e-17, -1.58727e-16, 1.38777e-17], "axis": [1, 0, 0], "limit": [-2.09439, 1.74533]},
    ("right", "joint3"): {"xyz": [-0.0377, -0.00519997, -0.1348], "rpy": [-1.5708, 3.84241e-16, -1.20677e-16], "axis": [1, 0, 0], "limit": [-0.349066, 3.31613]},
    ("right", "joint4"): {"xyz": [0.0199967, 2.91434e-15, -0.061], "rpy": [6.02058e-17, 1.65148e-18, 1.73472e-18], "axis": [0, 0, 1], "limit": [-2.97901, 2.95511]},
    ("right", "joint5"): {"xyz": [0.0183464, -0.00285582, -0.060508], "rpy": [8.12663e-12, -7.31558e-26, 0.0119469], "axis": [-1, 0, 0], "limit": [-2.0944, 1.74533]},
    ("right", "joint6"): {"xyz": [-0.0202033, 2.91434e-15, -0.061], "rpy": [-2.8453e-31, -9.56554e-42, -4.62593e-18], "axis": [0, 0, 1], "limit": [-2.96706, 2.96706]},
    ("right", "gripper"): {"xyz": [0.0202033, -0.0181, -0.0234], "rpy": [9.95431e-26, 1.36046e-09, 4.62593e-18], "axis": [0, 1, 0], "limit": [-1.91986, 0.174533]},
}


def vec(text: str | None, default=(0.0, 0.0, 0.0)) -> np.ndarray:
    return np.asarray([float(x) for x in text.split()], dtype=float) if text else np.asarray(default, dtype=float)


def rpy_matrix(v: np.ndarray) -> np.ndarray:
    r, p, y = v
    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=float)
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=float)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=float)
    return rz @ ry @ rx


def transform(xyz: np.ndarray, rpy: np.ndarray) -> np.ndarray:
    out = np.eye(4)
    out[:3, :3] = rpy_matrix(rpy)
    out[:3, 3] = xyz
    return out


def origin_transform(node: ET.Element | None) -> np.ndarray:
    if node is None:
        return np.eye(4)
    return transform(vec(node.get("xyz")), vec(node.get("rpy")))


def rotation_error_deg(a: np.ndarray, b: np.ndarray) -> float:
    rel = a.T @ b
    c = float(np.clip((np.trace(rel) - 1.0) / 2.0, -1.0, 1.0))
    return math.degrees(math.acos(c))


def canonical_link(name: str) -> str:
    return LINK_ALIAS.get(name, name)


def read_stl_vertices(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError(f"LFS pointer was not materialized: {path}")
    if len(data) >= 84:
        n = struct.unpack_from("<I", data, 80)[0]
        if 84 + 50 * n == len(data):
            dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attr", "<u2")])
            records = np.frombuffer(data, dtype=dtype, offset=84, count=n)
            return np.asarray(records["vertices"], dtype=np.float64).reshape(-1, 3)
    pts = []
    for line in data.decode("ascii", errors="strict").splitlines():
        f = line.strip().split()
        if len(f) == 4 and f[0].lower() == "vertex":
            pts.append([float(f[1]), float(f[2]), float(f[3])])
    if not pts:
        raise RuntimeError(f"unrecognized STL encoding: {path}")
    return np.asarray(pts, dtype=float)


def mesh_path(repo: Path, uri: str) -> Path:
    prefix = "package://assembly_1/"
    if not uri.startswith(prefix):
        raise RuntimeError(f"unexpected mesh URI: {uri}")
    return repo / "dual_scorpion_Full_urdf" / uri[len(prefix):]


def transform_points(T: np.ndarray, pts: np.ndarray) -> np.ndarray:
    return pts @ T[:3, :3].T + T[:3, 3]


def line_radius_stats(points: np.ndarray, origin: np.ndarray, axis: np.ndarray) -> dict[str, float]:
    axis = axis / np.linalg.norm(axis)
    delta = points - origin
    axial = delta @ axis
    radial = np.linalg.norm(delta - np.outer(axial, axis), axis=1)
    return {
        "min_radius_m": float(np.min(radial)),
        "p01_radius_m": float(np.percentile(radial, 1.0)),
        "p05_radius_m": float(np.percentile(radial, 5.0)),
        "axial_min_m": float(np.min(axial)),
        "axial_max_m": float(np.max(axial)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--output", type=Path, default=Path("dual-scorpion-full-urdf-audit.json"))
    args = ap.parse_args()
    repo = args.repo.resolve()
    urdf_path = repo / FULL_URDF
    root = ET.parse(urdf_path).getroot()

    links = {x.get("name"): x for x in root.findall("link")}
    joints = {x.get("name"): x for x in root.findall("joint")}
    child_links = {j.find("child").get("link") for j in joints.values() if j.find("child") is not None}
    roots = sorted(set(links) - child_links)

    topology = []
    for name, j in joints.items():
        p = j.find("parent").get("link")
        c = j.find("child").get("link")
        topology.append({"joint": name, "type": j.get("type"), "parent": p, "child": c, "canonical_parent": canonical_link(p), "canonical_child": canonical_link(c)})

    # Zero-configuration world transforms. The root fixed transform is retained,
    # so the report also exposes the exported assembly/world offset.
    world: dict[str, np.ndarray] = {roots[0]: np.eye(4)} if len(roots) == 1 else {}
    pending = list(joints.values())
    for _ in range(len(pending) + 2):
        changed = False
        for j in list(pending):
            p = j.find("parent").get("link")
            c = j.find("child").get("link")
            if p in world:
                world[c] = world[p] @ origin_transform(j.find("origin"))
                pending.remove(j)
                changed = True
        if not pending or not changed:
            break

    mesh_rows = []
    link_points_world: dict[str, np.ndarray] = {}
    for link_name, link in links.items():
        visual = link.find("visual")
        if visual is None or visual.find("geometry/mesh") is None:
            continue
        mesh = visual.find("geometry/mesh")
        uri = mesh.get("filename")
        path = mesh_path(repo, uri)
        pts = read_stl_vertices(path)
        Tvisual = origin_transform(visual.find("origin"))
        Tworld = world.get(link_name)
        if Tworld is None:
            raise RuntimeError(f"no world transform for {link_name}")
        wpts = transform_points(Tworld @ Tvisual, pts)
        link_points_world[link_name] = wpts
        bmin, bmax = wpts.min(axis=0), wpts.max(axis=0)
        mesh_rows.append({
            "link": link_name,
            "canonical_link": canonical_link(link_name),
            "uri": uri,
            "file": str(path.relative_to(repo)),
            "bytes": path.stat().st_size,
            "vertex_count": int(len(pts)),
            "bbox_world_min_m": bmin.tolist(),
            "bbox_world_max_m": bmax.tolist(),
            "centroid_world_m": wpts.mean(axis=0).tolist(),
        })

    joint_geometry = []
    for name, j in joints.items():
        if j.get("type") == "fixed":
            continue
        p = j.find("parent").get("link")
        c = j.find("child").get("link")
        Tj = world[p] @ origin_transform(j.find("origin"))
        axis_local = vec(j.find("axis").get("xyz") if j.find("axis") is not None else None, (1, 0, 0))
        axis_world = Tj[:3, :3] @ axis_local
        row: dict[str, Any] = {"joint": name, "parent": p, "child": c, "origin_world_m": Tj[:3, 3].tolist(), "axis_world": axis_world.tolist()}
        if p in link_points_world:
            row["parent_mesh_axis_support"] = line_radius_stats(link_points_world[p], Tj[:3, 3], axis_world)
        if c in link_points_world:
            row["child_mesh_axis_support"] = line_radius_stats(link_points_world[c], Tj[:3, 3], axis_world)
        joint_geometry.append(row)

    reference_compare = []
    for full_name, key in JOINT_MAP.items():
        j = joints[full_name]
        ref = REFERENCE[key]
        o = j.find("origin")
        xyz = vec(o.get("xyz") if o is not None else None)
        rpy = vec(o.get("rpy") if o is not None else None)
        axis = vec(j.find("axis").get("xyz") if j.find("axis") is not None else None, (1, 0, 0))
        axis /= np.linalg.norm(axis)
        ref_axis = np.asarray(ref["axis"], dtype=float)
        ref_axis /= np.linalg.norm(ref_axis)
        lim = j.find("limit")
        full_limit = [float(lim.get("lower")), float(lim.get("upper"))]
        ref_limit = list(ref["limit"])
        neg_ref_limit = [-ref_limit[1], -ref_limit[0]]
        axis_dot = float(axis @ ref_axis)
        limit_same = float(np.max(np.abs(np.asarray(full_limit) - np.asarray(ref_limit))))
        limit_if_axis_flipped = float(np.max(np.abs(np.asarray(full_limit) - np.asarray(neg_ref_limit))))
        parent = canonical_link(j.find("parent").get("link"))
        child = canonical_link(j.find("child").get("link"))
        reference_compare.append({
            "full_joint": full_name,
            "side": key[0],
            "canonical_joint": key[1],
            "canonical_parent": parent,
            "canonical_child": child,
            "origin_delta_m": float(np.linalg.norm(xyz - np.asarray(ref["xyz"], dtype=float))),
            "rotation_delta_deg": rotation_error_deg(rpy_matrix(np.asarray(ref["rpy"], dtype=float)), rpy_matrix(rpy)),
            "axis_dot_reference": axis_dot,
            "axis_relation": "same" if axis_dot > 0.999999 else ("flipped" if axis_dot < -0.999999 else "different"),
            "limit_max_delta_same_axis_rad": limit_same,
            "limit_max_delta_if_axis_flipped_rad": limit_if_axis_flipped,
            "full_limit_rad": full_limit,
            "reference_limit_rad": ref_limit,
        })

    # Mirror sanity at q=0 in exported world coordinates. This is diagnostic;
    # it does not assume mirror symmetry is an acceptance contract.
    pair_names = [
        ("left_link_1", "right_link_1"),
        ("ds_urdf_v4_1", "right_link_2"),
        ("left_link_3", "right_link_3"),
        ("left_link_4", "right_link_4"),
        ("ds_urdf_v4", "right_link_5"),
        ("left_link_6", "right_link_6"),
        ("left_link_7", "right_link_7"),
        ("left_gripper_link", "right_gripper_link"),
    ]
    mirror = []
    for left, right in pair_names:
        lp, rp = link_points_world[left], link_points_world[right]
        lmin, lmax = lp.min(axis=0), lp.max(axis=0)
        rmin, rmax = rp.min(axis=0), rp.max(axis=0)
        mirrored_rmin = np.array([-rmax[0], rmin[1], rmin[2]])
        mirrored_rmax = np.array([-rmin[0], rmax[1], rmax[2]])
        mirror.append({
            "left": left,
            "right": right,
            "bbox_mirror_max_error_m": float(max(np.max(np.abs(lmin - mirrored_rmin)), np.max(np.abs(lmax - mirrored_rmax)))),
            "centroid_mirror_error_m": float(np.linalg.norm(lp.mean(axis=0) - np.array([-rp.mean(axis=0)[0], rp.mean(axis=0)[1], rp.mean(axis=0)[2]]))),
        })

    inertial_warnings = []
    for name, link in links.items():
        inertial = link.find("inertial")
        if inertial is None:
            continue
        mass_node = inertial.find("mass")
        mass = float(mass_node.get("value")) if mass_node is not None else None
        inertia = inertial.find("inertia")
        diag = [float(inertia.get(k)) for k in ("ixx", "iyy", "izz")] if inertia is not None else []
        if mass is not None and mass < 1e-6:
            inertial_warnings.append({"link": name, "kind": "sub_milligram_mass", "mass_kg": mass})
        if diag and min(diag) <= 0:
            inertial_warnings.append({"link": name, "kind": "nonpositive_principal_inertia", "diag": diag})

    launch_text = (repo / FULL_LAUNCH).read_text(encoding="utf-8") if (repo / FULL_LAUNCH).exists() else ""
    launch_urdf_match = re.search(r"urdf_file.*?default=\"([^\"]+)\"", launch_text)
    launch_urdf = launch_urdf_match.group(1) if launch_urdf_match else None

    report = {
        "schema_version": 1,
        "upstream_full_urdf": str(FULL_URDF),
        "links": sorted(links),
        "canonical_links": sorted(canonical_link(x) for x in links),
        "joints": sorted(joints),
        "roots": roots,
        "unresolved_fk_joints": [j.get("name") for j in pending],
        "package_xml_exists": (repo / FULL_PACKAGE).exists(),
        "launch_urdf_reference": launch_urdf,
        "actual_urdf_relative_path": str(FULL_URDF),
        "launch_path_matches_actual_filename": bool(launch_urdf and Path(launch_urdf).name == FULL_URDF.name),
        "topology": topology,
        "mesh_count": len(mesh_rows),
        "meshes": mesh_rows,
        "joint_geometry": joint_geometry,
        "reference_joint_comparison": reference_compare,
        "left_right_mirror_diagnostic": mirror,
        "inertial_warnings": inertial_warnings,
        "summary": {
            "tree_connected": len(roots) == 1 and not pending,
            "expected_17_meshes_present": len(mesh_rows) == 17,
            "canonical_left_link_2_alias": "ds_urdf_v4_1" in links,
            "canonical_left_link_5_alias": "ds_urdf_v4" in links,
            "reference_joint_rows_with_axis_flip": [f"{r['side']}/{r['canonical_joint']}" for r in reference_compare if r["axis_relation"] == "flipped"],
            "reference_joint_rows_origin_gt_1mm": [f"{r['side']}/{r['canonical_joint']}" for r in reference_compare if r["origin_delta_m"] > 0.001],
            "reference_joint_rows_rotation_gt_0_1deg": [f"{r['side']}/{r['canonical_joint']}" for r in reference_compare if r["rotation_delta_deg"] > 0.1],
            "max_mirror_bbox_error_m": max((r["bbox_mirror_max_error_m"] for r in mirror), default=None),
        },
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print("REFERENCE_COMPARISON")
    for row in reference_compare:
        print(json.dumps(row, sort_keys=True))
    print("MIRROR_DIAGNOSTIC")
    for row in mirror:
        print(json.dumps(row, sort_keys=True))
    print("INERTIAL_WARNINGS")
    for row in inertial_warnings:
        print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
