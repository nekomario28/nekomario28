# Envelope v5 live evidence — 2026-08-24

## Decision

Envelope v5 `continuous-segmented-flow` is the live README-area pseudo-overlay. It strengthens the v4 enclosure with a Hero top cap, Footer bottom cap, shared rails at x=18 / x=882, and sparse top-to-bottom rail pulses while leaving factual README content and links independent from the decorative frame.

This is **not** a GitHub page-wide overlay. GitHub-owned avatar/sidebar/page chrome/pinned repository UI remain outside README authority.

## Live implementation

- profile PR: `nekomario28/nekomario28#34`
- live merge: `1e14ea1d4541420dbb95a6141c23a8d9df6996b6`
- manifest version: 6
- envelope version: 5
- frame mode: `continuous-segmented-flow`
- motion handoff: `phase-tolerant-segmented-handoff`
- rail coordinates: x=18 / x=882 in 900-wide SVG assets
- common rail pulse duration: 12s
- cross-document hard synchronization: **false**
- static fallback: enabled
- reduced motion: enabled

Separate README `<img>` SVGs are independent documents. Equal durations do not establish a shared runtime clock. v5 therefore repeats the same coordinates, direction, duration, pulse spacing, and low-density motion grammar so phase drift does not make adjacent segments look contradictory.

## Four-season validation

- initial v5 run `32710254375`: **SUCCESS**
- proof-head v5 run `32710456884`: **SUCCESS**
- all Spring/Summer/Autumn/Winter candidates generated and checked for canonical geometry, v5 frame marker, 12s rail flow, reduced-motion behavior, no script, shared rail positions, and vector-outline section labels
- five-asset seasonal promotion remains atomic: Hero + bridge + Projects + Activity + Footer

## GitHub branch README render proof

- run `32710456838`: **SUCCESS**
- artifact `envelope-v5-github-render-proof`
- artifact id `9513875708`
- desktop dark captures at virtual-time 2s and 8s
- mobile dark capture at 430px / 8s
- no observed horizontal overflow or table-style center compression
- time-separated captures show visible SVG motion in the README area

The first proof attempt `32710329752` failed after creating its screenshots because Pillow was absent on the runner. The implementation validation was already GREEN; the proof path was made dependency-free and rerun successfully. This is infrastructure/proof negative evidence, not an Envelope v5 failure.

## Actual public profile playback proof

One-shot read-only proof PR `#35` captured the actual public profile `https://github.com/nekomario28` after the v5 merge.

- proof PR: `nekomario28/nekomario28#35` — closed unmerged
- proof head: `0936b9f5670a6353383fde92d8fd0aa6064b6063`
- workflow run `32711023842`: **SUCCESS**
- artifact `envelope-v5-public-profile-proof`
- artifact id `9514071223`
- desktop dark: virtual-time 2s and 8s
- mobile dark: 430px / 8s

Observed target-surface evidence:

- the live public profile renders the v5 Hero top cap, shared segmented rails, bridge transitions, section bands, and Footer bottom cap;
- mobile showed no observed horizontal overflow or host-table-style center compression;
- the 2s/8s desktop diff was bounded to the README visual region (`bbox=(471, 228, 1326, 2284)`), not the entire GitHub page chrome;
- changed pixels occur in the expected left/right rail strips across multiple vertical sections, in addition to the existing Summer Hero motion and dynamic project-map content;
- therefore Summer embedded SVG/SMIL motion is visibly progressing on the **actual public GitHub profile surface in the tested headless Chrome environment**.

Accordingly, Summer `motion.live_verification` is promoted from `NOT_RUN` to `PASS`. Spring, Autumn, and Winter remain `NOT_RUN` until each is observed live after promotion.

## Evidence boundary

`PASS` here means target-surface playback was observed in the tested GitHub/headless-Chrome environment. It does not guarantee identical playback in every browser/client, and a user requesting reduced motion is expected to see the static fallback instead.

The separate SVG assets still do not share a guaranteed clock. The correct claim is **phase-tolerant visual handoff**, not perfect/hard synchronization.

## Reusable lessons

1. For animation that should appear to cross separately embedded README SVGs, do not promise perfect synchronization from equal durations alone.
2. Use phase-tolerant handoff: repeat spatial rails, direction, duration class, pulse spacing, entry/exit behavior, and sparse density across segments.
3. Keep top/bottom caps and shared rails removable from factual content authority; the envelope must remain decorative chrome.
4. Verify playback with time-separated target-surface captures, then localize the changed region because host/dynamic content can also change between captures.
5. Scope playback PASS to the actually tested season/surface/environment; do not automatically transfer it to future seasonal variants.
6. Keep static/reduced-motion composition authoritative even after live playback is proven.
