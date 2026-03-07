# Claude BambuLab Printer Interface

## What This Is

A Claude Code skill that turns natural language descriptions into print-ready 3MF files and sends them directly to BambuLab printers. Users can generate models via OpenSCAD, search MakerWorld for existing designs, customize with scaling and settings, and print — all through conversation.

## Core Value

Any 3D printer owner can go from "I want to print X" to a physical print through natural language — no CAD skills required.

## Requirements

### Validated

- ✓ User describes desired object in natural language and gets a print-ready 3MF file — v1.0
- ✓ Search MakerWorld for existing open-source models matching the description — v1.0
- ✓ Select the most durable and recommended model from search results — v1.0
- ✓ Apply uniform and per-axis scaling to models — v1.0
- ✓ Generate OpenSCAD models when no match exists on MakerWorld — v1.0
- ✓ Export all models to 3MF format for BambuLab printers — v1.0
- ✓ Handle simple-to-moderate geometry (boxes, brackets, holders, mounts) — v1.0
- ✓ Send 3MF to BambuLab printer and monitor print status — v1.0

### Active

(None yet — define in next milestone)

### Out of Scope

- Complex multi-part assemblies — OpenSCAD generation limited to simple/moderate models
- Standalone app / dashboard — informed by skill feedback
- Support for non-MakerWorld repositories (Thingiverse, Printables) — future
- Parametric editing of downloaded models (beyond scaling) — no .scad source
- Non-BambuLab printers — BambuLab ecosystem focus

## Context

Shipped v1.0 with 3,387 LOC across Python scripts and Markdown skill files.
Tech stack: OpenSCAD (generation), Playwright (MakerWorld scraping), bambu-lab-cloud-api (printer).
Known issue: MakerWorld Cloudflare protection intermittently blocks automated downloads.
All printer operations require physical hardware — tested via code review, not E2E.

## Constraints

- **Format**: 3MF output only (BambuLab ecosystem standard)
- **Models**: Open-source licensed models only from MakerWorld
- **Runtime**: Requires local OpenSCAD and BambuStudio installation
- **Printer API**: bambu-lab-cloud-api is unofficial — may break with firmware updates
- **Auth**: BambuLab JWT tokens expire after ~24h, require re-authentication

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MakerWorld scraping (no API) | Only option — no public API exists | ✓ Works via Playwright persistent context |
| OpenSCAD for model generation | Claude can generate SCAD code; proven for simple models | ✓ Reliable for simple-moderate geometry |
| 3MF as sole export format | BambuLab standard, most capable format | ✓ Good — supports embedded settings |
| Claude Code skill first, app later | De-risks product with technical early adopters | ✓ Good — shipped full pipeline as skill |
| Open-source models only | Avoids licensing complications | ✓ Good |
| Raw OpenSCAD over SolidPython2 | More LLM training data, users can edit .scad directly | ✓ Good |
| Playwright with persistent context | Cloudflare bypass for MakerWorld | ⚠ Revisit — Cloudflare now blocking intermittently |
| bambu-lab-cloud-api for printer | Cloud API auth + MQTT monitoring | ✓ Good — handles auth, upload, status |
| BambuStudio CLI for auto-slicing | Required for cloud print (sliced 3MF) | ⚠ Revisit — LOW confidence on reliability |

---
*Last updated: 2026-03-07 after v1.0 milestone*
