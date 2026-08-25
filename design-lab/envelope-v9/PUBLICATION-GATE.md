# Envelope v9 / Profile Envelope publication gate

Status: **technical product copy set PASS / private working repository CREATED / product repository-history provenance PASS / public publication DEFERRED**  
Reviewed: **2026-08-26 JST**

This receipt keeps four claims separate:

1. historical donor extraction readiness;
2. private working-repository development authority;
3. current P10 product-copy-set technical/provenance readiness;
4. authority to publish either a clean release or the whole existing private repository.

The first three are now established at their stated scope. Public publication remains deferred because no redistribution license has been selected, and whole-repository publication has not been audited.

## Current working repository

- repository: `nekomario28/profile-envelope`;
- visibility: **private**;
- current working main: `960171849769830b0fa72b00c438c7c716ab2e3c`;
- initial donor source: `nekomario28/nekomario28@bf3960dc85eebf8e25c5e8a015e968322a984597`;
- initial retained filtered-history head: `ee0a07b9e85f7a57c6b2146149e68420202f4fe5`;
- first post-bootstrap working main: `d916b057ec897ceef94bdee293d4e02f42e46d1b`.

The initial six-file extraction preserved retained donor Author/Committer metadata through path-filtered Git history. P9/P10 then added/modified design-system code directly in the private working repository; those deltas are covered by the current product repository-history audit rather than falsely attributed back to the donor.

## P10 renderer state

- P9 grammar fingerprint: `24ee74fdb9ae669390244af16463220e0f9b0f9e0661159c19b0ced0a69a4ced`;
- P10 geometry implementation: `c73c902661ceadd93ae15a89d9eea352f2d1ac5e`;
- frame-rail grammar projection: **opt-in**;
- legacy default: **preserved**;
- global design-grammar renderer authority: **false**;
- exact proven donor frame-geometry equivalence: **PASS / 15 SVG assets**.

The 100px donor remains byte-identical under the opt-in semantic rail projection, while the heterogeneous 120px right-side fixture resolves to x=102 from `local_width - 18` rather than inheriting the historical x=82 literal. This does not establish browser, perceptual, responsive-layout, live-playback, or public-profile P10 PASS.

## Current P10 product release boundary

Product-content revision `a4a954f22aa3511540c17723d88a33de38733910` declared and closed an **eight-file** product copy set. The provenance-only main `960171849769830b0fa72b00c438c7c716ab2e3c` does not alter those eight product bytes.

Release-copy-set exact-head evidence:

- ShotFork run `32883641201`, job `97918842614` — **SUCCESS**;
- **18 tests PASS**;
- isolated Python `-I` execution of only the eight declared product files — **PASS**;
- Python dependency boundary — standard library/local package only;
- donor legacy-vs-grammar equivalence — **PASS / 15 assets**.

P10 product provenance exact-head evidence:

- ShotFork run `32884162091`, job `97920532341` — **SUCCESS**;
- exact provenance head: `960171849769830b0fa72b00c438c7c716ab2e3c`;
- **19 tests PASS**;
- all eight expected product blob identities — **PASS**;
- grammar fingerprint unchanged — **PASS**;
- donor legacy-vs-grammar equivalence — **PASS / 15 assets**;
- `historical_six_file_donor_audit=PASS`;
- `p9_p10_delta_repository_history_audit=PASS`;
- `product_copy_set_repository_history_audit=PASS`;
- `legal_conclusion=NOT_CLAIMED`;
- `whole_repository_publication_audit=NOT_ESTABLISHED`.

## Current machine gate

```text
technical_copy_set=PASS
independent_consumer=NOT_ESTABLISHED
concrete_reuse_request=ESTABLISHED
license_selection=UNSELECTED
repository_creation=DEFERRED
working_repository=CREATED_PRIVATE
current_working_main_sha=960171849769830b0fa72b00c438c7c716ab2e3c
p10_product_files=8
p10_product_technical_standalone=PASS
p10_product_repository_history_audit=PASS
legal_conclusion=NOT_CLAIMED
whole_repository_publication_audit=NOT_ESTABLISHED
public_release=DEFERRED
```

`repository_creation=DEFERRED` continues to mean the **public publication/repository gate**, not absence of a private working repository.

The existing public-readiness rule remains:

```text
READY =
  technical_copy_set == PASS
  AND (independent_consumer == ESTABLISHED
       OR concrete_reuse_request == ESTABLISHED)
  AND license_selection == SELECTED
```

The explicit reuse request satisfies the demand term. It does not select a license.

## Two publication operations, two gates

### A. Clean product release/export

A future clean public release may start from the audited eight-file product boundary, then add only explicitly reviewed publication-facing support files. Before release:

- choose the redistribution license explicitly for the exact release set;
- review provenance/licensing of added support files;
- rerun standalone and render/browser/motion evidence required by the intended claims;
- record the exact exported revision.

### B. Make the existing private repository public

Changing the current private repository to public visibility exposes more than the eight-file product set: support/evidence files and repository history become part of the publication event. That operation therefore remains **DEFERRED** until `whole_repository_publication_audit=ESTABLISHED`, a license/publication decision is explicit, and the exact visibility-transition revision is revalidated.

Do not infer whole-repository publication authority from product-copy-set provenance PASS. A clean export is the preferred narrower route when exposing private development history is unnecessary.

## Evidence retained from earlier phases

Earlier evidence remains scoped rather than erased:

- bootstrap carrier `32868834661` — SUCCESS;
- first exact extracted-head validation `32869436824` — SUCCESS;
- portable regression `32871700639` / `97880025443` — SUCCESS;
- P9 design grammar `32876973365` / `97897147907` — SUCCESS;
- P10 geometry implementation `32881179871` / `97910809919` — SUCCESS;
- P10 geometry evidence head `32881471260` / `97911747424` — SUCCESS;
- nine-case historical Chrome matrix — PASS for its tested donor/revision;
- public GitHub-profile v9/P10 playback — `NOT_RUN`;
- cross-document hard synchronization — not claimed.

These earlier browser/render proofs do not automatically transfer to a future default grammar migration or public release revision.

## Skill boundary

A standalone `profile-envelope` Skill remains **DEFERRED**. The reusable lessons belong to existing cross-project guidance unless an independent visual-system consumer and discriminating evaluation justify a new Skill.
