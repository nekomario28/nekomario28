# Envelope v7 evidence

Status after live verification: **LIVE / target-layout PASS / Summer public-playback PASS (bridge + Projects/Activity composite outer rails)**.

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
- Envelope v7 panel generation treats current checked-in `project-map/galaxy.svg` and `assets/github-contributions-dark.svg` as authorities and regenerates mounted canvas assets rather than freezing Design Lab copies.

## Derived-source synchronization receipt

After v7 first went live, `project-map/galaxy.svg` advanced while `assets/profile-projects-canvas.svg` was still an older derivative. This exposed two automation defects rather than a Project Map data defect:

- v7 validation checked geometry/motion but did not prove that mounted canvases came from the current authoritative source;
- exact-SHA checkout left push-triggered seasonal jobs on a detached HEAD while the writeback step used a bare `git push`.

PR #41 (`Guard Envelope v7 derived source sync`) added source SHA-256 fingerprints and stale-derivative validation. Exact-head run `32751928244`, job `97510643671`, succeeded with `source_sync=PASS`, target-layout PASS, and `ENVELOPE_V7_LIVE_SOURCE_SYNC_PASS`. The detached-HEAD writeback was then fixed to `git push origin HEAD:main`; bot commit `18c091cbe7f3e40ee7b56afbdd952a414b204395` regenerated the live Summer canvases from then-current sources.

That receipt originally referred to the then-current Contributed external-rail presentation. The later profile-local Galaxy world release changed Contributed presentation to an external halo; the atomic Project Map publish receipt below supersedes the old presentation-specific detail while retaining the source-fingerprint contract.

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

## Summer bridge public playback receipt

The first accepted v7 live playback proof established representative rail motion on the actual public GitHub profile.

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

The first proof attempt failed only because current Chrome did not expose CDP without a dedicated `--user-data-dir`; it is not product evidence. A second attempt successfully loaded the real v7 public profile and sampled only the Projects canvas left outer strip for 9 seconds, but observed zero changed pairs. That zero-change result was retained instead of being discarded and directly led to the composite placement correction below.

## Composite motion-layer correction

The 9-second Projects-left zero-change diagnostic was **not** explained by sparse phase coverage. The configured Projects window and left-particle phases should have produced visible motion during that interval. Source inspection found the real cause in `render_continuous_canvas.py`:

- `inject()` used `svg_text.replace("</svg>", layer + "\n</svg>", 1)`;
- Projects and Activity are outer 900px SVG stages that contain nested `<svg>` foreground viewports;
- therefore the v7 global rail layer was inserted before the **first nested** `</svg>` instead of before the outer/root `</svg>`;
- the motion existed, but inside the mounted foreground viewport, so the outer Projects left strip correctly showed no rail changes.

PR #44 (`Fix Envelope v7 composite motion layer placement`) changed injection to target the final/root closing SVG and added a structural invariant: exactly one `v7-global-window` must exist and it must be a direct child of the root SVG.

- Exact head: `2cab6b3adf23708e0f850bbbb38545c12b06acc9`.
- Workflow run: `32755375291`.
- Job: `97521572849`.
- Result: `SUCCESS`.
- Validation: all 4 seasons / 12 assets PASS, source-sync PASS, desktop/mobile target-layout PASS.
- Merge: `1a28248811f0b56cd3020973abb243c036159fb5`.
- First regenerated live Summer assets after the fix: bot commit `be7a1519baeeff9dad9957d634e34e457aba7790`.

Post-regeneration structure confirmed that the nested Project Map / contribution SVG closes first and `v7-global-window` follows at the outer 900px stage level for both Projects and Activity.

### Composite public playback proof

PR #45 was a one-shot read-only proof carrier and was closed unmerged.

- Exact head: `3d3a8d9de966b7b63beefee0882aac50d1972c01`.
- Workflow run: `32755621394`.
- Job: `97522354218`.
- Result: `SUCCESS` / `ENVELOPE_V7_COMPOSITE_PUBLIC_PLAYBACK result=PASS`.
- Actual public target: `https://github.com/nekomario28`.
- Main observed by the proof: `c125b5d44b05d6b6916e747dfe1d4d6a43b40dab`.
- Browser model: one persistent headless-Chrome page.
- Media state: `prefers-reduced-motion: reduce=false`, `no-preference=true`.
- Sampling: 25 captures over 12.0 seconds at 500 ms intervals.
- Isolation: only the outer 48 logical pixels on each side were evaluated; this excludes the nested Project Map starting at x=80 and the contribution chart starting at x=70.
- Projects changed adjacent pairs: left `18`, right `20`.
- Activity changed adjacent pairs: left `11`, right `12`.
- Later localized bboxes appeared at the expected rail positions (displayed left around x=15..19 and the corresponding right-edge crop around x=26..30), independently of initial whole-strip page settling.
- Cross-document hard synchronization remains **not claimed**.

This closes the old Projects-left zero-change diagnostic: it was a real renderer placement bug, not a false-negative sampling window. The live verification state now points to this stronger Projects/Activity composite outer-rail proof rather than only the earlier representative bridge proof.

## Atomic Project Map → profile canvas publish

A final workflow-boundary problem remained after source fingerprinting: `update-knowledge-graph.yml` writes Project Map updates with `github-actions[bot]` using `GITHUB_TOKEN`. GitHub intentionally prevents such commits from recursively triggering a second workflow. Therefore a successful `update project map` bot commit could still leave `profile-projects-canvas.svg` stale even though the seasonal workflow listed `project-map/galaxy.svg` in its push paths.

Commit `c125b5d44b05d6b6916e747dfe1d4d6a43b40dab` demonstrated this exact case: the canonical Galaxy changed while the Projects canvas still carried the previous source SHA-256.

PR #46 (`Refresh Project Map and profile canvas atomically`) removed the cross-workflow dependency:

- exact head: `d5c73955e85d2f0cc20d03f4bf4586b3d4bd2cb2`;
- workflow run: `32756119667`;
- publish job: `97524027994`;
- generated map validation: `14 owned + 1 accepted Contributed`, profile-local Galaxy background + external halo verified;
- Envelope refresh result: Summer `changed=true`;
- `ENVELOPE_V7_VALIDATION_PASS seasons=4 assets=12 extent=1662 source_sync=PASS`;
- desktop/mobile target-layout PASS;
- PR-only gate: `PROJECT_MAP_ENVELOPE_ATOMIC_REFRESH_PR_PASS`;
- publish commit step correctly skipped on the PR.

The workflow now:

1. generates and validates the canonical Project Map;
2. refreshes Envelope v7 from that generated map **inside the same publish job**;
3. validates all v7 assets against the generated source;
4. stages the Project Map, mounted live assets, and `live-theme.json` together;
5. writes one commit with `git push origin HEAD:main`;
6. runs the same generate/validate/refresh path on workflow-file PRs without publishing.

PR #46 squash-merged as `3aec3079b40bd1d1841956e02c9b68944ae0270b`. Its main-push workflow immediately produced the first atomic production receipt:

- bot commit: `63cb430f3ae079f0795a738602b5ae8ce35c1d1f`;
- message: `update project map and profile canvas`;
- the generated Galaxy SVG was already current, while `project-map/graph.json` and `assets/profile-projects-canvas.svg` changed together;
- Projects canvas source SHA-256 advanced from `77d926143107d27578fb1889cea188bd5ead7a17581394a8ae9a15c1ef16efd7` to `299f4456c251d13d5e806df22c04449189b58380e6242a1c89a7e5b27bf884e5`;
- Summer `live_verification=PASS` was preserved across the same-target refresh.

The authoritative source and its mounted Projects derivative therefore no longer depend on a second workflow being recursively triggered by a bot commit.

## Verification-state retention

A live playback receipt should survive same-season derived-asset refreshes, but it must not silently transfer to a different seasonal target. `promote-season.py` preserves `PASS` plus its receipt metadata only when the active season, Envelope version, seasonal source, and global-motion-space target remain the same. A season/source/Envelope target change resets the new live state to `NOT_RUN` and requires a new target-surface proof. Renderer/layout changes are required to advance the Envelope version before release, which also invalidates the receipt.

Current Summer receipt scope is `projects-activity-composite-outer-rails-public-profile`, backed by run `32755621394` / job `97522354218`. This remains a per-document playback statement; it does not claim one shared runtime clock or frame-perfect synchronization across independent GitHub README image documents.
