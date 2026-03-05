# Roadmap: Claude BambuLab Printer Interface

## Overview

This project delivers a Claude Code skill that turns natural language descriptions into print-ready 3MF files. The roadmap moves from self-contained model generation (zero external dependencies) through model refinement, then tackles the highest-risk component (MakerWorld scraping), and finishes with printer integration (requires hardware). Each phase delivers a usable, verifiable capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Skill Foundation + Model Generation** - Claude Code skill that generates parametric 3D models from natural language and exports 3MF files
- [ ] **Phase 2: Model Refinement + Customization** - Iterative model modification, scaling, and print settings recommendations
- [ ] **Phase 3: MakerWorld Search + Download** - Natural language search for existing models on MakerWorld with download pipeline
- [ ] **Phase 4: Printer Integration** - Send 3MF files to BambuLab printer and monitor print status

## Phase Details

### Phase 1: Skill Foundation + Model Generation
**Goal**: Users can describe a simple object in natural language and get a print-ready 3MF file on their filesystem
**Depends on**: Nothing (first phase)
**Requirements**: SKIL-01, SKIL-02, SKIL-03, GEN-01, GEN-02, GEN-03, CUST-03
**Success Criteria** (what must be TRUE):
  1. User can invoke the skill from Claude Code with a natural language request like "make me a phone stand"
  2. System checks for OpenSCAD installation and provides clear install instructions if missing
  3. User can specify dimensions for a generated model and receive valid OpenSCAD code that renders successfully
  4. User receives a 3MF file saved to a clear local path, ready to open in BambuStudio
  5. Generated models handle simple-to-moderate geometry (boxes, brackets, holders, mounts)
**Plans**: TBD

Plans:
- [ ] 01-01: TBD
- [ ] 01-02: TBD
- [ ] 01-03: TBD

### Phase 2: Model Refinement + Customization
**Goal**: Users can iterate on generated models and resize any model to fit their needs
**Depends on**: Phase 1
**Requirements**: GEN-04, GEN-05, CUST-01, CUST-02, CUST-04
**Success Criteria** (what must be TRUE):
  1. User can modify a previously generated model by description ("add a hole", "make walls thicker", "add screw holes")
  2. User can apply uniform scaling ("make it 20% bigger") and per-axis scaling ("make it 10cm wider but keep the height")
  3. System communicates confidence level when attempting complex geometry (hooks, organic shapes)
  4. System recommends print settings (infill, layer height) based on what the model is for
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: MakerWorld Search + Download
**Goal**: Users can find and download existing open-source models from MakerWorld instead of generating from scratch
**Depends on**: Phase 1
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04
**Success Criteria** (what must be TRUE):
  1. User can describe a desired object and see matching MakerWorld results with name, image URL, dimensions, license, and ratings
  2. System selects and highlights the most durable/recommended model from search results
  3. User can download the selected model file to their local filesystem
  4. Downloaded models integrate with Phase 1/2 pipeline (scaling, 3MF export)
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Printer Integration
**Goal**: Users can send models directly to their BambuLab printer without leaving Claude Code
**Depends on**: Phase 1
**Requirements**: PRNT-01, PRNT-02
**Success Criteria** (what must be TRUE):
  1. User can send a 3MF file to their BambuLab printer for printing
  2. User can check printer status (idle, printing, error) from Claude Code
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4
Note: Phases 3 and 4 depend only on Phase 1, not on each other. Execution is sequential but they could theoretically be reordered.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Skill Foundation + Model Generation | 0/3 | Not started | - |
| 2. Model Refinement + Customization | 0/2 | Not started | - |
| 3. MakerWorld Search + Download | 0/2 | Not started | - |
| 4. Printer Integration | 0/1 | Not started | - |
