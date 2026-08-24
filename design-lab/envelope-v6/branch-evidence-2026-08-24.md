# Envelope v6 branch evidence — 2026-08-24

## Decision target

Envelope v6 replaces segment-local rail-pulse ownership with one logical global motion field. Each participating SVG is a clipping window into that field.

The implementation is specifically intended to remove the visible failure mode where a moving object appears to die as soon as its center reaches an SVG edge.

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

The same global trajectory is embedded in every participating asset. The local viewport uses an explicit clip path and does not own a separate boundary-fade lifecycle.

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

A later proof-head seasonal run `32727489372` also completed successfully while the temporary render proof was present.

## GitHub branch render proof

Proof run `32727489379`: **SUCCESS**.

Artifact:

- name: `envelope-v6-render-proof`
- artifact id: `9520079458`

Target branch README:

- desktop dark 1440px capture: PASS for layout
- mobile dark 430px capture: PASS for layout
- no observed table-style center compression or horizontal overflow

The full branch README screenshots were not used alone to claim the rail boundary behavior because the small rail pulse was not cleanly discriminated at the chosen full-page timestamp.

## Direct boundary clipping proof

The same proof run also rendered the first repository-owned v6 bridge SVG directly through headless Chrome from the GitHub raw branch URL.

The first primary pulse traverses the first bridge window around 14.82s-15.42s under the frozen 36s/global-extent contract.

Observed frames:

- `bridge-t14.80.png`: the leading circle is partially visible at the top edge;
- `bridge-t15.42.png`: the pulse reaches the lower boundary;
- `bridge-t15.50.png`: the center has crossed beyond the 32px viewport but a portion of the 13px trailing line still intersects the bottom of the clipping window;
- `bridge-t15.70.png`: the trailing geometry has also left and the pulse is no longer visible.

Pixel inspection around the left rail confirms motion in the expected x=18 strip. Between 15.42s and 15.50s changed pixels remain in the lower boundary region even after the leading center has moved outside the local window.

This proves the intended local boundary rule:

> the object is not deleted or faded when its center crosses the edge; the global trajectory continues, and the SVG draws only the geometry that still intersects its clipping window.

It does **not** prove a shared clock between separate README SVG documents.

## Evidence boundary

Established:

- global-coordinate/windowed renderer exists and is deterministic;
- local boundary fade has been removed from the v6 rail field;
- partial overrun geometry is rendered through clipping;
- three repeated bridge positions have distinct global windows;
- all four seasonal variants generate and validate;
- dark desktop/mobile branch layout remains usable.

Still not established until live promotion:

- Summer v6 playback on the actual public profile surface;
- frame-perfect cross-document synchronization (not claimed and not required);
- Spring/Autumn/Winter live playback.

Summer `live_verification` therefore remains `NOT_RUN` until a post-merge public-profile proof is captured.

The temporary branch render-proof workflow was removed before the final clean-head validation; it is evidence tooling only and is not part of the Envelope v6 product/runtime surface.
