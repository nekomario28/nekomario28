# Profile Design Lab

Experimental visual directions for the `nekomario28` GitHub profile.

The live profile is intentionally separate from this lab. Concepts can be compared, revised, or deleted here without turning the profile README into a gallery.

## Design lineage

| ID | Status | Meaning |
|---|---|---|
| D1 | archived | First animated neon/sakura SVG. Preserved exactly from commit `4fc69a45a60ad74a13ed75e46c40881bebb12880`. |
| D2 | archived lineage | Restrained indigo/sakura rewrite from commit `0c8aebb6c976c78e6ad940cf8f5a37c6db4883bd`. Useful as evidence, not the target aesthetic. |
| D3 | live system | Dark seasonal visual-envelope system. Four static-first seasonal heroes share one layout grammar. |
| D3.1 | live envelope v2 | Seasonal grammar expanded from the hero to Projects/Activity bands and footer. |
| D3.2 | motion envelope v3 | Redundant post-hero divider removed; each seasonal hero gains a small optional motion layer with a static/reduced-motion fallback. |
| D3.3 | envelope v4 shadow | Background/frame experiments tested in GitHub's actual dark desktop/mobile renderer. Segmented bridge remains the refinement candidate; HTML table enclosure is rejected. |

D1 and D2 are saved in `archive/`; neither should be silently overwritten when a later direction wins.

## D3 — dark seasonal concepts

### Spring

![Spring dark concept](seasons/spring-dark.svg)

### Summer

![Summer dark concept](seasons/summer-dark.svg)

### Autumn

![Autumn dark concept](seasons/autumn-dark.svg)

### Winter

![Winter dark concept](seasons/winter-dark.svg)

The palette and motif change, while username placement, dark base, spacing rhythm, border geometry, and section-envelope grammar remain stable.

Each current seasonal hero contains an **optional embedded SMIL motion layer**:

- spring: breathing mist + sparse drifting petals
- summer: sparse rain + water shimmer + tiny leaf sway
- autumn: faint ember breathing + sparse drifting leaves
- winter: moon haze + sparse slow snow

The complete static composition remains underneath the motion layer. Every source includes a `prefers-reduced-motion` fallback and contains no JavaScript. Actual motion playback on the public GitHub profile remains a separate runtime verification gate; source presence is not treated as proof of playback.

## Live promotion model

The root README never points directly at a seasonal experiment. Envelope v3 references these stable live assets only:

- `assets/profile-hero.svg`
- `assets/profile-section-projects.svg`
- `assets/profile-section-activity.svg`
- `assets/profile-footer.svg`

`assets/profile-divider.svg` remains available as an archived/optional envelope element but is no longer part of the live choreography.

`live-theme.json` records which seasonal source currently owns the complete live envelope. `scripts/promote-season.py` validates month mapping, approval flags, hero SVG XML/geometry, motion fallback policy, and the matching section chrome before promotion.

This means seasonal switching does not rewrite README structure. The README remains one selected projection while the Design Lab remains the source of candidates and lineage.

## Seasonal mapping

`theme-manifest.json` maps in the `Asia/Tokyo` timezone:

- March–May -> spring
- June–August -> summer
- September–November -> autumn
- December–February -> winter

`.github/workflows/update-seasonal-profile.yml` checks on the first day of every month at about 09:17 JST. A scheduled run applies the approved seasonal envelope; if the stable assets already match, the commit step is a no-op. Manual dispatch defaults to dry-run.

The workflow also runs read-only on pull requests and on relevant pushes, so policy/source changes can be validated before a live mutation. Representative dates exercise all four seasonal heroes, and all generated section/footer assets are geometry-checked.

## Visual envelope / pseudo-overlay

GitHub README content **cannot** place a real overlay over GitHub page chrome, the avatar/sidebar, pinned-repository UI, or other host-owned profile elements. README HTML/CSS/JS also cannot restyle the surrounding GitHub application.

Envelope v3 uses this live choreography:

`seasonal animated/static-first hero -> existing character content -> seasonal Projects band -> project map -> seasonal Activity band -> contribution graph -> seasonal footer`

The post-hero divider from v2 was removed after review because the hero already acts as the opening boundary. Keeping another full-width separator immediately after it fragmented the reading flow and weakened the illusion of one continuous composition.

The factual section labels remain full-width seasonal bands, so the palette/motif recurs through the vertical reading path without putting a decorative separator at every boundary. On GitHub dark theme, these bands visually blend with the host background and make the README read more like one continuous composition.

This remains visual choreography, not DOM overlay authority. It cannot place true side rails behind arbitrary Markdown content or cover host-owned UI.

## Envelope v4 shadow comparison

Two stronger enclosure strategies are preserved under `envelope-v4/` and were tested against GitHub's actual branch README renderer in dark desktop/mobile views.

### Segmented bridge

A 32px seasonal bridge repeats only at natural transitions and keeps the existing semantic content/link structure. GitHub render proof run `32696523661` showed:

- desktop layout intact;
- mobile layout intact without observed horizontal overflow;
- readable project map and contribution graph;
- frame/background continuity stronger than v3, but still perceptual rather than a literal full-height surrounding rail.

This remains the **preferred refinement candidate**, not a live selection yet.

### Single HTML table frame

The three-column table/side-rail experiment was rendered in run `32696767046`. GitHub preserved the structure, so it can create a more literal enclosure, but the result is rejected because:

- GitHub-owned table borders/padding are visually prominent;
- mobile compresses the center content too strongly;
- the host container becomes a larger part of the design than the intended subtle frame.

The rejected experiment remains useful negative evidence and should not be promoted.

### Font portability observation

The same headless proof environment rendered Japanese text inside the SVG section bands as missing-glyph boxes. This proves a client-font dependency exists; it does **not** prove that every Japanese desktop/browser fails. Before a v4 live promotion, remove essential section-label dependence on client-installed Japanese fonts, preferably with deterministic repository-owned vector outlines or another font-independent representation.

Exact decisions and evidence classifications are recorded in `envelope-v4/decision.json` and `envelope-v4/render-evidence-2026-08-24.md`.

## Current design authority

- target theme: **dark**
- copy: username/factual labels only; no invented motivational slogans
- motion: sparse/slow/optional and secondary to a complete static frame
- reduced motion: animated overlays are removable without deleting essential content
- structure: stable live assets are independent from the Design Lab
- section chrome: Projects/Activity labels are part of the seasonal envelope rather than plain Markdown headings
- separators: use only when they improve rhythm; do not insert one automatically after every major block
- enclosure: prefer removable segmented chrome over host-table enclosure unless target rendering proves the latter is responsive and visually superior
- culture-specific direction: use concrete composition/material/palette references; avoid postcard/tourist-symbol accumulation
- automatic mutation: only manifest-approved, static-rendered seasonal candidates may be promoted

## Promotion gate

A new seasonal variant is not eligible for automatic live promotion merely because it exists in `seasons/`. It must retain the common grammar, parse cleanly, keep a complete static frame, expose reduced-motion behavior, contain no scripted animation, and be explicitly marked `auto_promote=true` with `static_render=PASS` in the manifest. Generated live chrome must also pass canonical section/footer geometry checks. Unapproved experiments remain Design Lab-only.

For envelope v4, source/CI success is not enough: the selected enclosure must also beat v3 in actual GitHub dark/mobile rendering, keep links/content readable, avoid host-table artifacts, and remove essential client-font dependence before promotion.
