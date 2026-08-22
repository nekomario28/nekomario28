from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from gradio_client import Client, handle_file
from huggingface_hub import hf_hub_download

DATASET = "UBC-ViL/Spotlight-VideoGen-Errors"
OUT = Path("wan_outcomes")
SRC = OUT / "source"
FRESH = OUT / "fresh"
ANCHOR = OUT / "anchor_suffix"
for p in (SRC, FRESH, ANCHOR):
    p.mkdir(parents=True, exist_ok=True)

PROMPTS = {
    "sid_003": "A bicycle pedals itself down the street, stops at a red light, and then continues when it turns green.",
    "sid_004": "A parking meter is fed coins, the time increases, and then starts to count down.",
    "sid_005": "A flamingo stands on one leg, and then preens its feathers.",
    "sid_007": "A robot stands on a table, lifts one foot, and then starts dancing by moving its arms up and down.",
    "sid_008": "A kangaroo joey peeks out from its mother's pouch, hops out, and then runs away.",
    "sid_013": "A chef tosses vegetables into the air, they arrange themselves into a salad, and then land back in the bowl.",
    "sid_015": "A puffin carries fish in its beak and then feeds its chicks.",
    "sid_017": "A woman pours sugar into her coffee, and then the cup overflows with snow.",
    "sid_018": "A book opens itself, the words rise off the pages, and then form images in the air.",
    "sid_021": "A cat sits in a box, and then pokes its head out.",
}

ANCHORS = {
    "sid_003": (1.10, "The self-pedaling bicycle continues down the street, comes to a stop at a red traffic light, waits, then resumes moving when the light turns green."),
    "sid_004": (1.00, "The parking meter visibly receives coins; its displayed remaining time increases, then the countdown begins."),
    "sid_007": (0.40, "The robot lifts one foot and starts dancing on the table, repeatedly moving both arms up and down."),
    "sid_013": (0.30, "The chef tosses the vegetables upward; the vegetables assemble into a salad in midair and fall neatly back into the bowl."),
    "sid_015": (0.40, "The puffin keeps the fish in its beak, approaches its chicks and feeds the fish to the chicks."),
    "sid_017": (1.40, "The woman finishes pouring sugar into the coffee; the cup then overflows with fluffy white snow."),
    "sid_021": (0.90, "The same tabby cat remains inside the cardboard box and slowly pokes only its head out over the edge, looking around."),
}


def ffprobe(path: Path) -> dict:
    cp = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(cp.stdout).get("format", {})


def download_source(pid: str) -> Path:
    return Path(hf_hub_download(
        repo_id=DATASET, repo_type="dataset",
        filename=f"test/spotlight/ltx2/{pid}.mp4",
        local_dir=SRC,
    ))


def extract_anchor(pid: str, at: float) -> Path:
    src = download_source(pid)
    dst = ANCHOR / f"{pid}-anchor-{at:.2f}.png"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{at:.3f}", "-i", str(src), "-frames:v", "1", str(dst)
    ], check=True)
    return dst


def save_video_ref(ref, dst: Path) -> Path:
    if ref is None:
        raise RuntimeError("No video result")
    if isinstance(ref, dict):
        ref = ref.get("path") or ref.get("url") or ref.get("video")
    ref = str(ref)
    if ref.startswith("http://") or ref.startswith("https://"):
        with requests.get(ref, stream=True, timeout=180) as r:
            r.raise_for_status()
            with dst.open("wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
    else:
        src = Path(ref)
        if not src.exists():
            raise RuntimeError(f"Video ref is neither URL nor local file: {ref!r}")
        shutil.copy2(src, dst)
    return dst


def first_api(client: Client, contains: str) -> str:
    api = client.view_api(print_info=False) or {}
    named = api.get("named_endpoints", {}) if isinstance(api, dict) else {}
    for name in named:
        if contains in name:
            return name
    # Common Gradio default.
    return f"/{contains}"


def poll_task(client: Client, task_id: str, task_kind: str, timeout_s: int = 900):
    endpoint = first_api(client, "status_refresh")
    start = time.time()
    last = None
    while time.time() - start < timeout_s:
        try:
            res = client.predict(task_id, task_kind, False, api_name=endpoint)
            last = res
            print("POLL", task_kind, task_id, repr(res), flush=True)
            if isinstance(res, (tuple, list)) and len(res) > 0 and res[0]:
                return res[0], res
        except Exception as e:
            last = repr(e)
            print("POLL_ERROR", task_id, repr(e), flush=True)
        time.sleep(20)
    raise TimeoutError(f"Task {task_id} did not produce a video in {timeout_s}s; last={last!r}")


def submit_fresh(client: Client, pid: str) -> dict:
    endpoint = first_api(client, "t2v_generation_async")
    seed = 2000 + int(pid.split("_")[1])
    print("FRESH_SUBMIT", pid, endpoint, flush=True)
    res = client.predict(PROMPTS[pid], "1280*720", False, seed, api_name=endpoint)
    print("FRESH_SUBMITTED", pid, repr(res), flush=True)
    task_id = res[0] if isinstance(res, (tuple, list)) else res
    if not task_id:
        raise RuntimeError(f"Fresh submission rejected: {res!r}")
    video_ref, poll = poll_task(client, str(task_id), "t2v")
    dst = FRESH / f"{pid}-wan21-fresh.mp4"
    save_video_ref(video_ref, dst)
    return {"pid": pid, "action": "FRESH_REGENERATE", "executor": "Wan-AI/Wan2.1 wanx2.1-t2v-plus", "seed": seed, "task_id": str(task_id), "output": str(dst), "probe": ffprobe(dst)}


def submit_anchor(client: Client, pid: str, at: float, suffix_prompt: str) -> dict:
    endpoint = first_api(client, "i2v_generation_async")
    seed = 3000 + int(pid.split("_")[1])
    anchor = extract_anchor(pid, at)
    print("ANCHOR_SUBMIT", pid, endpoint, anchor, flush=True)
    res = client.predict(suffix_prompt, handle_file(str(anchor)), False, seed, api_name=endpoint)
    print("ANCHOR_SUBMITTED", pid, repr(res), flush=True)
    task_id = res[0] if isinstance(res, (tuple, list)) else res
    if not task_id:
        raise RuntimeError(f"Anchor submission rejected: {res!r}")
    video_ref, poll = poll_task(client, str(task_id), "i2v")
    dst = ANCHOR / f"{pid}-wan21-anchor-suffix.mp4"
    save_video_ref(video_ref, dst)
    return {"pid": pid, "action": "ANCHOR_SUFFIX_REGENERATE", "executor": "Wan-AI/Wan2.1 wanx2.1-i2v-plus", "seed": seed, "anchor_sec": at, "anchor_image": str(anchor), "suffix_prompt": suffix_prompt, "task_id": str(task_id), "output": str(dst), "probe": ffprobe(dst)}


def main():
    client = Client("Wan-AI/Wan2.1", verbose=True)
    api = client.view_api(print_info=False)
    print("WAN_API", json.dumps(api, default=str)[:30000], flush=True)
    manifest = {"api": api, "fresh": [], "anchor_suffix": []}

    # Submit one-at-a-time to respect the public Space's own concurrency guard.
    for pid in PROMPTS:
        try:
            manifest["fresh"].append(submit_fresh(client, pid))
        except Exception as e:
            print("FRESH_ERROR", pid, repr(e), flush=True)
            manifest["fresh"].append({"pid": pid, "action": "FRESH_REGENERATE", "error": repr(e)})
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    for pid, (at, suffix_prompt) in ANCHORS.items():
        try:
            manifest["anchor_suffix"].append(submit_anchor(client, pid, at, suffix_prompt))
        except Exception as e:
            print("ANCHOR_ERROR", pid, repr(e), flush=True)
            manifest["anchor_suffix"].append({"pid": pid, "action": "ANCHOR_SUFFIX_REGENERATE", "anchor_sec": at, "error": repr(e)})
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    print(json.dumps(manifest, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
