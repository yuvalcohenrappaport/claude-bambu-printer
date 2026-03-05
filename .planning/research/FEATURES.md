# Feature Landscape

**Domain:** Claude-powered 3D printing automation
**Researched:** 2026-03-05

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Natural language model search | Core value prop -- "find me a phone stand" | Medium | MakerWorld scraping, result ranking |
| Model preview/info display | Users need to see what they're getting before printing | Low | Show name, image URL, dimensions, license |
| Download existing model | Basic retrieval from MakerWorld | Medium | Handle auth, file formats, rate limits |
| Generate simple parametric models | "Make a box 10x5x3cm" | Medium | SolidPython2 + OpenSCAD for basic shapes |
| Export to 3MF | BambuLab printers require 3MF | Low | OpenSCAD CLI or lib3mf |
| Scale/resize models | "Make it 20% bigger" | Low | trimesh affine transform |
| Print job submission | Send 3MF to BambuLab printer | Medium | bambulabs-api MQTT connection |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI-driven model generation | "Design a hook that holds 5kg" -- Claude reasons about geometry | High | Prompt engineering + SolidPython2 code generation |
| Model modification from description | "Add a hole in the center" -- modify existing .scad | High | Requires understanding existing model structure |
| Print settings recommendation | "What infill for this?" based on model purpose | Low | Claude's knowledge + BambuLab presets |
| Multi-model composition | "Combine this base with that top piece" | High | trimesh boolean operations, alignment |
| Printer status monitoring | "Is my print done?" | Low | bambulabs-api status polling |
| Model parameter tweaking | "Make the walls thicker" on parametric models | Medium | Requires parameterized .scad with variables |
| Batch search + comparison | "Show me 5 options for a desk organizer" | Medium | Parallel MakerWorld queries |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full CAD editor | Massive scope, already solved by FreeCAD/Fusion360 | Generate .scad files users can edit in OpenSCAD |
| Model marketplace | Legal complexity, hosting costs | Link to MakerWorld, respect licenses |
| Slicing engine | BambuStudio/OrcaSlicer already handles this | Export 3MF and let existing slicers handle it |
| Real-time 3D viewer | Requires WebGL/Three.js, huge scope | Show model dimensions + preview image |
| User accounts/auth | Unnecessary for CLI/skill tool | Local config file for printer credentials |
| Cloud storage | Adds infrastructure complexity | Local file system for models |

## Feature Dependencies

```
MakerWorld Search --> Model Download --> Scale/Transform --> Export 3MF --> Print Job
                                                                  ^
OpenSCAD Generation --> Render to Mesh ---------> Scale/Transform -+
                                                                   |
                                              Printer Connection --+
```

## MVP Recommendation

Prioritize (Phase 1 -- Claude Code Skill):
1. **Natural language model search** on MakerWorld (table stakes, core UX)
2. **Generate simple parametric models** via SolidPython2 (differentiator, showcases AI)
3. **Export to 3MF** (table stakes, required for printing)
4. **Scale/resize models** (table stakes, low complexity)

Defer:
- **Print job submission**: Requires physical printer setup/testing. Phase 2.
- **Model modification**: Requires structural understanding of .scad files. Phase 2+.
- **Multi-model composition**: Complex boolean ops. Phase 3.
- **Printer monitoring**: Nice-to-have, not core. Phase 2.

## Sources

- MakerWorld platform analysis (scraping tools on Apify confirm data availability)
- OpenSCAD CLI capabilities (official docs confirm headless rendering)
- bambulabs-api documentation (confirms print job submission API)
