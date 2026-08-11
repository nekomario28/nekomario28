#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
import random
import re
from pathlib import Path


CATEGORY_RE = re.compile(
    r'<circle class="category"[^>]*cx="(?P<x>-?[\d.]+)" cy="(?P<y>-?[\d.]+)"[^>]*/>'
)
HALO_RE = re.compile(
    r'<circle class="halo"[^>]*cx="(?P<x>-?[\d.]+)" cy="(?P<y>-?[\d.]+)"'
)
COSMIC_RE = re.compile(r'(<g id="cosmic-preview" pointer-events="none">)(?P<body>.*?)(</g>)', re.DOTALL)


def enhance(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if 'id="stellar-associations"' in text:
        return

    halo = HALO_RE.search(text)
    cosmic = COSMIC_RE.search(text)
    categories = list(CATEGORY_RE.finditer(text))
    if not halo or not cosmic or not categories:
        raise RuntimeError(f"could not locate common-center preview geometry in {path}")

    owner_x = float(halo.group("x"))
    owner_y = float(halo.group("y"))
    dark = "#0d1117" in text
    group_color = "#1f6feb" if dark else "#0969da"
    owner_color = "#58a6ff" if dark else "#54aeff"
    star_color = "#f0f6fc" if dark else "#57606a"

    gradients: list[str] = []
    association_shapes: list[str] = ['<g id="stellar-associations" pointer-events="none">']

    for category_index, match in enumerate(categories):
        x = float(match.group("x"))
        y = float(match.group("y"))
        tangent_degrees = math.degrees(math.atan2(y - owner_y, x - owner_x) + math.pi / 2)
        rng = random.Random(280828 + category_index * 7919)
        major = 72.0 + rng.uniform(-5.0, 9.0)
        minor = 30.0 + rng.uniform(-3.0, 6.0)
        lobe_count = 4

        association_shapes.append(
            f'<g transform="translate({x:.1f} {y:.1f}) rotate({tangent_degrees:.1f})">'
        )

        for lobe_index in range(lobe_count):
            gradient_id = f"association-{category_index}-{lobe_index}"
            along = rng.uniform(-0.34, 0.34) * major
            across = rng.uniform(-0.36, 0.36) * minor
            rx = major * rng.uniform(0.42, 0.66)
            ry = minor * rng.uniform(0.50, 0.82)
            tilt = rng.uniform(-12.0, 12.0)
            gradients.append(
                "".join(
                    [
                        f'<radialGradient id="{gradient_id}" cx="50%" cy="50%" r="50%">',
                        f'<stop offset="0" stop-color="{group_color}" stop-opacity="{0.043 if dark else 0.026}"/>',
                        f'<stop offset="42%" stop-color="{group_color}" stop-opacity="{0.025 if dark else 0.015}"/>',
                        f'<stop offset="78%" stop-color="{owner_color}" stop-opacity="{0.008 if dark else 0.005}"/>',
                        f'<stop offset="100%" stop-color="{group_color}" stop-opacity="0"/>',
                        "</radialGradient>",
                    ]
                )
            )
            association_shapes.append(
                f'<ellipse cx="{along:.1f}" cy="{across:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
                f'transform="rotate({tilt:.1f} {along:.1f} {across:.1f})" fill="url(#{gradient_id})"/>'
            )

        # Fixed local stars suggest a loose stellar association without drawing a
        # hard boundary. Nothing here animates or changes shape over time.
        for star_index in range(7):
            sx = rng.uniform(-0.56, 0.56) * major
            sy = rng.uniform(-0.58, 0.58) * minor
            normalized = math.hypot(sx / major, sy / minor)
            if normalized > 0.90:
                scale = 0.90 / normalized
                sx *= scale
                sy *= scale
            radius = rng.uniform(0.45, 0.95)
            opacity = rng.uniform(0.07 if not dark else 0.09, 0.14 if not dark else 0.17)
            association_shapes.append(
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{radius:.2f}" fill="{star_color}" opacity="{opacity:.3f}"/>'
            )

        association_shapes.append("</g>")

    association_shapes.append("</g>")

    # Replace the matched cosmic group while its offsets still refer to the original
    # text. Only after that is it safe to change the length of the <defs> section.
    enhanced_cosmic = cosmic.group(1) + cosmic.group("body") + "\n" + "\n".join(association_shapes) + "\n" + cosmic.group(3)
    text = text[: cosmic.start()] + enhanced_cosmic + text[cosmic.end() :]
    text = text.replace("</defs>", "\n" + "\n".join(gradients) + "\n</defs>", 1)

    # Category remains a tiny location anchor for its label rather than a celestial
    # body. The diffuse association behind it carries the category's visual extent.
    text = re.sub(
        r'(<circle class="category"[^>]*r=")5("[^>]*/>)',
        r'\g<1>2\g<2>',
        text,
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.files:
        enhance(path)


if __name__ == "__main__":
    main()
