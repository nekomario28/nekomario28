# Envelope v7 — continuous canvas

## Goal

Make the GitHub profile README read as one continuous dark canvas whose real media appears mounted above that canvas, including the left/right area around narrower content.

This remains a README-area illusion. It does not claim authority over GitHub page chrome, the profile sidebar, pinned repositories, or host CSS.

## Composition model

Envelope v7 uses a hybrid strategy because the foreground sources have different ownership and browser constraints.

1. **Repository-owned SVG foregrounds** (`project-map/galaxy.svg`, `assets/github-contributions-dark.svg`) are copied structurally into generated 900 px composite stage SVGs. The copied body remains the authoritative visual data; no fake project/activity data is invented.
2. **Third-party character media** remains the original external `<img>` in README HTML. It is not copied into the repository and is not nested as an external `<image>` inside a repository SVG. Matching left/right repository-owned surface SVGs flank it responsively.
3. **Attribution** is a full-width repository-owned vector-outline band, keeping the required rights line visible without relying on client Japanese fonts.
4. Hero, section bands, bridges and footer remain full-width repository-owned stages.

## Responsive character stage

The character row is one adjacent HTML row:

- left surface: `11.111%`;
- authoritative character image: `77.778%`;
- right surface: `11.111%`.

The source widths are 100 / 700 / 100 and share the same 394 px source height, so the three pieces preserve one common aspect-height when scaled proportionally. There is intentionally no whitespace between the inline elements.

This strategy is preferred to placing the third-party image inside an SVG because nested cross-origin subresources are a portability/security-policy boundary on GitHub.

## Repository-owned composite stages

### Projects

- outer canvas: 900 × 420;
- project map: copied from the checked-in 740 × 420 SVG body into x = 80..820;
- side background: 80 px each side;
- the existing project-map link remains on the outer README image.

### Activity

- outer canvas: 900 × 220;
- contribution graph: copied from the checked-in 760 × 220 SVG body into x = 70..830;
- side background: 70 px each side.

Generated composite panels must be regenerated whenever their authoritative source changes. A stale copied project map or contribution graph is a release blocker.

## Full logical canvas

Envelope v7 replaces v6 invisible content gaps with rendered surfaces.

Logical order:

1. Hero — 260
2. Character stage — 394
3. Attribution — 44
4. Character → Projects bridge — 32
5. Projects header — 68
6. Projects canvas — 420
7. Projects → Activity bridge — 32
8. Activity header — 68
9. Activity canvas — 220
10. Activity → Footer bridge — 32
11. Footer — 92

Total logical extent: **1662 px**.

The motion authority is `global-motion-space.json`.

## Motion model

The v6 object-lifecycle rule remains authoritative and is extended to the newly visible v7 surfaces:

- moving rail objects belong to one logical global field;
- local assets are clipping windows, not object owners;
- local Y is `global_y - window_start`;
- an object is never deleted or opacity-faded merely because its center crosses a local SVG edge;
- partial circle/tail geometry remains visible while it intersects a viewport;
- separate SVG documents still do **not** prove one shared runtime clock;
- repeated / paired physical assets that show one logical window use the same logical trajectory grammar but remain independent runtime documents.

For the character stage, left and right side SVGs are two physical viewports over the same logical `character` time span. Each only draws its own rail-side objects; the central third-party image stays untouched.

## Background illusion

The 900 px stages fade their outer surface toward GitHub dark `#0d1117`, while inner areas use the seasonal envelope palette. This reduces the perception of a hard image slab and makes foreground media read as mounted on a continuous background.

The effect is optimized for GitHub Dark. Light-theme equivalence is not claimed.

## Promotion gates

Do not promote v7 live until all are true:

- source XML/JSON validation passes;
- generated Projects and Activity panels match the current authoritative source blobs;
- attribution contains no client-font-dependent `<text>`;
- character remains a normal external README image, not a copied asset;
- desktop/mobile target render has no destructive wrap or overflow;
- no excessive vertical host gap breaks the continuous-canvas illusion;
- all rendered v7 windows use the same global coordinate specification;
- reduced-motion/static composition remains complete;
- actual target playback is re-earned after promotion rather than inherited from v6.
