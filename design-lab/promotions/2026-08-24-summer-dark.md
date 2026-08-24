# Summer dark live promotion — 2026-08-24

## Result

Promoted the D3 Summer dark concept from the Design Lab into the live profile README.

- source concept: `design-lab/seasons/summer-dark.svg`
- stable live hero: `assets/profile-hero.svg`
- stable live divider: `assets/profile-divider.svg`
- stable live footer: `assets/profile-footer.svg`
- live README activation commit: `8b3dc0daf2b71d91b9ebd1a741dae6c79cf2cac2`
- previous live README blob: `382034397984a45ffa5ddf958d1cc05e1efb9789`
- new live README blob: `39550fee551501c8a5abb5e61c0d83511e7fd37c`

## Promotion pattern

The live README does not point directly at an experimental season file. The selected variant is copied/promoted into a stable `assets/profile-*.svg` surface. This keeps the Design Lab independent and means future seasonal changes can replace the active hero without restructuring the README.

The envelope uses the GitHub-supported README surface only:

`hero -> divider -> existing profile content -> divider -> project map -> divider -> contributions -> footer`

It does not claim to overlay GitHub-owned avatar/navigation/pinned-repository surfaces.

## Preserved material

- D1 initial neon sakura remains archived at `design-lab/archive/d1-neon-sakura.svg`.
- D2 Japanese-minimal remains archived at `design-lab/archive/d2-japanese-minimal.svg`.
- all four D3 seasonal concepts remain under `design-lab/seasons/`.
- the existing Megumin image, Project Map, and contribution SVG remain in the live README.

## Verification status

Confirmed through the GitHub repository API:

- live README points to all three stable profile assets;
- the live README declares `summer-dark` as the active theme;
- the pre-existing content references remain present.

The promoted `assets/profile-hero.svg` was also rendered locally at its canonical `900x260` geometry with CairoSVG. The static render completed without parser/render failure, clipping, or missing internal SVG references. This proves the hero asset itself is renderable; it does not prove the complete GitHub profile composition.

The public GitHub profile HTML could not be independently fetched by the available web path at promotion time, so browser-level full-profile visual verification remains `NOT_RUN` rather than being inferred from source or hero-only rendering.

## Rollback

The activation is deliberately reversible. Restore the previous README content/blob and leave the promoted assets in place, or point the stable live hero at another archived/seasonal candidate after review.
