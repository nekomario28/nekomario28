# Envelope v9 portable donor

Status: **Design Lab only / not live / P3 local-render PASS / public GitHub profile NOT_RUN**

Envelope v9 applies the portable profile-surface contract to the proven Envelope v8 donor without changing the current direct-IPM public profile.

## Scope

v9 implements the bounded contract surface:

- `profile.background = opaque | transparent`;
- `profile.text = safe | native | minimal`;
- `profile.motion = on | off`;
- mounted-source background `inherit | preserve`;
- frame `rail | none` and `outer-only | none` caps;
- label density `auto | full | minimal`;
- existing packing and external-media contract values are preserved for the target adapter.

This is not a new public API yet. The public contract remains `design-lab/profile-envelope-config.schema.json`; v9 is one donor implementation used to discover whether that contract is actually sufficient.

## Text policy

### safe

All supported visible SVG `<text>` nodes in repository-owned generated presentation assets are replaced with deterministic repository-owned vector strokes. No font file is embedded, copied or distributed. Unsupported visible glyphs fail closed instead of silently falling back to tofu/missing-glyph boxes.

The exact original string remains textual accessibility metadata inside the replacement group. Existing `<title>`, `<desc>` and other semantic metadata are not converted.

For a transparent outer surface, safe vector text uses `currentColor` with explicit `prefers-color-scheme` light/dark rules. P3 Chrome evidence verifies the resulting computed stroke and contrast instead of assuming the media query works from source inspection alone.

### native

Visible SVG `<text>` remains unchanged. This is the compact/host-native choice, but it is explicitly host-font-dependent and cannot earn a font-independent `TEXT PASS`.

### minimal

Essential/fixed visible text is vectorized, while visible dynamic labels in mounted Project Map and Activity content are suppressed. Semantic source data and accessibility metadata remain present. This mode is intended for dense or highly portable surfaces where the map/chart still communicates through geometry and accessible metadata.

`labels.density=minimal` also suppresses mounted dynamic visible labels independently of the selected text mode.

## Transparency policy

Outer surface transparency and mounted-source opacity are independent:

- `background=transparent` removes the v8 envelope-owned surface base;
- `mounted_source_background=inherit` keeps the v8 behavior that exposes the common envelope surface through known Project Map/Activity presentation backgrounds;
- `mounted_source_background=preserve` keeps those mounted source backgrounds intact.

Therefore transparent+preserve may intentionally produce opaque islands. The P1 contract resolver warns about that combination rather than silently changing it.

P3 verifies transparent safe output in Chrome at desktop/mobile widths and both light/dark host appearances. Screenshot corner pixels must expose the host background rather than merely omitting a source `<rect>`.

## Render-target identity

The normalized config fingerprint is not sufficient evidence identity because renderer/source changes can alter output without changing config.

v9 therefore derives one `data-profile-render-target-sha256` from:

- normalized contract identity;
- selected season;
- SHA-256 of every transformed generated SVG before the target marker is inserted.

The same target fingerprint is embedded into every generated SVG. Re-rendering the same target must reproduce the fingerprint; materially different tested configurations must produce distinct fingerprints. Browser and playback proof are bound to this rendered-target identity.

## Motion and frame

`motion=off` removes SMIL timing elements from the generated donor output, leaving the static-first composition.

`frame.mode=none` removes the v8 frame layer. `frame.caps=none` keeps straight through-rails but removes the outer-end cap geometry.

For motion-on, v9 preserves the inherited v8/v7 `.v7-motion` subtree exactly. P3 verifies actual playback using the same evidence shape as the accepted v8 public proof: persistent Chrome, real elapsed time, narrow rail-strip screenshots and localized pixel diffs. Reduced motion is applied browser-wide at Chrome startup so external SVG image documents receive the user preference; parent-page-only CDP media emulation is not accepted as equivalent evidence.

## P3 evidence boundary

See `EVIDENCE.md` for exact runs and negative proof lineage.

Established for the local generated render target:

- deterministic/target-sensitive render fingerprint;
- safe/native/minimal structural behavior;
- transparent/opaque and mounted-background separation;
- light/dark adaptive safe text in real Chrome;
- desktop/mobile rendered geometry for the tested hero cases;
- screenshot-backed transparent host-background exposure;
- dynamic Projects safe/minimal behavior;
- local isolated rail playback;
- reduced-motion silence;
- motion-off silence;
- exact v8-to-v9 inherited motion-subtree equivalence.

Not established:

- that v9 is mounted on the public GitHub profile;
- public GitHub v9 playback;
- cross-document hard clock synchronization or frame-perfect handoff;
- broad typography-quality equivalence to a conventional font face;
- a second independent consumer proving standalone public-repository extraction is worthwhile.

## Why this shape is portable

The adapter imports the existing v8 donor but does not put the donor username, IPM taxonomy or GitHub write credentials into the portable contract. The deterministic text primitive is font-file-free and renderer-local. Contract normalization remains separate from rendering, and publication authority remains outside the renderer.

That preserves the IPM lessons: small bounded inputs, read-only generation, semantic/presentation separation, source provenance, exact evidence identity, bounded browser proof, and no premature universal IR.
