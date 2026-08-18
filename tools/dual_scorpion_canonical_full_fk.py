#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "dual_scorpion_full_urdf_audit.py"
ADAPTER_PATH = HERE / "dual_scorpion_control_adapter_candidate.py"
ALIASES = {"ds_urdf_v4_1": "left_link_2", "ds_urdf_v4": "left_link_5"}
FULL_TO_CANONICAL_JOINT = {
    "revolute_1": "right_joint0", "revolute_2": "right_joint1", "revolute_3": "right_joint2", "revolute_4": "right_joint3",
    "revolute_5": "right_joint4", "revolute_6": "right_joint5", "revolute_7": "right_joint6", "revolute_8": "right_gripper_revolute_candidate",
    "revolute_9": "left_joint0", "revolute_10": "left_joint1", "revolute_11": "left_joint2", "revolute_12": "left_joint3",
    "revolute_13": "left_joint4", "revolute_14": "left_joint5", "revolute_15": "left_joint6", "revolute_16": "left_gripper_revolute_candidate",
}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m


def axis_angle(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = np.asarray(axis, float); axis /= np.linalg.norm(axis)
    x,y,z=axis; c=math.cos(angle); s=math.sin(angle); C=1-c
    R=np.array([[c+x*x*C, x*y*C-z*s, x*z*C+y*s],
                [y*x*C+z*s, c+y*y*C, y*z*C-x*s],
                [z*x*C-y*s, z*y*C+x*s, c+z*z*C]], float)
    T=np.eye(4); T[:3,:3]=R; return T


def vec(text: str | None, default=(0,0,0)) -> np.ndarray:
    return np.asarray([float(x) for x in text.split()], float) if text else np.asarray(default,float)


def origin_T(node: ET.Element | None) -> np.ndarray:
    base=load(BASE_PATH,"fk_base_runtime")
    return base.origin_transform(node) if hasattr(base,"origin_transform") else base._origin_transform(node)


def fk(root: ET.Element, q_by_joint: dict[str,float], *, root_link: str="base_link") -> dict[str,np.ndarray]:
    world={root_link:np.eye(4)}
    pending=[]
    for j in root.findall("joint"):
        parent=j.find("parent").get("link"); child=j.find("child").get("link")
        if parent=="root":
            # Canonical comparison intentionally aligns base_link to identity.
            continue
        pending.append(j)
    for _ in range(len(pending)+2):
        changed=False
        for j in list(pending):
            parent=j.find("parent").get("link"); child=j.find("child").get("link")
            if parent not in world: continue
            T=world[parent]@origin_T(j.find("origin"))
            if j.get("type") in {"revolute","continuous"}:
                axis=vec(j.find("axis").get("xyz") if j.find("axis") is not None else None,(1,0,0))
                T=T@axis_angle(axis,q_by_joint.get(j.get("name"),0.0))
            world[child]=T
            pending.remove(j); changed=True
        if not pending or not changed: break
    if pending: raise RuntimeError([j.get("name") for j in pending])
    return world


def rename_link_refs(root: ET.Element, old: str, new: str):
    for tag in ("parent","child"):
        for node in root.findall(f".//{tag}"):
            if node.get("link")==old: node.set("link",new)


def canonicalize(full_root: ET.Element, signs: dict[str,int], common_ranges: dict[str,list[float]]) -> ET.Element:
    root=copy.deepcopy(full_root)
    # Drop Onshape export world wrapper: base_link becomes the standalone root.
    for j in list(root.findall("joint")):
        child=j.find("child")
        if j.get("type")=="fixed" and child is not None and child.get("link")=="base_link" and j.find("parent").get("link")=="root":
            root.remove(j)
    for link in list(root.findall("link")):
        if link.get("name")=="root": root.remove(link)
    for old,new in ALIASES.items():
        link=root.find(f"link[@name='{old}']")
        if link is None: raise RuntimeError(f"missing {old}")
        link.set("name",new); rename_link_refs(root,old,new)
    for joint in root.findall("joint"):
        old=joint.get("name")
        if old not in FULL_TO_CANONICAL_JOINT: continue
        new=FULL_TO_CANONICAL_JOINT[old]
        sign=signs[old]
        joint.set("name",new)
        axis=joint.find("axis")
        v=vec(axis.get("xyz") if axis is not None else None,(1,0,0))*sign
        if axis is None:
            axis=ET.SubElement(joint,"axis")
        axis.set("xyz"," ".join(f"{x:.17g}" for x in v))
        limit=joint.find("limit")
        if limit is not None:
            lo,hi=common_ranges[old]
            limit.set("lower",f"{lo:.17g}"); limit.set("upper",f"{hi:.17g}")
    root.set("name","dual_scorpion_full_canonical_candidate")
    return root


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("repo",type=Path); ap.add_argument("--samples",type=int,default=256); ap.add_argument("--seed",type=int,default=57057); ap.add_argument("--output-urdf",type=Path); args=ap.parse_args()
    base=load(BASE_PATH,"fk_base")
    full_root=ET.parse(args.repo/base.FULL_URDF).getroot()
    joints={j.get("name"):j for j in full_root.findall("joint")}
    signs={}; common={}
    for old,key in base.JOINT_MAP.items():
        j=joints[old]; ref=base.REFERENCE[key]
        fa=base.vec(j.find("axis").get("xyz") if j.find("axis") is not None else None,(1,0,0)); fa/=np.linalg.norm(fa)
        la=np.asarray(ref["axis"],float); la/=np.linalg.norm(la)
        dot=float(fa@la)
        if abs(abs(dot)-1)>1e-6: raise RuntimeError(f"non-collinear {old}: {dot}")
        sign=1 if dot>0 else -1; signs[old]=sign
        lim=j.find("limit"); native=[float(lim.get("lower")),float(lim.get("upper"))]
        mapped=native if sign>0 else [-native[1],-native[0]]
        lo=max(ref["limit"][0],mapped[0]); hi=min(ref["limit"][1],mapped[1])
        if lo>hi or not (lo<=0<=hi): raise RuntimeError(f"bad common range {old}: {(lo,hi)}")
        common[old]=[lo,hi]
    can=canonicalize(full_root,signs,common)
    if args.output_urdf:
        ET.indent(can,space="  "); ET.ElementTree(can).write(args.output_urdf,encoding="unicode",xml_declaration=True)
    rng=np.random.default_rng(args.seed)
    max_pos=0.0; max_rot=0.0; worst=None
    canonical_links={v:k for k,v in ALIASES.items()}
    # identity aliases too
    full_links=[x.get("name") for x in full_root.findall("link") if x.get("name")!="root"]
    for sample in range(args.samples):
        q_control={}
        q_native={}
        q_can={}
        for old,new in FULL_TO_CANONICAL_JOINT.items():
            lo,hi=common[old]
            # Add exact home and endpoints into the first few deterministic samples.
            if sample==0:q=0.0
            elif sample==1:q=lo
            elif sample==2:q=hi
            else:q=float(rng.uniform(lo,hi))
            q_control[old]=q; q_native[old]=signs[old]*q; q_can[new]=q
        wf=fk(full_root,q_native); wc=fk(can,q_can)
        for full_link in full_links:
            canonical=ALIASES.get(full_link,full_link)
            if canonical not in wc or full_link not in wf: continue
            A=wf[full_link]; B=wc[canonical]
            pos=float(np.linalg.norm(A[:3,3]-B[:3,3]))
            rel=A[:3,:3].T@B[:3,:3]
            c=float(np.clip((np.trace(rel)-1)/2,-1,1)); rot=math.degrees(math.acos(c))
            if pos>max_pos or rot>max_rot:
                worst={"sample":sample,"full_link":full_link,"canonical_link":canonical,"position_error_m":pos,"rotation_error_deg":rot}
            max_pos=max(max_pos,pos); max_rot=max(max_rot,rot)
    report={
      "status":"passed" if max_pos<1e-11 and max_rot<1e-7 else "failed",
      "samples":args.samples,"seed":args.seed,
      "mapping":"canonical joint axis = sign * native full axis; q_native = sign * q_control",
      "canonical_link_aliases":ALIASES,
      "canonical_joint_names":FULL_TO_CANONICAL_JOINT,
      "sign_flips":[new for old,new in FULL_TO_CANONICAL_JOINT.items() if signs[old]<0],
      "max_position_error_m":max_pos,"max_rotation_error_deg":max_rot,"worst":worst,
      "claim_boundary":"This proves algebraic FK equivalence to the pinned full URDF under the candidate software-q adapter. It does not verify real hardware q semantics, inertials, or collision.",
    }
    print(json.dumps(report,indent=2,sort_keys=True))
    if report["status"]!="passed": raise SystemExit(1)

if __name__=="__main__": main()
