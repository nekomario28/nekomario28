# Motion envelope v3 promotion candidate

Date: 2026-08-24

## Purpose

Refine the live dark seasonal profile envelope after two accepted corrections:

1. remove the redundant full-width divider immediately after the hero;
2. add restrained optional animation without making motion essential to the composition.

## Changes

- live choreography becomes:
  `seasonal hero -> character content -> Projects band -> project map -> Activity band -> contribution graph -> footer`
- `assets/profile-divider.svg` remains preserved but is no longer a live README dependency;
- Spring/Summer/Autumn/Winter hero sources all gain embedded SMIL motion layers;
- each hero retains the complete static composition under the motion layer;
- each hero includes a `prefers-reduced-motion` fallback;
- no JavaScript or scripted external dependency is introduced;
- stable seasonal promotion now owns only hero, Projects band, Activity band, and footer;
- manifest/live-state/promotion workflow move to envelope version 3;
- pull-request validation is added so seasonal policy can be tested before main mutation.

## Motion grammar

- Spring: breathing mist and sparse drifting petals.
- Summer: sparse rain, a slow water highlight, and tiny leaf sway.
- Autumn: faint ember breathing and sparse drifting leaves.
- Winter: moon haze and sparse slow snow.

Motion is deliberately slow and low-amplitude. Username and factual section labels do not animate.

## Evidence boundary

Source-level animation presence, XML validity, reduced-motion markup, and workflow validation can be checked automatically. Actual animation playback inside the public GitHub profile renderer remains a separate runtime gate and must not be inferred from source validity alone.

## Rollback

D1/D2 and prior D3 sources remain in repository history/Design Lab. The removed divider remains as `assets/profile-divider.svg` and can be restored without reconstructing it.
