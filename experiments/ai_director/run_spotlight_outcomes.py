from __future__ import annotations

import ast
import json
import shutil
import subprocess
from pathlib import Path

from gradio_client import Client
from huggingface_hub import hf_hub_download

DATASET = "UBC-ViL/Spotlight-VideoGen-Errors"
OUT = Path("outcomes")
SRC = OUT / "source"
SPLIT = OUT / "split_shot"
FRESH = OUT / "fresh_regenerate"
SCHEMA = OUT / "space_schema"
for p in (SRC, SPLIT, FRESH, SCHEMA):
    p.mkdir(parents=True, exist_ok=True)

PROMPTS = {
    "sid_003": "A bicycle pedals itself down the street, stops at a red light, and then continues when it turns green.",
}

# Human-annotated clean intervals from Spotlight, selected only for cases whose
# total clean footage can make a >=3 s editorial slot when split and concatenated.
SPLIT_INTERVALS = {
    "sid_004": [(0.0, 1.1), (6.1, 8.04)],
    "sid_008": [(3.0, 4.0), (6.0, 8.04)],
    "sid_015": [(0.0, 0.5), (2.5, 4.5), (7.2, 8.04)],
    "sid_017": [(0.0, 1.5), (6.0, 8.04)],
    "sid_021": [(0.0, 1.0), (2.0, 2.1), (6.1, 8.04)],
}


def run(*cmd: str) -> None:
    print("RUN", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def download_video(pid: str) -> Path:
    p = Path(hf_hub_download(
        repo_id=DATASET,
        repo_type="dataset",
        filename=f"test/spotlight/ltx2/{pid}.mp4",
        local_dir=SRC,
    ))
    print("DOWNLOADED", pid, p)
    return p


def ffprobe(path: Path) -> dict:
    cp = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "json", str(path)],
        text=True, capture_output=True, check=True,
    )
    return json.loads(cp.stdout)["format"]


def make_split(pid: str, intervals: list[tuple[float, float]]) -> dict:
    src = download_video(pid)
    work = SPLIT / pid
    work.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, (start, end) in enumerate(intervals):
        part = work / f"part-{i:02d}.mp4"
        duration = end - start
        run(
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{duration:.3f}",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", str(part),
        )
        parts.append(part)
    concat = work / "concat.txt"
    concat.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
    final = work / f"{pid}-split-shot.mp4"
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(final))
    meta = {
        "pid": pid,
        "action": "SPLIT_SHOT",
        "source": str(src),
        "intervals": intervals,
        "output": str(final),
        "probe": ffprobe(final),
    }
    (work / "outcome.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def extract_space_source(space: str) -> dict:
    app = Path(hf_hub_download(repo_id=space, repo_type="space", filename="app.py", local_dir=SCHEMA / space.replace("/", "__")))
    text = app.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(k in node.name.lower() for k in ("generate", "inpaint", "process")):
            functions[node.name] = [a.arg for a in node.args.args]
    return {"space": space, "app_path": str(app), "functions": functions}


def fresh_regenerate(pid: str) -> dict:
    prompt = PROMPTS[pid]
    client = Client("Lightricks/LTX-2-3", verbose=True)
    client.view_api()
    result = client.predict(
        None, prompt, 3.0, False, 1003, False, 512, 768,
        api_name="/generate_video",
    )
    print("FRESH_RESULT", repr(result), flush=True)
    if isinstance(result, (tuple, list)):
        video_ref = result[0]
        seed = result[1] if len(result) > 1 else None
    else:
        video_ref, seed = result, None
    src_path = Path(str(video_ref))
    if not src_path.exists():
        raise RuntimeError(f"Fresh generation returned non-local video reference: {video_ref!r}")
    dst = FRESH / f"{pid}-fresh-ltx23.mp4"
    shutil.copy2(src_path, dst)
    meta = {
        "pid": pid,
        "action": "FRESH_REGENERATE",
        "executor": "Lightricks/LTX-2-3",
        "prompt": prompt,
        "seed": seed,
        "output": str(dst),
        "probe": ffprobe(dst),
    }
    (FRESH / f"{pid}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main() -> None:
    manifest = {"split_shot": [], "fresh_regenerate": [], "space_schema": []}
    for pid, intervals in SPLIT_INTERVALS.items():
        manifest["split_shot"].append(make_split(pid, intervals))
    for space in (
        "ltx-community/ltx-2.3-inpaint",
        "linoyts/LTX-2-3-First-Last-Frame",
    ):
        try:
            manifest["space_schema"].append(extract_space_source(space))
        except Exception as exc:
            manifest["space_schema"].append({"space": space, "error": repr(exc)})
    try:
        manifest["fresh_regenerate"].append(fresh_regenerate("sid_003"))
    except Exception as exc:
        manifest["fresh_regenerate"].append({"pid": "sid_003", "error": repr(exc)})
        print("FRESH_REGENERATE_ERROR", repr(exc), flush=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
