#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
import random
import re
from pathlib import Path


CATEGORY_RE = re.compile(
    r'<circle class="category"[^>]*cx="(?P<x>-?[\d.]+)" cy="(?P<y>-?[\d.]+)"'
)
HALO_RE = re.compile(
    r'<circle class="halo"[^>]*cx="(?P<x>-?[\d.]+)" cy="(?P<y>-?[\d.]+)"'
)
VIEWBOX_RE = re.compile(r'viewBox="0 0 (?P<w>[\d.]+) (?P<h>[\d.]+)"')


def enhance(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if 'id="cosmic-preview"' in text:
        return

    viewbox = VIEWBOX_RE.search(text)
    halo = HALO_RE.search(text)
    categories = list(CATEGORY_RE.finditer(text))
    if not viewbox or not halo or not categories:
        raise RuntimeError(f"could not locate project-map geometry in {path}")

    width = float(viewbox.group("w"))
    height = float(viewbox.group("h"))
    owner_x = float(halo.group("x"))
    owner_y = float(halo.group("y"))
    dark = "#0d1117" in text

    nebula_primary = "#58a6ff" if dark else "#0969da"
    nebula_secondary = "#1f6feb" if dark else "#54aeff"
    star_color = "#f0f6fc" if dark else "#57606a"
    arm_color = "#58a6ff" if dark else "#0969da"

    gradients: list[str] = []
    for index, match in enumerate(categories):
        gradients.append(
            "\n".join(
                [
                    f'<radialGradient id="cosmic-nebula-{index}" cx="50%" cy="50%" r="50%">',
                    f'  <stop offset="0" stop-color="{nebula_primary}" stop-opacity="{0.12 if dark else 0.075}"/>',
                    f'  <stop offset="45%" stop-color="{nebula_secondary}" stop-opacity="{0.065 if dark else 0.040}"/>',
                    f'  <stop offset="78%" stop-color="{nebula_primary}" stop-opacity="0.015"/>',
                    f'  <stop offset="100%" stop-color="{nebula_primary}" stop-opacity="0"/>',
                    "</radialGradient>",
                ]
            )
        )

    text = text.replace("</defs>", "\n" + "\n".join(gradients) + "\n</defs>", 1)
    text = text.replace(
        "</style>",
        "\n.cosmic-star{animation:cosmicTwinkle 5.6s ease-in-out infinite}\n"
        "@keyframes cosmicTwinkle{0%,100%{opacity:.55}50%{opacity:1}}\n"
        "</style>",
        1,
    )

    rng = random.Random(280828)
    stars: list[str] = []
    for index in range(66):
        x = rng.uniform(18, width - 18)
        y = rng.uniform(66, height - 66)
        # Keep the call-to-action and owner label areas visually quiet.
        if y > height - 92 and width * 0.27 < x < width * 0.73:
            y -= 55
        if math.hypot(x - owner_x, y - owner_y) < 45:
            x = (x + 72) % (width - 36) + 18
        radius = rng.choice([0.55, 0.7, 0.85, 1.05, 1.3])
        opacity = rng.uniform(0.10 if not dark else 0.16, 0.30 if not dark else 0.42)
        delay = -rng.uniform(0, 5.6)
        stars.append(
            f'<circle class="cosmic-star" cx="{x:.1f}" cy="{y:.1f}" r="{radius:.2f}" '
            f'fill="{star_color}" opacity="{opacity:.3f}" style="animation-delay:{delay:.2f}s"/>'
        )

    nebulae: list[str] = []
    for index, match in enumerate(categories):
        x = float(match.group("x"))
        y = float(match.group("y"))
        angle = (index * 37 + 18) % 180
        nebulae.append(
            f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="94" ry="55" '
            f'transform="rotate({angle} {x:.1f} {y:.1f})" fill="url(#cosmic-nebula-{index})"/>'
        )

    arms: list[str] = []
    for index, rotation in enumerate((-18, 102, 222)):
        opacity = 0.075 if dark else 0.042
        arms.append(
            f'<ellipse cx="{owner_x:.1f}" cy="{owner_y:.1f}" rx="154" ry="58" '
            f'transform="rotate({rotation} {owner_x:.1f} {owner_y:.1f})" fill="none" '
            f'stroke="{arm_color}" stroke-width="1" opacity="{opacity * (1 - index * 0.08):.3f}" '
            'stroke-dasharray="2 9"/>'
        )

    cosmic = "\n".join(
        [
            '<g id="cosmic-preview" pointer-events="none">',
            *stars,
            *arms,
            *nebulae,
            "</g>",
        ]
    )

    background_rect = re.search(r'(<rect x="1" y="1"[^>]+/>)', text)
    if not background_rect:
        raise RuntimeError(f"could not locate preview background in {path}")
    insert_at = background_rect.end()
    text = text[:insert_at] + "\n" + cosmic + text[insert_at:]
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.files:
        enhance(path)


if __name__ == "__main__":
    main()
