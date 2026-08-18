#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import numpy as np

PAIRS = [
    ("left_link_1.stl", "right_link_1.stl"),
    ("ds_urdf_v4_1.stl", "right_link_2.stl"),
    ("left_link_3.stl", "right_link_3.stl"),
    ("left_link_4.stl", "right_link_4.stl"),
    ("ds_urdf_v4.stl", "right_link_5.stl"),
    ("left_link_6.stl", "right_link_6.stl"),
    ("left_link_7.stl", "right_link_7.stl"),
    ("left_gripper_link.stl", "right_gripper_link.stl"),
]


def read_triangles(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError(f"LFS pointer not materialized: {path}")
    if len(data) >= 84:
        n = struct.unpack_from("<I", data, 80)[0]
        if 84 + 50*n == len(data):
            dt = np.dtype([("normal", "<f4", (3,)), ("verts", "<f4", (3, 3)), ("attr", "<u2")])
            rec = np.frombuffer(data, dtype=dt, offset=84, count=n)
            return np.asarray(rec["verts"], dtype=np.float64)
    pts=[]
    for line in data.decode("ascii").splitlines():
        f=line.strip().split()
        if len(f)==4 and f[0].lower()=="vertex":
            pts.append([float(f[1]),float(f[2]),float(f[3])])
    if not pts or len(pts)%3:
        raise RuntimeError(f"bad STL: {path}")
    return np.asarray(pts,dtype=float).reshape(-1,3,3)


def invariants(tri: np.ndarray) -> dict:
    pts=tri.reshape(-1,3)
    center=pts.mean(axis=0)
    x=pts-center
    cov=(x.T@x)/len(x)
    eig=np.sort(np.linalg.eigvalsh(cov))
    eig_norm=eig/max(float(eig.sum()),1e-30)

    edges=np.concatenate([
        np.linalg.norm(tri[:,1]-tri[:,0],axis=1),
        np.linalg.norm(tri[:,2]-tri[:,1],axis=1),
        np.linalg.norm(tri[:,0]-tri[:,2],axis=1),
    ])
    edge_q=np.quantile(edges,[0.01,0.05,0.25,0.5,0.75,0.95,0.99])

    # Surface-area weighted centroid covariance is tessellation-insensitive enough
    # for detecting gross shape swaps while remaining rigid/reflection invariant.
    a,b,c=tri[:,0],tri[:,1],tri[:,2]
    area=0.5*np.linalg.norm(np.cross(b-a,c-a),axis=1)
    cent=(a+b+c)/3.0
    total=float(area.sum())
    sc=(cent*area[:,None]).sum(axis=0)/max(total,1e-30)
    sx=cent-sc
    scov=(sx.T@(sx*area[:,None]))/max(total,1e-30)
    seig=np.sort(np.linalg.eigvalsh(scov))
    seig_norm=seig/max(float(seig.sum()),1e-30)

    # PCA-aligned extents are invariant to proper/improper rigid orientation,
    # aside from eigenspace ambiguity for nearly repeated eigenvalues.
    _,axes=np.linalg.eigh(scov)
    pca=x@axes
    ext=np.sort(pca.max(axis=0)-pca.min(axis=0))
    ext_norm=ext/max(float(np.linalg.norm(ext)),1e-30)

    return {
        "facets":int(len(tri)),
        "surface_area_native2":total,
        "vertex_cov_eigs_norm":eig_norm.tolist(),
        "surface_centroid_cov_eigs_norm":seig_norm.tolist(),
        "pca_extents_native":ext.tolist(),
        "pca_extents_norm":ext_norm.tolist(),
        "edge_quantiles_native":edge_q.tolist(),
    }


def rel(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    return float(np.linalg.norm(a-b)/max(np.linalg.norm(a),np.linalg.norm(b),1e-30))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("repo",type=Path); args=ap.parse_args()
    root=args.repo/"dual_scorpion_Full_urdf/meshes"
    rows=[]
    for l,r in PAIRS:
        li=invariants(read_triangles(root/l)); ri=invariants(read_triangles(root/r))
        rows.append({
            "left":l,"right":r,
            "facet_delta":ri["facets"]-li["facets"],
            "surface_area_rel_delta":abs(ri["surface_area_native2"]-li["surface_area_native2"])/max(ri["surface_area_native2"],li["surface_area_native2"],1e-30),
            "vertex_cov_shape_error":rel(li["vertex_cov_eigs_norm"],ri["vertex_cov_eigs_norm"]),
            "surface_cov_shape_error":rel(li["surface_centroid_cov_eigs_norm"],ri["surface_centroid_cov_eigs_norm"]),
            "pca_extent_shape_error":rel(li["pca_extents_norm"],ri["pca_extents_norm"]),
            "edge_quantile_shape_error":rel(li["edge_quantiles_native"],ri["edge_quantiles_native"]),
            "left_invariants":li,"right_invariants":ri,
        })
    print(json.dumps({"pairs":rows},indent=2,sort_keys=True))

if __name__=="__main__": main()
