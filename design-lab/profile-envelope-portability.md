# Portable profile envelope contract

Status: **design contract + extraction candidate / not yet a public API**  
Updated: **2026-08-25 JST**

This document freezes the reusable boundary discovered while building the profile envelope and direct IPM surfaces. The current public profile is the direct-IPM surface; Envelope v8/v9 are evidence-bearing donors in Design Lab. No portability work should implicitly promote them live.

The eventual goal is a small public repository that can transform a declared GitHub-profile SVG bundle without depending on a username, private state, Project Map taxonomy internals, donor renderer implementation, or write-capable GitHub credentials.

## Current proven boundary

Envelope v9 has three explicit layers:

1. **portable core** — normalized contract, vector-text kernel, JSON Schema and examples;
2. **standalone GitHub-profile transformer** — applies text/background/frame/motion policy to a complete pre-rendered 15-SVG donor bundle;
3. **donor producer** — this profile repository's current v8-based bundle generator, intentionally still repository-bound.

P6 removes donor element identity from the transformer. Portable code no longer pattern-matches `v8-frame`, v8 surface IDs, Project Map gradient names or Activity-specific background geometry. The donor producer translates those local details into three semantic input markers:

```text
data-profile-envelope-surface-base="outer"
data-profile-envelope-frame="rail"
data-profile-envelope-mounted-background="presentation"
```

The transformer consumes the markers and removes them before final output fingerprinting. This keeps the portable boundary semantic and bounded without inventing a universal visual IR.

A heterogeneous synthetic second-consumer fixture proves that the copied transformer can operate on a donor with different dimensions, frame geometry, colors and mounted-background identity while using only those three markers. That fixture is evaluation evidence, **not an independent external consumer**.

## Public configuration v1

Keep the public control surface small:

```yaml
profile:
  theme: seasonal-dark
  background: opaque          # opaque | transparent
  text: safe                  # safe | native | minimal
  motion: on                  # on | off
```

Advanced bounded options may include:

```yaml
surface:
  mounted_source_background: inherit   # inherit | preserve
frame:
  mode: rail                           # rail | none
  caps: outer-only                     # outer-only | none
labels:
  density: auto                        # auto | full | minimal
packing:
  mode: auto                           # auto | off
external_media:
  mode: reference-only                 # reference-only | none
```

Do not expose arbitrary timelines, particle counts, style DSLs or dozens of typography controls before a real consumer requires them.

## Text policy

Text has three roles and they must not be conflated:

| Role | Policy |
| --- | --- |
| Essential fixed visible text | deterministic visible geometry under `safe`; must not depend on an arbitrary client font |
| Dynamic data labels | may use vector, native or minimal-density policy without changing semantic source data |
| Accessibility metadata | preserve textual `<title>`, `<desc>` and `aria-label` even when visible text is vectorized or suppressed |

`safe`
: Supported visible glyphs become repository-owned vector geometry. Unsupported glyphs fail closed rather than rendering tofu. Transparent safe text adapts to host light/dark appearance without font files.

`native`
: Visible SVG `<text>` is allowed and explicitly host-font-dependent.

`minimal`
: Essential fixed text remains safe while dynamic visible labels may be suppressed; semantic/accessibility metadata remains.

The extraction smoke discovered a real accessibility bug that donor-local rendering had not discriminated: an encoded source such as `&amp;` could be decoded for glyph geometry but double-escaped in `aria-label`/`title`. The kernel now derives both visible geometry and accessibility text from the same decoded visible string.

## Background policy

`opaque`
: Render the envelope-owned base surface.

`transparent`
: Remove only the envelope-owned base. Because the host now participates in appearance, verification expands to desktop/mobile × light/dark.

Mounted source backgrounds are a separate decision:

- `inherit` removes only the element explicitly marked as a mounted presentation background while retaining authoritative data marks;
- `preserve` leaves that marked source surface intact.

The donor producer owns recognition of donor-local background identity and marks it. The standalone transformer owns only the generic `inherit|preserve` policy.

## Render identity

Config identity is insufficient. Every generated target carries one target-sensitive SHA-256 derived from:

- normalized contract fingerprint;
- selected season/preset input;
- transformed bytes of every generated SVG before target-marker insertion.

Generic donor marker attributes are removed before the fingerprint is calculated. A pure adapter-boundary refactor can therefore remain byte-identical, while any actual visible/source change still changes the render-target identity and invalidates old render/playback evidence.

## Extraction package shape

The current candidate copy set is declared in `envelope-v9/portable-package-manifest.json`.

```text
profile-envelope/
├── src/profile_envelope/
│   ├── contract.py
│   ├── vector_text.py
│   └── github_profile_transform.py
├── schema/
│   └── profile-envelope-config.schema.json
├── examples/
│   ├── opaque-safe.json
│   └── transparent-safe.json
└── ... evidence / packaging surfaces added only when publication is justified
```

The Schema identity is owner-independent: `urn:profile-envelope:config:v1`.

The current repository-bound `render_portable_surface.py` is **not** part of that copyable package. It imports v8, materializes this profile's donor bundle and translates donor-specific element identity into the three generic marker attributes.

### Portable code must not know

- a concrete username;
- donor repository paths;
- Project Map category/ownership taxonomy;
- contribution-data producer paths;
- a third-party character URL;
- write-capable GitHub credentials;
- local absolute filesystem paths;
- Envelope v7/v8 implementation modules or element IDs;
- Project Map presentation gradient names/colors.

### GitHub-profile transformer may know

- the bounded 15-SVG profile bundle role/path contract;
- the three semantic input markers;
- GitHub-profile frame/packing presentation conventions;
- safe/native/minimal text policy;
- outer and mounted-source background policy;
- target-sensitive fingerprinting;
- script-free motion removal/preservation policy.

It must not generate donor semantic data itself.

## IPM lessons to preserve

The extraction deliberately reuses patterns that worked in Interactive Project Map:

- **Static first, user-owned artifacts.** Normal viewers consume generated artifacts, not shared API quota or a hosted daemon.
- **Canonical model vs projection.** Semantic truth remains upstream; presentation transforms do not mutate ownership/data meaning.
- **Small bounded inputs.** Prefer a short contract over a style DSL.
- **Risky/expensive behavior default-off.** Optional external behavior requires explicit opt-in.
- **Read-only generation vs write publication.** A renderer does not need a publication token.
- **Stable release channel + exact evidence.** Friendly versions and exact reviewed identities serve different jobs.
- **Actual browser gates.** XML validity is not rendered correctness.
- **Fail closed.** Unsupported glyphs/configs/source shapes do not silently degrade authority.
- **Derived provenance.** Generated targets bind to source/config/output identity.
- **Translate donor identity at the adapter edge.** Portable projection code consumes semantic markers rather than pattern-matching one donor's IDs.

Failures and near-failures to keep as regression rules:

- missing-glyph/tofu fixed text from host fonts;
- transparent output checked on only one host appearance;
- stale generated derivatives validated only by geometry;
- first-`</svg>` injection when nested SVG is legal;
- bare `git push` after exact-SHA detached checkout;
- relying on a GITHUB_TOKEN bot commit to trigger a second workflow;
- preserving a PASS after render-target bytes changed;
- top-level-only reduced-motion emulation treated as proof for separately decoded SVG images;
- async browser receipt races treated as product failures;
- public extraction declared from donor-local success without copying/running the candidate package elsewhere;
- accessibility metadata derived from differently encoded text than visible glyph geometry;
- portable code matching donor implementation IDs instead of explicit semantic markers;
- requiring dead SVG definitions to disappear when the contract only requires their rendered background paint to be removed;
- universal IR/adapter design before a second host or independent consumer exists.

## Evidence contract

A release claim should distinguish at least:

1. **STRUCTURE PASS** — config/XML/output invariants.
2. **SOURCE / INPUT PASS** — required donor inputs exist and derived provenance is current.
3. **TARGET LAYOUT PASS** — real browser geometry in required viewport/theme cases.
4. **TEXT PASS** — selected text policy renders without missing glyphs or unintended host-font dependence.
5. **TRANSPARENCY PASS** — real pixel evidence on required light/dark hosts when transparent.
6. **PLAYBACK PASS** — selected motion visibly runs, while reduced-motion and motion-off are static.
7. **EXTRACTION PASS** — declared copy set runs outside the donor repository.
8. **SECOND-FIXTURE PASS** — a structurally different donor exercises the portable marker boundary; this is not equivalent to an independent consumer.

`Actions success` alone is never equivalent to public rendered success.

## Migration status

### P0 — v8 donor freeze: complete

Preserved the evidence-bearing motion/layout donor and target fingerprint discipline.

### P1 — contract extraction: complete

Bounded config, Schema, normalization, target-case expansion and fail-closed validation are implemented.

### P2 — portable text/surface donor: complete

Safe/native/minimal text, opaque/transparent surface, mounted background policy and motion/frame switches exist in v9 Design Lab.

### P3 — rendered matrix: complete locally

Real Chrome verifies the nine-case light/dark + desktop/mobile + safe/native/minimal matrix. Local isolated rail playback, browser-wide reduced motion and motion-off are proven. Public GitHub v9 playback remains `NOT_RUN` because v9 is not mounted live.

### P4 — extraction kernel: complete

The five-file core copies into a temporary standalone repository, uses only the Python standard library, contains no donor-specific forbidden tokens, executes example contracts, aligns Schema/implementation enums and runs vector text independently.

### P5 — adapter decoupling: complete

PR #65 merged the standalone-copyable GitHub transformer. The old pre-stripped donor boundary and preserve-first donor boundary produce byte-identical `inherit` targets, and the existing Chrome/motion gates remain green.

### P6 — second-consumer fixture: complete

PR #68 merged the three-marker donor boundary and v8-independent heterogeneous fixture. Clean exact-head CI passed structure/extraction, the nine-case Chrome matrix and motion/reduced-motion gates. The current donor retained render target `62d68a97a354ffc3c82efdbe2396730f5ca90cafdfa5579c59504b7df9c35b4f`, proving the marker refactor did not change current rendered bytes.

The fixture is intentionally not counted as an external independent consumer.

### P7 — public repository publication: deferred

Do not create the repository solely because extraction is technically possible. Publication is justified when there is an independent consumer or concrete reuse request, and license/package/release surfaces can be chosen deliberately. At that point, use the manifest as the initial copy boundary rather than moving the entire Design Lab history.

Further generic abstraction before that signal is not justified by current evidence.

## Skill/reuse decision

Do **not** create a new `profile-envelope` Skill yet.

Current reusable guidance belongs primarily in existing domains:

- `readme-visual-design`: role-based font independence, transparent-host verification, target fingerprints and extraction-copy proof;
- `animation-composition`: motion isolation, real elapsed-time pixel proof and reduced-motion scope;
- project-incubator reusable-task evidence: canonical/projection separation, donor/adapter boundary, semantic-marker translation and promotion gates.

Promote a standalone Skill only after a discriminating evaluation shows the existing skills cannot express the workflow and the same need recurs outside this profile donor.
