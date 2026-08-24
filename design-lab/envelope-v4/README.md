# Envelope v4 frame lab

Goal: make the README area read as one enclosed dark surface without claiming CSS/background authority that GitHub does not provide.

This lab keeps envelope v3 live and tests two bounded approaches.

## A — segmented frame / background illusion

Status: **preferred safe candidate**.

Use full-width dark bridge strips with subtle left/right rails between existing factual content blocks. Existing character art, project map, contribution graph, section bands, and footer remain independent assets. The visual frame is therefore inferred across the vertical reading path rather than implemented as a literal background layer.

Advantages:

- keeps current README semantics and links;
- no table/layout dependency;
- narrow/mobile behavior remains close to the current profile;
- seasonal chrome can be generated deterministically from the same manifest;
- if bridges are removed, all content still reads normally.

Limit: rails cannot physically remain behind arbitrary Markdown/image content, so continuity is perceptual rather than literal.

Preview: [`segmented-frame-demo.md`](segmented-frame-demo.md)

## B — single-table outer frame experiment

Status: **Design Lab only / sanitizer + responsive verification required**.

Put the README-owned content into one HTML `<table>` so GitHub's own table box provides a real continuous outer boundary. Small rail assets can be placed beside central content to strengthen the effect.

Advantages:

- closest available README-only approximation to a literal enclosing box;
- one continuous DOM container rather than separate bands.

Risks:

- GitHub's table CSS owns border, padding, background, and responsive behavior;
- width/padding can make large images or mobile rendering worse;
- nested links/images may scan less cleanly;
- custom CSS cannot be relied on to remove host table styling.

Preview: [`table-frame-demo.md`](table-frame-demo.md)

## Decision gate

Do not promote B merely because it encloses more literally. Promote the smallest option that improves dark-theme continuity **without** degrading mobile width, link behavior, factual content, or the existing project/contribution visuals.

A live v4 should retain these boundaries:

- README area only; no claim over avatar/sidebar/pinned repositories;
- dark theme is the visual authority;
- no fabricated activity/project data;
- seasonal hero motion remains optional/static-first;
- no JavaScript;
- frame/background decoration is removable independently from content authority.
