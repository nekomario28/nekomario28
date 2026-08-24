# Profile Design Lab

Experimental visual directions for the `nekomario28` GitHub profile.

The live profile is intentionally separate from this lab. Concepts can be compared, revised, or deleted here without turning the profile README into a gallery.

## Design lineage

| ID | Status | Meaning |
|---|---|---|
| D1 | archived | First animated neon/sakura SVG. Preserved exactly from commit `4fc69a45a60ad74a13ed75e46c40881bebb12880`. |
| D2 | archived lineage | Restrained indigo/sakura rewrite from commit `0c8aebb6c976c78e6ad940cf8f5a37c6db4883bd`. Useful as evidence, not the target aesthetic. |
| D3 | live system | Dark seasonal visual-envelope system. Four static-first seasonal heroes share one layout grammar. |
| D3.1 | live envelope v2 | The seasonal grammar now applies to the README section chrome as well as the hero. |

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

The palette and motif change, while the username placement, dark base, spacing rhythm, border geometry, and section-envelope grammar remain stable. All four current static hero variants have been rendered successfully at `900x260` and are approved by `theme-manifest.json` for seasonal promotion.

## Live promotion model

The root README never points directly at a seasonal experiment. It references stable live assets only:

- `assets/profile-hero.svg`
- `assets/profile-divider.svg`
- `assets/profile-section-projects.svg`
- `assets/profile-section-activity.svg`
- `assets/profile-footer.svg`

`live-theme.json` records which seasonal source currently owns the complete envelope. `scripts/promote-season.py` validates the month mapping, approval flags, hero SVG XML/geometry, then promotes the hero and asks `scripts/render_envelope_chrome.py` to regenerate the matching divider, section bands, and footer.

This means seasonal switching does not rewrite README structure. The README remains one selected projection while the Design Lab remains the source of candidates and lineage.

## Seasonal mapping

`theme-manifest.json` maps in the `Asia/Tokyo` timezone:

- March–May -> spring
- June–August -> summer
- September–November -> autumn
- December–February -> winter

`.github/workflows/update-seasonal-profile.yml` checks on the first day of every month at about 09:17 JST. A scheduled run applies the approved seasonal envelope; if the stable assets already match, the commit step is a no-op. Manual dispatch defaults to dry-run.

The workflow also runs as a non-committing validation on pushes that change the seasonal policy, scripts, state, README structure, renderer, or source SVGs. All four seasonal chrome variants are rendered into temporary directories and geometry-checked before the live workflow is allowed to continue.

## Visual envelope / pseudo-overlay

GitHub README content **cannot** place a real overlay over GitHub page chrome, the avatar/sidebar, pinned-repository UI, or other host-owned profile elements. README HTML/CSS/JS also cannot restyle the surrounding GitHub application.

What is implementable is a visual envelope **inside the profile README rendering area**. Envelope v2 currently uses this choreography:

`seasonal hero -> seasonal divider -> existing character content -> seasonal Projects band -> project map -> seasonal Activity band -> contribution graph -> seasonal footer`

The important change from v1 is that section boundaries are no longer generic repeated separators. The factual section labels themselves are full-width seasonal bands, so the palette/motif recurs through the complete vertical reading path. On GitHub dark theme, these bands visually blend with the host background and make the README read more like one continuous composition.

This remains a visual illusion/choreography, not DOM overlay authority. It cannot place side rails behind arbitrary Markdown content or cover host-owned UI.

See `envelope-demo.md` for the bounded implementation concept.

## Current design authority

- target theme: **dark**
- copy: username/factual labels only; no invented motivational slogans
- motion: optional and secondary; static frame must remain complete
- structure: stable live assets are independent from the Design Lab
- section chrome: Projects/Activity labels are part of the seasonal envelope rather than plain Markdown headings
- culture-specific direction: use concrete composition/material/palette references; avoid postcard/tourist-symbol accumulation
- automatic mutation: only manifest-approved, static-rendered seasonal candidates may be promoted

## Promotion gate

A new seasonal variant is not eligible for automatic live promotion merely because it exists in `seasons/`. It must retain the common grammar, parse/render cleanly, and be explicitly marked `auto_promote=true` with `static_render=PASS` in the manifest. The generated chrome must also pass the canonical divider/section/footer geometry checks. Unapproved experiments remain Design Lab-only.
