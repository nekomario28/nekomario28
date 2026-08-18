#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
AUDIT=HERE/"dual_scorpion_full_urdf_audit.py"


def load_audit():
    spec=importlib.util.spec_from_file_location("full_audit",AUDIT)
    if spec is None or spec.loader is None: raise RuntimeError("cannot load audit module")
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m


def quat_wxyz(R: np.ndarray) -> list[float]:
    t=float(np.trace(R))
    if t>0:
        s=math.sqrt(t+1.0)*2; w=0.25*s; x=(R[2,1]-R[1,2])/s; y=(R[0,2]-R[2,0])/s; z=(R[1,0]-R[0,1])/s
    elif R[0,0]>R[1,1] and R[0,0]>R[2,2]:
        s=math.sqrt(1+R[0,0]-R[1,1]-R[2,2])*2; w=(R[2,1]-R[1,2])/s; x=0.25*s; y=(R[0,1]+R[1,0])/s; z=(R[0,2]+R[2,0])/s
    elif R[1,1]>R[2,2]:
        s=math.sqrt(1+R[1,1]-R[0,0]-R[2,2])*2; w=(R[0,2]-R[2,0])/s; x=(R[0,1]+R[1,0])/s; y=0.25*s; z=(R[1,2]+R[2,1])/s
    else:
        s=math.sqrt(1+R[2,2]-R[0,0]-R[1,1])*2; w=(R[1,0]-R[0,1])/s; x=(R[0,2]+R[2,0])/s; y=(R[1,2]+R[2,1])/s; z=0.25*s
    q=np.asarray([w,x,y,z],float); q/=np.linalg.norm(q)
    if q[0]<0: q=-q
    return q.tolist()


def new_world_from_base(a, root: ET.Element):
    links={x.get("name"):x for x in root.findall("link")}
    joints=root.findall("joint")
    world={"base_link":np.eye(4)}
    pending=[j for j in joints if not (j.get("type")=="fixed" and j.find("child").get("link")=="base_link")]
    for _ in range(len(pending)+2):
        changed=False
        for j in list(pending):
            p=j.find("parent").get("link"); c=j.find("child").get("link")
            if p in world:
                world[c]=world[p]@a.origin_transform(j.find("origin")); pending.remove(j); changed=True
        if not pending or not changed: break
    if pending: raise RuntimeError(f"unresolved new joints: {[j.get('name') for j in pending]}")
    return links,world


def old_world(a):
    out={"base_link":np.eye(4)}
    for side in ("left","right"):
        parent="base_link"
        for idx in range(7):
            key=(side,f"joint{idx}")
            ref=a.REFERENCE[key]
            child=f"{side}_link_{idx+1}"
            out[child]=out[parent]@a.transform(np.asarray(ref["xyz"],float),np.asarray(ref["rpy"],float))
            parent=child
        ref=a.REFERENCE[(side,"gripper")]
        out[f"{side}_gripper_link"]=out[parent]@a.transform(np.asarray(ref["xyz"],float),np.asarray(ref["rpy"],float))
    return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("repo",type=Path); ap.add_argument("--output",type=Path); args=ap.parse_args()
    a=load_audit(); repo=args.repo.resolve()
    root=ET.parse(repo/a.FULL_URDF).getroot()
    links,neww=new_world_from_base(a,root); oldw=old_world(a)
    rows=[]
    for new_name,link in links.items():
        vis=link.find("visual")
        if vis is None or vis.find("geometry/mesh") is None: continue
        canonical=a.canonical_link(new_name)
        if canonical not in oldw:
            if new_name=="base_link": canonical="base_link"
            else: continue
        Tnewlink_mesh=a.origin_transform(vis.find("origin"))
        Tcorr=np.linalg.inv(oldw[canonical])@neww[new_name]
        Thybrid=Tcorr@Tnewlink_mesh
        reconstructed=oldw[canonical]@Thybrid
        source_world=neww[new_name]@Tnewlink_mesh
        residual=float(np.max(np.abs(reconstructed-source_world)))
        uri=vis.find("geometry/mesh").get("filename")
        rows.append({
            "upstream_link":new_name,
            "canonical_link":canonical,
            "mesh_uri":uri,
            "old_link_from_new_link":{
                "translation_m":Tcorr[:3,3].tolist(),
                "quaternion_wxyz":quat_wxyz(Tcorr[:3,:3]),
                "matrix":Tcorr.tolist(),
            },
            "old_link_from_mesh":{
                "translation_m":Thybrid[:3,3].tolist(),
                "quaternion_wxyz":quat_wxyz(Thybrid[:3,:3]),
                "matrix":Thybrid.tolist(),
            },
            "zero_pose_reconstruction_max_abs":residual,
        })
    report={
        "schema_version":1,
        "method":"Preserve upstream full-URDF zero-pose mesh placement while re-expressing each visual in the existing canonical Dual Scorpion link frame.",
        "claim_boundary":"Candidate visual/frame conversion only. It does not validate joint dynamics or activate collision.",
        "base_frame_policy":"Ignore upstream root->base fixed assembly offset and align upstream base_link to canonical base_link before conversion.",
        "transforms":rows,
        "max_zero_pose_reconstruction_max_abs":max(r["zero_pose_reconstruction_max_abs"] for r in rows),
    }
    text=json.dumps(report,indent=2,sort_keys=True)
    if args.output: args.output.write_text(text,encoding="utf-8")
    print(text)

if __name__=="__main__": main()
