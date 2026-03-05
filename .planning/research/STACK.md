# Stack Research

**Domain:** Claude-powered 3D printing automation (MakerWorld scraping, OpenSCAD generation, 3MF export, BambuLab integration)
**Researched:** 2026-03-05
**Confidence:** MEDIUM-HIGH

## Recommended Stack

### Language: Python

Use Python. Rationale: Every critical library in this domain (SolidPython2, lib3mf, trimesh, bambulabs-api) is Python-native. OpenSCAD CLI integration is trivial from Python. The Claude Code skill layer is language-agnostic (bash scripts + SKILL.md). TypeScript has no equivalent ecosystem for CAD/mesh operations.

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Python** | 3.11+ | Runtime | All CAD/mesh/printer libraries are Python-first. 3.11+ for `tomllib` and performance. | HIGH |
| **SolidPython2** | 2.1.3 | OpenSCAD code generation from Python | Most mature Python-to-OpenSCAD bridge. Generates .scad files programmatically using Python syntax (loops, variables, functions). Active development (last release Aug 2025). | HIGH |
| **OpenSCAD** | 2025.08.17 | CSG rendering + export | CLI renders .scad to .stl/.3mf headlessly. Supports `openscad -o output.3mf input.scad` directly. Well-documented command-line interface. Must be installed as system dependency. | HIGH |
| **lib3mf** | 2.4.1 | 3MF file creation/manipulation | Official 3MF Consortium library. Python bindings on PyPI. Creates 3MF files with mesh data, metadata, color. The standard for 3MF. | HIGH |
| **trimesh** | 4.11.x | Mesh operations (scale, transform, validate) | Pure Python mesh library. Loads STL/3MF/OBJ. Handles scaling, transformations, boolean ops, watertight checks. Only hard dep is numpy. | HIGH |
| **bambulabs-api** | 2.6.6 | BambuLab printer control via MQTT | Unofficial but most maintained Python API for BambuLab printers. Connects over local network (MQTT on port 8883). Can send 3MF print jobs, monitor status. | MEDIUM |
| **httpx** | 0.28.x | HTTP client for MakerWorld scraping | Modern async-capable HTTP client. Replaces requests. Needed for MakerWorld API calls. | HIGH |
| **BeautifulSoup4** | 4.12.x | HTML parsing for MakerWorld | Lightweight HTML parser for extracting model data from MakerWorld pages. Pair with httpx. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **numpy** | 1.26+ | Mesh math / trimesh dependency | Always (trimesh requires it) |
| **Playwright** | 1.49+ | Browser automation for MakerWorld | Only if MakerWorld blocks httpx requests or requires JS rendering. Fallback, not default. |
| **lxml** | 5.x | Fast XML/HTML parsing | If BS4 is too slow on large MakerWorld responses. Also needed by trimesh for 3MF/XML formats. |
| **Pillow** | 10.x | Image processing for model thumbnails | When displaying/processing model preview images from MakerWorld |
| **pydantic** | 2.x | Data validation for model configs | Validate OpenSCAD parameters, printer configs, search results |
| **click** | 8.x | CLI interface | Phase 2 standalone app CLI. Not needed for Claude Code skill phase. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **pip** | Package management | Small project scope. Poetry overkill for Phase 1. |
| **pytest** | Testing | Test OpenSCAD generation, mesh operations, 3MF export |
| **ruff** | Linting + formatting | Fast, replaces flake8 + black + isort |
| **OpenSCAD (system)** | Rendering engine | Must be installed via `brew install openscad` on macOS |

### Claude Code Skill Layer

| Component | Implementation | Notes |
|-----------|---------------|-------|
| **SKILL.md** | `.claude/skills/3d-print/SKILL.md` | Skill entry point with description and instructions |
| **Python scripts** | `.claude/skills/3d-print/scripts/` | Core Python modules called by skill |
| **Bash wrappers** | `.claude/skills/3d-print/scripts/*.sh` | Thin wrappers Claude executes via `allowed-tools: Bash(python *)` |

Skill structure:
```
.claude/skills/3d-print/
  SKILL.md              # Instructions for Claude
  scripts/
    search_models.py    # MakerWorld search
    generate_scad.py    # OpenSCAD code generation
    render_model.py     # OpenSCAD CLI rendering
    export_3mf.py       # 3MF packaging
    print_job.py        # BambuLab printer integration
```

## Installation

```bash
# System dependencies (macOS)
brew install openscad

# Core Python dependencies
pip install solidpython2 lib3mf trimesh numpy httpx beautifulsoup4 lxml

# Printer integration
pip install bambulabs-api

# Data validation
pip install pydantic

# Dev dependencies
pip install pytest ruff

# Optional: browser automation fallback for MakerWorld
pip install playwright
playwright install chromium
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **SolidPython2** | **build123d** (BREP/OpenCascade) | When you need BREP modeling (fillets, chamfers, exact geometry). build123d is more powerful but heavier -- requires OpenCascade kernel compilation. SolidPython2 is simpler: generates .scad text, let OpenSCAD handle rendering. Better for LLM-generated code since output is readable text. |
| **SolidPython2** | **CadQuery** | CadQuery is mature but complex. Same OpenCascade dependency issue. SolidPython2's text-based output is easier to debug and inspect. |
| **SolidPython2** | **Raw OpenSCAD strings** | When models are simple enough (cube, cylinder). Avoids a dependency. But SolidPython2's Python API prevents syntax errors and enables parameterization. |
| **httpx** | **requests** | Never. requests lacks async support, which matters when searching multiple MakerWorld pages. httpx is a drop-in replacement with async. |
| **httpx + BS4** | **Scrapy** | When building a full crawling pipeline. Overkill for targeted MakerWorld search queries. |
| **lib3mf** | **trimesh 3MF export** | trimesh can export 3MF but with fewer features. Use lib3mf for full 3MF spec compliance (metadata, colors, print settings). Use trimesh for mesh operations before passing to lib3mf. |
| **bambulabs-api** | **bambu-connect** | bambu-connect is newer but less documented. bambulabs-api has more stars, examples, and active maintenance. |
| **bambulabs-api** | **bambu-lab-cloud-api** | For cloud-based (not local network) printer access. Requires Bambu Lab account auth. Use when printer isn't on local network. |
| **pip** | **Poetry** | When project grows to Phase 2 standalone app with many deps. Not needed for Phase 1 skill. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Selenium** | Heavy, slow, outdated for scraping. Playwright is faster with better API. | Playwright (only if JS rendering needed) |
| **STL format** | BambuLab printers use 3MF natively. STL loses color, metadata, print settings. | 3MF via lib3mf |
| **OpenPySCAD** | Abandoned (last update 2020). API incompatible with modern OpenSCAD. | SolidPython2 |
| **solidpython** (v1) | Legacy. All development moved to solidpython2. | solidpython2 |
| **FreeCAD Python** | Massive dependency, GUI-oriented. Overkill for programmatic model generation. | SolidPython2 + OpenSCAD CLI |
| **Blender Python** | Even heavier than FreeCAD. Designed for artistic modeling, not parametric CAD. | SolidPython2 + OpenSCAD CLI |
| **Node.js/TypeScript** | No equivalent ecosystem for CAD operations. Would require FFI bridges to C++ libs. | Python |
| **Thingiverse API** | Thingiverse is deprecated/unreliable. MakerWorld is BambuLab's native platform. | MakerWorld scraping |

## Stack Patterns by Variant

**Phase 1 -- Claude Code Skill:**
- Pure Python scripts in `.claude/skills/3d-print/scripts/`
- No web framework, no database
- Claude orchestrates via SKILL.md instructions
- User interaction through natural language in Claude Code

**Phase 2 -- Standalone CLI App:**
- Add `click` for CLI interface
- Add SQLite (via `sqlite3` stdlib) for caching MakerWorld results
- Add `rich` for terminal UI
- Consider Poetry for dependency management

**Phase 2 -- Web App (if needed):**
- Add FastAPI for API layer
- Add React/Next.js frontend
- Add PostgreSQL for persistent storage
- This is a significant scope expansion -- only if CLI proves insufficient

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| solidpython2 2.1.x | OpenSCAD 2021.01+ | Generates .scad syntax compatible with all recent OpenSCAD versions |
| OpenSCAD 2025.08.17 | lib3mf (system) | OpenSCAD's 3MF export requires lib3mf at system level (bundled in brew install) |
| trimesh 4.x | numpy 1.26+ | trimesh 4.x dropped numpy <1.26 support |
| lib3mf 2.4.1 | Python 3.8+ | C++ bindings, works on macOS/Linux/Windows |
| bambulabs-api 2.6.x | paho-mqtt 1.x/2.x | Uses MQTT for printer communication |
| httpx 0.28.x | Python 3.8+ | No conflicts with other deps |

## Critical Technical Notes

### MakerWorld Scraping Strategy
MakerWorld has no public API. Two approaches:
1. **Reverse-engineer internal JSON API** (recommended): Inspect network traffic to find search/detail endpoints that return JSON. Likely `https://makerworld.com/api/...` endpoints. MEDIUM confidence this exists based on SPA architecture.
2. **HTML scraping with httpx + BS4**: Fallback if no JSON API found. May need Playwright if content is JS-rendered.
3. **Model download**: Models are typically .3mf or .stl files behind authenticated download URLs. May require session cookies.

**Risk:** MakerWorld may block automated access. Rate limiting and user-agent rotation may be needed. This is the highest-risk component of the stack.

### OpenSCAD as External Process
SolidPython2 generates .scad text files. Rendering requires shelling out to `openscad` CLI:
```python
import subprocess
subprocess.run(["openscad", "-o", "output.3mf", "input.scad"], check=True)
```
This is the standard pattern. OpenSCAD handles all CSG computation and mesh generation. Python never touches the geometry directly.

### 3MF Pipeline
Two paths to 3MF:
1. **OpenSCAD direct**: `openscad -o output.3mf input.scad` -- simplest, use when generating new models
2. **trimesh + lib3mf**: Load existing STL/3MF from MakerWorld, transform with trimesh, export with lib3mf -- use when modifying existing models

## Sources

- [SolidPython2 PyPI](https://pypi.org/project/solidpython2/) -- version 2.1.3, last updated Aug 2025
- [lib3mf PyPI](https://pypi.org/project/lib3mf/) -- version 2.4.1, official 3MF Consortium
- [lib3mf docs](https://lib3mf.readthedocs.io/) -- v2.5.0 docs available
- [trimesh GitHub](https://github.com/mikedh/trimesh) -- v4.11.2, actively maintained
- [bambulabs-api PyPI](https://pypi.org/project/bambulabs-api/) -- v2.6.6, unofficial BambuLab API
- [bambulabs-api GitHub](https://github.com/BambuTools/bambulabs_api) -- examples and docs
- [OpenSCAD CLI docs](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Using_OpenSCAD_in_a_command_line_environment) -- command-line usage
- [OpenSCAD releases](https://github.com/openscad/openscad/releases) -- 2025.08.17 with 3MF export
- [Claude Code Skills docs](https://code.claude.com/docs/en/skills) -- skill structure and frontmatter
- [MakerWorld Apify scrapers](https://apify.com/stealth_mode/makerworld-models-details-scraper) -- confirms scraping is feasible
- [build123d docs](https://build123d.readthedocs.io/) -- BREP alternative considered

---
*Stack research for: Claude-powered BambuLab 3D printing automation*
*Researched: 2026-03-05*
