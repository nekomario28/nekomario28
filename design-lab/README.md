# Profile Design Lab

Experimental visual directions, evidence lineage, and reusable-contract work for the `nekomario28` GitHub profile.

## Current authority

The **live public profile is the direct IPM surface**, not Envelope v9. The root README owns the live composition and references the profile hero, the external character image by reference, `project-map/galaxy.svg`, and the contribution SVG.

Envelope v4-v8 remains historical/proven donor evidence. Envelope v9 is the portable donor/extraction lineage. None of those Design Lab generations should be described as currently live unless the root README is explicitly promoted back to an Envelope presentation.

As of **2026-08-26 JST**, the reusable six-file core has also been extracted into a dedicated **private working repository**:

- repository: `nekomario28/profile-envelope`;
- donor source: `nekomario28/nekomario28@bf3960dc85eebf8e25c5e8a015e968322a984597`;
- extracted working main: `d916b057ec897ceef94bdee293d4e02f42e46d1b`;
- visibility: private;
- public license: unselected;
- public release/public visibility: deferred.

The private repository is now the working home for the reusable core. This Design Lab remains the historical donor, profile-specific renderer/evidence source, and publication/provenance authority until the extracted repository earns its own release evidence.

## Why private extraction is allowed while public publication remains deferred

These are separate claims:

1. the portable copy set can technically be extracted and validated;
2. an authorized private working repository may be created for continued development;
3. public redistribution requires an explicit license and release evidence.

The repository owner explicitly requested extraction on 2026-08-26, so `concrete_reuse_request=ESTABLISHED`. The publication license is still `UNSELECTED`; therefore the public publication gate remains `DEFERRED` even though the private working repository now exists.

See `envelope-v9/PUBLICATION-GATE.md` and `envelope-v9/portable-package-manifest.json` for the current machine/document authority.

## Portable core boundary

The extracted boundary remains deliberately small:

```text
profile-envelope/
├── src/profile_envelope/
│   ├── contract.py
│   ├── vector_text.py
│   └── github_profile_transform.py
├── schema/
│   └── profile-envelope-config.schema.json
└── examples/
    ├── opaque-safe.json
    └── transparent-safe.json
```

Profile-specific artwork, v7/v8 renderer code, Project Map data, Activity data, character media, fonts, and donor presentation assets are intentionally excluded.

The extracted history was produced by filtering the donor Git history to the six audited files and then normalizing paths in the new repository. This preserves retained donor Author/Committer metadata better than recreating the files in an unrelated root commit, while acknowledging that filtered commit object IDs necessarily change with their trees and parents.

## Current bounded public controls

The contract remains intentionally small:

```yaml
profile:
  theme: seasonal-dark
  background: opaque        # opaque | transparent
  text: safe                # safe | native | minimal
  motion: on                # on | off
```

Advanced/internal policy may additionally control:

- mounted source background: `inherit | preserve`;
- frame: `rail | none`, with outer caps only;
- label density: `auto | full | minimal`;
- packing: `auto | off`;
- external media: `reference-only | none`.

Do not add speed sliders, particle-count knobs, arbitrary animation timelines, a style DSL, installer infrastructure, or a universal rendering IR until a real consumer requires them.

## Text policy

`safe`
: Essential fixed visible text is deterministic and font-independent. The proven implementation uses repository-owned vector strokes rather than redistributing a font. Unsupported glyphs fail closed. Dynamic labels use the bounded transformation/density policy.

`native`
: Visible SVG `<text>` remains allowed. The result is intentionally host-font-dependent and cannot claim font-independent `TEXT PASS`.

`minimal`
: Essential fixed text stays deterministic while non-essential dynamic visible labels may be suppressed. Semantic data and accessibility metadata remain present.

Accessibility `<title>`, `<desc>`, and equivalent metadata are not the same role as visible glyph rendering and should remain textual.

## Transparency policy

Two independent decisions remain explicit:

- `profile.background = opaque | transparent` controls the Envelope-owned outer surface;
- `surface.mounted_source_background = inherit | preserve` controls known presentation backgrounds inside mounted content.

A transparent outer surface with preserved mounted backgrounds is valid but may create opaque islands. Transparent mode requires real light/dark target proof rather than source-only assumptions.

## Evidence vocabulary

Keep claims separated:

1. **STRUCTURE PASS** — config/SVG/XML invariants.
2. **SOURCE SYNC PASS** — generated derivatives match authoritative source fingerprints.
3. **TARGET LAYOUT PASS** — real target geometry/seams pass required viewport/appearance cases.
4. **TEXT PASS** — selected text policy satisfies its declared font/degradation contract.
5. **PLAYBACK PASS** — optional motion visibly runs on the actual target and reduced-motion/static behavior remains complete.

Actions success alone is never equivalent to rendered/public success. An Actions job that fails before any repository steps execute is an executor/provider result, not code-test evidence.

## Historical Envelope lineage

| Generation | Current role | Main lesson |
|---|---|---|
| D1-D2 | archived visual lineage | preserve rejected/older directions rather than silently overwriting evidence |
| v3 | historical donor | static-first seasonal motion and reduced-motion fallback |
| v4 | evidence donor | actual GitHub rendering exposed Japanese missing-glyph failure and table-frame drawbacks |
| v5-v6 | motion donor | continuous-flow experiments and shared logical coordinate space |
| v7 | proven donor | source fingerprints, safe nested-SVG injection, atomic refresh, scoped public playback proof |
| v8 | proven donor / previously live | seamless zero-gap packing, unified surface, target fingerprinting, broad public rail playback evidence |
| v9 | portable donor / extracted core | safe/native/minimal text, opaque/transparent policy, generic markers, standalone-copyable transformer, publication gate |

v8 established that the segmented README surface can visually behave as one continuous profile canvas on the real GitHub target. It did **not** claim one shared runtime clock or frame-perfect synchronization across independent SVG image documents.

## v9 progression

- **P0 — donor freeze:** preserve v8 evidence separately from the live direct-IPM profile.
- **P1 — contract extraction:** bounded config, verification policy, contract fingerprint.
- **P2 — donor implementation:** portable text/background/motion/frame behavior.
- **P3 — browser matrix:** desktop/mobile, light/dark, text modes, transparency, motion/reduced-motion.
- **P4 — extraction readiness:** standalone-copyable kernel and provenance-aware package boundary.
- **P5 — adapter decoupling:** portable GitHub transformer separated from donor producer.
- **P6 — second-consumer fixture:** v8-independent synthetic donor proves the generic marker boundary without pretending to be an independent external consumer.
- **P7 — publication gate:** technical copyability cannot silently authorize public publication.
- **P8 — six-file provenance audit:** repository-local introduction history and copy boundary recorded without making a legal conclusion.
- **P9 — private working extraction:** explicit reuse request, history-preserving extraction to `nekomario28/profile-envelope`, exact-head validation, public release still deferred pending license.

## Extracted-repository bootstrap evidence

The first repository-creation route was not exposed by the connected GitHub mutation surface. An already-authorized self-hosted ShotFork carrier on `MeguminDesktop` used the host's existing `gh` authentication as a bounded one-shot alternate.

Bootstrap run `32868834661`:

- created `nekomario28/profile-envelope` as private;
- filtered exact donor `bf3960dc85eebf8e25c5e8a015e968322a984597` to the six audited files;
- verified all six donor blob identities;
- normalized paths and added minimal README/provenance/tests;
- ran `compileall` and unit tests;
- pushed and independently re-read the new repository head.

A first exact-head hygiene probe found that `compileall` generated ignored-by-intent but not-yet-ignored `__pycache__` files. After adding a minimal `.gitignore`, exact-head carrier run `32869436824` passed compile, tests, and clean-worktree verification. The validated candidate was then force-free fast-forwarded to `profile-envelope/main` at `d916b057ec897ceef94bdee293d4e02f42e46d1b`.

The broad host-auth carrier is **not** permanent CI. A permanent execution lane should use a repository-scoped runner/token or equivalent narrower identity.

## IPM lessons carried forward

Preserve the parts of Interactive Project Map and Envelope that worked:

- static-first, user-owned generated artifacts;
- one semantic source model with separate visual projections;
- small bounded public inputs and safe defaults;
- risky/heavier optional behavior default-off;
- read-only generation separated from write publication;
- stable release channel plus exact implementation/evidence identity;
- real-browser target gates rather than syntax-only claims;
- bounded validation and fail-closed recovery;
- provenance/fingerprint checks for derived artifacts;
- exact source revision and copy-set identity when extracting across repositories.

Failures/near-failures to keep explicit:

- do not add presets merely because ideas exist;
- do not build installer infrastructure before measured onboarding friction exists;
- do not let presentation mutate semantic ownership/truth;
- do not treat dense-label fixture success as readability proof;
- do not rely on a second automation-token workflow to recursively refresh derivatives;
- do not inject nested SVG/XML by replacing the first closing tag;
- do not preserve render/playback PASS after its visible target fingerprint changes;
- do not create a public repository or choose a license merely because extraction is technically possible;
- do not promote a broad host-credential carrier into unattended permanent CI solely because a bounded run succeeded.

## Skill decision

Do **not** create a standalone `profile-envelope` Skill merely because the code now has a dedicated repository. The reusable visual-design workflow still belongs primarily to:

- `readme-visual-design` — text-role/font-independence, transparent-host verification, target-layout proof, generated-source provenance;
- `animation-composition` — target-native motion, reduced-motion, playback claim scope;
- project-incubator reuse evidence — portable generated README/profile surface contract and extraction gates.

The repository-creation fallback learned during P9 is a general execution/authority pattern and belongs in `alternate-execution-routing` / repository-workbench guidance instead of a Profile Envelope-specific Skill.
