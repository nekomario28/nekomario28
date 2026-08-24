# Envelope v7 evidence

Status before live merge: **LIVE_CANDIDATE / target-layout PASS**.

## Authoritative branch gate

- Pull request: #40
- Clean read-only workflow run: `32748702976`
- Job: `97500259376`
- Result: `SUCCESS`
- Source/generation proof: `ENVELOPE_V7_VALIDATION_PASS seasons=4 assets=12 extent=1662`
- Target layout proof: real GitHub branch README through headless Chrome CDP.

Measured responsive geometry:

- desktop: hero `838px`; character row `93.11 + 651.77 + 93.11 = 837.99px`;
- mobile 430px viewport: hero `364px`; character row `40.44 + 283.11 + 40.44 = 363.99px`.

The proof requires the character side surfaces and external foreground image to stay on one row, have no inline gap, load successfully, match the hero width, and remain inside the README container. Full-width attribution, Projects canvas, Activity canvas, section bands, and footer must also match the hero width.

## Architecture decision

Selected: **Hybrid C**.

- Third-party character media remains a normal external README image; repository-owned side surfaces provide the visible background around it.
- Repository-owned Project Map and contribution SVG bodies are embedded into generated 900px canvas SVGs, preserving their real checked-in data while filling the left/right background.
- All logical Y spans are visible rendered windows in one 1662px coordinate space.
- The shared particle field is clipped by local windows; no edge-triggered opacity lifecycle is used.
- Independent SVG documents do not imply a shared runtime clock.

Rejected/retained as negative lineage:

- three-piece rows for repository-owned Project/Activity SVGs: unnecessary wrapping risk;
- one composite Character SVG containing the cross-origin official image: portability/CSP boundary;
- host-native tables: previously rejected for visible GitHub table chrome and mobile compression.

## Remaining proof after merge

Public live playback is `NOT_RUN` for Envelope v7. The previous Envelope v6 Summer playback PASS must not be inherited across the renderer/layout version change. Re-earn Summer playback on the actual public profile after merge using one persistent page and a sampling window long enough to catch sparse rail motion.
