#!/usr/bin/env python3
"""Validate Envelope v7 generation and, on PR CI, its real GitHub layout."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V7 = Path(__file__).resolve().parent
RENDERER = V7 / "render_continuous_canvas.py"
SPACE = V7 / "global-motion-space.json"

GEOMETRY = {
    "hero": ("900", "260", "0 0 900 260"),
    "character_left": ("100", "394", "0 0 100 394"),
    "character_right": ("100", "394", "0 0 100 394"),
    "attribution": ("900", "44", "0 0 900 44"),
    "bridge_character_projects": ("900", "32", "0 0 900 32"),
    "projects": ("900", "68", "0 0 900 68"),
    "projects_canvas": ("900", "420", "0 0 900 420"),
    "bridge_projects_activity": ("900", "32", "0 0 900 32"),
    "activity": ("900", "68", "0 0 900 68"),
    "activity_canvas": ("900", "220", "0 0 900 220"),
    "bridge_activity_footer": ("900", "32", "0 0 900 32"),
    "footer": ("900", "92", "0 0 900 92"),
}

WINDOW_FOR_ASSET = {
    "hero": "hero",
    "character_left": "character",
    "character_right": "character",
    "attribution": "attribution",
    "bridge_character_projects": "bridge_character_projects",
    "projects": "projects",
    "projects_canvas": "projects_canvas",
    "bridge_projects_activity": "bridge_projects_activity",
    "activity": "activity",
    "activity_canvas": "activity_canvas",
    "bridge_activity_footer": "bridge_activity_footer",
    "footer": "footer",
}


def load_module():
    spec = importlib.util.spec_from_file_location("envelope_v7", RENDERER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load Envelope v7 renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ensure_websocket_client():
    try:
        import websocket  # type: ignore
        return websocket
    except ModuleNotFoundError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "websocket-client"],
            check=True,
        )
        import websocket  # type: ignore
        return websocket


def target_layout_proof_once() -> None:
    """Measure the actual GitHub branch README on the already-running hosted PR job."""
    if os.environ.get("GITHUB_ACTIONS") != "true" or not os.environ.get("GITHUB_HEAD_REF"):
        return
    runner_temp = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir()))
    stamp = runner_temp / "envelope-v7-target-layout-pass.json"
    if stamp.is_file():
        print(stamp.read_text(encoding="utf-8").strip())
        return

    chrome = next(
        (p for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
         if (p := shutil.which(name))),
        None,
    )
    if not chrome:
        raise SystemExit("Envelope v7 target proof requires Chrome/Chromium on hosted PR runner")
    websocket = _ensure_websocket_client()

    profile = runner_temp / "envelope-v7-target-chrome"
    shutil.rmtree(profile, ignore_errors=True)
    profile.mkdir(parents=True, exist_ok=True)
    port = 9237
    proc = subprocess.Popen(
        [
            chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
            "--hide-scrollbars", f"--user-data-dir={profile}", f"--remote-debugging-port={port}",
            "--remote-allow-origins=*", "--window-size=1440,3400", "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        targets = None
        for _ in range(120):
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as response:
                    targets = json.load(response)
                if targets:
                    break
            except Exception:
                time.sleep(0.2)
        if not targets:
            raise SystemExit("Chrome did not expose CDP for Envelope v7 target proof")
        target = next(t for t in targets if t.get("type") == "page")
        ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=25)
        seq = 0

        def call(method: str, params: dict | None = None) -> dict:
            nonlocal seq
            seq += 1
            ident = seq
            ws.send(json.dumps({"id": ident, "method": method, "params": params or {}}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == ident:
                    if "error" in msg:
                        raise RuntimeError(f"CDP {method}: {msg['error']}")
                    return msg.get("result", {})

        def evaluate(expr: str):
            return call(
                "Runtime.evaluate",
                {"expression": expr, "returnByValue": True, "awaitPromise": True},
            ).get("result", {}).get("value")

        def wait_ready() -> None:
            end = time.time() + 30
            while time.time() < end:
                state = evaluate("(() => ({ready:document.readyState, imgs:Array.from(document.images).every(i=>i.complete)}))()")
                if state and state["ready"] == "complete" and state["imgs"]:
                    time.sleep(0.8)
                    return
                time.sleep(0.2)
            raise SystemExit("Envelope v7 target page/images did not become ready")

        metrics_js = r'''(() => {
          const imgs = Array.from(document.images);
          const rect = i => { if (!i) return null; const r=i.getBoundingClientRect(); return {src:i.src,alt:i.alt,x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom,nw:i.naturalWidth,nh:i.naturalHeight}; };
          const bySrc = token => rect(imgs.find(i => i.src.includes(token)));
          const byAlt = text => rect(imgs.find(i => i.alt === text));
          const out = {
            hero: bySrc('profile-hero.svg'),
            character_left: bySrc('character-side-left.svg'),
            character_media: byAlt('めぐみん'),
            character_right: bySrc('character-side-right.svg'),
            attribution: bySrc('attribution-band.svg'),
            bridge1: bySrc('profile-frame-bridge-character-projects.svg'),
            projects: bySrc('profile-section-projects.svg'),
            projects_canvas: bySrc('projects-panel.svg'),
            bridge2: bySrc('profile-frame-bridge-projects-activity.svg'),
            activity: bySrc('profile-section-activity.svg'),
            activity_canvas: bySrc('activity-panel.svg'),
            bridge3: bySrc('profile-frame-bridge-activity-footer.svg'),
            footer: bySrc('profile-footer.svg'),
          };
          const c=document.querySelector('article.markdown-body')||document.querySelector('.markdown-body');
          out.container=c?(()=>{const r=c.getBoundingClientRect();return {x:r.x,w:r.width,right:r.right};})():null;
          out.viewport={w:innerWidth,h:innerHeight};
          return out;
        })()'''

        def assert_layout(label: str, metrics: dict) -> None:
            required = [
                "hero", "character_left", "character_media", "character_right", "attribution",
                "bridge1", "projects", "projects_canvas", "bridge2", "activity", "activity_canvas",
                "bridge3", "footer",
            ]
            missing = [key for key in required if not metrics.get(key)]
            if missing:
                raise SystemExit(f"{label}: missing v7 target images: {missing}")
            failed = [key for key in required if metrics[key]["nw"] <= 0 or metrics[key]["nh"] <= 0]
            if failed:
                raise SystemExit(f"{label}: failed image loads: {failed}")

            left, media, right = (metrics[k] for k in ("character_left", "character_media", "character_right"))
            if max(abs(left["y"] - media["y"]), abs(media["y"] - right["y"])) > 2.5:
                raise SystemExit(f"{label}: character three-piece row wrapped vertically")
            if abs(media["x"] - left["right"]) > 2.5 or abs(right["x"] - media["right"]) > 2.5:
                raise SystemExit(f"{label}: character three-piece row has an inline gap")
            hero_w = metrics["hero"]["w"]
            if abs((left["w"] + media["w"] + right["w"]) - hero_w) > 4:
                raise SystemExit(f"{label}: character row width does not match hero")
            if not (0.09 < left["w"] / hero_w < 0.13 and 0.74 < media["w"] / hero_w < 0.81):
                raise SystemExit(f"{label}: character percentage widths collapsed")

            for key in ("attribution", "projects", "projects_canvas", "activity", "activity_canvas", "footer"):
                if abs(metrics[key]["w"] - hero_w) > 3:
                    raise SystemExit(f"{label}: {key} width differs from hero")
            if metrics.get("container"):
                for key in required:
                    item = metrics[key]
                    if item["x"] < metrics["container"]["x"] - 3 or item["right"] > metrics["container"]["right"] + 3:
                        raise SystemExit(f"{label}: {key} overflows README container")

        call("Page.enable")
        call("Runtime.enable")
        call("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "dark"}]})
        target_url = f"https://github.com/nekomario28/nekomario28/tree/{os.environ['GITHUB_HEAD_REF']}"
        summaries: dict[str, dict] = {}
        for label, width, mobile in (("desktop", 1440, False), ("mobile", 430, True)):
            call(
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": 3400, "deviceScaleFactor": 1, "mobile": mobile},
            )
            call("Page.navigate", {"url": target_url})
            wait_ready()
            metrics = evaluate(metrics_js)
            assert_layout(label, metrics)
            summaries[label] = metrics
        ws.close()

        compact = {
            "result": "PASS",
            "target": target_url,
            "desktop_hero_width": round(summaries["desktop"]["hero"]["w"], 2),
            "desktop_character_widths": [round(summaries["desktop"][k]["w"], 2) for k in ("character_left", "character_media", "character_right")],
            "mobile_hero_width": round(summaries["mobile"]["hero"]["w"], 2),
            "mobile_character_widths": [round(summaries["mobile"][k]["w"], 2) for k in ("character_left", "character_media", "character_right")],
        }
        stamp.write_text("ENVELOPE_V7_TARGET_LAYOUT_PASS " + json.dumps(compact, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(stamp.read_text(encoding="utf-8").strip())
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    module = load_module()
    space = json.loads(SPACE.read_text(encoding="utf-8"))
    module.validate_space(space)

    assert space["global_extent"] == 1662
    assert space["rail_x"] == [18, 882]
    assert space["duration_seconds"] == 32
    assert space["cross_document_hard_sync"] is False
    assert space["render_model"] == "shared-global-field-clipped-by-rendered-canvas-windows"
    assert list(space["windows"]) == [
        "hero", "character", "attribution", "bridge_character_projects",
        "projects", "projects_canvas", "bridge_projects_activity", "activity",
        "activity_canvas", "bridge_activity_footer", "footer",
    ]

    for season in ("spring", "summer", "autumn", "winter"):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            written = module.render(season, out)
            assert len(written) == len(GEOMETRY)
            expected_paths = {out / module.LIVE_ASSETS[key] for key in GEOMETRY}
            assert set(written) == expected_paths

            for key, geometry in GEOMETRY.items():
                path = out / module.LIVE_ASSETS[key]
                root = ET.parse(path).getroot()
                actual = (root.attrib.get("width"), root.attrib.get("height"), root.attrib.get("viewBox"))
                assert actual == geometry, (season, key, actual, geometry)
                text = path.read_text(encoding="utf-8")
                window_name = WINDOW_FOR_ASSET[key]
                window = space["windows"][window_name]
                assert 'id="v7-global-window"' in text
                assert f'data-window="{window_name}"' in text
                assert f'data-global-start="{window["start"]}"' in text
                assert f'data-global-end="{window["end"]}"' in text
                assert f'data-global-extent="{space["global_extent"]}"' in text
                assert 'clip-path="url(#v7-window)"' in text
                assert 'prefers-reduced-motion' in text
                assert '<animateTransform' in text and 'dur="32s"' in text
                assert '<script' not in text.lower() and 'javascript:' not in text.lower()
                v7_tail = text.split('id="v7-global-window"', 1)[1]
                assert '<animate attributeName="opacity"' not in v7_tail

            left = (out / module.LIVE_ASSETS["character_left"]).read_text(encoding="utf-8")
            right = (out / module.LIVE_ASSETS["character_right"]).read_text(encoding="utf-8")
            assert 'data-global-x-offset="0"' in left
            assert 'data-global-x-offset="800"' in right
            assert 'cx="18"' in left
            assert 'cx="82"' in right

            projects = (out / module.LIVE_ASSETS["projects_canvas"]).read_text(encoding="utf-8")
            activity = (out / module.LIVE_ASSETS["activity_canvas"]).read_text(encoding="utf-8")
            attribution = (out / module.LIVE_ASSETS["attribution"]).read_text(encoding="utf-8")
            assert '<image ' not in projects and '<image ' not in activity
            assert '<svg x="80"' in projects
            assert '<svg x="70"' in activity
            assert '<text' not in attribution.lower()

    print("ENVELOPE_V7_VALIDATION_PASS seasons=4 assets=12 extent=1662")
    target_layout_proof_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
