# Envelope v9 publication gate

Status: **technical copy set PASS / private working repository CREATED / public publication DEFERRED**  
Reviewed: **2026-08-26 JST**

This receipt separates three claims that must not be conflated:

1. **technical extraction readiness** — the declared package can be copied and validated outside the donor repository;
2. **private working extraction** — an authorized working repository may exist for continued development without making the package publicly redistributable;
3. **public publication authority/readiness** — external demand exists and an explicit license choice authorizes the intended public copy set.

Envelope v9 has the first claim. On 2026-08-26 the repository owner explicitly requested extraction and continued work, so a private working repository now establishes the second claim. The third claim remains deferred because the publication license is still unselected.

## Current working repository

- repository: `nekomario28/profile-envelope`;
- visibility: **private**;
- donor source: `nekomario28/nekomario28@bf3960dc85eebf8e25c5e8a015e968322a984597`;
- retained filtered-history head before path normalization: `ee0a07b9e85f7a57c6b2146149e68420202f4fe5`;
- first post-bootstrap working main: `d916b057ec897ceef94bdee293d4e02f42e46d1b`;
- current working main: `3379342a048e5d64f36a28e91ce132b14592961b`;
- one-shot bootstrap carrier: ShotFork run `32868834661` on `MeguminDesktop` / `shotroute` — **SUCCESS**;
- exact-head validation after `.gitignore` hygiene repair: ShotFork run `32869436824` — **SUCCESS**;
- portable regression exact-head validation: ShotFork run `32871700639`, job `97880025443` — **SUCCESS**, 7 tests;
- P9 design-grammar exact-head validation: ShotFork run `32876973365`, job `97897147907` — **SUCCESS**, 14 tests;
- P9 design-grammar fingerprint: `24ee74fdb9ae669390244af16463220e0f9b0f9e0661159c19b0ced0a69a4ced`;
- P9 actual donor-bundle design lint: **PASS**, 15 SVG assets at donor `36a8a57cb5cfe0b7af4bf1499b06e629dba55141`;
- P10 geometry-projection implementation: `c73c902661ceadd93ae15a89d9eea352f2d1ac5e`;
- P10 evidence head / current working main: `3379342a048e5d64f36a28e91ce132b14592961b`;
- P10 implementation validation: ShotFork run `32881179871`, job `97910809919` — **SUCCESS**, 15 tests;
- P10 exact evidence-head validation: ShotFork run `32881471260`, job `97911747424` — **SUCCESS**, 15 tests;
- P10 exact donor frame-geometry equivalence: **PASS**, 15 SVG assets at donor `0ed9c954283661edd924d0abb6c22c3544b3ae93`;
- P10 frame-rail grammar projection: **opt-in**; legacy default preserved;
- global design-grammar renderer authority: **false**;
- retained donor history: eight path-filtered commits plus one path-normalization/bootstrap commit and subsequent validation-boundary/hygiene/regression/design-grammar/geometry-projection commits;
- public license: **not selected**;
- public release: **DEFERRED**.

The extraction preserved retained donor Author/Committer metadata through path-filtered Git history rather than copying the six files into an unrelated root commit. Commit object IDs necessarily changed because filtering changes trees and parent topology.

The initial repository-local hosted `ubuntu-latest` validation run `32868886581` failed before repository steps were assigned a runner. It is classified as provider/executor failure rather than a portable-core failure. The extracted code is now covered by repository-local deterministic regression, P9 design-grammar tests and P10 geometry-projection tests, validated at exact heads through the bounded self-hosted carrier. The carrier is not promoted to permanent unattended CI because its pre-existing host `gh` credential is broader than the new repository's least-privilege requirement.

The portable regression suite covers schema/contract alignment, fail-closed contract keys, deterministic safe vector text, unsupported-glyph fail-closed behavior, and a structurally different synthetic 15-SVG second consumer whose outputs are deterministic and stripped of donor-only input markers/background state. P9 adds a measured semantic design grammar for proven geometry, seasonal palette roles, typography hierarchy and motion boundaries plus bounded design lint against the actual 15-SVG donor bundle.

P10 begins the renderer migration one field at a time. Only frame-rail geometry has an explicit opt-in projection from the normalized grammar. Full-width assets use `geometry.rails`; a left character-side window uses `geometry.rail_inset`; a right character-side window uses `local_width - geometry.rail_inset`. The existing 100px donor therefore remains x=82, while the heterogeneous 120px synthetic fixture correctly resolves to x=102 instead of inheriting the historical 100px-only literal.

The exact proven donor was rendered through both the legacy path and the grammar-projected path under the `frame.caps=none` case. All 15 transformed SVG bytes and the render-target fingerprint were identical. This establishes bounded semantic-projection equivalence for that case; it does **not** establish browser, perceptual, responsive-layout, live-playback or public-profile P10 PASS.

## Current machine gate

`portable-package-manifest.json` now records:

```text
technical_copy_set=PASS
independent_consumer=NOT_ESTABLISHED
concrete_reuse_request=ESTABLISHED
license_selection=UNSELECTED
repository_creation=DEFERRED
working_repository=CREATED_PRIVATE
current_working_main_sha=3379342a048e5d64f36a28e91ce132b14592961b
portable_regression_tests=7
design_grammar=P9/measured-reference-detection-only
design_grammar_sha256=24ee74fdb9ae669390244af16463220e0f9b0f9e0661159c19b0ced0a69a4ced
geometry_projection=P10/opt-in-semantic-frame-rail-projection
geometry_projection_tests=15
geometry_projection_donor_byte_equivalence=PASS/15-assets
geometry_projection_legacy_default_preserved=true
design_grammar_global_renderer_authority=false
```

`repository_creation=DEFERRED` remains the **public publication/repository gate**. It no longer means that no private development repository exists.

The validator derives public repository readiness with this rule:

```text
READY =
  technical_copy_set == PASS
  AND (independent_consumer == ESTABLISHED
       OR concrete_reuse_request == ESTABLISHED)
  AND license_selection == SELECTED
```

Every other state is `DEFERRED`.

The 2026-08-26 explicit extraction request satisfies the concrete reuse/demand term, but it does not select a redistribution license. Therefore the public gate correctly remains `DEFERRED`.

## P9/P10 design-grammar promotion boundary

P9 records measured design decisions without silently changing the already-proven renderer. P10 has now satisfied one part of the migration rule for **frame-rail geometry only**: the opt-in semantic projection is byte-equivalent to the legacy path on the exact proven donor under the tested frame-caps-none contract, while a heterogeneous synthetic fixture demonstrates that the semantic formula generalizes beyond the old 100px literal.

Global renderer authority is still not earned. Before the grammar can become the default source of renderer values, the affected implementation must continue through bounded migrations and re-earn the evidence relevant to each claim:

1. each migrated semantic field continues to pass against the proven donor or receives explicit visual review for an intentional change;
2. legacy-vs-grammar byte equivalence is retained where output is intended to remain unchanged;
3. browser/static/reduced-motion evidence is rerun before a migrated path is used for corresponding render claims;
4. optical or data-derived exceptions are recorded by semantic reason rather than hidden raw literals;
5. affected public/live claims are re-earned after deployment when those claims are required.

Until these conditions are met, P10 means **opt-in frame-geometry projection PASS**, not global renderer migration or visual acceptance PASS.

## Canonical P7 implementation

P7 originally merged through PR #71 as:

- merge commit: `0a6fb92240a85f1ee36c36cca27eeef413ef8ce8`;
- accepted clean head: `d0ea3525e794924338a2df0f0fa51518853f9e5c`;
- accepted base main: `c1bd7f255cfa7e0ac372731cad9d5f49e31f9142`;
- accepted workflow run: `32814044647`;
- accepted job: `97698734935`.

That P7 receipt established the fail-closed public-publication rule. The later private extraction and P9/P10 design-consistency work do not invalidate it; they only add a private development surface, a pre-render consistency gate and one bounded opt-in renderer projection without authorizing redistribution.

## Technical evidence retained from P7/P8

The portable donor remains backed by:

- `ENVELOPE_V9_EXTRACTION_TRANSFORM_PASS`;
- `SECOND_CONSUMER_FIXTURE_PASS donor_identity=v8-independent geometry=heterogeneous generic_markers=3`;
- nine-case Chrome matrix: **PASS**;
- target layout/text/transparency: **PASS**;
- motion-on and reduced-motion evidence bound to the tested donor target;
- exact v8 -> v9 inherited motion-subtree equivalence across 15 generated assets;
- public GitHub-profile v9 playback: `NOT_RUN`;
- cross-document hard synchronization: not claimed;
- P8 six-file repository-history provenance audit.

These donor proofs do not automatically transfer to arbitrary future renderer changes. The extracted repository must re-earn the evidence affected by each implementation or release change.

## Why private was selected

Creating the new repository as public would have turned a development-organization action into a redistribution/publication action while `license_selection=UNSELECTED` remained authoritative. The requested work could proceed without weakening that boundary, so the least-claim option was:

```text
create private working repository
-> preserve audited provenance/history
-> validate exact extracted head
-> continue development
-> select publication license explicitly later
-> revalidate intended public release
-> only then consider public visibility
```

Private visibility is therefore a staging/publication-boundary decision, not a statement that the project should remain private permanently.

## Public publication trigger

Reconsider public visibility only when all of the following are true in one current-authority review:

1. the explicit reuse request remains applicable or an independent consumer exists;
2. the intended public copy set still passes standalone structure/extraction and the browser/motion evidence required by its claims;
3. a publication license has been selected explicitly for that exact copy set;
4. provenance/ownership review covers any files added after the P8 six-file boundary;
5. the target `profile-envelope` revision and visibility transition are recorded as one bounded publication event.

Do not make the repository public merely because it already exists privately.

## Skill boundary

A standalone `profile-envelope` Skill remains **DEFERRED**. The implementation now has a real extracted working repository, but a new Skill still needs recurrence outside this profile donor plus a discriminating evaluation showing that existing `readme-visual-design` and `animation-composition` guidance is insufficient.

The P9/P10 lesson strengthens the broader `design-system-consistency` candidate: measured design decisions -> semantic grammar -> detection-only lint -> one-field-at-a-time renderer projection -> byte equivalence or explicit visual review -> rendered verification. One Profile Envelope lineage is still not enough to create that Skill. Preserve it as a candidate until an independent UI/visual consumer demonstrates the same workflow.

The repository-creation execution lesson remains a general alternate-execution/authority pattern and belongs in `alternate-execution-routing`, not a Profile Envelope-specific Skill.
