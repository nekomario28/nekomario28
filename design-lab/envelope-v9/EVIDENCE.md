# Envelope v9 evidence

Status: **Design Lab only / local render-target P3 PASS / public GitHub profile NOT_RUN**

Envelope v9 remains a donor/portability experiment. The current public profile remains the direct-IPM surface. No v9 asset is promoted live by this work.

## P2 baseline

Envelope v9 P2 was merged by PR #56 as `ed11b1c01ed3506e1bb6d16563ba014da962681e`.

P2 established bounded configuration and structural generation for:

- `safe | native | minimal` text;
- `opaque | transparent` outer background;
- mounted-source `inherit | preserve` background;
- motion/frame/cap controls;
- font-file-free deterministic vector text;
- fail-closed unsupported glyphs.

P2 did not establish rendered typography, light/dark transparent behavior or playback.

## P3 render-target identity

PR #59 adds a rendered-target receipt that is stronger than config identity alone.

The target SHA-256 is derived from:

- normalized portable-contract SHA-256;
- season;
- SHA-256 of every transformed generated SVG before inserting the target marker.

The same `data-profile-render-target-sha256` is embedded into every generated SVG. Structural validation requires:

- repeat generation of an identical target -> identical target fingerprint;
- five materially different tested configurations -> five different target fingerprints;
- every generated asset -> same target fingerprint for one render.

This means browser/playback evidence can be bound to actual generated target bytes rather than surviving a renderer/source change merely because the config did not change.

## P3 rendered browser matrix

Accepted pre-clean proof lineage:

- exact head `1bfd628bbbf5538af06f44a15e99f1fe209ac342`;
- run `32771366221`;
- job `97572238941`;
- runner: Ubuntu 24.04 / `ubuntu-24.04` image `20260816.277.1`;
- Chrome: runner-provided `/usr/bin/google-chrome`.

Structure output:

- `ENVELOPE_V9_PORTABLE_STRUCTURE_PASS cases=5 text=safe/native/minimal background=opaque/transparent mounted=inherit/preserve`;
- `RENDER_TARGET_FINGERPRINT=PASS deterministic=true target_sensitive=true`.

Rendered browser output:

- `ENVELOPE_V9_BROWSER_MATRIX_PASS cases=9 schemes=light/dark widths=desktop/mobile surfaces=hero/projects`;
- `TARGET_LAYOUT=PASS`;
- `TEXT_RENDER=PASS`;
- `TRANSPARENCY_RENDER=PASS`;
- `NATIVE_RENDER=OBSERVED`;
- `MINIMAL_DYNAMIC_TEXT=PASS`.

The nine browser cases cover:

1. transparent-safe hero / light / desktop 846px;
2. transparent-safe hero / light / mobile 390px;
3. transparent-safe hero / dark / desktop 846px;
4. transparent-safe hero / dark / mobile 390px;
5. transparent-safe Projects canvas / light;
6. transparent-safe Projects canvas / dark;
7. transparent-native hero / light;
8. transparent-minimal Projects canvas / light;
9. opaque-safe hero / dark.

Assertions include:

- actual `prefers-color-scheme` state in Chrome;
- generated root width after host scaling;
- no surviving visible `<text>` in safe mode;
- vector glyph finite geometry and no hero overflow in tested desktop/mobile widths;
- adaptive safe-text computed stroke approximately `rgb(31,35,40)` on light and `rgb(240,246,252)` on dark;
- contrast ratio >= 12 against GitHub-like host backgrounds;
- screenshot corner pixel equals the host background for transparent cases;
- native mode retains visible SVG text and explicitly remains host-font-dependent;
- minimal Projects removes dynamic visible labels while preserving semantic `<title>/<desc>` metadata;
- opaque safe does not expose a sentinel host background.

## P3 local playback / reduced motion

Accepted pre-clean proof lineage uses the same exact head/run/job above.

Rendered motion output:

- render target `b066530383868472d10bf7389f3c45b226dad870383bea14db6fd868d1b41482`;
- exact v8->v9 `.v7-motion` subtree equivalence: **15 generated assets**;
- normal motion-on: 6.0s, 0.5s interval, 13 samples;
  - left character rail changed adjacent pairs: **7**;
  - right character rail changed adjacent pairs: **12**;
- browser-wide reduced motion: 3.0s, 0.5s interval, 7 samples;
  - left: **0**;
  - right: **0**;
- motion-off: 3.0s, 0.5s interval, 7 samples;
  - left: **0**;
  - right: **0**.

Accepted output:

- `LOCAL_RENDER_TARGET_PLAYBACK=PASS`;
- `REDUCED_MOTION=PASS`;
- `MOTION_OFF=PASS`;
- `V8_PUBLIC_PLAYBACK_INHERITANCE=BOUNDED motion_subtree_equivalent=true`;
- `PUBLIC_GITHUB_PROFILE=NOT_RUN`.

The character-side surfaces are used because they isolate the inherited rail motion from seasonal hero animation, Project Map motion and contribution-chart foreground behavior.

## Negative proof lineage retained

### Async `--dump-dom` browser probe

An earlier P3 browser attempt failed because asynchronous fetch/measurement had not populated its `<pre>` receipt before `--dump-dom` serialized the page. Structure validation had passed, but no render result had been measured. This is a **proof-harness failure**, not product evidence.

Repair: embed generated SVG synchronously for DOM metrics and use real Chrome screenshots for pixel-level transparency proof.

### `SVGSVGElement.setCurrentTime()` + `getCTM()`

An earlier motion attempt observed:

- `prefers-reduced-motion: no-preference=true`;
- `.v7-motion` visible;
- six motion timing elements present;
- but `setCurrentTime(0)` versus `setCurrentTime(4)` produced no `getCTM()` delta in the inline-HTML harness.

This was not generalized into “playback is broken”. The method was replaced with the known-good v8 evidence shape: persistent page + real elapsed time + screenshot pixel diffs.

### Parent-target CDP reduced-motion emulation

A later real-time attempt set `prefers-reduced-motion=reduce` through CDP on the top-level page. The top-level `matchMedia` reported reduce, but external SVG `<img>` documents still animated:

- left rail: 4 changed pairs;
- right rail: 6 changed pairs.

This was retained as a harness-scope diagnostic. It did not prove the SVG's reduced-motion CSS was broken because the emulation applied to the page target did not establish propagation into separately decoded SVG image documents.

Repair: launch a separate Chrome process with browser-wide `--force-prefers-reduced-motion`. Under that user preference the same external SVG image surfaces produced **0 / 0** rail changes, while normal mode produced **7 / 12**.

## Relationship to v8 public evidence

Envelope v8 already has actual-public-profile rail playback evidence in its own `EVIDENCE.md`: 8 non-hero documents / 14 rail strips on `https://github.com/nekomario28`, with no cross-document hard-sync claim.

v9 does **not** inherit that result wholesale. P3 proves only:

- its inherited `.v7-motion` subtrees are exact-equivalent to v8 across the generated target;
- the local v9 render target actually plays in Chrome;
- browser-wide reduced motion silences the isolated external SVG rails;
- motion-off is static.

A public v9 playback claim would still require v9 to be intentionally mounted on a stable public target and separately observed there.

## Claim boundary

Established:

- deterministic target-sensitive generated-output fingerprint;
- local Chrome light/dark and desktop/mobile rendering for the tested matrix;
- font-independent safe visible text for supported glyphs;
- screenshot-backed transparent host-background exposure;
- local isolated v9 rail playback;
- browser-wide reduced-motion silence;
- motion-off silence;
- exact inherited motion-subtree equivalence to v8.

Not established:

- v9 is live;
- public GitHub profile v9 playback;
- shared runtime clocks across SVG documents;
- frame-perfect cross-document synchronization;
- universal typography quality for every future glyph/data density;
- a second independent consumer justifying standalone executable extraction.

## Next safe action

Keep v9 Design-Lab-only while the current profile remains direct IPM. Rebase/clean the P3 change onto current main, require one final exact-head CI run, and merge the evidence/tooling without live promotion. After that, update the existing project-incubator portability backflow with the new render-target/browser-proof lessons; do not create a new Skill or standalone public repository until an independent consumer or discriminating Skill eval justifies promotion.
