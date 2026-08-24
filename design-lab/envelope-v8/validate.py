#!/usr/bin/env python3
"""Validate Envelope v8 seamless presentation and GitHub README seam geometry."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V8 = Path(__file__).resolve().parent
V8_RENDERER = V8 / "render_continuous_canvas.py"
V7_VALIDATE = ROOT / "design-lab" / "envelope-v7" / "validate.py"
README = ROOT / "README.md"
MANIFEST = ROOT / "design-lab" / "theme-manifest.json"

COMPOSITE_GEOMETRY = {
    "attribution_projects_transition": ("900", "76", "0 0 900 76", 654, 730),
    "activity_header": ("900", "100", "0 0 900 100", 1218, 1318),
    "footer_transition": ("900", "124", "0 0 900 124", 1538, 1662),
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_generated() -> None:
    renderer = load_module("envelope_v8_renderer", V8_RENDERER)

    # Reuse the mature v7 coordinate/source-sync validator against the v8 adapter.
    inherited = load_module("envelope_v7_validate_for_v8", V7_VALIDATE)
    inherited.RENDERER = V8_RENDERER
    inherited.validate_generated()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("presentation_assets") != renderer.PRESENTATION_ASSETS:
        raise SystemExit("manifest presentation_assets drift from Envelope v8 renderer")

    readme = README.read_text(encoding="utf-8")
    if "active-profile-envelope: v8 seamless-surface" not in readme:
        raise SystemExit("README does not declare Envelope v8 seamless surface")
    image_tags = re.findall(r"<img\b[^>]*>", readme)
    if len(image_tags) != 10:
        raise SystemExit(f"expected 10 README image tags after short-window packing, got {len(image_tags)}")
    if any('align="top"' not in tag for tag in image_tags):
        raise SystemExit("every profile image must opt out of baseline spacing with align=top")
    for rel in renderer.PRESENTATION_ASSETS.values():
        if readme.count(rel) != 1:
            raise SystemExit(f"README must reference each v8 presentation asset exactly once: {rel}")
    for hidden_key in (
        "attribution",
        "bridge_character_projects",
        "bridge_projects_activity",
        "activity",
        "bridge_activity_footer",
        "footer",
    ):
        rel = renderer.LIVE_ASSETS[hidden_key]
        if rel in renderer.PRESENTATION_ASSETS.values():
            continue
        if rel in readme:
            raise SystemExit(f"legacy short-window asset leaked back into README: {rel}")

    full_size_keys = {"hero", "projects", "activity", "footer"}
    geometries = inherited.GEOMETRY
    for season in ("spring", "summer", "autumn", "winter"):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            renderer.render(season, out)
            for key, rel in renderer.LIVE_ASSETS.items():
                path = out / rel
                root = ET.parse(path).getroot()
                if root.attrib.get("data-envelope-presentation") != "v8-seamless-surface":
                    raise SystemExit(f"missing v8 marker: {season}/{key}")
                text = path.read_text(encoding="utf-8")
                if key in full_size_keys:
                    width, height, _ = geometries[key]
                    for tag in re.findall(r"<rect\b[^>]*>", text):
                        if f'width="{width}"' in tag and f'height="{height}"' in tag:
                            if ' rx="' in tag or ' ry="' in tag:
                                raise SystemExit(f"full-canvas rounding survived: {season}/{key}")
                if key == "hero" and re.search(
                    r'<rect\b(?=[^>]*\bx="\.5")(?=[^>]*\by="\.5")'
                    r'(?=[^>]*\bwidth="899")(?=[^>]*\bheight="259")'
                    r'(?=[^>]*\bfill="none")[^>]*/>',
                    text,
                ):
                    raise SystemExit(f"independent hero card border survived: {season}")

            for key, (width, height, view_box, start, end) in COMPOSITE_GEOMETRY.items():
                path = out / renderer.PRESENTATION_ASSETS[key]
                root = ET.parse(path).getroot()
                if (root.attrib.get("width"), root.attrib.get("height"), root.attrib.get("viewBox")) != (width, height, view_box):
                    raise SystemExit(f"unexpected packed geometry: {season}/{key}")
                if root.attrib.get("data-envelope-presentation") != "v8-seamless-surface":
                    raise SystemExit(f"missing packed v8 marker: {season}/{key}")
                text = path.read_text(encoding="utf-8")
                if text.count('id="v7-global-window"') != 1:
                    raise SystemExit(f"packed surface must own one global motion layer: {season}/{key}")
                if f'data-global-start="{start}"' not in text or f'data-global-end="{end}"' not in text:
                    raise SystemExit(f"packed surface changed logical coordinates: {season}/{key}")
                if 'clip-path="url(#v7-window)"' not in text or 'dur="32s"' not in text:
                    raise SystemExit(f"packed surface lost shared motion semantics: {season}/{key}")
                if "prefers-reduced-motion" not in text:
                    raise SystemExit(f"packed surface lost reduced-motion fallback: {season}/{key}")
                direct_layers = [child for child in root if child.attrib.get("id") == "v7-global-window"]
                if len(direct_layers) != 1:
                    raise SystemExit(f"packed motion layer must be a root child: {season}/{key}")
    print("ENVELOPE_V8_SEAMLESS_STATIC_PASS seasons=4 presentation_assets=9 packed_surfaces=3")


def target_seam_proof_once() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true" or not os.environ.get("GITHUB_HEAD_REF"):
        return
    temp = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir()))
    chrome = next((p for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if (p := shutil.which(name))), None)
    node = shutil.which("node")
    if not chrome or not node:
        raise SystemExit("Envelope v8 target seam proof requires Chrome/Chromium and Node")

    profile = temp / "envelope-v8-seam-chrome"
    shutil.rmtree(profile, ignore_errors=True)
    profile.mkdir(parents=True, exist_ok=True)
    port = 9241
    proc = subprocess.Popen([
        chrome,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        f"--user-data-dir={profile}",
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        "--window-size=1440,4200",
        "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as response:
                    if json.load(response):
                        break
            except Exception:
                time.sleep(.2)
        else:
            raise SystemExit("Chrome did not expose CDP")

        js = temp / "envelope-v8-seam-proof.mjs"
        js.write_text(r'''const port=Number(process.env.V8_CDP_PORT),url=process.env.V8_TARGET_URL,sleep=ms=>new Promise(r=>setTimeout(r,ms));
const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(),target=targets.find(t=>t.type==='page');
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});let seq=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result||{});}};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evalv=async e=>(await call('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true})).result?.value;
await call('Page.enable');await call('Runtime.enable');await call('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'dark'}]});
const ready=async()=>{for(let i=0;i<160;i++){const s=await evalv(`(()=>({r:document.readyState,i:Array.from(document.images).every(x=>x.complete)}))()`);if(s?.r==='complete'&&s.i){await sleep(900);return}await sleep(200)}throw new Error('images not ready')};
const expr=`(()=>{const a=Array.from(document.images),r=i=>{if(!i)return null;const b=i.getBoundingClientRect();return{x:b.x,y:b.y,w:b.width,h:b.height,bottom:b.bottom,right:b.right,align:i.getAttribute('align'),nw:i.naturalWidth,nh:i.naturalHeight}},s=t=>r(a.find(i=>i.src.includes(t))),alt=t=>r(a.find(i=>i.alt===t));return{hero:s('profile-hero.svg'),l:s('profile-character-side-left.svg'),c:alt('めぐみん'),rr:s('profile-character-side-right.svg'),ap:s('profile-attribution-projects-transition.svg'),p:s('profile-section-projects.svg'),pc:s('profile-projects-canvas.svg'),ah:s('profile-activity-header.svg'),ac:s('profile-activity-canvas.svg'),ft:s('profile-footer-transition.svg')}})()`;
const check=(label,m)=>{const keys=['hero','l','c','rr','ap','p','pc','ah','ac','ft'];if(keys.some(k=>!m[k]||m[k].nw<=0||m[k].nh<=0))throw new Error(`${label}: missing/failed image`);if(keys.some(k=>m[k].align!=='top'))throw new Error(`${label}: align=top missing`);if(Math.max(Math.abs(m.l.y-m.c.y),Math.abs(m.c.y-m.rr.y))>2.5)throw new Error(`${label}: character row wrapped`);const rowTop=Math.min(m.l.y,m.c.y,m.rr.y),rowBottom=Math.max(m.l.bottom,m.c.bottom,m.rr.bottom);const segments=[['hero-character',m.hero.bottom,rowTop],['character-attribution-projects',rowBottom,m.ap.y],['attribution-projects-label',m.ap.bottom,m.p.y],['projects-label-canvas',m.p.bottom,m.pc.y],['projects-canvas-activity-header',m.pc.bottom,m.ah.y],['activity-header-canvas',m.ah.bottom,m.ac.y],['activity-canvas-footer',m.ac.bottom,m.ft.y]];const gaps=Object.fromEntries(segments.map(([n,b,t])=>[n,+(t-b).toFixed(3)]));for(const [n,g] of Object.entries(gaps))if(Math.abs(g)>1.25)throw new Error(`${label}: seam ${n}=${g}px`);return{gaps,heights:{ap:+m.ap.h.toFixed(3),p:+m.p.h.toFixed(3),ah:+m.ah.h.toFixed(3),ft:+m.ft.h.toFixed(3)}}};
const out={};for(const [label,width,mobile] of [['desktop',1440,false],['mobile',430,true]]){await call('Emulation.setDeviceMetricsOverride',{width,height:4200,deviceScaleFactor:1,mobile});await call('Page.navigate',{url});await ready();const m=await evalv(expr);out[label]=check(label,m)}ws.close();console.log('ENVELOPE_V8_TARGET_SEAMS_PASS '+JSON.stringify({result:'PASS',target:url,measurements:out}));''', encoding="utf-8")
        target = f"https://github.com/nekomario28/nekomario28/tree/{os.environ['GITHUB_HEAD_REF']}"
        run = subprocess.run(
            [node, str(js)],
            env={**os.environ, "V8_CDP_PORT": str(port), "V8_TARGET_URL": target},
            capture_output=True,
            text=True,
            timeout=75,
        )
        if run.stdout:
            print(run.stdout.strip())
        if run.returncode:
            if run.stderr:
                print(run.stderr.strip())
            raise SystemExit("Envelope v8 target seam proof failed")
        if "ENVELOPE_V8_TARGET_SEAMS_PASS " not in run.stdout:
            raise SystemExit("Envelope v8 target seam proof emitted no PASS")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    validate_generated()
    target_seam_proof_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
