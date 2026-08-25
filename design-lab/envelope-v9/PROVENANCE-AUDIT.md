# Envelope v9 portable copy-set provenance audit

Status: **history audited / publication license still UNSELECTED / legal conclusion NOT_CLAIMED**  
Reviewed: **2026-08-25 JST**

This receipt narrows one remaining publication unknown for the candidate `profile-envelope` repository: where the declared six-file copy set entered this donor repository and what can actually be established from repository history.

It does **not** select a license, provide legal advice, or prove exclusive copyright ownership. The P7 publication gate remains authoritative and keeps repository creation `DEFERRED` until real external demand exists and a publication license is chosen explicitly.

## Audited copy set

The current `portable-package-manifest.json` declares five portable-core files plus one standalone GitHub-profile adapter:

| Destination role | Donor path | Current blob | Observed introduction |
| --- | --- | --- | --- |
| contract | `design-lab/scripts/profile_envelope_contract.py` | `8ff931cfcbc21f1f7bf76339de42d913724880cc` | added in P1 commit `82a40d05c3160124a08e192c5cd1384e38e794b6` |
| vector text | `design-lab/envelope-v9/vector_text.py` | `95b4d094abd0ce9d3671d95e8a1da30d84c84be2` | added in P2 commit `ed11b1c01ed3506e1bb6d16563ba014da962681e` |
| config schema | `design-lab/profile-envelope-config.schema.json` | `71af412dc3400e72dec7261a9891a2bd05326986` | added in commit `22c1c5ada647d796e84670e10d6fc39b6dac310b` |
| opaque example | `design-lab/profile-envelope-config.example.json` | `ad7763f29f3d4e92c0063be190af88fec37da8b1` | added in commit `390b00315af575a97e531fe39c15580fcecd5f6c` |
| transparent example | `design-lab/profile-envelope-config.transparent.example.json` | `f84884734f98de9dbfdd44a982b1af952bf89fa0` | added in P1 commit `82a40d05c3160124a08e192c5cd1384e38e794b6` |
| GitHub-profile transformer | `design-lab/envelope-v9/github_profile_transform.py` | `e7c4799cd96f578f3153a26cdca966bb6dfc01fb` | added in P5 commit `6fb4bdf1ef33402ad5635ad188410d5dbed2eb51` |

The blob identities above are the current-main blobs at the audited profile main lineage immediately after P7 receipt commit `cc482c5cf74b6bb3f5d760a0a6d4a92ff31aa502`.

## Introduction evidence

Repository history shows each audited file appearing as a repository-local **added** file rather than a rename from another path in this repository:

- `profile-envelope-config.schema.json`: one-file add, 113 lines, commit `22c1c5ada647d796e84670e10d6fc39b6dac310b`;
- `profile-envelope-config.example.json`: one-file add, 26 lines, commit `390b00315af575a97e531fe39c15580fcecd5f6c`;
- P1 commit `82a40d05c3160124a08e192c5cd1384e38e794b6`: adds the 307-line dependency-free contract normalizer and the 26-line transparent example;
- P2 commit `ed11b1c01ed3506e1bb6d16563ba014da962681e`: adds the 247-line `vector_text.py` together with the first v9 donor implementation;
- P5 commit `6fb4bdf1ef33402ad5635ad188410d5dbed2eb51`: adds the 247-line standalone `github_profile_transform.py` while shrinking the donor producer.

Those commits are all in the `nekomario28/nekomario28` history and identify `Yuu` / `nekomario28` as the repository commit author. Later P3/P4/P6 commits modify the vector/transformer implementations, but do not change the fact that their repository-local lineage begins as new files in this donor.

## Current dependency / attribution observations

The audited current files establish the following technical facts:

- `profile_envelope_contract.py` describes itself as operating without third-party dependencies and imports only Python standard-library modules;
- `vector_text.py` does not embed or redistribute a font and describes its glyph construction as repository-owned segment geometry;
- `github_profile_transform.py` imports Python standard-library modules plus the local `profile_envelope.vector_text` kernel; it contains no v7/v8 or Project Map implementation import;
- the schema and two examples are data/contract files rather than vendored runtime libraries;
- the existing extraction validator already proves the copied Python package uses only standard-library/extracted-package dependencies and contains none of the configured donor-specific forbidden tokens.

No file-level third-party copyright, SPDX, or license notice was observed in the inspected current Python-file headers. That absence is only an observation; it is not proof that every idea or implementation expression is independently copyrightable/original, nor that no external influence ever occurred.

## What this audit does not prove

Repository history alone cannot establish all rights needed for redistribution. In particular, this audit does not prove:

- exclusive copyright ownership of every line;
- absence of external conceptual inspiration or generated-code provenance that is not represented in Git history;
- that any particular open-source license is the correct publication choice;
- that the donor repository's other assets, v7/v8 renderers, Project Map data, Activity data, character media, or historical Design Lab files may be copied into the future package;
- that an external consumer or concrete reuse request exists.

The proposed public copy boundary intentionally excludes those donor-only assets and producers.

## Publication consequence

The history audit reduces uncertainty about the six-file candidate boundary, but it does **not** change the P7 readiness state:

```text
technical_copy_set=PASS
independent_consumer=NOT_ESTABLISHED
concrete_reuse_request=NOT_ESTABLISHED
license_selection=UNSELECTED
repository_creation=DEFERRED
```

Do not flip `license_selection=SELECTED` merely because the files have a clean repository-local introduction history. The explicit publication decision should consider ownership/provenance and the intended downstream reuse context together.

## Minimal future package shape

If the P7 gate later becomes eligible, start from the already-proven copy boundary rather than exporting Design Lab history:

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
├── README.md                 # new publication-facing documentation
└── LICENSE                   # must be chosen explicitly at publication time
```

Do not add packaging frameworks, hosted services, installers, donor artwork, fonts, Project Map data, Activity data, or a universal renderer until a real consumer requires them. A `pyproject.toml`, CLI entry point, release workflow, versioning policy, or package-index publication should be justified by the first real consumption path rather than created speculatively.

## Next safe action

There is no remaining profile-envelope implementation task that should be manufactured solely to create progress. Wait for either an independent consumer or a concrete reuse request. When one appears:

1. compare that consumer's actual needs with this exact six-file boundary;
2. re-audit any copy-set changes since this receipt;
3. make an explicit ownership/provenance + license decision for the intended package;
4. re-run standalone extraction and required browser evidence on the exact proposed release revision;
5. only then allow the P7 machine state to derive `repository_creation=READY`.
