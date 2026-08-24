# Envelope v4 GitHub render evidence — 2026-08-24

## Purpose

Record target-render evidence for the two README-area enclosure strategies without promoting either to live main merely because source/CI validation passed.

## Segmented bridge candidate

Preview PR: `#30`

Clean candidate head before temporary proof instrumentation:

- `4292b507eb7acf56efef40f89c03f571aa5c3a79`

Seasonal/promotion validation:

- run `32696060316`
- job `97338223492`
- all seasonal policy/variant validation: SUCCESS
- promotion dry-run: SUCCESS
- stable envelope validation: SUCCESS
- live mutation: SKIPPED by design on pull request

Actual GitHub branch README capture:

- render proof run `32696523661`
- artifact `envelope-v4-github-render-proof`
- desktop dark screenshot: captured successfully
- mobile dark screenshot: captured successfully

Observed result:

- no obvious horizontal overflow in either capture;
- hero, character image, project map, activity graph and footer remain readable;
- bridge chrome survives GitHub rendering and responsive shrinkage;
- the bridge reads primarily as a dark transition/background continuation, not as a literal full-height rail around arbitrary content.

Decision: `PREFERRED_REFINEMENT`, not live promotion.

## Single-table frame candidate

Shadow PR: `#31`

Actual GitHub branch README capture:

- render proof run `32696767046`
- seasonal read-only validation run `32696766978`
- artifact `envelope-v4-table-github-render-proof`

Observed result:

- GitHub preserves the three-column table structure;
- desktop obtains a literal surrounding table/frame;
- GitHub-owned borders and cell padding become visually dominant;
- mobile significantly compresses the center column and all primary visuals;
- no obvious horizontal overflow was observed, but the responsive quality is materially worse than the segmented approach.

Decision: `REJECTED`. PR closed unmerged and preserved as negative evidence.

## Font portability observation

Both headless GitHub captures showed missing-glyph boxes for Japanese text rendered *inside SVG section assets*. The runner environment does not provide the client font assumptions used by the SVG `<text>` element.

Evidence boundary:

- this proves the asset is client-font-dependent;
- it does **not** prove that every Japanese user's browser or OS lacks suitable glyphs;
- portable visual assets should not require client-installed Japanese fonts for essential section labels.

Preferred next correction: replace essential Japanese SVG label text with deterministic repository-owned vector outlines or another font-independent representation, then rerun target GitHub dark/mobile proof.

## Live boundary

Live main remains Envelope v3 while v4 is refined. No claim is made that README content can paint behind GitHub-owned page chrome, avatar/sidebar, pinned repositories, or other host UI. Public SMIL playback is also a separate evidence gate from static/dark/mobile layout proof.
