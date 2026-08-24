#!/usr/bin/env python3
"""Rendered browser matrix for the lab-only Envelope v9 portable donor.

The harness embeds each generated SVG directly into a local HTML page so DOM
metrics are synchronous, then uses a real headless Chrome screenshot to prove
whether the host background is visible through the SVG corner. This is not
public GitHub-profile evidence and does not mutate live assets.
"""
from __future__ import annotations

import html
import importlib.util
import json
import math
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDERER_PATH = HERE / "render_portable_surface.py"
OPAQUE_SAFE = ROOT / "design-lab" / "profile-envelope-config.example.json"
TRANSPARENT_SAFE = ROOT / "design-lab" / "profile-envelope-config.transparent.example.json"


def load_renderer():
    spec = importlib.util.spec_from_file_location("envelope_v9_browser_renderer", RENDERER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load v9 renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = load_renderer()


def write_config(root: Path, name: str, *, background: str, text: str, motion: str, density: str = "auto") -> Path:
    path = root / f"{name}.json"
    path.write_text(
        json.dumps(
            {
                "contract_version": 1,
                "target_adapter": "github-profile-readme",
                "profile": {"theme": "seasonal-dark", "background": background, "text": text, "motion": motion},
                "surface": {"mounted_source_background": "inherit"},
                "frame": {"mode": "rail", "caps": "outer-only"},
                "labels": {"density": density},
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


def make_probe_html(svg_source: str, *, host: str, width: int) -> str:
    return f'''<!doctype html>
<meta charset="utf-8"><title>probe</title>
<style>
html,body{{margin:0;padding:0;background:{host};}}
#holder{{width:{width}px;display:block;}}
#holder>svg{{display:block;width:100%;height:auto;}}
#result{{display:none;}}
</style>
<div id="holder">{svg_source}</div><pre id="result"></pre>
<script>
function finiteRect(r){{return [r.x,r.y,r.width,r.height].every(Number.isFinite);}}
const svg=document.querySelector('#holder>svg');
const root=svg.getBoundingClientRect();
const vectors=[...svg.querySelectorAll('[data-vector-text="v1"]')];
const rects=vectors.map(node=>node.getBoundingClientRect());
const adaptive=[...svg.querySelectorAll('.v9-adaptive-vector-text path')];
const overflow=rects.filter(r=>!finiteRect(r)||r.left<root.left-1||r.top<root.top-1||r.right>root.right+1||r.bottom>root.bottom+1).length;
const result={{
 schemeDark:matchMedia('(prefers-color-scheme: dark)').matches,
 schemeLight:matchMedia('(prefers-color-scheme: light)').matches,
 rootWidth:root.width,rootHeight:root.height,
 textCount:svg.querySelectorAll('text').length,
 semanticTextCount:svg.querySelectorAll('title,desc').length,
 vectorCount:vectors.length,
 adaptivePathCount:adaptive.length,
 adaptiveStrokes:[...new Set(adaptive.map(path=>getComputedStyle(path).stroke))],
 vectorOverflowCount:overflow,
 allVectorRectsFinite:rects.every(finiteRect),
 renderTarget:svg.getAttribute('data-profile-render-target-sha256'),
 contractTarget:svg.getAttribute('data-profile-contract-sha256'),
 background:svg.getAttribute('data-profile-background'),
 textMode:svg.getAttribute('data-profile-text'),
 hostFontIndependent:svg.getAttribute('data-host-font-independent')
}};
document.getElementById('result').textContent=JSON.stringify(result);
document.title='PROBE_DONE';
</script>'''


def parse_probe_dom(dom: str) -> dict:
    match = re.search(r'<pre id="result"[^>]*>(.*?)</pre>', dom, flags=re.S)
    if not match:
        raise AssertionError(f"probe result element not found: {dom[-1600:]}")
    payload = html.unescape(match.group(1)).strip()
    if not payload:
        title = re.search(r"<title>(.*?)</title>", dom, flags=re.S)
        raise AssertionError(f"probe result empty title={title.group(1) if title else 'UNKNOWN'} tail={dom[-1600:]}")
    data = json.loads(payload)
    if "error" in data:
        raise AssertionError(f"browser probe failed: {data['error']}")
    return data


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def png_pixel(path: Path, x: int, y: int) -> tuple[int, int, int, int]:
    raw = path.read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("Chrome screenshot is not PNG")
    cursor = 8
    width = height = bit_depth = color_type = None
    idat = bytearray()
    while cursor < len(raw):
        length = struct.unpack(">I", raw[cursor:cursor + 4])[0]
        kind = raw[cursor + 4:cursor + 8]
        data = raw[cursor + 8:cursor + 8 + length]
        cursor += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", data)
            assert compression == 0 and filter_method == 0 and interlace == 0
        elif kind == b"IDAT":
            idat.extend(data)
        elif kind == b"IEND":
            break
    if bit_depth != 8 or color_type not in {2, 6}:
        raise AssertionError(f"unsupported PNG format bit_depth={bit_depth} color_type={color_type}")
    assert width is not None and height is not None and 0 <= x < width and 0 <= y < height
    bpp = 3 if color_type == 2 else 4
    stride = width * bpp
    decoded = zlib.decompress(bytes(idat))
    rows: list[bytearray] = []
    offset = 0
    previous = bytearray(stride)
    for _ in range(height):
        filter_type = decoded[offset]
        offset += 1
        scan = bytearray(decoded[offset:offset + stride])
        offset += stride
        recon = bytearray(stride)
        for index, value in enumerate(scan):
            left = recon[index - bpp] if index >= bpp else 0
            up = previous[index]
            upper_left = previous[index - bpp] if index >= bpp else 0
            if filter_type == 0:
                recon[index] = value
            elif filter_type == 1:
                recon[index] = (value + left) & 0xff
            elif filter_type == 2:
                recon[index] = (value + up) & 0xff
            elif filter_type == 3:
                recon[index] = (value + ((left + up) // 2)) & 0xff
            elif filter_type == 4:
                recon[index] = (value + _paeth(left, up, upper_left)) & 0xff
            else:
                raise AssertionError(f"unsupported PNG filter {filter_type}")
        rows.append(recon)
        previous = recon
    start = x * bpp
    pixel = rows[y][start:start + bpp]
    if bpp == 3:
        return pixel[0], pixel[1], pixel[2], 255
    return pixel[0], pixel[1], pixel[2], pixel[3]


def rgb(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)", value)
    if not match:
        raise AssertionError(f"unsupported computed color {value!r}")
    return tuple(int(match.group(index)) for index in range(1, 4))


def relative_luminance(color: tuple[int, int, int]) -> float:
    def channel(value: int) -> float:
        scaled = value / 255.0
        return scaled / 12.92 if scaled <= 0.04045 else ((scaled + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(value) for value in color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def run_probe(chrome: str, work: Path, *, svg_path: Path, scheme: str, width: int, viewport_width: int, host: str) -> tuple[dict, tuple[int, int, int, int]]:
    probe_id = f"{svg_path.parent.parent.name}-{svg_path.stem}-{scheme}-{width}-{host.replace('#','')}"
    html_path = work / f"{probe_id}.html"
    png_path = work / f"{probe_id}.png"
    html_path.write_text(make_probe_html(svg_path.read_text(encoding="utf-8"), host=host, width=width), encoding="utf-8")
    profile = work / f"chrome-{probe_id}"
    common = [
        chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
        f"--user-data-dir={profile}", f"--window-size={viewport_width},900",
    ]
    if scheme == "dark":
        common.append("--force-dark-mode")
    url = html_path.resolve().as_uri()
    dumped = subprocess.run(common + ["--dump-dom", url], text=True, capture_output=True, timeout=30, check=False)
    if dumped.returncode != 0:
        raise AssertionError(f"DOM browser returned {dumped.returncode}: {dumped.stderr[-1200:]}")
    data = parse_probe_dom(dumped.stdout)
    shot_profile = work / f"chrome-shot-{probe_id}"
    screenshot_common = [
        chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
        f"--user-data-dir={shot_profile}", f"--window-size={viewport_width},900",
    ]
    if scheme == "dark":
        screenshot_common.append("--force-dark-mode")
    shot = subprocess.run(screenshot_common + [f"--screenshot={png_path}", url], text=True, capture_output=True, timeout=30, check=False)
    if shot.returncode != 0 or not png_path.exists():
        raise AssertionError(f"screenshot browser returned {shot.returncode}: {shot.stderr[-1200:]}")
    assert data["schemeDark"] is (scheme == "dark"), (scheme, data)
    assert data["schemeLight"] is (scheme == "light"), (scheme, data)
    assert math.isfinite(float(data["rootWidth"])) and math.isfinite(float(data["rootHeight"]))
    assert abs(float(data["rootWidth"]) - width) <= 1.5, (width, data["rootWidth"])
    return data, png_pixel(png_path, 1, 1)


def main() -> int:
    chrome = browser_binary()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        configs = work / "configs"
        configs.mkdir()
        cases: dict[str, tuple[Path, dict]] = {}
        configs_to_render = (
            ("opaque-safe", OPAQUE_SAFE),
            ("transparent-safe", TRANSPARENT_SAFE),
            ("transparent-native", write_config(configs, "native", background="transparent", text="native", motion="on")),
            ("transparent-minimal", write_config(configs, "minimal", background="transparent", text="minimal", motion="off", density="minimal")),
        )
        for name, config in configs_to_render:
            output = work / "cases" / name
            output.mkdir(parents=True)
            _, resolved = R.render(config, season="summer", output_root=output)
            cases[name] = (output, resolved)

        probes = 0
        for scheme in ("light", "dark"):
            host = "#ffffff" if scheme == "light" else "#0d1117"
            for width, viewport in ((846, 900), (390, 430)):
                data, pixel = run_probe(
                    chrome, work,
                    svg_path=cases["transparent-safe"][0] / "assets/profile-hero.svg",
                    scheme=scheme, width=width, viewport_width=viewport, host=host,
                )
                probes += 1
                assert data["background"] == "transparent" and data["textMode"] == "safe"
                assert data["hostFontIndependent"] == "true"
                assert data["textCount"] == 0 and data["vectorCount"] > 0
                assert data["adaptivePathCount"] > 0 and data["allVectorRectsFinite"] is True
                assert data["vectorOverflowCount"] == 0
                expected = (31, 35, 40) if scheme == "light" else (240, 246, 252)
                stroke = rgb(data["adaptiveStrokes"][0])
                assert max(abs(stroke[index] - expected[index]) for index in range(3)) <= 1
                host_rgb = (255, 255, 255) if scheme == "light" else (13, 17, 23)
                assert contrast(stroke, host_rgb) >= 12.0
                assert pixel[:3] == host_rgb, (scheme, pixel, host_rgb)
                assert data["renderTarget"] == cases["transparent-safe"][1]["render_target_sha256"]

        for scheme in ("light", "dark"):
            host = "#ffffff" if scheme == "light" else "#0d1117"
            projects, pixel = run_probe(
                chrome, work,
                svg_path=cases["transparent-safe"][0] / "assets/profile-projects-canvas.svg",
                scheme=scheme, width=846, viewport_width=900, host=host,
            )
            probes += 1
            assert projects["textCount"] == 0 and projects["vectorCount"] > 0
            assert projects["adaptivePathCount"] > 0 and projects["allVectorRectsFinite"] is True
            assert pixel[:3] == ((255, 255, 255) if scheme == "light" else (13, 17, 23))
            assert projects["renderTarget"] == cases["transparent-safe"][1]["render_target_sha256"]

        native, native_pixel = run_probe(
            chrome, work,
            svg_path=cases["transparent-native"][0] / "assets/profile-hero.svg",
            scheme="light", width=846, viewport_width=900, host="#ffffff",
        )
        probes += 1
        assert native["textMode"] == "native" and native["hostFontIndependent"] == "false"
        assert native["textCount"] > 0 and native["vectorCount"] == 0 and native_pixel[:3] == (255, 255, 255)

        minimal, minimal_pixel = run_probe(
            chrome, work,
            svg_path=cases["transparent-minimal"][0] / "assets/profile-projects-canvas.svg",
            scheme="light", width=846, viewport_width=900, host="#ffffff",
        )
        probes += 1
        assert minimal["textMode"] == "minimal" and minimal["hostFontIndependent"] == "true"
        assert minimal["textCount"] == 0 and minimal["vectorCount"] == 0
        assert minimal["semanticTextCount"] > 0 and minimal_pixel[:3] == (255, 255, 255)

        opaque, opaque_pixel = run_probe(
            chrome, work,
            svg_path=cases["opaque-safe"][0] / "assets/profile-hero.svg",
            scheme="dark", width=846, viewport_width=900, host="#ff00ff",
        )
        probes += 1
        assert opaque["background"] == "opaque" and opaque["hostFontIndependent"] == "true"
        assert opaque["textCount"] == 0 and opaque["vectorCount"] > 0
        assert opaque_pixel[:3] != (255, 0, 255)
        assert opaque["renderTarget"] == cases["opaque-safe"][1]["render_target_sha256"]

    print(f"ENVELOPE_V9_BROWSER_MATRIX_PASS cases={probes} schemes=light/dark widths=desktop/mobile surfaces=hero/projects")
    print("TARGET_LAYOUT=PASS TEXT_RENDER=PASS TRANSPARENCY_RENDER=PASS NATIVE_RENDER=OBSERVED MINIMAL_DYNAMIC_TEXT=PASS")
    print("PLAYBACK=NOT_RUN PUBLIC_GITHUB_PROFILE=NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
