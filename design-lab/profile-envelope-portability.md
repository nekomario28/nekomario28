# Portable profile envelope contract

Status: **design contract / not yet a public API**  
Updated: **2026-08-25 JST**

This document freezes the reusable boundary discovered while building Envelope v4-v8 in this profile repository. It is intentionally separate from the live renderer so the current public surface is not changed merely by documenting the next architecture.

The eventual goal is a small public repository that can generate a GitHub profile surface without depending on `nekomario28`-specific paths, fonts, project taxonomy, or private state.

## Current production baseline

Envelope v8 currently provides:

- one 900px logical surface and a 1662px global Y motion space;
- a unified rectangular skin with one rail per visible edge;
- packed short SVG windows so GitHub mobile line-height does not create seams;
- mounted Project Map and Activity SVG content with source fingerprints;
- reduced-motion fallback and script-free SMIL rail motion;
- exact GitHub desktop/mobile zero-gap validation;
- atomic Project Map + mounted derivative publication, including the three packed v8 assets;
- public playback evidence that observed all 14 tested non-hero rail strips moving on the actual public profile;
- verification-target fingerprinting so a renderer/README/presentation change cannot silently retain an older playback PASS.

The live renderer remains profile-specific. This document defines what should be extracted later and what should remain adapter-specific.

## Why text needs an explicit policy

Text is not one problem. It has three different roles and they should not share one switch.

| Role | Current examples | Required policy |
| --- | --- | --- |
| Essential fixed UI text | profile handle/name, fixed section labels, attribution | must remain readable without relying on an arbitrary client font |
| Dynamic data labels | repository/category labels in Project Map, Activity headings/axes/dates/counts | may trade file size/density against host-font dependence |
| Accessibility metadata | `<title>`, `<desc>`, `aria-label` | retain as text metadata even when visible glyphs are outlined or hidden |

Envelope v4 already proved the important failure mode: Japanese section labels rendered as missing-glyph boxes in a GitHub proof environment. Replacing the visible labels with deterministic outline paths fixed desktop and mobile rendering, and CI now protects those section labels from regressing to client-side `<text>`.

Current v8 still has host-font-dependent visible text in at least:

- the hero handle/name;
- Project Map owner/category/repository/legend labels;
- the generated Activity chart heading, totals, axes and dates.

Therefore the next live presentation change should treat font independence as a first-class render contract rather than a one-off patch.

## Proposed public configuration v1

Keep the public control surface small. Do not expose every renderer parameter.

```yaml
profile:
  theme: seasonal-dark        # first public release may support fewer values
  background: opaque          # opaque | transparent
  text: safe                  # safe | native | minimal
  motion: on                  # on | off
```

### `background`

`opaque`
: Render the envelope-owned surface background. This is the deterministic default and is easiest to verify across hosts.

`transparent`
: Omit the envelope base fill while retaining content/frame/motion that is otherwise enabled. Transparent mode must be verified separately on GitHub light and dark appearance because the host now participates in the visual result.

Do **not** conflate this with mounted-source backgrounds. The outer envelope background and an embedded Project Map/Activity background are separate decisions.

### `text`

`safe`
: Essential fixed text must be deterministic outlines. Dynamic data text should use a deterministic vector strategy when available; if a glyph cannot be rendered safely, degrade by a documented label-density/fallback rule rather than displaying tofu. Accessibility metadata remains intact.

`native`
: Allow visible SVG `<text>` for users who prefer smaller files and accept host-font rendering differences. Essential Japanese/non-ASCII fixed labels should still warn or fail validation unless explicitly allowed.

`minimal`
: Keep essential fixed labels as outlines and suppress non-essential dynamic visible labels while preserving semantic `<title>/<desc>`/accessible context. Useful for dense or font-hostile targets.

The first extraction does not need a universal font engine. A small deterministic ASCII vector fallback plus pre-outlined fixed labels is preferable to bundling/distributing font files or introducing a large typography dependency solely for a README.

### `motion`

`on`
: Use the target-native script-free motion provider with reduced-motion fallback.

`off`
: Emit a complete static surface; essential information must remain present.

Do not expose speed, particle count, individual phase controls or arbitrary keyframes in the first public API. Those are presentation implementation details until a real second consumer needs them.

## Advanced/internal options

These can exist in an internal config/schema before they become public controls:

```yaml
surface:
  mounted_source_background: inherit   # inherit | preserve
frame:
  mode: rail                           # rail | none
  caps: outer-only
labels:
  density: auto                        # auto | full | minimal
packing:
  mode: auto                           # auto | off
external_media:
  mode: reference-only                 # reference-only | none
```

Rules:

- `mounted_source_background=inherit` removes only the known presentation background from an embedded source and keeps its authoritative data marks.
- `preserve` keeps the source surface intact when visual integration is less important than source fidelity.
- `labels.density=auto` is target/density policy, not semantic filtering. Never delete repositories/data merely to reduce label clutter.
- `packing=auto` may merge adjacent logical windows into a taller physical SVG, but global logical start/end coordinates must remain unchanged.
- external media is referenced, not copied into repository-owned generated SVG bytes unless licensing/provenance explicitly permits that.

## Recommended additional features

Add only features with a clear failure mode or portability benefit:

1. **Text-role policy and visible-font independence** — highest priority because current rendering can visibly fail.
2. **Opaque/transparent outer surface** — requested user choice; verify both host appearances.
3. **Mounted-source background inherit/preserve** — needed because transparency and embedded source backgrounds are independent.
4. **Label density / font-safe fallback** — prevents dense Project Map or Activity labels from becoming unreadable without changing semantic data.
5. **Motion on/off + reduced motion** — already mostly proven; expose only the high-level switch.
6. **Deterministic public-target fingerprint** — bind proof to the visible renderer/README contract so old evidence cannot survive a changed target.
7. **Source provenance** — generated mounted artifacts must carry source path + fingerprint and CI must reject stale derivatives.
8. **Target adapter identity** — `github-profile-readme` should be explicit because packing, line-height, supported markup and browser proof are host constraints rather than core visual semantics.

Defer until evidence demands them:

- arbitrary custom animation timelines;
- many visual presets/skins;
- a one-click installer/GitHub App;
- a universal Visual/Animation IR;
- server-side rendering services or shared runtime daemons;
- dozens of typography/style knobs.

## Extraction architecture

The eventual public repository should separate a small pure core from host-specific behavior.

```text
profile-envelope/
├── core/
│   ├── contract            # normalized user/profile options
│   ├── render              # deterministic SVG composition
│   ├── text                # fixed-outline + bounded dynamic label strategy
│   ├── surface             # opaque/transparent and mounted-background policy
│   └── validate            # source/output/semantic invariants
├── adapters/
│   └── github-profile/
│       ├── readme          # allowed markup and external media mounting
│       ├── packing         # GitHub line-box/mobile seam mitigation
│       └── verify          # desktop/mobile/light/dark rendered gates
├── presets/
│   └── unified-v1
├── examples/
│   └── example-profile
└── .github/workflows/
    └── generate-profile
```

### Core must not know

- the username `nekomario28`;
- repository-specific file paths outside declared inputs/outputs;
- Project Map category names or ownership taxonomy internals;
- the current third-party character image URL;
- GitHub-specific line-height hacks;
- write-capable GitHub credentials.

### GitHub profile adapter owns

- README `<img>`/external-image composition;
- top vertical alignment and responsive-row behavior;
- short-window packing thresholds;
- GitHub desktop/mobile/light/dark browser verification;
- the fact that independent SVG documents do not share one runtime animation clock.

## IPM lessons to preserve

The public extraction should deliberately reuse the approaches that worked in Interactive Project Map:

- **Static first, user-owned artifacts.** Normal viewers should read checked-in/generated assets rather than spending shared API quota or depending on a hosted rendering service.
- **One canonical model, multiple projections.** Keep data/semantic truth separate from visual projection; do not let presentation convenience mutate ownership/data meaning.
- **Small public inputs.** Start with a few bounded options and safe defaults; do not ship a large style DSL.
- **Default-off for risky/expensive optional behavior.** Optional external data or heavier behavior should require explicit opt-in.
- **Read-only generation separated from write publication.** A reusable generator should not receive a write-capable publication token merely because the caller later commits artifacts.
- **Stable release channel plus exact implementation evidence.** A stable `@v1` can exist for users while maintainers keep an exact reviewed implementation identity for acceptance evidence.
- **Actual browser gates.** Syntax validity is not rendered correctness; verify target desktop/mobile and dense/failure cases numerically where possible.
- **Bounded validation and fail-closed recovery.** Invalid/missing input should produce clear recovery guidance or a safe static fallback instead of silently changing authority/source.

Failures/near-failures to avoid repeating:

- do not add more visual presets merely because new ideas are available;
- do not build a one-click installer before measured onboarding friction justifies it;
- do not maintain duplicate setup surfaces that can drift;
- do not let static and interactive/rendered projections develop different semantic rules;
- do not use small fixtures as evidence that dense labels are readable;
- do not rely on a second GITHUB_TOKEN-triggered workflow to refresh derived artifacts;
- do not validate only geometry while allowing a stale derived source;
- do not inject XML/SVG layers by replacing the first matching closing tag when nested SVGs are legal;
- do not retain playback/render PASS after the visible target contract changes;
- do not extract a universal adapter/IR without a real second consumer.

## Evidence contract for the public repository

A release claim should distinguish at least:

1. **STRUCTURE PASS** — generated SVG/XML/config invariants.
2. **SOURCE SYNC PASS** — derived artifacts match authoritative source fingerprints.
3. **TARGET LAYOUT PASS** — real target page has acceptable seams/geometry in required viewport/theme combinations.
4. **TEXT PASS** — required visible text has no host-font dependency under the selected safe policy and no missing-glyph/tofu result in target render proof.
5. **PLAYBACK PASS** — selected motion is visibly running on the actual target while reduced-motion/static fallback remains valid.

`Actions success` alone must never be reported as equivalent to public rendered success.

## Migration plan

### Phase P0 — current v8 freeze

- Preserve current v8 as evidence-bearing donor behavior.
- Keep the new target fingerprint rule.
- Do not reinterpret the latest public playback proof as proof for a changed text/background configuration.

### Phase P1 — contract extraction

- Normalize the configuration fields above in a target-neutral contract object.
- Keep current visual defaults byte-equivalent where practical.
- Add explicit validation for supported enum combinations.
- Do not publish a new public repo yet.

### Phase P2 — next live presentation revision

Treat visible text/background behavior as a new presentation target (prefer a v9/revision boundary rather than silently mutating verified v8):

- outline the hero handle/name;
- add safe/native/minimal text policy;
- add opaque/transparent surface policy;
- separate outer transparency from mounted-source background behavior;
- add data-label density/fallback behavior;
- ensure all generated README-mounted assets are in every atomic publication path.

### Phase P3 — matrix verification

At minimum verify:

- desktop dark / mobile dark;
- desktop light / mobile light for transparent mode;
- opaque + safe text;
- transparent + safe text;
- native text as explicitly host-dependent;
- minimal text on a dense fixture;
- motion on and reduced-motion/static path;
- source refresh with no stale mounted derivatives.

### Phase P4 — public extraction

Extract only after the contract has survived the donor and at least one structurally different example/configuration. Keep the profile repository as one consumer, not the semantic owner of the new public package.

## Skill/reuse decision

Do **not** create a new `profile-envelope` Skill yet.

Current evidence supports narrower reuse:

- extend `readme-visual-design` with role-based font-independence, transparent-host verification, and generated-source provenance guidance;
- keep motion composition/proof scope in `animation-composition`;
- capture the generated README surface contract as a reusable-task candidate in project-incubator;
- promote a standalone Skill or shared executable component only after a second independent consumer demonstrates the same need.
