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

HERE = Path(__file__).resolve().parent
BASE = HERE / "dual_scorpion_full_urdf_audit.py"


def load_base():
    spec = importlib.util.spec_from_file_location("full_audit", BASE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load full audit")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def interval_intersection(a, b):
    lo=max(a[0],b[0]); hi=min(a[1],b[1])
    return [lo,hi] if lo <= hi else None


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("repo",type=Path); args=ap.parse_args()
    a=load_base(); root=ET.parse(args.repo/a.FULL_URDF).getroot()
    joints={j.get("name"):j for j in root.findall("joint")}
    rows=[]
    for full_name,key in sorted(a.JOINT_MAP.items(), key=lambda kv:(kv[1][0], kv[1][1])):
        j=joints[full_name]; ref=a.REFERENCE[key]
        full_axis=a.vec(j.find("axis").get("xyz") if j.find("axis") is not None else None,(1,0,0)); full_axis/=np.linalg.norm(full_axis)
        legacy_axis=np.asarray(ref["axis"],float); legacy_axis/=np.linalg.norm(legacy_axis)
        dot=float(full_axis@legacy_axis)
        if abs(abs(dot)-1.0)>1e-6:
            sign=None
        else:
            # Candidate convention only: preserve the legacy/control positive-q
            # direction when driving a collinear full-URDF native axis.
            sign=1 if dot>0 else -1
        lim=j.find("limit"); full_native=[float(lim.get("lower")),float(lim.get("upper"))]
        legacy=list(ref["limit"])
        if sign is None:
            full_in_control=None; safe=None
        elif sign>0:
            full_in_control=full_native
            safe=interval_intersection(legacy,full_in_control)
        else:
            full_in_control=[-full_native[1],-full_native[0]]
            safe=interval_intersection(legacy,full_in_control)
        legacy_width=legacy[1]-legacy[0]
        safe_width=(safe[1]-safe[0]) if safe else 0.0
        rows.append({
            "side":key[0],"joint":key[1],"full_joint":full_name,
            "full_axis_dot_legacy":dot,
            "candidate_q_full_from_q_control_sign":sign,
            "legacy_control_limit_rad":legacy,
            "full_native_limit_rad":full_native,
            "full_limit_mapped_to_control_rad":full_in_control,
            "candidate_common_limit_rad":safe,
            "candidate_common_limit_deg":[math.degrees(x) for x in safe] if safe else None,
            "common_width_fraction_of_legacy":safe_width/max(legacy_width,1e-30),
            "zero_is_in_common_limit":bool(safe and safe[0] <= 0 <= safe[1]),
        })
    report={
      "schema_version":1,
      "decision":"candidate_only_not_hardware_safety_limits",
      "mapping":"q_full_native = sign * q_control_candidate for collinear legacy/full local axes",
      "claim_boundary":"Sign preserves the existing software convention only; it is not proof of real-controller positive direction. Common limits are a simulation validation envelope, not measured hardware safety limits.",
      "rows":rows,
      "all_axes_collinear":all(r["candidate_q_full_from_q_control_sign"] is not None for r in rows),
      "all_common_limits_nonempty":all(r["candidate_common_limit_rad"] is not None for r in rows),
      "all_common_limits_include_zero":all(r["zero_is_in_common_limit"] for r in rows),
      "minimum_common_width_fraction_of_legacy":min(r["common_width_fraction_of_legacy"] for r in rows),
      "sign_flips":[f"{r['side']}/{r['joint']}" for r in rows if r["candidate_q_full_from_q_control_sign"] == -1],
    }
    print(json.dumps(report,indent=2,sort_keys=True))
    if not report["all_axes_collinear"] or not report["all_common_limits_nonempty"] or not report["all_common_limits_include_zero"]:
        raise SystemExit(1)

if __name__=="__main__": main()
