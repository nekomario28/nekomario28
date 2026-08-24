# Envelope v7 evidence

Status after live verification: **LIVE / target-layout PASS / Summer public-playback PASS (representative v7 rail)**.

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

## Live promotion receipt

- PR #40 merged as `66a2c43ab0db5d918279c44663b6fdee128f6dfd`.
- Merge parent: `75da76d478a92d1d36404afb691517b95df85fb3` (`update project map`).
- Promoted tree: `b7446097b6ad80f5b8304fb6a4f871cbf20ddf6e`.
- The promoted tree was rebuilt directly on the latest main parent so the experimental 50-commit branch history and temporary `.noop*` / cleanup-marker files were not carried into main.
- The Project Map had advanced to the accepted-Contributed external-rail renderer before the v7 merge. Envelope v7 panel generation therefore treats current checked-in `project-map/galaxy.svg` and `assets/github-contributions-dark.svg` as authorities and regenerates mounted canvas assets on push/schedule rather than freezing Design Lab copies.

## Derived-source synchronization receipt

After v7 went live, `project-map/galaxy.svg` advanced to the accepted-Contributed external-rail renderer while `assets/profile-projects-canvas.svg` was still an older derivative. This exposed two independent automation defects rather than a Project Map data defect:

- v7 validation checked geometry/motion but did not prove that mounted canvases came from the current authoritative source;
- exact-SHA checkout left push-triggered seasonal jobs on a detached HEAD while the writeback step used a bare `git push`.

PR #41 (`Guard Envelope v7 derived source sync`) added source SHA-256 fingerprints and stale-derivative validation. Exact-head run `32751928244`, job `97510643671`, succeeded with `source_sync=PASS`, target-layout PASS, and `ENVELOPE_V7_LIVE_SOURCE_SYNC_PASS`. The detached-HEAD writeback was then fixed to `git push origin HEAD:main`; bot commit `18c091cbe7f3e40ee7b56afbdd952a414b204395` regenerated the live Summer canvases from current sources. The live Projects canvas contains the Contributed external rail and both Projects/Activity canvases carry their authoritative source fingerprints.

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

## Summer public playback receipt

Accepted proof: **PASS**, scoped to representative Envelope v7 rail playback on the actual public GitHub profile.

- Proof carrier: PR #42, closed unmerged.
- Final accepted head: `ae5b0dde67f1766c8e0a7ad37faa2de184175b96`.
- Workflow run: `32752864753`.
- Job: `97513627206`.
- Result: `SUCCESS`.
- Actual target: `https://github.com/nekomario28`.
- Live main observed by the proof: `18c091cbe7f3e40ee7b56afbdd952a414b204395`.
- Browser model: one persistent headless-Chrome page.
- Media state: `prefers-reduced-motion: reduce=false`, `no-preference=true`.
- Sample target: `profile-frame-bridge-character-projects.svg`, natural `900x32`, displayed approximately `846x30.08`.
- Sampling: 37 captures over 9.0 seconds at 250 ms intervals.
- Observed: 10 adjacent changed pairs; 9 were localized to the left/right rail edges.
- Left-edge examples: bboxes around `x=15..19`; right-edge examples: `x=827..832` in the displayed 846px bridge.
- Maximum localized adjacent change: 71 pixels.
- Cross-document hard synchronization remains **not claimed**.

Diagnostic lineage is intentionally retained. The first proof attempt failed only because current Chrome did not expose CDP without a dedicated `--user-data-dir`; it is not product evidence. A second attempt successfully loaded the real v7 public profile and sampled only the Projects canvas left outer strip for 9 seconds, but observed zero changed pairs. That negative result is kept as a composite-canvas diagnostic and is not generalized into a claim about all v7 documents. The accepted third run deliberately matched the known-good v6 bridge-proof method and isolated a v7 bridge with no unrelated Project Map animation.

Therefore `PASS` means: **v7 rail motion is visibly playing on a representative live Envelope v7 document in the tested public GitHub/headless-Chrome environment**. It does not mean every one of the 12 live assets has been independently observed animating, and it does not upgrade the architecture to frame-perfect cross-document synchronization.

## Verification-state retention

A live playback receipt should survive same-season derived-asset refreshes, but it must not silently transfer to a different seasonal target. `promote-season.py` therefore preserves `PASS` plus its receipt metadata only when the active season, Envelope version, seasonal source, and global-motion-space target remain the same. A season/source/Envelope target change resets the new live state to `NOT_RUN` and requires a new target-surface proof. Renderer/layout changes are required to advance the Envelope version before release, which also invalidates the receipt.
