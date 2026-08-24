# Envelope v6 branch evidence — 2026-08-24

## Decision target

Envelope v6 replaces segment-local rail-pulse ownership with one logical global motion field. Each participating SVG is a clipping window into that field.

The implementation is intended to remove the visible failure mode where a moving object appears to die as soon as its center reaches an SVG edge.

## Implementation identity

Profile PR: `nekomario28/nekomario28#37`

Authority:

- `design-lab/envelope-v6/SPEC.md`
- `design-lab/envelope-v6/global-motion-space.json`
- `design-lab/scripts/render_global_motion.py`
- `design-lab/scripts/promote-season.py`

Core model:

```text
local_y(t) = global_y(t) - window_start
```

The same logical trajectory is embedded in every participating asset. Each local SVG clips that trajectory to its viewport and does not own a separate edge-triggered opacity lifecycle.

## Global space

- coordinate system: `profile-envelope-logical-y-v1`
- global extent: 1868 logical units
- bleed: 24
- rail x: 18 / 882
- duration: 36s
- direction: top to bottom
- global field particles: 6 sparse pulses
- each pulse: leading circle + short trailing line
- cross-document hard synchronization: false

Three bridge occurrences are separate stable files because one reused SVG cannot represent three different global windows:

- character -> Projects: start 765
- Project Map -> Activity: start 1360
- Contributions -> Footer: start 1744

## Four-season validation

PR head validation run `32726860050` / job `97429997350`: **SUCCESS**.

Validated for Spring, Summer, Autumn and Winter:

- manifest v7 and complete month partition;
- seven-asset live set;
- global-space partition and visible-window heights;
- three distinct bridge global starts;
- exact per-window global translate values;
- 36s common global travel;
- explicit `v6-window` clipping;
- no v6 boundary opacity animation;
- reduced-motion fallback;
- no script/JavaScript;
- repository-owned vector-outline Japanese section labels;
- Hero top cap / Footer bottom cap;
- dry-run seasonal promotion;
- stable Summer preview matching the renderer.

Additional successful seasonal runs included `32727489372` and final clean-head run `32727783004`.

## Branch layout proof

Run `32727489379` captured the branch README in dark desktop/mobile and confirmed layout usability without table-style center compression or observed horizontal overflow.

### Correction to the original boundary-playback interpretation

The same run also produced direct raw-SVG screenshots using separate Chrome invocations with `--virtual-time-budget`. Later re-analysis showed those direct bridge screenshots were byte-identical across the requested virtual times. Therefore they **must not** be treated as proof that the pulse visibly crossed the local boundary.

The previous text that described those images as showing a circle/tail progression was an over-interpretation and is superseded by this correction.

What remains valid from source/CI inspection is the deterministic geometry rule:

- the v6 particle is represented by a circle plus trailing line;
- no local boundary opacity animation exists;
- every window uses explicit clipping;
- the global trajectory is translated by that window's `window_start`;
- therefore geometry that still intersects a window is eligible to render even after the leading center has crossed the edge.

This geometry property is distinct from target-surface playback evidence.

## Public-profile playback evidence

Public playback is recorded separately in `design-lab/envelope-v6/live-evidence-2026-08-24.md`.

A persistent-browser proof on the actual public profile was required because restarting Chrome for every timestamp resets or obscures the relevant timeline.

## Evidence boundary

Established:

- deterministic global-coordinate/windowed renderer;
- local boundary opacity lifecycle removed;
- partial geometry is represented by clip-based intersection rather than edge-triggered deletion logic;
- three repeated bridge positions have distinct global windows;
- all four seasonal variants generate and validate;
- dark desktop/mobile layout remains usable;
- Summer public-profile v6 playback is separately observed and PASS.

Not claimed:

- frame-perfect synchronization between independent SVG documents;
- a shared runtime clock across README `<img>` documents;
- Spring/Autumn/Winter public playback before those variants are actually observed live.

The temporary proof workflows were evidence tooling only and are not part of the Envelope v6 product/runtime surface.
