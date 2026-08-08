#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import render_galaxy_project_map as base

collision_size = base.collision_size


def screen_mobility(node: dict[str, Any]) -> float:
    if node.get("type") == "owner":
        return 0.0
    if node.get("type") == "group":
        return 0.10
    return 1.0


def clamp_screen(value: list[Any]) -> None:
    width, height = base.collision_size(value[2])
    value[0] = max(base.SAFE_LEFT + width / 2, min(base.SAFE_RIGHT - width / 2, value[0]))
    value[1] = max(base.SAFE_TOP + height / 2, min(base.SAFE_BOTTOM - height / 2, value[1]))


def separate_screen_pair(first: list[Any], second: list[Any]) -> bool:
    a_width, a_height = base.collision_size(first[2])
    b_width, b_height = base.collision_size(second[2])
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    overlap_x = (a_width + b_width) / 2 + 26 - abs(dx)
    overlap_y = (a_height + b_height) / 2 + 22 - abs(dy)
    if overlap_x <= 0 or overlap_y <= 0:
        return False

    a_mobility = screen_mobility(first[2])
    b_mobility = screen_mobility(second[2])
    total = a_mobility + b_mobility
    if total <= 0:
        return False
    a_share = a_mobility / total
    b_share = b_mobility / total

    candidates: list[tuple[float, float, list[Any], list[Any]]] = []
    for axis, overlap, delta in (("x", overlap_x, dx), ("y", overlap_y, dy)):
        a = [first[0], first[1], first[2]]
        b = [second[0], second[1], second[2]]
        direction = 1 if delta >= 0 else -1
        push = overlap + 1.0
        if axis == "x":
            a[0] -= direction * push * a_share
            b[0] += direction * push * b_share
        else:
            a[1] -= direction * push * a_share
            b[1] += direction * push * b_share
        clamp_screen(a)
        clamp_screen(b)

        new_dx = b[0] - a[0]
        new_dy = b[1] - a[1]
        remaining_x = (a_width + b_width) / 2 + 26 - abs(new_dx)
        remaining_y = (a_height + b_height) / 2 + 22 - abs(new_dy)
        remaining_area = max(0.0, remaining_x) * max(0.0, remaining_y)
        movement = (
            abs(a[0] - first[0])
            + abs(a[1] - first[1])
            + abs(b[0] - second[0])
            + abs(b[1] - second[1])
        )
        candidates.append((remaining_area, movement, a, b))

    _, _, best_a, best_b = min(candidates, key=lambda candidate: (candidate[0], candidate[1]))
    first[0], first[1] = best_a[0], best_a[1]
    second[0], second[1] = best_b[0], best_b[1]
    return True


def relax_screen(positions: dict[str, list[Any]], iterations: int, pull: bool) -> None:
    values = list(positions.values())
    for _ in range(iterations):
        moved = False
        for first_index in range(len(values)):
            for second_index in range(first_index + 1, len(values)):
                moved = separate_screen_pair(values[first_index], values[second_index]) or moved

        if pull:
            for value in values:
                node = value[2]
                if node.get("type") == "owner":
                    continue
                strength = 0.11 if node.get("type") == "group" else 0.022
                value[0] += (value[3] - value[0]) * strength
                value[1] += (value[4] - value[1]) * strength

        for value in values:
            clamp_screen(value)
        if not moved:
            break


def fit_world_to_preview(world: dict[str, list[Any]]) -> dict[str, list[Any]]:
    # Keep the core galaxy physics for the unconstrained layout.
    base.relax_layout(world, 260, pull=True, screen=False)
    base.relax_layout(world, 110, pull=False, screen=False)

    min_x = min(value[0] for value in world.values())
    max_x = max(value[0] for value in world.values())
    min_y = min(value[1] for value in world.values())
    max_y = max(value[1] for value in world.values())
    available_width = base.SAFE_RIGHT - base.SAFE_LEFT - 150
    available_height = base.SAFE_BOTTOM - base.SAFE_TOP - 110
    scale = min(
        1.0,
        available_width / max(1.0, max_x - min_x),
        available_height / max(1.0, max_y - min_y),
    )
    world_cx = (min_x + max_x) / 2
    world_cy = (min_y + max_y) / 2

    screen: dict[str, list[Any]] = {}
    for node_id, value in world.items():
        x = base.OWNER_X + (value[0] - world_cx) * scale
        y = base.OWNER_Y + (value[1] - world_cy) * scale
        screen[node_id] = [x, y, value[2], x, y]

    owner_id = next(
        node_id for node_id, value in screen.items() if value[2].get("type") == "owner"
    )
    owner_dx = base.OWNER_X - screen[owner_id][0]
    owner_dy = base.OWNER_Y - screen[owner_id][1]
    for value in screen.values():
        value[0] += owner_dx
        value[1] += owner_dy
        value[3] += owner_dx
        value[4] += owner_dy

    # The README preview has hard edges. Resolve collisions using the axis that
    # still has room instead of repeatedly pushing nodes into a boundary.
    relax_screen(screen, 260, pull=True)
    relax_screen(screen, 240, pull=False)
    return screen


# Patch only the finite-canvas fitting step; the shared galaxy geometry stays in
# render_galaxy_project_map.py.
base.fit_world_to_preview = fit_world_to_preview


def preview_positions(project_map: dict[str, Any]) -> dict[str, tuple[float, float, dict[str, Any]]]:
    return base.preview_positions(project_map)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render validated galaxy-style project map previews")
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--light", type=Path, required=True)
    parser.add_argument("--dark", type=Path, required=True)
    args = parser.parse_args()
    project_map = json.loads(args.json.read_text(encoding="utf-8"))
    base.render(project_map, args.light, "light")
    base.render(project_map, args.dark, "dark")


if __name__ == "__main__":
    main()
