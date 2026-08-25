# Envelope v9 / Profile Envelope provenance audit

Status: **historical donor six-file audit PASS / current P10 eight-file product repository-history audit PASS / legal conclusion NOT_CLAIMED / whole private repository publication audit NOT_ESTABLISHED**  
Reviewed: **2026-08-26 JST**

This receipt distinguishes the historical extraction boundary in `nekomario28/nekomario28` from the current product boundary developed in the private `nekomario28/profile-envelope` working repository.

It does **not** select a license, provide legal advice, prove exclusive copyright ownership, or authorize changing the existing private working repository to public visibility.

## 1. Historical donor extraction boundary — six files

P8 audited the six files that were copied from this donor repository into the initial private working repository at exact donor revision `bf3960dc85eebf8e25c5e8a015e968322a984597`:

| Destination role | Donor path | Extracted blob | Observed donor introduction |
| --- | --- | --- | --- |
| contract | `design-lab/scripts/profile_envelope_contract.py` | `8ff931cfcbc21f1f7bf76339de42d913724880cc` | P1 `82a40d05c3160124a08e192c5cd1384e38e794b6` |
| vector text | `design-lab/envelope-v9/vector_text.py` | `95b4d094abd0ce9d3671d95e8a1da30d84c84be2` | P2 `ed11b1c01ed3506e1bb6d16563ba014da962681e` |
| config schema | `design-lab/profile-envelope-config.schema.json` | `71af412dc3400e72dec7261a9891a2bd05326986` | `22c1c5ada647d796e84670e10d6fc39b6dac310b` |
| opaque example | `design-lab/profile-envelope-config.example.json` | `ad7763f29f3d4e92c0063be190af88fec37da8b1` | `390b00315af575a97e531fe39c15580fcecd5f6c` |
| transparent example | `design-lab/profile-envelope-config.transparent.example.json` | `f84884734f98de9dbfdd44a982b1af952bf89fa0` | P1 `82a40d05c3160124a08e192c5cd1384e38e794b6` |
| GitHub-profile transformer | `design-lab/envelope-v9/github_profile_transform.py` | `e7c4799cd96f578f3153a26cdca966bb6dfc01fb` | P5 `6fb4bdf1ef33402ad5635ad188410d5dbed2eb51` |

Repository history showed those donor paths entering as repository-local additions rather than renames from another donor path. The private working extraction retained the relevant Author/Committer metadata through path-filtered history before path normalization.

That P8 evidence remains authoritative for the **historical six-file donor lineage**. It must not be rewritten to pretend the later P9/P10 working-repository files came from this donor.

## 2. Current P10 working product boundary — eight files

The private working repository evolved after extraction. Its P10 product-content revision `a4a954f22aa3511540c17723d88a33de38733910` declares exactly eight product files:

```text
src/profile_envelope/contract.py
src/profile_envelope/vector_text.py
src/profile_envelope/github_profile_transform.py
src/profile_envelope/design_grammar.py
schema/profile-envelope-config.schema.json
examples/opaque-safe.json
examples/transparent-safe.json
design/reference-grammar.json
```

The two design-grammar files were not retroactively copied from this donor:

- working-repository P9 commit `5e13f266f78d06acc1b680faac71cfce477296c1` added `design/reference-grammar.json` and `src/profile_envelope/design_grammar.py` as repository-local new files;
- working-repository P10 commit `c73c902661ceadd93ae15a89d9eea352f2d1ac5e` extended `design_grammar.py` and explicitly modified the inherited transformer for the opt-in frame-rail grammar projection.

The current product blobs at P10 product-content revision `a4a954f22aa3511540c17723d88a33de38733910` are:

| Product path | Current blob | Provenance route |
| --- | --- | --- |
| `src/profile_envelope/contract.py` | `8ff931cfcbc21f1f7bf76339de42d913724880cc` | P8 donor lineage; unchanged since extraction |
| `src/profile_envelope/vector_text.py` | `95b4d094abd0ce9d3671d95e8a1da30d84c84be2` | P8 donor lineage; unchanged since extraction |
| `src/profile_envelope/github_profile_transform.py` | `f4b509fd2f8ad6d6e60729fcba5589ebf0feaacd` | P8 inherited lineage + explicit P10 working-repository modification |
| `src/profile_envelope/design_grammar.py` | `6320ca6c24474de977fe994ba91ad480b468684b` | P9 working-repository addition + P10 modification |
| `schema/profile-envelope-config.schema.json` | `71af412dc3400e72dec7261a9891a2bd05326986` | P8 donor lineage; unchanged since extraction |
| `examples/opaque-safe.json` | `ad7763f29f3d4e92c0063be190af88fec37da8b1` | P8 donor lineage; unchanged since extraction |
| `examples/transparent-safe.json` | `f84884734f98de9dbfdd44a982b1af952bf89fa0` | P8 donor lineage; unchanged since extraction |
| `design/reference-grammar.json` | `b4902be138e8ba831587d75dce0354b7ad668903` | P9 working-repository addition; unchanged after introduction |

This closes the **repository-history provenance audit for the declared eight-file product set**. The working repository's `release-copy-set.json` is the current product-boundary authority; this donor manifest remains the historical extraction/provenance authority.

## 3. Technical dependency and notice observations

The current release-copy-set regression proves the four product Python files import only Python standard-library modules or the local `profile_envelope` package, and the eight files run from an isolated temporary copy without reading the development checkout.

Repository search during the P10 review returned no `SPDX` or `Copyright` string matches in `nekomario28/profile-envelope`. That is an observation only. Absence of such strings does not prove exclusive ownership, originality, or absence of external/generated conceptual provenance that is not encoded in Git history.

## 4. Claim boundary

Established repository-history state:

```text
historical_six_file_donor_audit=PASS
p9_p10_delta_repository_history_audit=PASS
product_copy_set_repository_history_audit=PASS
legal_conclusion=NOT_CLAIMED
whole_repository_publication_audit=NOT_ESTABLISHED
concrete_reuse_request=ESTABLISHED
license_selection=UNSELECTED
public_release=DEFERRED
```

This audit does **not** prove:

- exclusive copyright ownership of every line or design decision;
- that a particular open-source license is the correct choice;
- that donor-only artwork/data/renderers outside the declared product boundary are redistributable;
- that every support/evidence file or every reachable historical object in the private working repository has been reviewed for public exposure;
- browser, perceptual, responsive-layout, live-playback, or public-profile P10 acceptance.

## 5. Product publication versus repository visibility

Two future publication operations have different authority requirements:

1. **Clean product release/export** — start from the audited eight-file product set, add only explicitly reviewed publication-facing support files, select a redistribution license for that exact release, and re-run the evidence required by its claims.
2. **Flip the existing private `profile-envelope` repository to public** — this exposes more than the eight-file product set, including support files and private development history. It therefore requires a separate whole-repository publication audit before the visibility mutation.

Product-copy-set audit PASS is **not** whole-repository publication authority. If whole-repository review is unnecessary or undesirable, prefer a clean public export/release surface rather than weakening this boundary.

## 6. Current publication consequence

The explicit 2026-08-26 reuse/extraction request means demand is established. The remaining public gate is not demand; it is the explicit license/publication decision plus the evidence appropriate to the exact publication operation.

Until that is completed:

```text
working_repository=PRIVATE
license_selection=UNSELECTED
public_release=DEFERRED
existing_private_repo_visibility_flip=DEFERRED
```

Do not infer `license_selection=SELECTED` from repository-history provenance PASS.
