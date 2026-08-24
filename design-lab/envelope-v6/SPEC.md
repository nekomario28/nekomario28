# Envelope v6 — global motion space + clipped windows

Status: implementation candidate
Target: GitHub profile README dark surface

## Problem

Envelope v5 gives every embedded SVG the same rail positions and duration class, but each asset owns a local particle that starts above its own viewport and disappears at its own lower edge. The result can read as `object dies at the boundary -> a new object starts elsewhere`.

The desired behavior is different:

> Define one logical coordinate space first. Objects move in that shared space. Every SVG is only a viewport/window into the shared object field and draws the part that intersects its window.

GitHub still loads each `<img>` as an independent SVG document, so v6 does **not** claim one shared runtime clock. The improvement is shared **space/object identity/velocity grammar**, plus geometric clipping at boundaries.

## Authority

`global-motion-space.json` is the v6 motion-space authority.

It defines:

- one 900-wide logical coordinate space;
- a global Y extent;
- visible windows for Hero, three distinct bridges, Projects, Activity and Footer;
- invisible logical gaps for the character image, project map and contribution graph;
- one rail pair (`x=18`, `x=882`);
- one global travel duration;
- one particle set with stable phase offsets;
- a bleed allowance for partial geometry at viewport boundaries.

The gap lengths are logical approximations derived from the accepted GitHub desktop composition. They are not claims about GitHub-owned page geometry.

## Rendering equation

For a particle with global position `G(t)` and a rendered asset whose window begins at `S`:

```text
local_y(t) = G(t) - S
```

The asset does not create a new trajectory. It renders the same global trajectory after subtracting its window start.

Every participating SVG explicitly clips the motion group to:

```text
0 <= local_x <= 900
0 <= local_y <= asset_height
```

Objects are allowed to continue beyond those bounds. The clip shows only the geometric intersection.

## Boundary behavior

Do **not** bind opacity to the local asset boundary.

A moving pulse consists of:

- a leading circle;
- a short trailing line above it.

As the center passes the bottom edge, the tail remains visible until it also leaves the window. At the next visible global window, the same global trajectory is already defined and becomes visible when it intersects that window.

This is the key v6 change: the object is not deleted at the edge; the current viewport simply stops seeing it.

## Distinct bridge assets

The README previously reused one bridge file three times. That cannot represent three different global windows because the same SVG would have the same `window_start` each time.

v6 therefore publishes three stable bridge assets:

- `profile-frame-bridge-character-projects.svg`
- `profile-frame-bridge-projects-activity.svg`
- `profile-frame-bridge-activity-footer.svg`

Their static art may be identical, but their global-window metadata and motion transforms are different.

## Synchronization boundary

Separate GitHub README SVG documents are still independent documents.

Therefore:

- `cross_document_hard_sync = false` remains mandatory;
- equal durations/phases are not described as a proven shared clock;
- slow global velocity and sparse particles reduce visible phase error;
- negative phase offsets make the field populated immediately after load;
- static/reduced-motion rendering remains complete.

If a future requirement needs exact object continuity at a single animation-frame boundary, the architecture must collapse that region into one timeline-owning document/runtime. README-separated images cannot honestly guarantee it.

## Promotion gate

Before v6 may replace v5 live:

1. parse and compile renderer/promoter code;
2. validate the global window partition and all visible window heights;
3. generate all four seasons;
4. verify each of the seven stable live assets has `v6-global-window`, reduced-motion handling, no script, and the expected geometry;
5. verify three bridge assets have three distinct global starts;
6. verify particle opacity is not animated as a boundary fade;
7. verify README references all three distinct bridges exactly once;
8. render GitHub dark desktop/mobile;
9. capture two time-separated frames and localize expected rail movement;
10. only then promote the tested season's live playback state to `PASS`.

## Rollback

Envelope v5 remains recoverable from repository history and its Design Lab evidence. The legacy single bridge asset may remain checked in as an optional/rollback artifact but is not part of the v6 live set.
