# Requirements: Claude BambuLab Printer Interface

**Defined:** 2026-03-05
**Core Value:** Any 3D printer owner can go from "I want to print X" to a print-ready 3MF file through natural language — no CAD skills required.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Search

- [x] **SRCH-01**: User can describe desired object in natural language and get matching MakerWorld results
- [x] **SRCH-02**: User can see model preview info (name, image URL, dimensions, license, ratings)
- [x] **SRCH-03**: System selects most durable/recommended model from results
- [x] **SRCH-04**: User can download selected model file from MakerWorld

### Generation

- [x] **GEN-01**: User can request a simple parametric model by description (boxes, brackets, holders, mounts)
- [x] **GEN-02**: Claude generates valid OpenSCAD code from natural language description
- [x] **GEN-03**: User can specify dimensions for generated models
- [x] **GEN-04**: User can modify generated models ("add a hole", "make walls thicker", "add screw holes")
- [x] **GEN-05**: Claude attempts complex geometry (hooks with load reasoning, organic shapes) with clear communication of confidence level

### Customization

- [x] **CUST-01**: User can apply uniform scaling to any model ("make it 20% bigger")
- [x] **CUST-02**: User can apply per-axis scaling ("make it 10cm wider but keep the height")
- [x] **CUST-03**: System exports all models to 3MF format
- [x] **CUST-04**: System recommends print settings (infill, layer height) based on model purpose

### Printer

- [x] **PRNT-01**: User can send 3MF to BambuLab printer for printing
- [x] **PRNT-02**: User can check printer status

### Skill

- [x] **SKIL-01**: Tool works as a Claude Code skill invoked via natural language
- [x] **SKIL-02**: System checks for OpenSCAD installation and guides user if missing
- [x] **SKIL-03**: All generated files saved to local filesystem with clear paths

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Generation

- **AGEN-01**: Multi-model composition (combine base with top piece)
- **AGEN-02**: Boolean operations on meshes (subtract, union, intersect)
- **AGEN-03**: Batch search with side-by-side comparison of 5+ options

### Standalone App

- **APP-01**: Web dashboard interface for non-CLI users
- **APP-02**: Integration with BambuLab app
- **APP-03**: Model history and favorites

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full CAD editor | Massive scope, solved by FreeCAD/Fusion360 |
| Slicing engine | BambuStudio/OrcaSlicer handles this; export 3MF only |
| Real-time 3D viewer | Requires WebGL/Three.js, huge scope for a CLI skill |
| Model marketplace | Legal complexity, hosting costs |
| User accounts/auth | Unnecessary for CLI skill |
| Cloud storage | Local filesystem sufficient for skill phase |
| Non-BambuLab printers | Focus on BambuLab ecosystem first |
| Non-MakerWorld repositories | Thingiverse, Printables deferred to future |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SRCH-01 | Phase 3 | Complete |
| SRCH-02 | Phase 3 | Complete |
| SRCH-03 | Phase 3 | Complete |
| SRCH-04 | Phase 3 | Complete |
| GEN-01 | Phase 1 | Complete |
| GEN-02 | Phase 1 | Complete |
| GEN-03 | Phase 1 | Complete |
| GEN-04 | Phase 2 | Complete |
| GEN-05 | Phase 2 | Complete |
| CUST-01 | Phase 2 | Complete |
| CUST-02 | Phase 2 | Complete |
| CUST-03 | Phase 1 | Complete |
| CUST-04 | Phase 2 | Complete |
| PRNT-01 | Phase 4 | Complete |
| PRNT-02 | Phase 4 | Complete |
| SKIL-01 | Phase 1 | Complete |
| SKIL-02 | Phase 1 | Complete |
| SKIL-03 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-03-05*
*Last updated: 2026-03-05 after roadmap creation*
