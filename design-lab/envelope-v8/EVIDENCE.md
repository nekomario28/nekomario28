# Envelope v8 evidence

Status: **LIVE / unified static PASS / desktop+mobile seams PASS / Summer public rail playback PASS**

Envelope v8 keeps the proven v7 1662px logical global-motion field while changing the visible presentation into one unified rectangular surface. GitHub README SVG documents remain independent runtime documents; no shared runtime clock or frame-perfect cross-document synchronization is claimed.

## Static and layout evidence

The v8 validator renders all four seasons and requires the unified-v1 presentation grammar, all nine README presentation assets, the three packed short-window surfaces, source fingerprints for mounted Project Map / Activity data, reduced-motion fallback, clipped global motion, and the inherited 32s global field.

The final seamless-layout proof measures the actual GitHub branch rendering at desktop and mobile widths. All seven physical boundaries measured **0px** in both modes:

- hero -> character
- character -> attribution/projects packed transition
- attribution/projects transition -> Projects label
- Projects label -> Projects canvas
- Projects canvas -> Activity packed header
- Activity header -> Activity canvas
- Activity canvas -> footer packed transition

The packed surfaces preserve logical global coordinates rather than deleting spans:

- attribution + character/projects bridge: global 654..730, physical height 76px
- Projects/Activity bridge + Activity label: global 1218..1318, physical height 100px
- Activity/footer bridge + footer: global 1538..1662, physical height 124px

## Project Map atomic publish evidence

PR #50 (`Include Envelope v8 packed assets in atomic publish`) closed the remaining alternate-publisher gap by adding all three README-mounted packed v8 surfaces to the Project Map workflow's atomic commit set.

Accepted exact-head evidence:

- head `a0d72abd53abf883f6079a0bf135e97cd1797644`
- run `32763739562`
- generate job `97548353570`: SUCCESS
- publish job `97548428392`: SUCCESS
- generated Project Map: 14 owned + 1 accepted Contributed
- arm-free profile-local Galaxy background + external halo: PASS
- `ENVELOPE_V8_UNIFIED_STATIC_PASS seasons=4 presentation_assets=9 packed_surfaces=3 skin=unified-v1`
- desktop/mobile seam proof: all seven gaps 0px
- `PROJECT_MAP_ENVELOPE_ATOMIC_REFRESH_PR_PASS`

PR #50 was squash-merged as `de743235acfddafa93fb3b378ecf08fbea921291`. Its push-triggered Project Map workflow then published `17f8085900b9e09b938c6f1317a93b4aebf9673d` (`update project map and profile canvas`), confirming the production atomic path still writes successfully.

## Summer public playback evidence

Proof carrier PR #51 (`TEMP: prove Envelope v8 public playback`) was intentionally **closed unmerged**.

Accepted exact-head evidence:

- proof head `3a900cd8374319217193673184f9823da9f24d57`
- run `32764113788`
- job `97549551648`
- result `ENVELOPE_V8_PUBLIC_PLAYBACK PASS`
- actual target `https://github.com/nekomario28`
- observed main before sample `17f8085900b9e09b938c6f1317a93b4aebf9673d`
- observed main after sample: same SHA
- main stable during the sample: true
- `prefers-reduced-motion: reduce=false`
- `prefers-reduced-motion: no-preference=true`
- one persistent Chrome page
- 25 samples over 12.0 seconds at 500ms intervals

Accepted scope is **8 non-hero repository-owned Envelope v8 documents / 14 rail strips**. The seasonal hero is deliberately excluded from the accepted rail-isolation scope because it contains unrelated local seasonal animation. The proof does not claim that hero rail motion was independently isolated.

Changed adjacent-pair counts:

| Document | Left | Right |
| --- | ---: | ---: |
| character side | 18 | 20 |
| attribution/projects transition | 7 | 4 |
| Projects label | 8 | 4 |
| Projects canvas | 19 | 21 |
| Activity header | 7 | 5 |
| Activity canvas | 14 | 9 |
| footer transition | 5 | 10 |

The proof logs retain localized particle-shaped examples on every tested rail, typically only 3-5 displayed pixels wide. Acceptance therefore does not rely only on broad page-level screenshot changes or mounted Project Map / contribution animation.

## Verification target identity

PR #52 (`Bind Envelope v8 playback proof to rendered target`) fixes PASS-retention semantics so a renderer/README/presentation change cannot inherit a stale PASS merely because the semantic Envelope version and season are unchanged.

The target fingerprint covers the tested public rail-playback surface:

- Envelope version
- presentation contract
- global motion contract
- current season visual configuration
- SHA-256 of `design-lab/envelope-v8/render_continuous_canvas.py`
- SHA-256 of `README.md`

Changing Project Map data is intentionally excluded because the accepted proof isolates Envelope rail strips from mounted Project Map / Activity foreground content.

Accepted #52 exact-head CI:

- head `30481fdce004380466efa79eeb1df8b7337dbd8e`
- run `32764545025`
- job `97550925593`
- Summer target fingerprint `7f95e61db7c2a3447879bf8dd0d160bbfa6f548c5ed54b6c311e79e7d63ef83c`
- Summer apply `changed=false`
- four-season static validation PASS
- desktop/mobile all seven seams 0px
- stable live source sync PASS

PR #52 was squash-merged as `babc3f2aa291e2db49ab6b9f499e3137ee0642ca`.

The Summer PASS receipt in `design-lab/live-theme.json` is bound to the fingerprint above. A same-target deterministic refresh may preserve that receipt; a changed target must invalidate it and return to `NOT_RUN` until public playback is re-earned.

## Claim boundary

What is established:

- the v8 unified static presentation renders for all four seasons;
- the visible desktop/mobile GitHub layout has zero measured gaps across all seven physical transitions;
- Project Map refreshes and v8 mounted derivatives have an atomic publish path, including all three packed surfaces;
- on the actual Summer public profile, every one of 14 tested non-hero rail strips showed motion during a stable 12-second sample;
- reduced-motion support remains present;
- source fingerprints and Contributed ownership separation remain validated by their respective pipelines.

What is **not** established:

- a shared runtime clock across separate SVG documents;
- frame-perfect cross-document phase synchronization;
- independently isolated hero rail playback in the accepted v8 public proof;
- that Actions success alone proves public playback without the separate browser proof above.
