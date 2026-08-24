# Envelope v7 — continuous canvas experiment

Goal: make the README read as one dark surface with foreground media mounted on top, including the left/right areas around narrower real content.

This is an experimental branch surface, not the live authority.

## Strategy

1. Replace paragraph-wrapped image blocks with adjacent block-level `<div>` rows to remove GitHub paragraph margins as a first experiment.
2. Keep full-width Hero / bridge / section / footer assets.
3. For content that must remain a real independent source, fill the unused width with repository-owned left/right background surfaces:
   - character: `100 + 700 + 100`;
   - project map: `80 + 740 + 80`;
   - contributions: `70 + 760 + 70`.
4. Fade the outermost surface edge toward GitHub dark `#0d1117` so the README background appears to bleed beyond the 900px canvas instead of ending as a hard slab.
5. Add an inner hairline/glow at the media boundary so the center image/SVG reads like a mounted foreground layer.
6. Keep the actual project-map SVG and contribution SVG authoritative; do not replace them with fake cards.
7. The character image continues to use the official remote source rather than copying copyrighted bytes into the repository.

## Validation gates before any live promotion

- GitHub branch README desktop target render.
- Narrow/mobile target render: no row wrap, overflow, or destructive center compression.
- External character image still loads.
- Actual project map remains clickable.
- Attribution remains visible; the current experimental Japanese `<text>` must be converted to deterministic outlines before promotion if font portability is not proven.
- Existing v6 global-motion contract is not silently claimed across the newly rendered gap surfaces. A future v7 motion pass must define a new contiguous logical space if this layout is accepted.

If the three-piece rows wrap on mobile, the fallback is a generated composite panel for repository-owned SVGs and a narrower/edge-matched character treatment rather than reviving host-native tables.
