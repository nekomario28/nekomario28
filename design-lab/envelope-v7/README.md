# Envelope v7 — continuous canvas experiment

Goal: make the README read as one dark surface with foreground media mounted on top, including the left/right areas around narrower real content.

This is an experimental branch surface, not the live authority. Live remains Envelope v6 until v7 earns target-render and playback evidence.

## Current candidate — Hybrid C

Hybrid C combines two techniques instead of forcing one container model onto every source.

### Third-party character media

The official character image remains a normal external README `<img>` and is not copied into the repository. It is flanked by repository-owned surfaces on the same row:

- left surface: `11.111%` (source width 100);
- character image: `77.778%` (source width 700);
- right surface: `11.111%` (source width 100).

All three sources use the same 394 px source height and adjacent markup without whitespace. This is intended to scale the complete row proportionally on narrow layouts while preserving the external image as the foreground authority.

### Repository-owned Projects / Activity media

The actual checked-in SVG body is embedded directly into one generated 900 px SVG stage:

- Projects: `80 + 740 + 80`, height 420;
- Activity: `70 + 760 + 70`, height 220.

The center data is not mocked. `render_panels.py` regenerates each stage from the current `project-map/galaxy.svg` and `assets/github-contributions-dark.svg` sources. Stale composite output is a promotion blocker.

### Attribution

The rights line is a dedicated 900 px background band whose visible glyphs are vector outlines. Essential Japanese text therefore does not depend on fonts installed on the GitHub rendering client. The accessible rights string remains in `aria-label`/README alt text.

## Continuous background

Every outer stage fades toward GitHub Dark `#0d1117` at the canvas edge and toward the active seasonal palette near mounted foreground media. Shared rails stay at logical x = 18 / 882.

The full v7 canvas is specified in `SPEC.md` and `global-motion-space.json`:

`Hero → Character → Attribution → bridge → Projects → Projects canvas → bridge → Activity → Activity canvas → bridge → Footer`

All logical spans are now rendered. The v6 invisible character/map/contribution gaps are removed from the logical model.

## Motion

`render_continuous_canvas.py` extends the v6 clipping-window rule to all v7 surfaces.

- one logical global Y field;
- local Y = global Y − window start;
- no edge-triggered object deletion/fade;
- partial tail/circle geometry exits through normal clipping;
- character left/right surfaces are two physical views over the same logical Character window;
- the right global rail x=882 maps to local x=82 inside the 100 px right surface;
- no shared runtime clock is claimed between independent SVG documents.

The total v7 logical extent is 1662 px and the current common travel duration is 32 s.

## Earlier candidates retained as evidence

### Candidate A — three-piece rows everywhere

Used side SVG + real center image/SVG + side SVG for Character, Projects and Activity. This preserved source independence but created unnecessary responsive/wrapping risk for repository-owned SVG content. The side assets remain in Design Lab as lineage, but Projects/Activity no longer use this model.

### Candidate B — composite everything

Generated 900 px composite SVGs for all major foregrounds. This is good for repository-owned SVGs, but the Character panel nested a cross-origin remote image inside repository SVG content. That creates a target security/CSP portability boundary and is not the promotion path. `character-panel.svg` remains negative/alternate evidence only.

## Proof-environment history

Several one-shot target proof attempts failed before reaching a valid layout judgment:

- GitHub-hosted proof: Chrome CDP failed to start in one run;
- later target-repo workflows required action approval;
- self-hosted carrier lacked proof Python packages, then hit PEP 668, then succeeded with an isolated venv but had no Chrome;
- private hosted fallback failed before executable proof steps.

These are proof-environment failures and must not be counted as positive or negative v7 visual evidence.

## Promotion gates

- branch/current-source XML and JSON validity;
- renderer syntax and deterministic generation for all four seasons;
- Projects/Activity composite source freshness;
- no `<text>` in essential attribution asset;
- external Character image remains normal HTML media and rights attribution remains visible;
- desktop target render without overflow or destructive stage gaps;
- 430 px target render without wrap/compression failure;
- v7 global windows cover the full 1662 px logical extent;
- reduced-motion/static fallback remains complete;
- public playback PASS is re-earned after live promotion and is not inherited from v6.
