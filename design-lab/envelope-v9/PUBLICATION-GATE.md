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
- current extracted main after bootstrap validation cleanup: `d916b057ec897ceef94bdee293d4e02f42e46d1b`;
- one-shot bootstrap carrier: ShotFork run `32868834661` on `MeguminDesktop` / `shotroute` — **SUCCESS**;
- exact-head validation after `.gitignore` hygiene repair: ShotFork run `32869436824` — **SUCCESS**;
- retained donor history: eight path-filtered commits plus one path-normalization/bootstrap commit and subsequent validation-boundary/hygiene commits;
- public license: **not selected**;
- public release: **DEFERRED**.

The extraction preserved retained donor Author/Committer metadata through path-filtered Git history rather than copying the six files into an unrelated root commit. Commit object IDs necessarily changed because filtering changes trees and parent topology.

The initial repository-local hosted `ubuntu-latest` validation run `32868886581` failed before repository steps were assigned a runner. It is classified as provider/executor failure rather than a portable-core failure. The same extracted code passed `compileall` and unit tests on the bounded self-hosted carrier. The carrier is not promoted to permanent unattended CI because its pre-existing host `gh` credential is broader than the new repository's least-privilege requirement.

## Current machine gate

`portable-package-manifest.json` now records:

```text
technical_copy_set=PASS
independent_consumer=NOT_ESTABLISHED
concrete_reuse_request=ESTABLISHED
license_selection=UNSELECTED
repository_creation=DEFERRED
working_repository=CREATED_PRIVATE
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

## Canonical P7 implementation

P7 originally merged through PR #71 as:

- merge commit: `0a6fb92240a85f1ee36c36cca27eeef413ef8ce8`;
- accepted clean head: `d0ea3525e794924338a2df0f0fa51518853f9e5c`;
- accepted base main: `c1bd7f255cfa7e0ac372731cad9d5f49e31f9142`;
- accepted workflow run: `32814044647`;
- accepted job: `97698734935`.

That P7 receipt established the fail-closed public-publication rule. The later private extraction does not invalidate it; it only clarifies that a private development surface can be created without satisfying the public redistribution gate.

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

The repository-creation execution lesson is different: it is a general alternate-execution/authority pattern and should be fed back into `alternate-execution-routing`, not promoted as a Profile Envelope-specific Skill.
