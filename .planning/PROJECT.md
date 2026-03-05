# Claude BambuLab Printer Interface

## What This Is

A Claude-powered tool that takes a natural language description of a desired 3D model, searches MakerWorld for an existing open-source match, customizes it to the user's measurements, and exports a print-ready 3MF file. When no existing model is found, Claude generates one using OpenSCAD. Phase 1 is a Claude Code skill for early adopters; Phase 2 is a standalone app.

## Core Value

Any 3D printer owner can go from "I want to print X" to a print-ready 3MF file through natural language — no CAD skills required, no giving up when a model doesn't exist.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] User describes desired object in natural language and gets a print-ready 3MF file
- [ ] Search MakerWorld for existing open-source models matching the description
- [ ] Select the most durable and recommended model from search results
- [ ] Ask user for measurements and apply scaling to found models
- [ ] Generate OpenSCAD models when no match exists on MakerWorld
- [ ] Export all models to 3MF format for BambuLab printers
- [ ] Handle simple-to-moderate geometry (boxes, brackets, holders, mounts, organizers)

### Out of Scope

- Complex multi-part assemblies — OpenSCAD generation limited to simple/moderate models for v1
- Standalone app / dashboard — Phase 2, informed by skill feedback
- Direct printer integration via BambuLab API — future
- Support for non-MakerWorld repositories (Thingiverse, Printables) — future
- Parametric editing of downloaded models (beyond scaling) — future
- OAuth or user accounts — not needed for skill phase

## Context

- MakerWorld has no public API; scraping is required (fragile to site changes)
- OpenSCAD must be installed locally for model generation and 3MF export
- Claude can reliably generate working OpenSCAD code for simple models (tested)
- Most user resizing needs are simple uniform scaling; per-axis scaling is occasional
- Target early adopters are Claude Code users who own 3D printers — technical, tolerant of rough edges
- PM discovery documents at `docs/product/` (DISC-001, OA-001, SM-001)

## Constraints

- **Format**: 3MF output only (BambuLab ecosystem standard)
- **Models**: Open-source licensed models only from MakerWorld
- **Runtime**: Requires local OpenSCAD installation
- **Complexity**: OpenSCAD generation reliable for simple geometry only

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MakerWorld scraping (no API) | Only option — no public API exists | — Pending |
| OpenSCAD for model generation | Claude can generate SCAD code; proven for simple models | — Pending |
| 3MF as sole export format | BambuLab standard, most capable format | — Pending |
| Claude Code skill first, app later | De-risks product with technical early adopters before investing in UI | — Pending |
| Open-source models only | Avoids licensing complications | — Pending |

---
*Last updated: 2026-03-05 after initialization*
