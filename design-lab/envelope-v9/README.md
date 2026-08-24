# Envelope v9 portable donor

Status: **Design Lab only / not live / P2 donor implementation**

Envelope v9 applies the portable profile-surface contract to the proven Envelope v8 donor without changing the current direct-IPM public profile.

## Scope

v9 intentionally implements the small contract surface first:

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

All simple visible SVG `<text>` nodes in repository-owned generated presentation assets are replaced with deterministic repository-owned vector strokes. No font file is embedded, copied or distributed. Unsupported visible glyphs fail closed instead of silently falling back to tofu/missing-glyph boxes.

The exact original string remains textual accessibility metadata inside the replacement group. Existing `<title>`, `<desc>` and other semantic metadata are not converted.

The current primitive is deliberately small and utilitarian. It proves host-font independence; it is not yet a typography-quality claim. Browser readability and dense-label quality remain `TEXT_RENDER=NOT_RUN` until target evidence exists.

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

Transparent output requires later target proof on GitHub light and dark appearances at desktop and mobile widths.

## Motion and frame

`motion=off` removes SMIL timing elements from the generated donor output, leaving the static-first composition.

`frame.mode=none` removes the v8 frame layer. `frame.caps=none` keeps straight through-rails but removes the outer-end cap geometry.

## Evidence boundary

`validate.py` currently proves only deterministic generation/structure policy:

- safe/native/minimal transformations;
- opaque/transparent surface policy;
- inherit/preserve mounted-background separation;
- motion-off static structure;
- normalized contract fingerprint embedded into every generated SVG;
- XML parseability and expected role markers.

It deliberately reports:

- `TARGET_LAYOUT=NOT_RUN`;
- `TEXT_RENDER=NOT_RUN`;
- `PLAYBACK=NOT_RUN`.

A later P3 browser matrix must prove actual typography/readability, transparent light/dark contrast, desktop/mobile layout, dense-label behavior, motion and reduced-motion before v9 can be considered a release candidate.

## Why this shape is portable

The adapter imports the existing v8 donor but does not put the donor username, IPM taxonomy or GitHub write credentials into the portable contract. The new deterministic text primitive is font-file-free and renderer-local. Contract normalization remains separate from rendering, and publication authority remains outside the renderer.

That preserves the IPM lessons: small bounded inputs, read-only generation, semantic/presentation separation, source provenance, exact evidence identity, and no premature universal IR.
