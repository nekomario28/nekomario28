# Envelope v6 live evidence — 2026-08-24

## Decision

Envelope v6 `global-windowed-flow` is live on the actual public profile and Summer playback is **PASS** for the tested GitHub/headless-Chrome environment.

This PASS is scoped to Summer and to the tested target surface. It is not automatically transferred to Spring, Autumn or Winter.

## Live implementation

- profile merge: `1a2eb9a82ac67b04662b2bbc45477278f3414e32`
- envelope version: 6
- global motion authority: `design-lab/envelope-v6/global-motion-space.json`
- visible assets: Hero + 3 unique bridge windows + Projects + Activity + Footer
- shared rail x: 18 / 882
- global duration: 36s
- cross-document hard synchronization: false
- reduced-motion/static fallback: enabled

## Public-profile proof

One-shot proof PR `#38` used one persistent Chrome page against `https://github.com/nekomario28`.

Final successful run:

- run: `32731491688`
- job: `97444494630`
- result: **SUCCESS**
- actual first-bridge DOM source: `.../raw/main/assets/profile-frame-bridge-character-projects.svg`
- rendered bridge size on desktop: approximately 846 × 30 CSS px

The proof sampled that same live bridge every 0.25 seconds for 7 seconds without reloading the page.

Observed adjacent-frame changes included:

- sample 6 -> 7: 17 changed pixels, bbox `(15, 0, 19, 6)`
- sample 7 -> 8: 45 changed pixels, bbox `(15, 0, 19, 18)`
- sample 8 -> 9: 52 changed pixels, bbox `(15, 7, 19, 30)`
- sample 9 -> 10: 24 changed pixels, bbox `(15, 20, 19, 30)`

Those bboxes stay in the expected left-rail strip and move from the upper edge toward the lower edge across consecutive samples. This is direct target-surface evidence that the v6 bridge rail animation is progressing on the public GitHub profile.

A large sample 2 -> 3 full-bridge diff was also observed (`21822` changed pixels across the bridge rectangle) and is retained as evidence, but the narrow sequential left-rail bboxes above are the cleaner v6 motion signal.

## Why this proof supersedes earlier attempts

Earlier proof attempts restarted Chrome for every requested timestamp or used `--virtual-time-budget`. Re-analysis showed the direct raw-bridge screenshots from that method were byte-identical, so they are not valid boundary-playback evidence.

The final proof keeps one browser/page alive and samples the same displayed bridge over wall-clock time. That is the correct target-surface playback test for this environment.

## Boundary model

Playback PASS and boundary-geometry correctness are separate claims.

The renderer/CI establishes that:

- each asset is a window into one logical global trajectory;
- local y is derived from global y minus window start;
- no local edge-triggered opacity fade exists;
- circle and tail geometry are clipped by the viewport;
- three bridge occurrences have distinct global starts.

Therefore v6 no longer owns an object lifecycle at each segment edge. A local SVG only decides which part of the global object intersects its window.

This does not imply a shared runtime clock between separate SVG documents.

## Mobile/layout

The proof also captured the public profile at a 430px mobile viewport. The v6 structure remains usable without the table-style center compression that caused the earlier literal-table enclosure candidate to be rejected.

## Remaining evidence boundary

- Summer public playback: **PASS**
- Spring public playback: `NOT_RUN`
- Autumn public playback: `NOT_RUN`
- Winter public playback: `NOT_RUN`
- frame-perfect cross-document synchronization: **not claimed**
- true overlay outside the README rendering area: **not possible / not claimed**
