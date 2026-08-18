#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

PAIR_NAMES = [
    ("left_link_1", "right_link_1"),
    ("ds_urdf_v4_1", "right_link_2"),
    ("left_link_3", "right_link_3"),
    ("left_link_4", "right_link_4"),
    ("ds_urdf_v4", "right_link_5"),
    ("left_link_6", "right_link_6"),
    ("left_link_7", "right_link_7"),
    ("left_gripper_link", "right_gripper_link"),
]


def vec(text, default=(0.0, 0.0, 0.0)):
    return np.asarray([float(x) for x in text.split()], dtype=float) if text else np.asarray(default, dtype=float)


def rpy_matrix(v):
    r, p, y = v
    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    return np.array([
        [cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
        [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr],
        [-sp, cp*sr, cp*cr],
    ])


def T_origin(node):
    out = np.eye(4)
    if node is not None:
        out[:3, :3] = rpy_matrix(vec(node.get("rpy")))
        out[:3, 3] = vec(node.get("xyz"))
    return out


def read_stl(path: Path):
    data = path.read_bytes()
    if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError(f"LFS pointer not materialized: {path}")
    if len(data) >= 84:
        n = struct.unpack_from("<I", data, 80)[0]
        if 84 + 50*n == len(data):
            dt = np.dtype([("normal", "<f4", (3,)), ("verts", "<f4", (3,3)), ("attr", "<u2")])
            rec = np.frombuffer(data, dtype=dt, offset=84, count=n)
            return np.asarray(rec["verts"], dtype=np.float64).reshape(-1, 3)
    pts=[]
    for line in data.decode("ascii").splitlines():
        f=line.strip().split()
        if len(f)==4 and f[0].lower()=="vertex": pts.append([float(f[1]),float(f[2]),float(f[3])])
    return np.asarray(pts, dtype=float)


def apply(T, p):
    return p @ T[:3,:3].T + T[:3,3]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    args=ap.parse_args()
    repo=args.repo.resolve()
    root=ET.parse(repo/"dual_scorpion_Full_urdf/urdf/dual_scorpion.urdf").getroot()
    links={x.get("name"):x for x in root.findall("link")}
    joints=root.findall("joint")
    children={j.find("child").get("link") for j in joints}
    roots=list(set(links)-children)
    if len(roots)!=1: raise RuntimeError(f"expected one root, got {roots}")
    world={roots[0]:np.eye(4)}
    pending=list(joints)
    while pending:
        changed=False
        for j in list(pending):
            p=j.find("parent").get("link"); c=j.find("child").get("link")
            if p in world:
                world[c]=world[p]@T_origin(j.find("origin")); pending.remove(j); changed=True
        if not changed: raise RuntimeError("disconnected URDF")

    geom={}
    for name,link in links.items():
        vis=link.find("visual")
        if vis is None: continue
        mesh=vis.find("geometry/mesh")
        if mesh is None: continue
        uri=mesh.get("filename")
        rel=uri.removeprefix("package://assembly_1/")
        pts=read_stl(repo/"dual_scorpion_Full_urdf"/rel)
        w=apply(world[name]@T_origin(vis.find("origin")), pts)
        geom[name]={
            "centroid":w.mean(axis=0),
            "min":w.min(axis=0),
            "max":w.max(axis=0),
            "extent":w.max(axis=0)-w.min(axis=0),
        }

    planes=[]
    for l,r in PAIR_NAMES:
        planes.append((geom[l]["centroid"][0]+geom[r]["centroid"][0])/2.0)
    plane=float(np.mean(planes))

    rows=[]
    for l,r in PAIR_NAMES:
        L,R=geom[l],geom[r]
        rc=R["centroid"].copy(); rc[0]=2*plane-rc[0]
        rmin=R["min"].copy(); rmax=R["max"].copy()
        mmin=np.array([2*plane-rmax[0], rmin[1], rmin[2]])
        mmax=np.array([2*plane-rmin[0], rmax[1], rmax[2]])
        rows.append({
            "left":l,"right":r,
            "pair_plane_x_m":float((L["centroid"][0]+R["centroid"][0])/2.0),
            "centroid_residual_m":float(np.linalg.norm(L["centroid"]-rc)),
            "bbox_residual_m":float(max(np.max(np.abs(L["min"]-mmin)),np.max(np.abs(L["max"]-mmax)))),
            "extent_delta_m":float(np.max(np.abs(L["extent"]-R["extent"]))),
        })

    report={
        "best_global_mirror_plane_x_m":plane,
        "pair_plane_spread_m":float(np.ptp(np.asarray(planes))),
        "max_centroid_residual_m":max(x["centroid_residual_m"] for x in rows),
        "max_bbox_residual_m":max(x["bbox_residual_m"] for x in rows),
        "max_extent_delta_m":max(x["extent_delta_m"] for x in rows),
        "pairs":rows,
    }
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=="__main__": main()
