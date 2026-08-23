# Profile Design Lab

Experimental visual directions for the `nekomario28` GitHub profile.

The live profile is intentionally separate from this lab. Concepts can be compared, revised, or deleted here without turning the profile README into a gallery.

## Design lineage

| ID | Status | Meaning |
|---|---|---|
| D1 | archived | First animated neon/sakura SVG. Preserved exactly from commit `4fc69a45a60ad74a13ed75e46c40881bebb12880`. |
| D2 | archived/current lineage | Restrained indigo/sakura rewrite from commit `0c8aebb6c976c78e6ad940cf8f5a37c6db4883bd`. Useful as evidence, not the target aesthetic. |
| D3 | experimental | Dark seasonal visual-envelope system. Four static-first seasonal heroes share one layout grammar. |

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

The palette and motif change, while the username placement, dark base, spacing rhythm, border geometry, and section-envelope grammar remain stable.

## Seasonal mapping

`theme-manifest.json` currently maps:

- March–May -> spring
- June–August -> summer
- September–November -> autumn
- December–February -> winter

This is a design mapping, not yet an automatic mutation policy for the live profile.

## Visual envelope / pseudo-overlay

GitHub README content **cannot** place a real overlay over GitHub page chrome, the avatar/sidebar, pinned-repository UI, or other host-owned profile elements. README HTML/CSS/JS also cannot restyle the surrounding GitHub application.

What is implementable is a visual envelope **inside the profile README rendering area**:

`seasonal hero -> dark divider -> profile content -> dark divider -> activity/content -> closing footer`

On GitHub dark theme, dark full-width SVG bands visually blend with the host background and can make the README read as one continuous composition. This is a visual illusion/choreography, not DOM overlay authority.

See `envelope-demo.md` for a bounded implementation using repository-owned assets only.

## Current design authority

- target theme: **dark**
- copy: username/factual labels only; no invented motivational slogans
- motion: optional and secondary; static frame must remain complete
- structure: assets remain independently removable/revertible
- culture-specific direction: use concrete composition/material/palette references; avoid postcard/tourist-symbol accumulation

## Promotion gate

Do not replace the live hero merely because one concept looks promising in isolation. Promote only after the candidate is reviewed together with the existing character image, project map, and contribution block on an actual dark-theme README render.
