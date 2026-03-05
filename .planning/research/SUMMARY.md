# Project Research Summary

**Project:** Claude-powered BambuLab 3D Printing Automation
**Domain:** AI-assisted CAD/3D printing tooling (Claude Code skill)
**Researched:** 2026-03-05
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project is a Claude Code skill that lets users search MakerWorld for existing 3D models, generate new parametric models via natural language, and prepare them for printing on BambuLab printers. The expert approach is a modular Python script architecture where Claude acts as the orchestrator -- reading a SKILL.md for instructions, then calling discrete Python scripts (search, generate, render, transform, export, print) based on user intent. The entire CAD pipeline is Python-native: SolidPython2 generates OpenSCAD code, OpenSCAD CLI renders meshes, trimesh validates/transforms geometry, and lib3mf packages the final 3MF files.

The recommended approach is to build this as a Claude Code skill first (Phase 1), not a standalone app. Each capability lives in its own Python script under `.claude/skills/3d-print/scripts/`. Claude reads SKILL.md, understands what the user wants, and chains the right scripts together. This keeps the architecture simple, composable, and testable. The stack is mature -- SolidPython2, OpenSCAD, trimesh, and lib3mf are all well-maintained with high confidence. The main uncertainty is bambulabs-api (unofficial) and MakerWorld scraping (no public API, anti-bot protections).

The two highest risks are: (1) MakerWorld blocking automated access, which would break the search feature entirely -- mitigate with aggressive caching, internal JSON API reverse-engineering, and graceful fallback to manual search; (2) Claude generating invalid SolidPython2 code -- mitigate with API reference in SKILL.md, output validation after every render, and known-good templates for common shapes. A critical constraint is that BambuLab printers need **sliced** 3MF files (not raw meshes), so Phase 1 must export raw 3MF and tell users to slice in BambuStudio. Direct print submission requires sliced files, making printer integration a Phase 2+ concern.

## Key Findings

### Recommended Stack

Python is the only viable language -- every critical library (SolidPython2, lib3mf, trimesh, bambulabs-api) is Python-native. TypeScript has no equivalent CAD/mesh ecosystem. pip is sufficient for Phase 1; no need for Poetry yet.

**Core technologies:**
- **SolidPython2** (2.1.3): Python-to-OpenSCAD bridge -- generates readable .scad text, ideal for LLM code generation
- **OpenSCAD** (2025.08+): System dependency for CSG rendering -- called via CLI subprocess, handles all geometry computation
- **lib3mf** (2.4.1): Official 3MF Consortium library -- full spec compliance for packaging mesh + metadata
- **trimesh** (4.11.x): Mesh operations -- scale, transform, validate watertight, repair common issues
- **httpx + BeautifulSoup4**: MakerWorld scraping -- async HTTP client + HTML parser, with Playwright as JS-rendering fallback
- **bambulabs-api** (2.6.6): BambuLab printer control via local MQTT -- unofficial but most maintained option

**Critical version note:** OpenSCAD 2025.08+ required for native 3MF export. Must be installed via `brew install openscad` (system dependency, not pip).

### Expected Features

**Must have (table stakes):**
- Natural language model search on MakerWorld
- Generate simple parametric models ("make a box 10x5x3cm")
- Export to 3MF format
- Scale/resize models

**Should have (differentiators):**
- AI-driven model generation (Claude writes SolidPython2 geometry code)
- Print settings recommendations
- Model parameter tweaking on parametric models
- Batch search with comparison

**Defer (v2+):**
- Print job submission (requires sliced 3MF, physical printer testing)
- Model modification from description (requires understanding existing .scad structure)
- Multi-model composition (complex boolean operations)
- Printer status monitoring

### Architecture Approach

Claude Code skill with script-per-action pattern. Each Python script handles exactly one operation (search, generate, render, transform, export, print). Claude orchestrates by reading SKILL.md and calling scripts sequentially based on user intent. Scripts communicate via JSON on stdin/stdout. Printer credentials live in `~/.config/bambulab/config.json`.

**Major components:**
1. **SKILL.md** -- instructs Claude on when and how to use each script
2. **search_models.py** -- queries MakerWorld, returns structured JSON results
3. **generate_scad.py** -- Claude writes SolidPython2 code, script renders to .scad
4. **render_model.py** -- shells out to OpenSCAD CLI, produces .stl/.3mf
5. **transform_model.py** -- trimesh operations (scale, rotate, validate, repair)
6. **export_3mf.py** -- lib3mf packaging with metadata
7. **print_job.py** -- bambulabs-api MQTT integration (Phase 2)

### Critical Pitfalls

1. **MakerWorld blocks automated access** -- Reverse-engineer internal JSON API first, rate-limit to 1-2 req/s, cache results 24h+, degrade gracefully to manual search suggestions
2. **OpenSCAD not installed** -- Fail fast with clear error on skill init, check `openscad --version`, document brew install prominently
3. **Non-watertight meshes fail to print** -- Validate with `mesh.is_watertight` after every render/transform, auto-repair with trimesh
4. **Claude generates invalid SolidPython2** -- Include API cheatsheet in SKILL.md, validate render output, catch OpenSCAD errors for self-correction, maintain template library
5. **Raw vs sliced 3MF confusion** -- Phase 1 exports raw 3MF only, user slices in BambuStudio; direct printing requires sliced 3MF (Phase 2 with OrcaSlicer CLI)

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Skill Foundation + Model Generation
**Rationale:** Model generation is self-contained (no external API risk), proves the core value prop, and establishes the skill architecture.
**Delivers:** Working Claude Code skill that generates parametric 3D models from natural language and exports 3MF files.
**Addresses:** Generate simple parametric models, export to 3MF, scale/resize models.
**Avoids:** MakerWorld scraping risk (deferred). Printer integration complexity (deferred).
**Stack:** SolidPython2, OpenSCAD CLI, trimesh, lib3mf, SKILL.md + script-per-action pattern.

### Phase 2: MakerWorld Search + Download
**Rationale:** Search depends on reverse-engineering MakerWorld's internal API -- highest-risk component. Isolating it lets Phase 1 ship independently.
**Delivers:** Natural language search for existing models on MakerWorld, download, and transform pipeline.
**Addresses:** Natural language model search, model preview/info, download existing model, batch search.
**Avoids:** Anti-bot blocking (via caching + rate limiting + fallback strategy).
**Stack:** httpx, BeautifulSoup4, possibly Playwright as fallback.

### Phase 3: Printer Integration
**Rationale:** Requires physical printer for testing, network configuration, and sliced 3MF files. Least risky to defer -- users can manually print via BambuStudio until this ships.
**Delivers:** Direct print job submission from Claude Code, printer status monitoring.
**Addresses:** Print job submission, printer status monitoring, print settings recommendation.
**Avoids:** Raw vs sliced 3MF confusion (by this phase, pipeline is proven). Network connectivity issues (connection test script).
**Stack:** bambulabs-api, config.py for credentials.

### Phase 4: Advanced Model Operations
**Rationale:** Requires mature understanding of model structure. Builds on proven Phase 1-3 foundation.
**Delivers:** Model modification, multi-model composition, advanced parametric tweaking.
**Addresses:** Model modification from description, multi-model composition, model parameter tweaking.

### Phase Ordering Rationale

- Phase 1 first because it has zero external dependencies (no network APIs, no hardware) and establishes the entire skill architecture pattern that all later phases plug into.
- Phase 2 second because MakerWorld scraping is the highest-risk unknown -- isolating it means failure here does not block model generation.
- Phase 3 third because printer integration requires physical testing and the raw-vs-sliced 3MF distinction means the pipeline must be proven before adding direct printing.
- Phase 4 last because advanced model operations are differentiators, not table stakes -- they layer on top of working generation and search.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (MakerWorld):** Needs hands-on API reverse-engineering. No documentation exists. Anti-bot protections are confirmed. Research-phase required.
- **Phase 3 (Printer):** bambulabs-api is unofficial with MEDIUM confidence. Sliced 3MF requirements need validation. Research-phase recommended.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Model Generation):** SolidPython2 + OpenSCAD is well-documented with HIGH confidence. Standard subprocess pattern.
- **Phase 4 (Advanced Operations):** trimesh boolean ops are documented. Can research during implementation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core libraries verified on PyPI with recent releases. Well-established ecosystem. |
| Features | MEDIUM-HIGH | Feature set is clear from domain analysis. MVP scope is well-defined. |
| Architecture | HIGH | Script-per-action with Claude as orchestrator is the documented Claude Code skill pattern. |
| Pitfalls | MEDIUM | MakerWorld risk is real but mitigation strategies are sound. Printer integration pitfalls need hardware validation. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **MakerWorld API structure:** No documentation exists. Must be reverse-engineered from browser DevTools during Phase 2 planning. This is the single biggest unknown.
- **Sliced 3MF creation:** bambulabs-api requires sliced 3MF. Whether OrcaSlicer CLI can automate slicing needs validation before Phase 3.
- **bambulabs-api stability:** Unofficial library. API may change with printer firmware updates. Need to assess maintenance cadence.
- **SolidPython2 + Claude accuracy:** How reliably Claude generates valid SolidPython2 code needs empirical testing in Phase 1. Template library scope TBD.

## Sources

### Primary (HIGH confidence)
- [SolidPython2 PyPI](https://pypi.org/project/solidpython2/) -- v2.1.3, API and usage
- [lib3mf docs](https://lib3mf.readthedocs.io/) -- v2.5.0 docs, 3MF spec compliance
- [trimesh GitHub](https://github.com/mikedh/trimesh) -- v4.11.2, mesh operations API
- [OpenSCAD CLI docs](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Using_OpenSCAD_in_a_command_line_environment) -- command-line rendering
- [Claude Code Skills docs](https://code.claude.com/docs/en/skills) -- skill structure and frontmatter

### Secondary (MEDIUM confidence)
- [bambulabs-api GitHub](https://github.com/BambuTools/bambulabs_api) -- v2.6.6, printer integration examples
- [MakerWorld Apify scrapers](https://apify.com/stealth_mode/makerworld-models-details-scraper) -- confirms scraping feasibility and anti-bot protections
- [build123d docs](https://build123d.readthedocs.io/) -- BREP alternative considered and rejected

### Tertiary (LOW confidence)
- MakerWorld internal API structure -- inferred from SPA architecture, needs hands-on validation
- OrcaSlicer CLI slicing capabilities -- not yet researched, needed for Phase 3

---
*Research completed: 2026-03-05*
*Ready for roadmap: yes*
