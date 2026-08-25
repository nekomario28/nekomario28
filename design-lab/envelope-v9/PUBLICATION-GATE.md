# Envelope v9 publication gate

Status: **P7 merged / publication DEFERRED / public repository NOT_CREATED**  
Reviewed: **2026-08-25 JST**

This receipt separates two claims that must not be conflated:

1. **technical extraction readiness** — the declared package can be copied and validated outside the donor repository;
2. **publication authority/readiness** — there is a justified external demand signal and an explicit license choice for a new public repository.

Envelope v9 has the first claim. It does not yet have the second.

## Canonical implementation

P7 merged through PR #71 as:

- merge commit: `0a6fb92240a85f1ee36c36cca27eeef413ef8ce8`;
- accepted clean head: `d0ea3525e794924338a2df0f0fa51518853f9e5c`;
- accepted base main: `c1bd7f255cfa7e0ac372731cad9d5f49e31f9142`;
- accepted workflow run: `32814044647`;
- accepted job: `97698734935`;
- clean head shape: one commit directly over the accepted base, changing only `portable-package-manifest.json` and `validate_extraction.py`.

The merge commit tree is the exact clean-head tree used for the accepted P7 validation.

## Machine gate

`portable-package-manifest.json` now records:

```text
technical_copy_set=PASS
independent_consumer=NOT_ESTABLISHED
concrete_reuse_request=NOT_ESTABLISHED
license_selection=UNSELECTED
repository_creation=DEFERRED
```

`validate_extraction.py` derives repository readiness with this rule:

```text
READY =
  technical_copy_set == PASS
  AND (independent_consumer == ESTABLISHED
       OR concrete_reuse_request == ESTABLISHED)
  AND license_selection == SELECTED
```

Every other state is `DEFERRED`.

The validator includes discriminating state checks proving that:

- technical copyability plus a selected license but no external demand is still `DEFERRED`;
- an independent consumer without a selected license is still `DEFERRED`;
- a concrete reuse request plus technical PASS plus selected license can become `READY`;
- external demand and license selection cannot override a failed technical copy set.

This prevents a future automation or maintainer from treating `EXTRACTION PASS` as publication authorization.

## Accepted P7 evidence

The clean exact head reported:

```text
PUBLICATION_GATE=PASS technical_copy_set=PASS independent_consumer=NOT_ESTABLISHED concrete_reuse_request=NOT_ESTABLISHED license_selection=UNSELECTED repository_creation=DEFERRED
PUBLIC_REPO_CREATE=DEFERRED donor_producer=donor-bound second_consumer=FIXTURE_ONLY independent_consumer=NOT_ESTABLISHED concrete_reuse_request=NOT_ESTABLISHED license_selection=UNSELECTED new_skill=DEFERRED
```

Existing technical evidence remained unchanged:

- `ENVELOPE_V9_EXTRACTION_TRANSFORM_PASS`;
- `SECOND_CONSUMER_FIXTURE_PASS donor_identity=v8-independent geometry=heterogeneous generic_markers=3`;
- nine-case Chrome matrix: **PASS**;
- target layout/text/transparency: **PASS**;
- render target: `62d68a97a354ffc3c82efdbe2396730f5ca90cafdfa5579c59504b7df9c35b4f`;
- motion-on: left **7**, right **12** changed pairs over 13 samples;
- browser-wide reduced motion: **0/0**;
- motion-off: **0/0**;
- v8 -> v9 motion-subtree equivalence: 15 generated assets;
- public GitHub-profile v9 playback: `NOT_RUN`;
- cross-document hard synchronization: not claimed.

The unchanged render-target fingerprint confirms P7 changed publication metadata/validation only, not the rendered v9 target.

## Why the P6 fixture does not satisfy demand

The P6 second donor is a deliberately heterogeneous **synthetic fixture** executed from the copied package tree. It proves that the portable transformer no longer requires v8/Project Map implementation identity.

It is not an external user, repository, integration, or concrete reuse request. Counting a fixture manufactured by the donor project as an independent consumer would make the publication gate circular, so the manifest keeps:

```text
independent_consumer=NOT_ESTABLISHED
concrete_reuse_request=NOT_ESTABLISHED
```

## License snapshot and claim boundary

Immediately before P7, GitHub repository metadata for `nekomario28/nekomario28` reported no detected repository license (`license: null`), and the root tree contained no root `LICENSE`/`COPYING` file. P7 therefore records `license_selection=UNSELECTED` and does **not** choose MIT, Apache-2.0, or another license automatically.

This is a publication-readiness snapshot, not a legal conclusion about copyright ownership or every historical file's provenance. Before external publication, the chosen copy set still needs an explicit license decision appropriate to its actual ownership/provenance.

## Publication trigger

Do not create `profile-envelope` merely because the package is technically copyable.

Reconsider repository creation only when all of the following are true in one current-authority review:

1. an independent consumer exists **or** a concrete reuse request is present;
2. the declared extracted package still passes standalone structure/extraction and required browser evidence;
3. a publication license has been selected explicitly for the intended copy set;
4. the manifest is updated to the current evidence rather than inheriting an old PASS after source/package changes.

At that point, change the readiness fields in one reviewed change and let the validator derive `repository_creation=READY`. Do not bypass or delete the gate just to create the repository.

## Skill boundary

A standalone `profile-envelope` Skill remains **DEFERRED**. The current reusable guidance continues to belong primarily to `readme-visual-design`, `animation-composition`, and project-incubator reuse evidence. A new Skill still requires recurrence outside this donor plus a discriminating evaluation showing that existing guidance is insufficient.
