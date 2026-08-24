# Envelope v4 live evidence — 2026-08-24

Selected implementation: shared segmented rails inside the GitHub README rendering area.

## Evidence

- profile PR: #33
- merged commit: `fff229261dfa5b93ce3f9c42229b5e390d084132`
- four-season validation run: `32700948779` — SUCCESS
- render-proof head seasonal run: `32700999805` — SUCCESS
- GitHub-rendered desktop/mobile proof run: `32700999845` — SUCCESS
- final clean-head validation run after temporary proof removal: `32701140464` — SUCCESS
- proof artifact: `envelope-v4-refresh-github-render-proof` / artifact `9510487351`

## Result

Desktop GitHub dark rendering shows a repeated outer-frame grammar because bridge, Projects, Activity and footer share edge rails at x=18 and x=882. Mobile remains readable with no observed horizontal overflow or table-style center compression.

The HTML-table enclosure was rejected: although it created a more literal border, GitHub-owned table borders/padding dominated visually and compressed the center column on mobile.

Japanese Projects/Activity labels remain deterministic vector outlines and did not regress to client-font-dependent SVG `<text>`.

## Boundaries

This is a README-area pseudo-overlay, not control of GitHub page chrome, avatar/sidebar, pinned repositories, or other host-owned profile UI. Static/rendered envelope proof does not establish that optional embedded SMIL visibly plays on the public profile.
