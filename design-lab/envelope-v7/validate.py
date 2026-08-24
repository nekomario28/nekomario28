#!/usr/bin/env python3
"""Validate Envelope v7 generation and its real GitHub desktop/mobile layout."""
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
    "hero": "hero", "character_left": "character", "character_right": "character",
    "attribution": "attribution", "bridge_character_projects": "bridge_character_projects",
    "projects": "projects", "projects_canvas": "projects_canvas",
    "bridge_projects_activity": "bridge_projects_activity", "activity": "activity",
    "activity_canvas": "activity_canvas", "bridge_activity_footer": "bridge_activity_footer",
    "footer": "footer",
}


def load_renderer():
    spec = importlib.util.spec_from_file_location("envelope_v7", RENDERER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load Envelope v7 renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_generated() -> None:
    module = load_renderer()
    space = json.loads(SPACE.read_text(encoding="utf-8"))
    module.validate_space(space)
    assert space["global_extent"] == 1662
    assert space["rail_x"] == [18, 882]
    assert space["duration_seconds"] == 32
    assert space["cross_document_hard_sync"] is False
    assert space["render_model"] == "shared-global-field-clipped-by-rendered-canvas-windows"
    assert all(w.get("rendered") for w in space["windows"].values())

    for season in ("spring", "summer", "autumn", "winter"):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            written = module.render(season, out)
            assert len(written) == len(GEOMETRY)
            assert set(written) == {out / module.LIVE_ASSETS[k] for k in GEOMETRY}
            for key, geometry in GEOMETRY.items():
                path = out / module.LIVE_ASSETS[key]
                root = ET.parse(path).getroot()
                assert (root.attrib.get("width"), root.attrib.get("height"), root.attrib.get("viewBox")) == geometry
                text = path.read_text(encoding="utf-8")
                window_name = WINDOW_FOR_ASSET[key]
                window = space["windows"][window_name]
                assert 'id="v7-global-window"' in text
                assert f'data-window="{window_name}"' in text
                assert f'data-global-start="{window["start"]}"' in text
                assert f'data-global-end="{window["end"]}"' in text
                assert f'data-global-extent="{space["global_extent"]}"' in text
                assert 'clip-path="url(#v7-window)"' in text
                assert "prefers-reduced-motion" in text and '<animateTransform' in text and 'dur="32s"' in text
                assert "<script" not in text.lower() and "javascript:" not in text.lower()
                assert '<animate attributeName="opacity"' not in text.split('id="v7-global-window"', 1)[1]

            left = (out / module.LIVE_ASSETS["character_left"]).read_text(encoding="utf-8")
            right = (out / module.LIVE_ASSETS["character_right"]).read_text(encoding="utf-8")
            assert 'data-global-x-offset="0"' in left and 'cx="18"' in left
            assert 'data-global-x-offset="800"' in right and 'cx="82"' in right
            projects = (out / module.LIVE_ASSETS["projects_canvas"]).read_text(encoding="utf-8")
            activity = (out / module.LIVE_ASSETS["activity_canvas"]).read_text(encoding="utf-8")
            attribution = (out / module.LIVE_ASSETS["attribution"]).read_text(encoding="utf-8")
            assert '<image ' not in projects and '<svg x="80"' in projects
            assert '<image ' not in activity and '<svg x="70"' in activity
            assert '<text' not in attribution.lower()
    print("ENVELOPE_V7_VALIDATION_PASS seasons=4 assets=12 extent=1662")


def target_layout_proof_once() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true" or not os.environ.get("GITHUB_HEAD_REF"):
        return
    temp = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir()))
    stamp = temp / "envelope-v7-target-layout-pass.txt"
    if stamp.exists():
        print(stamp.read_text(encoding="utf-8").strip())
        return
    chrome = next((p for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if (p := shutil.which(n))), None)
    node = shutil.which("node")
    if not chrome or not node:
        raise SystemExit("Envelope v7 target proof requires Chrome/Chromium and Node")

    profile = temp / "envelope-v7-target-chrome"
    shutil.rmtree(profile, ignore_errors=True)
    profile.mkdir(parents=True, exist_ok=True)
    port = 9237
    proc = subprocess.Popen([
        chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
        "--hide-scrollbars", f"--user-data-dir={profile}", f"--remote-debugging-port={port}",
        "--remote-allow-origins=*", "--window-size=1440,3400", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as r:
                    if json.load(r):
                        break
            except Exception:
                time.sleep(.2)
        else:
            raise SystemExit("Chrome did not expose CDP")

        js = temp / "envelope-v7-target-proof.mjs"
        js.write_text(r'''const port=Number(process.env.V7_CDP_PORT),url=process.env.V7_TARGET_URL,sleep=ms=>new Promise(r=>setTimeout(r,ms));
const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(),target=targets.find(t=>t.type==='page');
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});let seq=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result||{});}};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evalv=async e=>(await call('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true})).result?.value;
const ready=async()=>{for(let i=0;i<150;i++){const s=await evalv(`(()=>({r:document.readyState,i:Array.from(document.images).every(x=>x.complete)}))()`);if(s?.r==='complete'&&s.i){await sleep(800);return}await sleep(200)}throw new Error('images not ready')};
const expr=`(()=>{const a=Array.from(document.images),r=i=>{if(!i)return null;const b=i.getBoundingClientRect();return{x:b.x,y:b.y,w:b.width,h:b.height,right:b.right,nw:i.naturalWidth,nh:i.naturalHeight}},s=t=>r(a.find(i=>i.src.includes(t))),alt=t=>r(a.find(i=>i.alt===t));const o={hero:s('profile-hero.svg'),l:s('profile-character-side-left.svg'),c:alt('めぐみん'),rr:s('profile-character-side-right.svg'),attr:s('profile-attribution.svg'),b1:s('profile-frame-bridge-character-projects.svg'),p:s('profile-section-projects.svg'),pc:s('profile-projects-canvas.svg'),b2:s('profile-frame-bridge-projects-activity.svg'),a:s('profile-section-activity.svg'),ac:s('profile-activity-canvas.svg'),b3:s('profile-frame-bridge-activity-footer.svg'),f:s('profile-footer.svg')};const c=document.querySelector('article.markdown-body')||document.querySelector('.markdown-body');if(c){const q=c.getBoundingClientRect();o.box={x:q.x,right:q.right}}return o})()`;
const check=(label,m)=>{const ks=['hero','l','c','rr','attr','b1','p','pc','b2','a','ac','b3','f'];if(ks.some(k=>!m[k]||m[k].nw<=0||m[k].nh<=0))throw new Error(`${label}: missing/failed image`);if(Math.max(Math.abs(m.l.y-m.c.y),Math.abs(m.c.y-m.rr.y))>2.5)throw new Error(`${label}: row wrapped`);if(Math.abs(m.c.x-m.l.right)>2.5||Math.abs(m.rr.x-m.c.right)>2.5)throw new Error(`${label}: row gap`);const hw=m.hero.w,sum=m.l.w+m.c.w+m.rr.w;if(Math.abs(sum-hw)>4)throw new Error(`${label}: row width`);if(!(m.l.w/hw>.09&&m.l.w/hw<.13&&m.c.w/hw>.74&&m.c.w/hw<.81))throw new Error(`${label}: percentages`);for(const k of ['attr','p','pc','a','ac','f'])if(Math.abs(m[k].w-hw)>3)throw new Error(`${label}: ${k} width`);if(m.box)for(const k of ks)if(m[k].x<m.box.x-3||m[k].right>m.box.right+3)throw new Error(`${label}: overflow ${k}`)};
await call('Page.enable');await call('Runtime.enable');await call('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'dark'}]});const out={};
for(const [label,width,mobile] of [['desktop',1440,false],['mobile',430,true]]){await call('Emulation.setDeviceMetricsOverride',{width,height:3400,deviceScaleFactor:1,mobile});await call('Page.navigate',{url});await ready();const m=await evalv(expr);check(label,m);out[label]=m}
ws.close();const z={result:'PASS',target:url,desktop_hero_width:+out.desktop.hero.w.toFixed(2),desktop_character_widths:[out.desktop.l,out.desktop.c,out.desktop.rr].map(x=>+x.w.toFixed(2)),mobile_hero_width:+out.mobile.hero.w.toFixed(2),mobile_character_widths:[out.mobile.l,out.mobile.c,out.mobile.rr].map(x=>+x.w.toFixed(2))};console.log('ENVELOPE_V7_TARGET_LAYOUT_PASS '+JSON.stringify(z));''', encoding="utf-8")
        target = f"https://github.com/nekomario28/nekomario28/tree/{os.environ['GITHUB_HEAD_REF']}"
        run = subprocess.run([node, str(js)], env={**os.environ, "V7_CDP_PORT": str(port), "V7_TARGET_URL": target}, capture_output=True, text=True, timeout=60)
        if run.stdout:
            print(run.stdout.strip())
        if run.returncode:
            if run.stderr:
                print(run.stderr.strip())
            raise SystemExit("Envelope v7 target-layout proof failed")
        line = next((x for x in run.stdout.splitlines() if x.startswith("ENVELOPE_V7_TARGET_LAYOUT_PASS ")), None)
        if not line:
            raise SystemExit("Envelope v7 target-layout proof emitted no PASS")
        stamp.write_text(line + "\n", encoding="utf-8")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    validate_generated()
    target_layout_proof_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
