#!/usr/bin/env python3
"""Validate Envelope v7 continuous-canvas generation without mutating live assets."""
from __future__ import annotations

import importlib.util
import json
import tempfile
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
