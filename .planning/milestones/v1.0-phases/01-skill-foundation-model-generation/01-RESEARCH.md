# Phase 1: Skill Foundation + Model Generation - Research

**Researched:** 2026-03-05
**Domain:** Claude Code Skills, OpenSCAD CLI, LLM-driven 3D model generation
**Confidence:** HIGH

## Summary

This phase creates a Claude Code skill that converts natural language descriptions into print-ready 3MF files via OpenSCAD. The core technical components are: (1) a Claude Code skill with slash command and natural language detection, (2) OpenSCAD code generation by Claude, (3) OpenSCAD CLI invocation for rendering PNG previews and exporting 3MF files.

The ecosystem is mature and well-documented. OpenSCAD's CLI supports all needed operations (render, preview PNG, export 3MF). Claude Code's skill system provides exactly the right abstraction for this use case -- a SKILL.md file with frontmatter for slash command registration and natural language intent detection. LLM-generated OpenSCAD is a proven pattern with known failure modes (origin offsets, tolerance oversights, magic numbers) that can be mitigated with good prompting and auto-retry.

**Primary recommendation:** Use raw OpenSCAD (not SolidPython2) for code generation, the stable Homebrew cask for installation, and Claude Code's skill system with supporting files for templates and reference material.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Dual trigger: slash command (/print) AND natural language intent detection
- Always ask clarifying questions before generating: dimensions, use case, material (PLA/PETG/TPU)
- Material choice affects design decisions (wall thickness, tolerances)
- Hybrid template approach: pre-built parametric templates when available, freeform for novel requests
- Templates built as needed based on actual user requests (not a pre-shipped starter set)
- Show generated OpenSCAD code to the user
- Save both .scad source and .3mf output files
- Render preview PNG via OpenSCAD before exporting 3MF
- Detailed output summary: preview image + dimensions + material suggestion + file path + SCAD code
- After generation, ask "Want me to open this in BambuStudio?" (don't auto-open, don't skip)
- Auto-fix and retry on OpenSCAD compilation errors (up to 3 attempts)
- For complex models: try anyway with a clear warning about accuracy
- OpenSCAD install check: ask user permission, then install via Homebrew
- Vague input: ask what they need and what it's for

### Claude's Discretion
- Project directory structure vs independent requests for file organization
- Raw OpenSCAD vs SolidPython2 (pick based on research findings)
- Exact retry logic and error message formatting
- Preview render angle and resolution

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SKIL-01 | Tool works as a Claude Code skill invoked via natural language | Claude Code skill system with `description` field enables automatic invocation on relevant prompts |
| SKIL-02 | System checks for OpenSCAD installation and guides user if missing | `which openscad` or check `/Applications/OpenSCAD.app`; install via `brew install --cask openscad` |
| SKIL-03 | All generated files saved to local filesystem with clear paths | Skill writes .scad and .3mf to a project output directory |
| GEN-01 | User can request a simple parametric model by description | OpenSCAD primitives (cube, cylinder, sphere) + CSG ops handle boxes, brackets, holders, mounts |
| GEN-02 | Claude generates valid OpenSCAD code from natural language | Raw OpenSCAD generation is a proven LLM pattern; reference material in skill supporting files |
| GEN-03 | User can specify dimensions for generated models | OpenSCAD parametric variables; clarification step captures dimensions before generation |
| CUST-03 | System exports all models to 3MF format | OpenSCAD CLI: `openscad -o output.3mf input.scad` (supported since 2021.01) |

</phase_requirements>

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| OpenSCAD | 2021.01 (stable cask) | 3D CSG modeling + CLI rendering/export | Only text-based parametric CAD with CLI export to 3MF; proven LLM target |
| Claude Code Skills | Current | Skill framework (SKILL.md + frontmatter) | Native skill system with slash commands + NL intent detection |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| Homebrew | System | OpenSCAD installation | When OpenSCAD not found on system |
| BambuStudio | User-installed | Open 3MF files for printing | Post-generation "open in slicer" step |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw OpenSCAD | SolidPython2 | SolidPython2 adds a Python dependency layer with no proven LLM generation advantage. Raw OpenSCAD has more training data, users can edit .scad files directly, and the code shown to users is more readable. **Recommendation: Use raw OpenSCAD.** |
| OpenSCAD stable (2021.01) | OpenSCAD snapshot (2026.01) | Snapshot has newer features but stable has 3MF export and is sufficient. Snapshot requires `brew install --cask openscad@snapshot`. Stick with stable unless a specific feature is needed. |
| OpenSCAD | CadQuery (Python) | CadQuery produces more concise code for complex shapes but requires Python kernel, has less LLM training data for OpenSCAD-style output, and doesn't align with the "show SCAD code" decision. |

**Installation (OpenSCAD):**
```bash
brew install --cask openscad
```

**Binary path on macOS:**
```
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD
```

## Architecture Patterns

### Recommended Skill Structure
```
.claude/skills/print/
  SKILL.md              # Main skill entry point (slash command + NL detection)
  reference/
    openscad-guide.md   # OpenSCAD patterns and best practices for generation
    materials.md        # Material-specific design parameters (wall thickness, tolerances)
  templates/            # Parametric templates (built over time)
    box.scad            # Example: parametric box template
```

### Recommended Output Structure
```
~/3d-prints/
  <project-name>/
    model.scad          # Generated OpenSCAD source
    model.3mf           # Exported 3MF file
    preview.png         # Rendered preview image
```

**Discretion recommendation (file organization):** Use a flat `~/3d-prints/` directory with timestamped or descriptive subdirectories per generation. No formal project management -- each generation is independent. This keeps things simple for the typical use case (one-off prints).

### Pattern 1: Skill Entry Point (SKILL.md)
**What:** Claude Code skill with dual invocation
**When to use:** Always -- this is the main entry point

```yaml
---
name: print
description: >
  Generate 3D printable models from natural language descriptions.
  Use when the user wants to 3D print something, create a model,
  design a part, or make something for their printer.
  Handles OpenSCAD code generation, preview rendering, and 3MF export.
allowed-tools: Bash, Read, Write, Glob, Grep
---
```

### Pattern 2: OpenSCAD CLI Invocation
**What:** Shell commands for rendering and exporting
**When to use:** After generating .scad code

```bash
# Check if OpenSCAD is installed
OPENSCAD="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
if [ ! -f "$OPENSCAD" ]; then
  # Try system PATH as fallback
  OPENSCAD=$(which openscad 2>/dev/null)
fi

# Render preview PNG (perspective view, 800x600)
"$OPENSCAD" --imgsize 800,600 --projection p --colorscheme DeepOcean --render -o preview.png model.scad

# Export 3MF
"$OPENSCAD" -o model.3mf model.scad

# Open in BambuStudio (macOS)
open -a BambuStudio model.3mf
```

### Pattern 3: Parametric OpenSCAD Template
**What:** Well-structured OpenSCAD code that Claude should generate
**When to use:** As a reference pattern for all generated code

```openscad
// Parametric Box with Lid
// Generated for: [user description]
// Material: PLA | Wall: 2mm | Tolerance: 0.3mm

/* [Dimensions] */
width = 80;       // mm
depth = 60;       // mm
height = 40;      // mm
wall = 2;         // mm - wall thickness
corner_r = 3;     // mm - corner radius

/* [Lid] */
lid_height = 10;  // mm
lid_clearance = 0.3; // mm - printing tolerance

/* [Quality] */
$fn = 60;         // circle resolution

module rounded_box(w, d, h, r) {
    hull() {
        for (x = [r, w-r], y = [r, d-r])
            translate([x, y, 0])
                cylinder(h=h, r=r);
    }
}

// Box body
difference() {
    rounded_box(width, depth, height, corner_r);
    translate([wall, wall, wall])
        rounded_box(width - 2*wall, depth - 2*wall, height, corner_r);
}

// Lid (offset for visibility)
translate([0, 0, height + 5]) {
    difference() {
        rounded_box(width, depth, lid_height, corner_r);
        translate([wall, wall, wall])
            rounded_box(width - 2*wall, depth - 2*wall, lid_height, corner_r);
    }
    // Lid insert lip
    translate([wall + lid_clearance, wall + lid_clearance, 0])
        difference() {
            rounded_box(width - 2*wall - 2*lid_clearance, depth - 2*wall - 2*lid_clearance, wall, corner_r);
            translate([wall, wall, -0.1])
                rounded_box(width - 4*wall - 2*lid_clearance, depth - 4*wall - 2*lid_clearance, wall + 0.2, corner_r);
        }
}
```

### Pattern 4: Error Detection and Retry
**What:** Parse OpenSCAD stderr for compilation errors, fix, retry
**When to use:** When OpenSCAD CLI returns non-zero exit code

```bash
# Run OpenSCAD and capture stderr
OPENSCAD="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
"$OPENSCAD" -o model.3mf model.scad 2>openscad_errors.txt
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    cat openscad_errors.txt
    # Claude reads error, fixes .scad, retries (up to 3 times)
fi
```

### Anti-Patterns to Avoid
- **Generating STL instead of 3MF:** The user decision is 3MF. STL lacks color/material metadata. Always export .3mf.
- **Hardcoded magic numbers:** Always use named variables at the top of the .scad file. This enables parametric modification.
- **Missing $fn:** Low polygon count makes cylinders look faceted. Always set `$fn` appropriately (40-60 for previews, 100+ for final).
- **Zero-thickness walls:** When subtracting shapes, ensure the subtracted shape extends slightly beyond the surface (add 0.1mm overlap) to avoid non-manifold geometry.
- **Generating code without clarification:** The locked decision requires always asking dimensions, use case, and material first.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 3MF export | Custom mesh-to-3MF converter | OpenSCAD CLI `-o model.3mf` | 3MF is complex (ZIP with XML); OpenSCAD handles it natively |
| PNG preview rendering | Three.js or custom renderer | OpenSCAD CLI `-o preview.png` | OpenSCAD has built-in ray-traced rendering |
| STL/3MF validation | Custom mesh validator | OpenSCAD's built-in manifold checks | OpenSCAD warns on non-manifold geometry during render |
| OpenSCAD installation | Custom installer script | `brew install --cask openscad` | Homebrew handles versioning, updates, uninstall |
| Parametric UI | Custom parameter editor | OpenSCAD `/* [Group] */` comments + variables | OpenSCAD Customizer reads these annotations natively |

**Key insight:** OpenSCAD's CLI is the entire rendering/export pipeline. The skill's job is generating good .scad code and orchestrating the CLI -- not reimplementing any CAD functionality.

## Common Pitfalls

### Pitfall 1: Non-Manifold Geometry
**What goes wrong:** Subtracting a cylinder from a cube where surfaces are perfectly flush creates zero-thickness walls. Slicers reject or misinterpret these models.
**Why it happens:** Beginner OpenSCAD mistake -- not extending cut shapes beyond the surface.
**How to avoid:** Always extend subtracted shapes by 0.1mm beyond the parent surface. Include this in the OpenSCAD generation prompt.
**Warning signs:** OpenSCAD warnings about "Object may not be a valid 2-manifold"

### Pitfall 2: Missing Tolerances for Interlocking Parts
**What goes wrong:** Parts designed to fit together (lid on box, insert in hole) are exact size, so they don't fit when printed.
**Why it happens:** 3D printing adds ~0.2-0.4mm per side. LLMs often ignore manufacturing tolerances.
**How to avoid:** Add clearance parameters. PLA: 0.3mm, PETG: 0.35mm, TPU: 0.4mm. The clarification step captures material to set this.
**Warning signs:** User says "it doesn't fit" after printing.

### Pitfall 3: Thin Walls Below Printable Minimum
**What goes wrong:** Walls thinner than 1.2mm (2 perimeters at 0.4mm nozzle) may not print or be fragile.
**Why it happens:** LLM generates aesthetically reasonable but physically unprintable dimensions.
**How to avoid:** Enforce minimum wall thickness: 1.2mm for PLA/PETG, 1.6mm for TPU. Warn if generated values are below.
**Warning signs:** Wall thickness variable < 1.2mm.

### Pitfall 4: OpenSCAD Headless Rendering on macOS
**What goes wrong:** OpenSCAD may need a display context even in CLI mode on some macOS versions.
**Why it happens:** OpenSCAD uses OpenGL for rendering, which may require a display.
**How to avoid:** The `--render` flag forces CGAL backend which is display-independent. For PNG export, test on target macOS to confirm headless works. If issues arise, the snapshot version may handle this better.
**Warning signs:** "Can't open display" or OpenGL errors in stderr.

### Pitfall 5: Large $fn Values Causing Slow Renders
**What goes wrong:** Setting `$fn = 200` on complex models causes renders to take minutes.
**Why it happens:** CGAL rendering time scales with polygon count.
**How to avoid:** Use `$fn = 60` as default. Only increase for final export of simple models. Use `$fn = 30` for quick previews.
**Warning signs:** OpenSCAD CLI hangs for > 30 seconds.

### Pitfall 6: Origin Offset Errors in Generated Code
**What goes wrong:** LLMs miscalculate coordinate positions, placing parts in wrong locations or overlapping.
**Why it happens:** Spatial reasoning is a known LLM weakness. Components end up intersecting or floating.
**How to avoid:** Use modular design (separate `module` per component), center objects at origin, use `translate()` for explicit positioning. Include positioning best practices in the generation prompt.
**Warning signs:** Preview PNG shows overlapping or disconnected geometry.

## Code Examples

### OpenSCAD Installation Check
```bash
# Check for OpenSCAD on macOS
check_openscad() {
    local openscad_path="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"

    if [ -f "$openscad_path" ]; then
        echo "$openscad_path"
        return 0
    fi

    # Check PATH as fallback
    local which_path=$(which openscad 2>/dev/null)
    if [ -n "$which_path" ]; then
        echo "$which_path"
        return 0
    fi

    return 1
}
```

### Full Render + Export Pipeline
```bash
OPENSCAD="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
SCAD_FILE="$OUTPUT_DIR/model.scad"
PREVIEW_FILE="$OUTPUT_DIR/preview.png"
EXPORT_FILE="$OUTPUT_DIR/model.3mf"

# Step 1: Render preview PNG
"$OPENSCAD" \
    --imgsize 800,600 \
    --projection p \
    --render \
    --colorscheme DeepOcean \
    -o "$PREVIEW_FILE" \
    "$SCAD_FILE" 2>>"$OUTPUT_DIR/openscad.log"

# Step 2: Export 3MF
"$OPENSCAD" \
    -o "$EXPORT_FILE" \
    "$SCAD_FILE" 2>>"$OUTPUT_DIR/openscad.log"
```

### Material-Specific Design Parameters
```
Material reference for generated OpenSCAD:

PLA:
  - Min wall thickness: 1.2mm
  - Tolerance/clearance: 0.3mm per side
  - Good for: rigid parts, display items, organizers
  - Avoid: high-temp or outdoor use

PETG:
  - Min wall thickness: 1.2mm
  - Tolerance/clearance: 0.35mm per side
  - Good for: mechanical parts, water-resistant items
  - Avoid: parts needing precise dimensional accuracy

TPU (flexible):
  - Min wall thickness: 1.6mm
  - Tolerance/clearance: 0.4mm per side
  - Good for: phone cases, gaskets, flexible mounts
  - Avoid: rigid structural parts
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| STL export only | 3MF as standard export | OpenSCAD 2021.01 | 3MF supports colors, materials, metadata |
| `.claude/commands/` | `.claude/skills/` with SKILL.md | Claude Code 2.1.3 (Jan 2026) | Skills support frontmatter, supporting files, subagents |
| SolidPython (v1) | SolidPython2 (v2.1.3) | 2024 | v2 is extensible but not needed -- raw OpenSCAD is better for LLM generation |
| Manual OpenSCAD prompting | Structured LLM + OpenSCAD pipelines | 2024-2025 | Multiple projects (MCP servers, Claude pipelines) demonstrate viability |

**Deprecated/outdated:**
- `.claude/commands/` directory: Still works but `.claude/skills/` is recommended. Skills support frontmatter and supporting files.
- SolidPython v1: Replaced by SolidPython2, but neither is needed for this use case.

## Open Questions

1. **Headless PNG rendering on macOS**
   - What we know: OpenSCAD uses OpenGL. CLI with `--render` should work headless via CGAL.
   - What's unclear: Whether all macOS versions (especially with Apple Silicon) handle this without issues.
   - Recommendation: Test early in implementation. Fall back to `--preview` mode or skip PNG if headless fails. This is low risk -- most macOS setups handle it fine.

2. **OpenSCAD snapshot vs stable for 3MF quality**
   - What we know: Stable (2021.01) supports 3MF via lib3MF v2.0. Snapshot (2026.01) may have improvements.
   - What's unclear: Whether stable 3MF output has any quality issues with modern slicers.
   - Recommendation: Start with stable. If 3MF issues arise, switch install instruction to `brew install --cask openscad@snapshot`.

3. **Optimal preview camera angle**
   - What we know: OpenSCAD supports `--camera` with gimbal or vector modes, `--viewall` and `--autocenter` flags.
   - What's unclear: Best default angle for showing most objects clearly.
   - Recommendation: Use `--autocenter --viewall` for automatic framing. For camera angle, use the default perspective (isometric-like view) which works well for most objects. Can be refined later.

## Sources

### Primary (HIGH confidence)
- [Claude Code Skills documentation](https://code.claude.com/docs/en/skills) -- full skill system reference (fetched 2026-03-05)
- [OpenSCAD CLI documentation](https://files.openscad.org/documentation/manual/Using_OpenSCAD_in_a_command_line_environment.html) -- all CLI flags and options
- [OpenSCAD Homebrew cask](https://formulae.brew.sh/cask/openscad) -- installation and version info
- [OpenSCAD 2021.01 release notes](https://github.com/openscad/openscad/releases/tag/openscad-2021.01) -- confirmed lib3MF v2 and 3MF export support

### Secondary (MEDIUM confidence)
- [LLM OpenSCAD generation analysis](https://xn--mikoak-6db.net/blog/2025/coding-llms-making-graphics-and-physical-things.html) -- tested multiple LLMs including Claude for OpenSCAD generation, documented common error types
- [Claude + OpenSCAD workflow](https://3dprinteracademy.com/blogs/news-1/ai-cad-design-with-openscad-and-anthropic-s-claude-3-5-sonnet) -- practical workflow validation
- [SolidPython2 on PyPI](https://pypi.org/project/solidpython2/) -- version 2.1.3, actively maintained

### Tertiary (LOW confidence)
- OpenSCAD headless rendering behavior on Apple Silicon macOS -- needs empirical validation
- BambuStudio CLI open command (`open -a BambuStudio`) -- assumed standard macOS `open` behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- OpenSCAD CLI and Claude Code skills are well-documented with official sources
- Architecture: HIGH -- skill structure follows official Claude Code patterns exactly
- Code generation approach: HIGH -- raw OpenSCAD over SolidPython2 is supported by LLM benchmarks and practical evidence
- Pitfalls: HIGH -- common OpenSCAD/3D-printing pitfalls are extensively documented
- Headless rendering: MEDIUM -- needs empirical testing on target macOS

**Discretion decisions made:**
- **Raw OpenSCAD over SolidPython2:** Raw OpenSCAD has more LLM training data, no dependency layer, users can edit .scad directly, and code shown to users is more readable. SolidPython2 adds complexity without proven generation quality improvement.
- **File organization:** Flat `~/3d-prints/<descriptive-name>/` directory per generation. Simple, no project management overhead.
- **Preview settings:** 800x600 PNG, perspective projection, `--autocenter --viewall`, DeepOcean color scheme (dark background, good contrast).
- **Retry logic:** 3 attempts max. On each failure: read stderr, identify error, fix .scad code, retry. After 3 failures, show error to user with the .scad code for manual fixing.

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain, 30-day validity)
