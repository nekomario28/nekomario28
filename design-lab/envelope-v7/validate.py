#!/usr/bin/env python3
"""Validate Envelope v7 generation and, on PR CI, its real GitHub layout."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
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


def target_layout_proof_once() -> None:
    """Measure the actual GitHub branch README on the existing hosted PR job."""
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
    node = shutil.which("node")
    if not chrome or not node:
        raise SystemExit("Envelope v7 target proof requires Chrome/Chromium and Node on hosted PR runner")

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
        ready = False
        for _ in range(120):
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as response:
                    if json.load(response):
                        ready = True
                        break
            except Exception:
                time.sleep(0.2)
        if not ready:
            raise SystemExit("Chrome did not expose CDP for Envelope v7 target proof")

        script = runner_temp / "envelope-v7-target-proof.mjs"
        script.write_text(
            r'''const port = Number(process.env.V7_CDP_PORT);
const targetUrl = process.env.V7_TARGET_URL;
const sleep = ms => new Promise(r => setTimeout(r, ms));
let targets;
for (let i=0;i<120;i++) {
  try { const r=await fetch(`http://127.0.0.1:${port}/json/list`); targets=await r.json(); if(targets.length) break; } catch {}
  await sleep(200);
}
if (!targets || !targets.length) throw new Error('CDP target not found');
const target = targets.find(t => t.type === 'page');
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
let seq=0; const pending=new Map();
ws.onmessage = ev => { const msg=JSON.parse(ev.data); if(msg.id && pending.has(msg.id)){const {resolve,reject}=pending.get(msg.id); pending.delete(msg.id); msg.error?reject(new Error(JSON.stringify(msg.error))):resolve(msg.result||{});} };
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evaluate=async expr => (await call('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true})).result?.value;
const waitReady=async()=>{for(let i=0;i<150;i++){const s=await evaluate(`(() => ({ready:document.readyState,imgs:Array.from(document.images).every(i=>i.complete)}))()`);if(s?.ready==='complete'&&s.imgs){await sleep(800);return;}await sleep(200);}throw new Error('target page/images did not become ready');};
const metricsExpr = `(() => {
  const imgs=Array.from(document.images);
  const rect=i=>{if(!i)return null;const r=i.getBoundingClientRect();return {src:i.src,alt:i.alt,x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom,nw:i.naturalWidth,nh:i.naturalHeight};};
  const bySrc=t=>rect(imgs.find(i=>i.src.includes(t)));
  const byAlt=t=>rect(imgs.find(i=>i.alt===t));
  const o={hero:bySrc('profile-hero.svg'),character_left:bySrc('character-side-left.svg'),character_media:byAlt('めぐみん'),character_right:bySrc('character-side-right.svg'),attribution:bySrc('attribution-band.svg'),bridge1:bySrc('profile-frame-bridge-character-projects.svg'),projects:bySrc('profile-section-projects.svg'),projects_canvas:bySrc('projects-panel.svg'),bridge2:bySrc('profile-frame-bridge-projects-activity.svg'),activity:bySrc('profile-section-activity.svg'),activity_canvas:bySrc('activity-panel.svg'),bridge3:bySrc('profile-frame-bridge-activity-footer.svg'),footer:bySrc('profile-footer.svg')};
  const c=document.querySelector('article.markdown-body')||document.querySelector('.markdown-body'); if(c){const r=c.getBoundingClientRect();o.container={x:r.x,w:r.width,right:r.right};} o.viewport={w:innerWidth,h:innerHeight}; return o;
})()`;
const check=(label,m)=>{
  const required=['hero','character_left','character_media','character_right','attribution','bridge1','projects','projects_canvas','bridge2','activity','activity_canvas','bridge3','footer'];
  const missing=required.filter(k=>!m[k]); if(missing.length) throw new Error(`${label}: missing ${missing}`);
  const failed=required.filter(k=>m[k].nw<=0||m[k].nh<=0); if(failed.length) throw new Error(`${label}: failed images ${failed}`);
  const [l,c,r]=['character_left','character_media','character_right'].map(k=>m[k]);
  if(Math.max(Math.abs(l.y-c.y),Math.abs(c.y-r.y))>2.5) throw new Error(`${label}: character row wrapped vertically`);
  if(Math.abs(c.x-l.right)>2.5||Math.abs(r.x-c.right)>2.5) throw new Error(`${label}: character row inline gap`);
  const hw=m.hero.w, sum=l.w+c.w+r.w; if(Math.abs(sum-hw)>4) throw new Error(`${label}: character row width ${sum} != hero ${hw}`);
  if(!(l.w/hw>.09&&l.w/hw<.13&&c.w/hw>.74&&c.w/hw<.81)) throw new Error(`${label}: character percentage widths collapsed`);
  for(const k of ['attribution','projects','projects_canvas','activity','activity_canvas','footer']) if(Math.abs(m[k].w-hw)>3) throw new Error(`${label}: ${k} width differs from hero`);
  if(m.container) for(const k of required) if(m[k].x<m.container.x-3||m[k].right>m.container.right+3) throw new Error(`${label}: ${k} overflows container`);
};
await call('Page.enable'); await call('Runtime.enable'); await call('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'dark'}]});
const summaries={};
for(const [label,width,mobile] of [['desktop',1440,false],['mobile',430,true]]){
  await call('Emulation.setDeviceMetricsOverride',{width,height:3400,deviceScaleFactor:1,mobile});
  await call('Page.navigate',{url:targetUrl}); await waitReady(); const m=await evaluate(metricsExpr); check(label,m); summaries[label]=m;
}
ws.close();
const result={result:'PASS',target:targetUrl,desktop_hero_width:Number(summaries.desktop.hero.w.toFixed(2)),desktop_character_widths:['character_left','character_media','character_right'].map(k=>Number(summaries.desktop[k].w.toFixed(2))),mobile_hero_width:Number(summaries.mobile.hero.w.toFixed(2)),mobile_character_widths:['character_left','character_media','character_right'].map(k=>Number(summaries.mobile[k].w.toFixed(2)))};
console.log('ENVELOPE_V7_TARGET_LAYOUT_PASS '+JSON.stringify(result));
''',
            encoding="utf-8",
        )
        target_url = f"https://github.com/nekomario28/nekomario28/tree/{os.environ['GITHUB_HEAD_REF']}"
        completed = subprocess.run(
            [node, str(script)],
            env={**os.environ, "V7_CDP_PORT": str(port), "V7_TARGET_URL": target_url},
            text=True,
            capture_output=True,
            timeout=60,
        )
        if completed.stdout:
            print(completed.stdout.strip())
        if completed.returncode != 0:
            if completed.stderr:
                print(completed.stderr.strip())
            raise SystemExit("Envelope v7 target-layout CDP proof failed")
        pass_line = next((line for line in completed.stdout.splitlines() if line.startswith("ENVELOPE_V7_TARGET_LAYOUT_PASS ")), None)
        if not pass_line:
            raise SystemExit("Envelope v7 target-layout proof did not emit PASS")
        stamp.write_text(pass_line + "\n", encoding="utf-8")
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
