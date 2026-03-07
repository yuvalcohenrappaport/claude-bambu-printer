# Phase 1: Skill Foundation + Model Generation - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Claude Code skill that generates parametric 3D models from natural language descriptions and exports 3MF files. Users describe what they want, Claude asks clarifying questions, generates OpenSCAD code, renders a preview, and exports a print-ready 3MF. No network dependencies (MakerWorld search is Phase 3). No printer integration (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Skill invocation flow
- Dual trigger: slash command (/print) for explicit use AND natural language intent detection
- Always ask clarifying questions before generating: dimensions, use case, and material (PLA/PETG/TPU)
- Material choice affects design decisions (wall thickness, tolerances)
- When description is too vague, ask what they need and what it's for — don't guess

### OpenSCAD generation approach
- Hybrid template approach: use pre-built parametric templates when available, freeform generation for novel requests
- Templates built as needed based on actual user requests (not a pre-shipped starter set)
- Show the generated OpenSCAD code to the user — fits early adopter audience, enables learning/tweaking
- Save both .scad source and .3mf output files

### Output & file handling
- Render a preview PNG via OpenSCAD before exporting 3MF so user sees the model visually
- Detailed output summary: preview image + dimensions + material suggestion + file path + SCAD code
- After generation, ask "Want me to open this in BambuStudio?" (don't auto-open, don't skip)
- Save both .scad and .3mf files for each generation

### Error handling
- Auto-fix and retry on OpenSCAD compilation errors (up to 3 attempts, Claude reads error and fixes)
- For complex models beyond Claude's capability: try anyway with a clear warning about accuracy
- OpenSCAD install check: ask user permission first, then install via Homebrew if they agree
- Vague input: ask what they need and what they'd use it for — probe the use case

### Claude's Discretion
- Project directory structure vs independent requests for file organization
- Raw OpenSCAD vs SolidPython2 (pick based on research findings)
- Exact retry logic and error message formatting
- Preview render angle and resolution

</decisions>

<specifics>
## Specific Ideas

- Early adopters are technical (Claude Code users) — showing SCAD code is a feature, not noise
- Material affects design: PLA vs PETG vs TPU have different wall thickness and tolerance requirements
- The clarification step (dimensions + use case + material) happens every time, no exceptions

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-skill-foundation-model-generation*
*Context gathered: 2026-03-05*
