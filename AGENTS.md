# AGENTS.md

This is a public production repository. Keep repository changes project-owned and publication-ready.

## Public-repository boundary

- Do not use this repository as the experimental foundation, scratch space, integration lab, or intermediate validation surface for another project.
- Cross-project experiments, exploratory integration, generated experiment artifacts, and intermediate validation must happen in an explicitly private repository, private sandbox, or other private experimental surface.
- This repository may be used as a read-only reference/source of current production truth.
- Changes imported from another project must arrive as independently validated, scoped deliverables with clear provenance and a project-specific reason to land here.
- Do not create temporary experiment branches, workflows, fixtures, or artifacts here solely to validate another project's design.

## Change discipline

Refresh current main before consequential writes. Prefer the smallest project-owned change, preserve existing production behavior unless the change explicitly intends otherwise, and do not weaken validation or provenance gates merely to obtain green.
