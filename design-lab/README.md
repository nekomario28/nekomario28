# Profile Design Lab

Experimental visual directions and reusable-contract work for the `nekomario28` GitHub profile.

## Current authority

The **live profile is currently the direct IPM surface**, not Envelope v8. The root README owns the live composition and references:

- `assets/sakura-profile-hero.svg`;
- the external character image by reference;
- `project-map/galaxy.svg` generated from Interactive Project Map;
- `assets/github-contributions-dark.svg`.

Envelope v4-v8 remains in this Design Lab as donor implementation/evidence. It must not be described as live unless the root README is explicitly promoted back to an Envelope presentation.

This separation is intentional: the live profile can stay simple while the reusable profile-surface contract is designed, validated, and later extracted without silently changing the public page.

## Active reusable work

The current reusable boundary is documented in:

- `profile-envelope-portability.md` — architecture, IPM lessons, failure lineage, migration phases and evidence contract;
- `profile-envelope-config.schema.json` — bounded public configuration schema;
- `profile-envelope-config.example.json` — opaque + safe-text example;
- `profile-envelope-config.transparent.example.json` — transparent + safe-text example;
- `scripts/profile_envelope_contract.py` — dependency-free contract normalizer/resolver.

The normalizer turns the small user-facing config into explicit internal policy:

- visible fixed text vs dynamic data labels vs accessibility metadata;
- host-font independence requirements;
- opaque vs transparent host participation;
- required desktop/mobile/light/dark verification cases;
- motion/static proof requirements;
- publication authority/source-provenance invariants;
- a deterministic normalized-contract SHA-256 for evidence binding.

This is **P1 contract extraction**, not a public API or a live-profile renderer yet.

## Current live text audit

The current direct profile still has visible client-font dependencies:

- `assets/sakura-profile-hero.svg` renders the visible `nekomario28` handle with SVG `<text>` and a system-font stack;
- `project-map/galaxy.svg` is a dynamic IPM projection whose repository/category/legend labels are generator-owned visible text;
- `assets/github-contributions-dark.svg` uses SVG `<text>` for its heading, total, y-axis values and dates.

Accessibility `<title>` / `<desc>` metadata is a separate role and should remain textual even when visible glyphs become deterministic outlines.

Do not treat every visible text defect as one failure class. Missing glyphs, host-font metric drift, dense-label overlap, clipping and insufficient contrast require different remedies. The portable contract therefore exposes `profile.text = safe | native | minimal` rather than one global “convert all text” switch.

### Text modes

`safe`
: Essential fixed UI text is deterministic and font-independent. Dynamic labels use a deterministic vector/fallback policy where available; when density is too high, reduce visible labels without removing semantic repositories/data. This mode can earn a font-independent `TEXT PASS`.

`native`
: Visible SVG `<text>` is allowed. Smaller output is possible, but the result is deliberately host-font-dependent and cannot be reported as font-independent `TEXT PASS`.

`minimal`
: Essential fixed text remains deterministic, while non-essential dynamic visible labels may be suppressed. Semantic data and accessibility metadata remain present.

The first portable implementation should prefer small deterministic glyph strategies and pre-outlined fixed labels over shipping font files or introducing a large typography runtime solely for a README surface.

## Transparency is two independent decisions

`profile.background = opaque | transparent` controls only the envelope-owned outer surface.

`surface.mounted_source_background = inherit | preserve` controls whether a known presentation background inside mounted Project Map/Activity content is removed or kept.

These must not be merged into one switch. A transparent outer surface with preserved mounted-source backgrounds is valid but may create opaque islands and therefore receives an explicit warning from the contract resolver.

Transparent mode requires actual target proof on both GitHub light and dark appearances. Opaque dark-first output does not inherit that requirement merely because transparent mode exists.

## Recommended bounded public controls

Keep the first public API deliberately small:

```yaml
profile:
  theme: seasonal-dark
  background: opaque        # opaque | transparent
  text: safe                # safe | native | minimal
  motion: on                # on | off
```

Advanced/internal policy may additionally expose:

- mounted source background: `inherit | preserve`;
- frame: `rail | none`, outer caps only;
- label density: `auto | full | minimal`;
- packing: `auto | off`;
- external media: `reference-only | none`.

Do not add speed sliders, particle counts, arbitrary animation timelines, a style DSL, installer/app infrastructure, or a universal rendering IR until a real second consumer demonstrates the need.

## IPM lessons carried forward

The future public profile-surface repository should intentionally preserve the parts of Interactive Project Map that worked:

- static-first, user-owned checked-in/generated artifacts;
- one canonical semantic model with separate visual projections;
- small bounded public inputs and safe defaults;
- risky/heavier optional behavior default-off;
- read-only generation separated from write publication;
- stable release channel plus exact implementation/evidence identity;
- real browser target gates rather than syntax-only claims;
- bounded validation and fail-closed recovery;
- provenance/fingerprint checks for derived artifacts.

Failures and near-failures that should remain explicit:

- do not add presets merely because ideas exist;
- do not build installer infrastructure before measured onboarding friction exists;
- do not maintain duplicate setup surfaces that drift;
- do not let presentation mutate ownership/semantic truth;
- do not use small fixtures as evidence that dense labels are readable;
- do not rely on a second `GITHUB_TOKEN` workflow to refresh derivatives;
- do not validate geometry while ignoring stale source fingerprints;
- do not inject into nested SVG/XML by replacing the first matching closing tag;
- do not preserve a render/playback PASS after its visible target fingerprint changes;
- do not extract a universal adapter/IR before a second consumer exists.

## Evidence vocabulary

Keep proof claims separate:

1. **STRUCTURE PASS** — config/SVG/XML invariants.
2. **SOURCE SYNC PASS** — generated derivatives match authoritative source fingerprints.
3. **TARGET LAYOUT PASS** — real target page geometry/seams pass required viewport/appearance cases.
4. **TEXT PASS** — selected text policy satisfies its declared font/degradation contract without tofu/overflow in target proof.
5. **PLAYBACK PASS** — optional motion visibly runs on the actual target and the reduced-motion/static path remains complete.

`Actions success` alone is never equivalent to rendered/public success.

## Historical Envelope lineage

| Generation | Current role | Main lesson |
|---|---|---|
| D1-D2 | archived visual lineage | preserve rejected/older directions rather than silently overwriting evidence |
| v3 | historical donor | static-first seasonal motion and reduced-motion fallback |
| v4 | evidence donor | actual GitHub rendering exposed Japanese missing-glyph failure and table-frame drawbacks |
| v5-v6 | motion donor | continuous-flow experiments and shared logical coordinate space |
| v7 | proven donor | source fingerprints, root-level nested-SVG injection safety, atomic derived refresh, scoped public playback proof |
| v8 | proven donor / not live | seamless zero-gap packing, unified surface, target fingerprinting, broader public rail playback evidence |

Historical details remain under `envelope-v4/` through `envelope-v8/`; keep generation-specific evidence there instead of duplicating it into this overview.

## Extraction order

- **P0 — donor freeze:** keep v8 evidence and the current direct-IPM live profile separate.
- **P1 — contract extraction:** normalize bounded configuration, derive verification policy, fingerprint the normalized contract, and validate representative examples.
- **P2 — donor implementation revision:** implement safe/native/minimal text and opaque/transparent behavior without silently reusing old render proof.
- **P3 — matrix proof:** desktop/mobile; transparent light/dark; safe/native/minimal text cases; dense labels; motion/reduced-motion; source-refresh atomicity.
- **P4 — public extraction:** move the stable core only after the donor plus one structurally different consumer/configuration prove the same contract.

## Skill decision

Do not create a standalone `profile-envelope` Skill from one donor project yet. The reusable **way of working** belongs first in existing skills/candidates:

- `readme-visual-design`: text-role/font-independence policy, transparent-host verification, target layout proof and generated-source provenance;
- `animation-composition`: target-native motion, reduced-motion and playback claim scope;
- project-incubator reusable-task candidate: portable generated README/profile surface contract and extraction gate.

A standalone Skill or shared runtime component becomes justified only after a second independent consumer demonstrates the same workflow/contract.
