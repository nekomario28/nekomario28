#!/usr/bin/env python3
"""Rendered motion proof for the lab-only Envelope v9 target.

The proof mirrors the accepted v8 public-playback method: one persistent Chrome
page per preference mode, real elapsed time, narrow rail-strip screenshots and
localized pixel diffs. Browser-wide reduced-motion is set at Chrome startup so
external SVG image documents receive the same user preference as the host page.

This is local rendered-target evidence. It does not claim that the lab-only v9
target is currently mounted on the public GitHub profile.
"""
from __future__ import annotations

import base64
import functools
import importlib.util
import json
import math
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import websocket
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDERER_PATH = HERE / "render_portable_surface.py"
OPAQUE_SAFE = ROOT / "design-lab" / "profile-envelope-config.example.json"

SIDE_SPECS = {
    "left": {"src": "profile-character-side-left.svg", "natural_width": 100, "natural_height": 394, "rail": 18},
    "right": {"src": "profile-character-side-right.svg", "natural_width": 100, "natural_height": 394, "rail": 82},
}


def load_renderer():
    spec = importlib.util.spec_from_file_location("envelope_v9_motion_renderer", RENDERER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load v9 renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = load_renderer()


def write_motion_off(root: Path) -> Path:
    path = root / "motion-off.json"
    path.write_text(
        json.dumps(
            {
                "contract_version": 1,
                "target_adapter": "github-profile-readme",
                "profile": {"theme": "seasonal-dark", "background": "opaque", "text": "safe", "motion": "off"},
                "surface": {"mounted_source_background": "inherit"},
                "frame": {"mode": "rail", "caps": "outer-only"},
                "labels": {"density": "auto"},
                "packing": {"mode": "auto"},
                "external_media": {"mode": "reference-only"},
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return path


def browser_binary() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError("Chrome/Chromium not found on runner")


def motion_subtree(path: Path) -> bytes | None:
    root = ET.parse(path).getroot()
    for element in root.iter():
        if "v7-motion" in element.attrib.get("class", "").split():
            return ET.tostring(element, encoding="utf-8")
    return None


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def make_page(target_prefix: str) -> str:
    return f'''<!doctype html><meta charset="utf-8"><title>Envelope v9 motion proof</title>
<style>
html,body{{margin:0;padding:0;background:#0d1117}}
#stage{{display:flex;width:200px;height:394px;gap:0}}
img{{display:block;width:100px;height:394px}}
</style>
<div id="stage">
<img data-side="left" src="/{target_prefix}/assets/profile-character-side-left.svg" width="100" height="394" alt="left">
<img data-side="right" src="/{target_prefix}/assets/profile-character-side-right.svg" width="100" height="394" alt="right">
</div>'''


def wait_complete(evaluate, timeout: float = 15.0) -> None:
    end = time.time() + timeout
    while time.time() < end:
        state = evaluate("""(() => ({
          ready: document.readyState,
          images: Array.from(document.images).every(i => i.complete && i.naturalWidth > 0),
          count: document.images.length
        }))()""")
        if state and state.get("ready") == "complete" and state.get("images") and state.get("count") == 2:
            time.sleep(0.4)
            return
        time.sleep(0.1)
    raise RuntimeError("motion proof page did not finish loading both SVG images")


def capture_sequence(call, out: Path, clip: dict, *, prefix: str, duration: float, interval: float) -> list[Path]:
    count = int(duration / interval) + 1
    samples: list[Path] = []
    start = time.monotonic()
    for index in range(count):
        result = call(
            "Page.captureScreenshot",
            {
                "format": "png",
                "captureBeyondViewport": True,
                "clip": {
                    "x": clip["x"], "y": clip["y"], "width": clip["width"], "height": clip["height"], "scale": 1,
                },
            },
        )
        path = out / f"{prefix}-{index:02d}.png"
        path.write_bytes(base64.b64decode(result["data"]))
        samples.append(path)
        target_time = start + (index + 1) * interval
        time.sleep(max(0.0, target_time - time.monotonic()))
    return samples


def rail_box(rect: dict, logical_x: int, clip: dict) -> tuple[int, int, int, int]:
    scale = rect["width"] / rect["naturalWidth"]
    center_x = rect["x"] - clip["x"] + logical_x * scale
    half = max(3, math.ceil(6 * scale))
    left = max(0, math.floor(center_x - half))
    right = min(math.ceil(clip["width"]), math.ceil(center_x + half))
    top = max(0, math.floor(rect["y"] - clip["y"]))
    bottom = min(math.ceil(clip["height"]), math.ceil(rect["y"] - clip["y"] + rect["height"]))
    return left, top, right, bottom


def changed_pairs(samples: list[Path], box: tuple[int, int, int, int]) -> tuple[int, list[dict]]:
    hits: list[dict] = []
    for index in range(len(samples) - 1):
        with Image.open(samples[index]) as first_image, Image.open(samples[index + 1]) as second_image:
            first = first_image.convert("RGB").crop(box)
            second = second_image.convert("RGB").crop(box)
            diff = ImageChops.difference(first, second)
            pixels = diff.get_flattened_data() if hasattr(diff, "get_flattened_data") else diff.getdata()
            changed = sum(1 for pixel in pixels if pixel != (0, 0, 0))
            if changed:
                hits.append(
                    {
                        "from": index,
                        "to": index + 1,
                        "changed_pixels": changed,
                        "bbox": diff.getbbox(),
                    }
                )
    return len(hits), hits[:3]


def wait_devtools_port(profile: Path, timeout: float = 16.0) -> int:
    marker = profile / "DevToolsActivePort"
    end = time.time() + timeout
    while time.time() < end:
        if marker.exists():
            lines = marker.read_text(encoding="utf-8").splitlines()
            if lines and lines[0].isdigit():
                return int(lines[0])
        time.sleep(0.2)
    raise RuntimeError("Chrome did not expose DevToolsActivePort")


def sample_browser_mode(
    chrome: str,
    work: Path,
    base_url: str,
    *,
    target_prefix: str,
    mode_name: str,
    reduced: bool,
    duration: float,
) -> dict:
    out = work / "screens"
    out.mkdir(exist_ok=True)
    profile = work / f"chrome-{mode_name}"
    profile.mkdir()
    command = [
        chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--hide-scrollbars",
        f"--user-data-dir={profile}", "--remote-debugging-port=0", "--remote-allow-origins=*",
        "--window-size=900,700", "about:blank",
    ]
    if reduced:
        command.insert(-1, "--force-prefers-reduced-motion")
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port = wait_devtools_port(profile)
        targets = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as response:
                    targets = json.load(response)
                break
            except Exception:
                time.sleep(0.1)
        if not targets:
            raise RuntimeError("Chrome DevTools target list unavailable")
        target = next(item for item in targets if item.get("type") == "page")
        ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=20)
        sequence = 0

        def call(method: str, params: dict | None = None) -> dict:
            nonlocal sequence
            sequence += 1
            ident = sequence
            ws.send(json.dumps({"id": ident, "method": method, "params": params or {}}))
            while True:
                message = json.loads(ws.recv())
                if message.get("id") == ident:
                    if "error" in message:
                        raise RuntimeError(f"CDP {method}: {message['error']}")
                    return message.get("result", {})

        def evaluate(expression: str):
            return call(
                "Runtime.evaluate",
                {"expression": expression, "returnByValue": True, "awaitPromise": True},
            ).get("result", {}).get("value")

        call("Page.enable")
        call("Runtime.enable")
        call("Emulation.setDeviceMetricsOverride", {"width": 900, "height": 700, "deviceScaleFactor": 1, "mobile": False})
        call("Page.navigate", {"url": f"{base_url}/{target_prefix}.html?mode={mode_name}&t={time.time_ns()}"})
        wait_complete(evaluate)

        media = evaluate("""(() => ({
          reduce: matchMedia('(prefers-reduced-motion: reduce)').matches,
          noPreference: matchMedia('(prefers-reduced-motion: no-preference)').matches
        }))()""")
        if media.get("reduce") is not reduced or media.get("noPreference") is reduced:
            raise AssertionError(f"unexpected browser-wide reduced-motion state for {mode_name}: {media}")

        rects = evaluate("""(() => {
          const out = {};
          for (const image of document.images) {
            const r = image.getBoundingClientRect();
            out[image.dataset.side] = {
              x:r.x,y:r.y,width:r.width,height:r.height,
              naturalWidth:image.naturalWidth,naturalHeight:image.naturalHeight,src:image.src
            };
          }
          return out;
        })()""")
        for side, spec in SIDE_SPECS.items():
            rect = rects.get(side)
            if not rect:
                raise AssertionError(f"missing {side} character-side image")
            if (rect["naturalWidth"], rect["naturalHeight"]) != (spec["natural_width"], spec["natural_height"]):
                raise AssertionError(f"unexpected {side} natural geometry: {rect}")

        clip = {
            "x": min(rect["x"] for rect in rects.values()),
            "y": min(rect["y"] for rect in rects.values()),
            "width": max(rect["x"] + rect["width"] for rect in rects.values()) - min(rect["x"] for rect in rects.values()),
            "height": max(rect["y"] + rect["height"] for rect in rects.values()) - min(rect["y"] for rect in rects.values()),
        }
        interval = 0.5
        samples = capture_sequence(call, out, clip, prefix=mode_name, duration=duration, interval=interval)
        counts: dict[str, int] = {}
        examples: dict[str, list[dict]] = {}
        for side, spec in SIDE_SPECS.items():
            count, first_changes = changed_pairs(samples, rail_box(rects[side], spec["rail"], clip))
            counts[side] = count
            examples[side] = first_changes
        ws.close()
        return {
            "media": media,
            "duration_seconds": duration,
            "interval_seconds": interval,
            "sample_count": len(samples),
            "changed_pair_counts": counts,
            "first_changes": examples,
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def run_browser_proof(chrome: str, work: Path, site: Path) -> dict:
    handler = functools.partial(QuietHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        return {
            "normal": sample_browser_mode(chrome, work, base_url, target_prefix="motion-on", mode_name="normal", reduced=False, duration=6.0),
            "reduced": sample_browser_mode(chrome, work, base_url, target_prefix="motion-on", mode_name="reduced", reduced=True, duration=3.0),
            "motion_off": sample_browser_mode(chrome, work, base_url, target_prefix="motion-off", mode_name="motion-off", reduced=False, duration=3.0),
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main() -> int:
    chrome = browser_binary()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        site = work / "site"
        v8 = work / "v8"
        v9 = site / "motion-on"
        off = site / "motion-off"
        for path in (site, v8, v9, off):
            path.mkdir(parents=True, exist_ok=True)

        R.V8.render("summer", v8)
        _, on_resolved = R.render(OPAQUE_SAFE, season="summer", output_root=v9)
        _, off_resolved = R.render(write_motion_off(work), season="summer", output_root=off)

        # v9 text/surface/fingerprint transforms must not rewrite the inherited
        # animated rail subtree. Keep this exact, not a semantic approximation.
        compared = 0
        for rel in R.asset_paths():
            before = motion_subtree(v8 / rel)
            after = motion_subtree(v9 / rel)
            if before is None and after is None:
                continue
            assert before is not None and after is not None, rel
            assert before == after, rel
            compared += 1
        assert compared >= 8, compared

        # motion=off must have no timing elements anywhere and must be a distinct
        # rendered target from motion=on.
        for rel in R.asset_paths():
            svg = (off / rel).read_text(encoding="utf-8")
            assert re.search(r"<(?:animate|animateTransform|animateMotion|set)\b", svg, flags=re.I) is None, rel
        assert off_resolved["render_target_sha256"] != on_resolved["render_target_sha256"]

        (site / "motion-on.html").write_text(make_page("motion-on"), encoding="utf-8")
        (site / "motion-off.html").write_text(make_page("motion-off"), encoding="utf-8")
        proof = run_browser_proof(chrome, work, site)

        normal_counts = proof["normal"]["changed_pair_counts"]
        reduced_counts = proof["reduced"]["changed_pair_counts"]
        off_counts = proof["motion_off"]["changed_pair_counts"]
        assert all(count > 0 for count in normal_counts.values()), proof["normal"]
        assert all(count == 0 for count in reduced_counts.values()), proof["reduced"]
        assert all(count == 0 for count in off_counts.values()), proof["motion_off"]

    metrics = {
        "result": "PASS",
        "render_target_sha256": on_resolved["render_target_sha256"],
        "motion_subtree_equivalent_v8_assets": compared,
        "normal": proof["normal"],
        "reduced": proof["reduced"],
        "motion_off": proof["motion_off"],
        "public_github_profile": "NOT_RUN",
        "cross_document_hard_sync_claimed": False,
    }
    print("ENVELOPE_V9_LOCAL_PLAYBACK " + json.dumps(metrics, separators=(",", ":")))
    print("LOCAL_RENDER_TARGET_PLAYBACK=PASS REDUCED_MOTION=PASS MOTION_OFF=PASS")
    print("V8_PUBLIC_PLAYBACK_INHERITANCE=BOUNDED motion_subtree_equivalent=true PUBLIC_GITHUB_PROFILE=NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
