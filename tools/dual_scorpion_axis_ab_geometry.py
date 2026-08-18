#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
BASE_AUDIT = HERE / "dual_scorpion_full_urdf_audit.py"

R_MIN, R_MAX = 0.003, 0.040
AXIAL_WINDOW = 0.045
NORMAL_AXIS_MAX, NORMAL_RADIAL_MIN = 0.30, 0.70
RADIUS_BIN, ANGLE_BINS = 0.001, 24


def load_base():
    spec = importlib.util.spec_from_file_location("full_audit", BASE_AUDIT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load base audit")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def tri_geom(tri: np.ndarray):
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    cross = np.cross(b - a, c - a)
    norm = np.linalg.norm(cross, axis=1)
    normals = np.zeros_like(cross)
    valid = norm > 1e-15
    normals[valid] = cross[valid] / norm[valid, None]
    return (a + b + c) / 3.0, normals, 0.5 * norm


def basis(axis: np.ndarray):
    seed = np.asarray([0.0, 1.0, 0.0]) if abs(axis[0]) > 0.8 else np.asarray([1.0, 0.0, 0.0])
    u = seed - np.dot(seed, axis) * axis
    u /= np.linalg.norm(u)
    return u, np.cross(axis, u)


def cylinder_support(centroids, normals, areas, origin, axis) -> dict[str, Any]:
    axis = np.asarray(axis, float)
    axis /= np.linalg.norm(axis)
    delta = centroids - origin
    axial = delta @ axis
    radial_vec = delta - axial[:, None] * axis
    radius = np.linalg.norm(radial_vec, axis=1)
    rhat = np.zeros_like(radial_vec)
    nz = radius > 1e-12
    rhat[nz] = radial_vec[nz] / radius[nz, None]
    mask = (
        (np.abs(axial) <= AXIAL_WINDOW)
        & (radius >= R_MIN) & (radius <= R_MAX)
        & (np.abs(normals @ axis) <= NORMAL_AXIS_MAX)
        & (np.abs(np.sum(normals * rhat, axis=1)) >= NORMAL_RADIAL_MIN)
        & (areas > 0)
    )
    if not np.any(mask):
        return {"score_m2": 0.0, "dominant_radius_m": None, "support_area_m2": 0.0, "angular_coverage": 0.0, "axial_span_m": 0.0, "candidate_face_count": 0}
    all_bins = np.floor(radius / RADIUS_BIN).astype(int)
    active_bins = all_bins[mask]
    best_bin = max(np.unique(active_bins), key=lambda k: float(np.sum(areas[mask][np.abs(active_bins - k) <= 1])))
    band = mask & (np.abs(all_bins - best_bin) <= 1)
    band_area = float(np.sum(areas[band]))
    dominant_radius = float(np.average(radius[band], weights=areas[band]))
    u, v = basis(axis)
    angles = np.arctan2(radial_vec[band] @ v, radial_vec[band] @ u)
    angle_idx = np.clip(np.floor((angles + math.pi) / (2 * math.pi) * ANGLE_BINS).astype(int), 0, ANGLE_BINS - 1)
    coverage = len(np.unique(angle_idx)) / ANGLE_BINS
    axial_span = float(np.max(axial[band]) - np.min(axial[band]))
    return {
        "score_m2": band_area * (0.25 + 0.75 * coverage),
        "dominant_radius_m": dominant_radius,
        "support_area_m2": band_area,
        "angular_coverage": coverage,
        "axial_span_m": axial_span,
        "candidate_face_count": int(np.count_nonzero(band)),
    }


def old_world(a):
    world = {"base_link": np.eye(4)}
    joints = {}
    for side in ("left", "right"):
        parent = "base_link"
        for idx in range(7):
            key = (side, f"joint{idx}")
            ref = a.REFERENCE[key]
            child = f"{side}_link_{idx + 1}"
            Tj = world[parent] @ a.transform(np.asarray(ref["xyz"], float), np.asarray(ref["rpy"], float))
            axis = Tj[:3, :3] @ np.asarray(ref["axis"], float)
            joints[key] = {"origin": Tj[:3, 3], "axis": axis, "parent": parent, "child": child}
            world[child] = Tj
            parent = child
        key = (side, "gripper")
        ref = a.REFERENCE[key]
        child = f"{side}_gripper_link"
        Tj = world[parent] @ a.transform(np.asarray(ref["xyz"], float), np.asarray(ref["rpy"], float))
        axis = Tj[:3, :3] @ np.asarray(ref["axis"], float)
        joints[key] = {"origin": Tj[:3, 3], "axis": axis, "parent": parent, "child": child}
        world[child] = Tj
    return world, joints


def new_world_and_joints(a, root):
    world = {"base_link": np.eye(4)}
    pending = [j for j in root.findall("joint") if j.find("parent").get("link") != "root"]
    joint_rows = {}
    for _ in range(len(pending) + 2):
        changed = False
        for j in list(pending):
            p = j.find("parent").get("link")
            c = j.find("child").get("link")
            if p not in world:
                continue
            Tj = world[p] @ a.origin_transform(j.find("origin"))
            axis_local = a.vec(j.find("axis").get("xyz") if j.find("axis") is not None else None, (1, 0, 0))
            axis = Tj[:3, :3] @ axis_local
            world[c] = Tj
            if j.get("type") != "fixed":
                key = a.JOINT_MAP[j.get("name")]
                joint_rows[key] = {"origin": Tj[:3, 3], "axis": axis, "parent": a.canonical_link(p), "child": a.canonical_link(c), "name": j.get("name")}
            pending.remove(j)
            changed = True
        if not pending or not changed:
            break
    if pending:
        raise RuntimeError(f"unresolved new joints: {[j.get('name') for j in pending]}")
    return world, joint_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    args = ap.parse_args()
    repo = args.repo.resolve()
    a = load_base()
    root = ET.parse(repo / a.FULL_URDF).getroot()
    links = {x.get("name"): x for x in root.findall("link")}
    new_world, new_joints = new_world_and_joints(a, root)
    _, canonical_joints = old_world(a)

    # Transform every full-URDF mesh exactly as the full URDF places it at q=0,
    # but index the geometry by canonical link name so both axis hypotheses are
    # scored against identical geometry.
    geom = {}
    for name, link in links.items():
        vis = link.find("visual")
        if vis is None or vis.find("geometry/mesh") is None or name not in new_world:
            continue
        uri = vis.find("geometry/mesh").get("filename")
        path = a.mesh_path(repo, uri)
        tri = a._read_stl(path) if hasattr(a, "_read_stl") else None
        if tri is None:
            # base audit exposes vertices only, so parse binary STL locally.
            data = path.read_bytes()
            import struct
            n = struct.unpack_from("<I", data, 80)[0]
            dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attr", "<u2")])
            tri = np.asarray(np.frombuffer(data, dtype=dtype, offset=84, count=n)["vertices"], dtype=np.float64)
        T = new_world[name] @ a.origin_transform(vis.find("origin"))
        tri_world = tri @ T[:3, :3].T + T[:3, 3]
        geom[a.canonical_link(name)] = tri_geom(tri_world)

    rows = []
    for key in sorted(canonical_joints):
        old = canonical_joints[key]
        new = new_joints[key]
        all_cent = []
        all_norm = []
        all_area = []
        for link_name in (old["parent"], old["child"]):
            if link_name in geom:
                c, n, ar = geom[link_name]
                all_cent.append(c); all_norm.append(n); all_area.append(ar)
        if not all_cent:
            continue
        cent = np.concatenate(all_cent)
        norm = np.concatenate(all_norm)
        area = np.concatenate(all_area)
        old_support = cylinder_support(cent, norm, area, old["origin"], old["axis"])
        new_support = cylinder_support(cent, norm, area, new["origin"], new["axis"])
        os = old_support["score_m2"]
        ns = new_support["score_m2"]
        rows.append({
            "side": key[0], "joint": key[1],
            "canonical_parent": old["parent"], "canonical_child": old["child"],
            "full_joint": new["name"],
            "canonical_axis_support": old_support,
            "full_axis_support": new_support,
            "canonical_minus_full_score_m2": os - ns,
            "canonical_to_full_score_ratio": os / max(ns, 1e-30),
            "full_to_canonical_score_ratio": ns / max(os, 1e-30),
            "axis_line_origin_delta_m": float(np.linalg.norm(old["origin"] - new["origin"])),
            "axis_abs_dot": float(abs(np.dot(old["axis"] / np.linalg.norm(old["axis"]), new["axis"] / np.linalg.norm(new["axis"])))),
        })

    focus = [r for r in rows if r["side"] == "right" and r["joint"] in {"joint1", "joint3"}]
    report = {
        "schema_version": 1,
        "method": "Identical full-URDF q=0 mesh triangles scored for cylindrical surface support around canonical-vs-full joint axis lines.",
        "claim_boundary": "Axis-line geometry can distinguish line placement/orientation but cannot determine the sign convention of a collinear axis.",
        "parameters": {"radial_min_m": R_MIN, "radial_max_m": R_MAX, "axial_window_m": AXIAL_WINDOW, "normal_axis_max": NORMAL_AXIS_MAX, "normal_radial_min": NORMAL_RADIAL_MIN, "radius_bin_m": RADIUS_BIN, "angle_bins": ANGLE_BINS},
        "focus_right_joint1_joint3": focus,
        "rows": rows,
    }
    print(json.dumps(report, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
