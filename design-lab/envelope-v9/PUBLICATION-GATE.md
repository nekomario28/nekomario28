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
- current working main: `23f9b3d546a9ca29435de3741f8bee848450a937`;
- one-shot bootstrap carrier: ShotFork run `32868834661` on `MeguminDesktop` / `shotroute` — **SUCCESS**;
- exact-head validation after `.gitignore` hygiene repair: ShotFork run `32869436824` — **SUCCESS**;
- portable regression exact-head validation: ShotFork run `32871700639`, job `97880025443` — **SUCCESS**, 7 tests;
- P9 design-grammar exact-head validation: ShotFork run `32876973365`, job `97897147907` — **SUCCESS**, 14 tests;
- P9 design-grammar fingerprint: `24ee74fdb9ae669390244af16463220e0f9b0f9e0661159c19b0ced0a69a4ced`;
- P9 actual donor-bundle design lint: **PASS**, 15 SVG assets at donor `36a8a57cb5cfe0b7af4bf1499b06e629dba55141`;
- P9 renderer authority: **false / detection-only**;
- retained donor history: eight path-filtered commits plus one path-normalization/bootstrap commit and subsequent validation-boundary/hygiene/regression/design-grammar commits;
- public license: **not selected**;
- public release: **DEFERRED**.

The extraction preserved retained donor Author/Committer metadata through path-filtered Git history rather than copying the six files into an unrelated root commit. Commit object IDs necessarily changed because filtering changes trees and parent topology.

The initial repository-local hosted `ubuntu-latest` validation run `32868886581` failed before repository steps were assigned a runner. It is classified as provider/executor failure rather than a portable-core failure. The extracted code is now covered by repository-local deterministic regression and P9 design-grammar tests, validated at exact heads through the bounded self-hosted carrier. The carrier is not promoted to permanent unattended CI because its pre-existing host `gh` credential is broader than the new repository's least-privilege requirement.

The portable regression suite covers schema/contract alignment, fail-closed contract keys, deterministic safe vector text, unsupported-glyph fail-closed behavior, and a structurally different synthetic 15-SVG second consumer whose outputs are deterministic and stripped of donor-only input markers/background state. P9 adds a measured semantic design grammar for proven geometry, seasonal palette roles, typography hierarchy and motion boundaries plus bounded design lint against the actual 15-SVG donor bundle.

P9 remains deliberately **detection-only**. It does not make the grammar the renderer source of truth, and its PASS does not replace GitHub target-render/browser, perceptual-quality, pixel-equivalence or live-playback evidence.

## Current machine gate

`portable-package-manifest.json` now records:

```text
technical_copy_set=PASS
independent_consumer=NOT_ESTABLISHED
concrete_reuse_request=ESTABLISHED
license_selection=UNSELECTED
repository_creation=DEFERRED
working_repository=CREATED_PRIVATE
current_working_main_sha=23f9b3d546a9ca29435de3741f8bee848450a937
portable_regression_tests=7
design_grammar=P9/measured-reference-detection-only
design_grammar_tests=14
design_grammar_donor_bundle_lint=PASS/15-assets
design_grammar_renderer_authority=false
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

## P9 design-grammar promotion boundary

P9 records measured design decisions without silently changing the already-proven renderer. It may become renderer authority only after all of the following are re-earned on the migrated implementation:

1. the measured grammar continues to pass against the proven donor bundle;
2. tokenizing each renderer-owned value preserves byte-equivalent output or receives explicit visual review for an intentional change;
3. browser/static/reduced-motion evidence is rerun and remains green;
4. optical or data-derived exceptions are recorded by semantic reason rather than hidden raw literals;
5. affected public/live claims are re-earned after deployment when those claims are required.

Until these conditions are met, design-grammar PASS means **consistency detection PASS**, not renderer migration or visual acceptance PASS.

## Canonical P7 implementation

P7 originally merged through PR #71 as:

- merge commit: `0a6fb92240a85f1ee36c36cca27eeef413ef8ce8`;
- accepted clean head: `d0ea3525e794924338a2df0f0fa51518853f9e5c`;
- accepted base main: `c1bd7f255cfa7e0ac372731cad9d5f49e31f9142`;
- accepted workflow run: `32814044647`;
- accepted job: `97698734935`.

That P7 receipt established the fail-closed public-publication rule. The later private extraction and P9 design consistency work do not invalidate it; they only add a private development surface and a pre-render consistency gate without authorizing redistribution.

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

The P9 lesson is a candidate for a broader design-consistency pattern — measured design decisions -> semantic grammar -> fail-closed design lint -> rendered verification — but one Profile Envelope case is not enough to create a new `design-system-consistency` Skill. Preserve it as a candidate until an independent UI/visual consumer demonstrates the same workflow.

The repository-creation execution lesson remains a general alternate-execution/authority pattern and belongs in `alternate-execution-routing`, not a Profile Envelope-specific Skill.
