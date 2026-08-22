from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from gradio_client import Client, handle_file
from huggingface_hub import hf_hub_download

DATASET = "UBC-ViL/Spotlight-VideoGen-Errors"
OUT = Path("repair_outcomes")
SRC = OUT / "source"
MASKS = OUT / "masks"
REPAIRED = OUT / "repaired"
for p in (SRC, MASKS, REPAIRED): p.mkdir(parents=True, exist_ok=True)

# Manual masks intentionally cover only the subject/interaction region, leaving
# a substantial portion of each frame untouched. Coordinates are in 1920x1080 source space.
CASES = {
    "sid_021": {
        "mask": (40, 180, 1480, 900),
        "frames": 73,
        "prompt": "the same realistic tabby cat remains seated inside the cardboard box; only its head slowly rises over the box edge and looks around, anatomically correct body and limbs, unchanged cardboard box and lighting",
    },
    "sid_008": {
        "mask": (380, 60, 1250, 1020),
        "frames": 73,
        "prompt": "the same mother kangaroo stays still while one anatomically correct joey peeks from the pouch, smoothly climbs out with correct limbs, and begins moving away; preserve the same landscape and camera",
    },
    "sid_015": {
        "mask": (180, 60, 1420, 980),
        "frames": 49,
        "prompt": "the same puffin carries intact fish naturally in its beak and moves toward its chicks, anatomically correct bird and fish, preserve the same grassy landscape and camera",
    },
    "sid_004": {
        "mask": (420, 0, 1080, 1080),
        "frames": 73,
        "prompt": "the same parking meter and human hand; the hand inserts coins naturally and the numeric display visibly increases correctly, preserve the same pole, street background, camera and lighting",
    },
}


def ffprobe(path: Path) -> dict:
    cp = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,size","-of","json",str(path)],capture_output=True,text=True,check=True)
    return json.loads(cp.stdout).get("format", {})


def download_source(pid: str) -> Path:
    return Path(hf_hub_download(repo_id=DATASET, repo_type="dataset", filename=f"test/spotlight/ltx2/{pid}.mp4", local_dir=SRC))


def make_mask(pid: str, rect: tuple[int,int,int,int], frames: int) -> Path:
    src = download_source(pid)
    x,y,w,h = rect
    # Inpaint app resamples masks to requested frame count, so create a 24fps mask
    # with the same duration and source resolution. White = inpaint.
    duration = frames / 24.0
    dst = MASKS / f"{pid}-mask-{frames}f.mp4"
    vf = f"drawbox=x={x}:y={y}:w={w}:h={h}:color=white:t=fill"
    subprocess.run([
        "ffmpeg","-hide_banner","-loglevel","error","-y",
        "-f","lavfi","-i",f"color=c=black:s=1920x1080:r=24:d={duration:.6f}",
        "-vf",vf,"-an","-c:v","libx264","-pix_fmt","yuv420p",str(dst)
    ],check=True)
    return dst


def endpoint(client: Client, needle: str) -> str:
    api = client.view_api(print_info=False) or {}
    named = api.get("named_endpoints", {}) if isinstance(api, dict) else {}
    for name in named:
        if needle in name:
            return name
    return f"/{needle}"


def main():
    # If a profile/repository secret exists, gradio_client may use it for better ZeroGPU priority.
    token = os.getenv("HF_TOKEN") or None
    try:
        client = Client("ltx-community/ltx-2.3-inpaint", token=token, verbose=True)
    except TypeError:
        client = Client("ltx-community/ltx-2.3-inpaint", verbose=True)
    api = client.view_api(print_info=False)
    print("INPAINT_API", json.dumps(api, default=str)[:30000], flush=True)
    ep = endpoint(client, "inpaint")
    manifest = {"api": api, "cases": []}
    for pid, cfg in CASES.items():
        src = download_source(pid)
        mask = make_mask(pid, cfg["mask"], cfg["frames"])
        seed = 4000 + int(pid.split("_")[1])
        rec = {"pid":pid,"action":"LOCAL_REPAIR","source":str(src),"mask":str(mask),"mask_rect":cfg["mask"],"frames":cfg["frames"],"prompt":cfg["prompt"],"seed":seed}
        try:
            print("REPAIR_SUBMIT", pid, ep, flush=True)
            res = client.predict(handle_file(str(src)), handle_file(str(mask)), cfg["prompt"], "Fast (768×448)", cfg["frames"], seed, False, api_name=ep)
            print("REPAIR_RESULT", pid, repr(res), flush=True)
            video_ref = res[0] if isinstance(res,(tuple,list)) else res
            src_out = Path(str(video_ref))
            if not src_out.exists():
                raise RuntimeError(f"Non-local repair output: {video_ref!r}")
            dst = REPAIRED / f"{pid}-ltx23-inpaint.mp4"
            shutil.copy2(src_out,dst)
            rec.update({"status":"success","output":str(dst),"probe":ffprobe(dst),"returned_seed":res[1] if isinstance(res,(tuple,list)) and len(res)>1 else None})
        except Exception as e:
            rec.update({"status":"failed","error":repr(e)})
            print("REPAIR_ERROR", pid, repr(e), flush=True)
        manifest["cases"].append(rec)
        (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2,default=str),encoding="utf-8")
    print(json.dumps(manifest,indent=2,default=str),flush=True)

if __name__ == "__main__": main()
