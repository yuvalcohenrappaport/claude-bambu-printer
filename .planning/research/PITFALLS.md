# Domain Pitfalls

**Domain:** Claude-powered 3D printing automation
**Researched:** 2026-03-05

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: MakerWorld Blocks Automated Access
**What goes wrong:** MakerWorld has anti-bot protections. Automated requests get blocked, rate-limited, or return CAPTCHAs.
**Why it happens:** MakerWorld is a commercial platform (Bambu Lab). They actively monitor and throttle scraping.
**Consequences:** Core search feature breaks. No models to show users.
**Prevention:**
- Start by reverse-engineering the internal JSON API (inspect browser DevTools network tab). SPA sites often have clean API endpoints.
- Implement request rate limiting (1-2 requests/second max).
- Use realistic User-Agent headers.
- Cache search results aggressively (24h+ for search queries, permanent for model metadata).
- Have a fallback: if API access fails, gracefully degrade to suggesting manual MakerWorld search.
**Detection:** HTTP 403/429 responses. Empty results for known-good queries.

### Pitfall 2: OpenSCAD Not Installed or Wrong Version
**What goes wrong:** Python scripts assume OpenSCAD CLI is available, but it's not installed or is an old version without 3MF support.
**Why it happens:** OpenSCAD is a system dependency, not a pip package. Users forget to install it.
**Consequences:** Model generation silently fails or produces STL instead of 3MF.
**Prevention:**
- Check OpenSCAD availability on skill initialization: `openscad --version`.
- Document `brew install openscad` prominently in setup instructions.
- Fail fast with clear error message if OpenSCAD is missing.
- Pin minimum version requirement (2021.01+ for basic, 2025.08+ for 3MF export).
**Detection:** `FileNotFoundError` on subprocess call. Missing 3MF output despite successful render.

### Pitfall 3: Non-Watertight Meshes Fail to Print
**What goes wrong:** Generated or downloaded models have holes, self-intersections, or inverted normals. BambuStudio/printer rejects them.
**Why it happens:** OpenSCAD CSG operations can produce degenerate geometry. Downloaded models from MakerWorld may have quality issues.
**Consequences:** Print job fails at slicer stage. User gets cryptic error from printer.
**Prevention:**
- Use trimesh to validate watertight status after every render: `mesh.is_watertight`.
- Auto-fix common issues: `trimesh.repair.fix_winding(mesh)`, `trimesh.repair.fill_holes(mesh)`.
- Warn user if mesh has issues that can't be auto-fixed.
**Detection:** `mesh.is_watertight == False`. Negative volume. Self-intersection check.

### Pitfall 4: Claude Generates Invalid OpenSCAD Code
**What goes wrong:** When Claude writes SolidPython2 code for model generation, the code may have syntax errors, invalid operations, or produce empty geometry.
**Why it happens:** LLMs hallucinate API calls. SolidPython2 has specific conventions that Claude may not know precisely.
**Consequences:** OpenSCAD render fails. User gets no model.
**Prevention:**
- Include SolidPython2 API reference in SKILL.md (common primitives, transforms, boolean ops).
- Always render and validate output before presenting to user.
- Catch subprocess errors from OpenSCAD and show Claude the error log for self-correction.
- Keep a library of known-good templates for common shapes (box, cylinder, hook, bracket, stand).
**Detection:** Non-zero exit code from OpenSCAD. Empty output file. Zero-volume mesh.

## Moderate Pitfalls

### Pitfall 1: 3MF Format Confusion
**What goes wrong:** Confusing "raw 3MF" (mesh only) with "sliced 3MF" (BambuStudio project with G-code). BambuLab printers need sliced 3MF for direct printing.
**Prevention:**
- For Phase 1, export raw 3MF and instruct user to open in BambuStudio for slicing.
- bambulabs-api's `start_print()` expects a sliced 3MF (created by BambuStudio/OrcaSlicer).
- Direct printing of unsliced 3MF is NOT supported by BambuLab printers.
- Phase 2 could integrate OrcaSlicer CLI for automated slicing.

### Pitfall 2: Printer Connection Requires Local Network
**What goes wrong:** bambulabs-api connects via MQTT on local network. Fails if printer is on different subnet or behind firewall.
**Prevention:**
- Document network requirements clearly (same network, ports 8883/6000/990 open).
- Provide connection test script that validates connectivity before attempting print.
- Consider bambu-lab-cloud-api as fallback for cloud-connected printers.

### Pitfall 3: SolidPython2 Import Name
**What goes wrong:** Package is `solidpython2` on PyPI but imported as `solid2` in Python. Confusing.
**Prevention:**
- Document clearly: `pip install solidpython2` but `from solid2 import *`.
- Include correct import in SKILL.md reference material.

### Pitfall 4: OpenSCAD Render Timeout
**What goes wrong:** Complex models (many boolean operations, high polygon count) can take minutes to render in OpenSCAD.
**Prevention:**
- Set subprocess timeout (60 seconds default).
- Warn user if model is complex.
- Suggest reducing detail for preview renders.
- Use `openscad --render` flag explicitly (some operations need full CGAL render).

### Pitfall 5: MakerWorld License Compliance
**What goes wrong:** Downloading and modifying models without respecting their license (CC-BY, CC-BY-NC, etc.).
**Prevention:**
- Always display license info in search results.
- Warn user about license restrictions before download.
- Store license metadata with downloaded models.

## Minor Pitfalls

### Pitfall 1: Large File Sizes
**What goes wrong:** High-polygon models create large 3MF files (50MB+).
**Prevention:** Use trimesh to simplify meshes before export. `mesh.simplify_quadric_decimation(target_faces)`.

### Pitfall 2: Unit Mismatch
**What goes wrong:** OpenSCAD defaults to mm, but user specifies cm or inches.
**Prevention:** Always convert to mm internally. Document unit convention in SKILL.md.

### Pitfall 3: macOS OpenSCAD Path
**What goes wrong:** Homebrew installs OpenSCAD differently than the .dmg installer. Path may be `/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD` or `/opt/homebrew/bin/openscad`.
**Prevention:** Check both paths. Use `which openscad` first, fall back to known locations.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| MakerWorld scraping | API blocks/changes without notice | Cache aggressively, have fallback search |
| OpenSCAD generation | Claude writes invalid SolidPython2 | Include API cheatsheet, validate output, retry |
| 3MF export | Confusing raw vs sliced 3MF | Phase 1: export raw, user slices in BambuStudio |
| Printer integration | Network connectivity issues | Connection test script, clear docs |
| Model transformation | Non-manifold geometry after operations | trimesh validation + repair after every transform |
| Claude Code skill | SKILL.md too large, exceeds context | Keep SKILL.md under 500 lines, use supporting files |

## Sources

- [OpenSCAD headless issues](https://github.com/openscad/openscad/issues/3368) -- known headless rendering challenges
- [bambulabs-api README](https://github.com/BambuTools/bambulabs_api/blob/main/README.md) -- network requirements
- [MakerWorld scraping tools](https://apify.com/stealth_mode/makerworld-models-details-scraper) -- confirms anti-bot protections exist
- [trimesh docs](https://trimesh.org/) -- mesh repair and validation API
- [Claude Code skills docs](https://code.claude.com/docs/en/skills) -- skill size recommendations
