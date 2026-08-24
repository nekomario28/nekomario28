# Profile section SVG font-independence proof — 2026-08-24

Problem discovered during Envelope v4 GitHub render tests: Japanese section labels inside repository-owned SVGs used client-side `<text>` and appeared as missing-glyph boxes in the headless GitHub proof environment.

Fix: PR `#32`, merged as `5bc90620a4acc34f2d83f8746d7ca1f51946f67d`, replaces `プロジェクト` and `活動` with deterministic vector outline paths and changes the seasonal renderer so all four seasons regenerate the same font-independent labels.

Validation evidence:

- local XML / 900x68 geometry: PASS
- local CairoSVG render for both labels: PASS
- all-season workflow run `32697562900`: SUCCESS
- proof-instrumented seasonal revalidation `32697607364`: SUCCESS
- actual GitHub branch README capture `32697607431`: SUCCESS
- desktop dark: both section labels visible, no tofu
- mobile dark: both section labels visible, no tofu; no obvious overflow introduced

CI now rejects `<text>` in generated or stable Projects/Activity section SVGs and requires outline paths.

Boundary: this fixes essential repository-owned SVG labels only. Browser/OS-rendered HTML text such as the copyright line may still depend on host fonts. Static section-label proof does not establish SMIL hero playback.
