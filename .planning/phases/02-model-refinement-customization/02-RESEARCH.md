# Phase 2: Model Refinement + Customization - Research

**Researched:** 2026-03-06
**Domain:** OpenSCAD model modification, scaling, printability analysis, 3MF metadata injection
**Confidence:** HIGH

## Summary

This phase extends the `/print` skill so users can iterate on generated models (modify by description, scale/resize), receive confidence feedback on complex geometry, and get print setting recommendations embedded directly into the 3MF file. The core technical challenges are: (1) modifying existing .scad files while preserving parametric structure, (2) implementing wall-thickness-preserving scaling, (3) analyzing .scad code for printability risks, and (4) injecting BambuStudio-compatible print settings into the 3MF output.

The modification and scaling work operates entirely within OpenSCAD code -- Claude reads existing .scad files, understands the parametric variables and module structure, then rewrites them. No new libraries are needed. Printability analysis is also code-based: Claude examines the .scad source for patterns known to cause print issues (steep overhangs, thin walls, long bridges, complex boolean operations). The 3MF embedding is the most technically involved piece -- 3MF files are ZIP archives, and BambuStudio stores print settings in `Metadata/` config files using Slic3r-derived INI-style key-value pairs. We can post-process the OpenSCAD-exported 3MF by unzipping, injecting a config file, and rezipping.

**Primary recommendation:** All Phase 2 capabilities are SKILL.md extensions -- add new sections to the existing skill for modification, scaling, confidence assessment, and print settings. The 3MF metadata injection uses a simple bash script (unzip/inject/rezip) rather than any external library.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Modification flow:**
- Reference previous models via conversation context if recent, or browse ~/3d-prints/ folders if starting fresh
- Edit existing .scad file in place, but keep backups as model_v1.scad, model_v2.scad, etc.
- After modifying, show the code changes and ask "want me to render this?" before running OpenSCAD -- do not auto-render
- After 5+ iterations, suggest regenerating from scratch if the model is getting messy

**Scaling behavior:**
- Preserve wall thickness when scaling -- walls stay at their designed value (e.g., 2mm stays 2mm), only outer dimensions change
- Accept both relative ("20% taller") and absolute ("set width to 10cm") scaling inputs
- Prefer modifying parametric variables in the .scad file; fall back to scale() transform only if model structure is unclear
- Auto-fix printability issues after scaling (e.g., enforce minimum wall thickness) and tell the user what was adjusted

**Confidence communication:**
- Warn before generating if clearly risky; note after generating for borderline cases
- Use descriptive natural language -- "Simple geometry, should work fine" vs "Complex curves, may need manual tweaking" -- no percentages or tiers
- For low-confidence models, offer alternatives first: "I can try this complex shape, or here's a simpler version that'll definitely work. Which one?"
- Explain WHY something is risky with brief technical reasons -- e.g., "overhangs > 45 degrees need supports", "thin walls under 1mm may not print solidly"

**Print settings:**
- Full profile recommendations: infill, layer height, supports, print speed, temperature, wall count, top/bottom layers
- Settings based on both purpose (what it's for) and geometry (overhangs, thin walls, bridges) -- purpose sets baseline, geometry adjusts specifics
- Embed print settings into the 3MF file metadata so BambuStudio picks them up automatically
- BambuLab-specific by default (BambuStudio profile names, Bambu filament presets), with generic equivalents mentioned

### Claude's Discretion
- Exact versioning scheme for backup files (v1, v2 vs timestamps)
- How to detect when a model is "getting messy" after iterations
- How to analyze .scad geometry for printability risks
- 3MF metadata format for embedding print settings

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GEN-04 | User can modify generated models ("add a hole", "make walls thicker", "add screw holes") | Modification flow pattern: read existing .scad, understand parametric structure, apply changes, backup versioning, show diff before render |
| GEN-05 | Claude attempts complex geometry with clear confidence communication | Printability risk analysis checklist (overhangs, thin walls, bridges, boolean complexity) with natural language confidence feedback |
| CUST-01 | User can apply uniform scaling ("make it 20% bigger") | Wall-preserving scaling via parametric variable modification; scale() transform as fallback |
| CUST-02 | User can apply per-axis scaling ("make it 10cm wider but keep the height") | Per-axis parametric variable adjustment; absolute and relative input parsing |
| CUST-04 | System recommends print settings based on model purpose | Purpose-to-settings mapping table + geometry-based adjustments; 3MF metadata injection via unzip/inject/rezip |

</phase_requirements>

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| OpenSCAD | 2021.01 (stable) | Model generation/modification/export | Already in use from Phase 1 |
| Claude Code Skills | Current | SKILL.md extensions | Already in use from Phase 1 |
| bash (zipinfo/unzip/zip) | System | 3MF metadata injection | 3MF files are ZIP archives; no external tools needed |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| Python zipfile | System Python | Alternative 3MF manipulation | If bash zip/unzip approach proves fragile |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| bash unzip/rezip | Python lib3mf | lib3mf is the official 3MF SDK but massive overkill for injecting a config file; bash keeps it simple |
| Manual config file | BambuStudio CLI import | BambuStudio has no documented CLI for importing settings; manual injection is the reliable path |

**No new installation needed.** All tools are already available from Phase 1 or macOS system tools.

## Architecture Patterns

### SKILL.md Extension Structure

Phase 2 adds new sections to the existing SKILL.md and new reference files:

```
.claude/skills/print/
  SKILL.md                    # Extended with modification, scaling, confidence, settings steps
  reference/
    openscad-guide.md         # Existing (Phase 1)
    materials.md              # Existing (Phase 1)
    print-settings.md         # NEW: purpose-to-settings mapping + BambuStudio parameter names
    printability-checklist.md # NEW: geometry risk patterns and confidence language
```

### Output Structure with Versioning
```
~/3d-prints/<project-name>/
  model.scad          # Current version (always the latest)
  model_v1.scad       # First version backup
  model_v2.scad       # Second version backup
  model.3mf           # Latest export
  preview.png         # Latest preview
  openscad.log        # Latest render log
```

### Pattern 1: Version-Preserving Modification Flow
**What:** Before modifying a .scad file, create a numbered backup, then edit in place
**When to use:** Every time the user requests a model modification

```bash
# Determine next version number
OUTPUT_DIR="$HOME/3d-prints/<project-name>"
NEXT_VER=1
while [ -f "$OUTPUT_DIR/model_v${NEXT_VER}.scad" ]; do
    NEXT_VER=$((NEXT_VER + 1))
done

# Backup current version
cp "$OUTPUT_DIR/model.scad" "$OUTPUT_DIR/model_v${NEXT_VER}.scad"

# Claude then modifies model.scad in place
# Show diff to user before rendering
```

**Discretion recommendation (versioning scheme):** Use sequential `v1`, `v2`, `v3` numbering rather than timestamps. Sequential numbers are easier to reference in conversation ("go back to v2") and sort naturally in file listings. Timestamps add noise without benefit since the file modification time already captures when.

### Pattern 2: Wall-Preserving Parametric Scaling
**What:** Modify outer dimension variables while keeping wall thickness constant
**When to use:** When user requests scaling (uniform or per-axis)

```openscad
// BEFORE scaling (original parametric variables):
width = 80;       // mm - X axis
depth = 60;       // mm - Y axis
height = 40;      // mm - Z axis
wall = 2;         // mm - wall thickness (DO NOT SCALE)

// AFTER "make it 20% bigger" -- scale dimensions, preserve wall:
width = 96;       // mm - X axis (was 80, scaled 1.2x)
depth = 72;       // mm - Y axis (was 60, scaled 1.2x)
height = 48;      // mm - Z axis (was 40, scaled 1.2x)
wall = 2;         // mm - wall thickness (PRESERVED)

// AFTER "make it 10cm wider but keep the height":
width = 100;      // mm - X axis (set to 100mm)
depth = 60;       // mm - Y axis (unchanged)
height = 40;      // mm - Z axis (unchanged)
wall = 2;         // mm - wall thickness (PRESERVED)
```

**Key insight:** The preferred approach is modifying the parametric variables at the top of the .scad file, NOT using `scale()`. The `scale()` transform scales everything including wall thickness, tolerances, and clearances -- which breaks printability. Only fall back to `scale()` if the model lacks clear parametric variables (e.g., imported/messy code).

### Pattern 3: scale() Fallback for Non-Parametric Models
**What:** When the .scad file doesn't have clean parametric variables, use OpenSCAD's scale() as last resort
**When to use:** Only when parametric approach is impossible

```openscad
// Fallback: scale() transform (scales EVERYTHING including walls)
// Warn user that wall thickness will change
scale([1.2, 1.2, 1.0]) {  // 20% wider and deeper, same height
    // ... existing model code ...
}
// NOTE: After scale(), check if wall thickness is still above minimum
// If wall was 2mm and scale is 0.5x, wall becomes 1mm -- below PLA minimum
```

### Pattern 4: 3MF Metadata Injection
**What:** Post-process the OpenSCAD-exported 3MF to inject BambuStudio print settings
**When to use:** After successful 3MF export, when print settings have been determined

```bash
OUTPUT_DIR="$HOME/3d-prints/<project-name>"
THREEMF="$OUTPUT_DIR/model.3mf"
TMPDIR=$(mktemp -d)

# Unzip the 3MF
cd "$TMPDIR"
unzip -q "$THREEMF"

# Create Metadata directory if it doesn't exist
mkdir -p Metadata

# Write print profile config (Slic3r/BambuStudio INI format)
cat > Metadata/print_profile.config << 'PROFILE'
; BambuStudio Print Profile
; Generated by Claude Print Skill

layer_height = 0.2
initial_layer_print_height = 0.2
wall_loops = 2
top_shell_layers = 4
bottom_shell_layers = 3
sparse_infill_density = 20%
sparse_infill_pattern = grid
enable_support = 0
support_type = normal(auto)
print_speed = 250
outer_wall_speed = 150
PROFILE

# Repack the 3MF
cd "$TMPDIR"
rm "$THREEMF"
zip -q -r "$THREEMF" .
rm -rf "$TMPDIR"
```

### Pattern 5: Messiness Detection Heuristic
**What:** After 5+ iterations, detect whether the .scad file has become overly complex
**When to use:** Check iteration count on each modification request

**Discretion recommendation (messiness detection):** Track iteration count via the backup version number. Additionally, check these code quality signals:
- File length exceeds ~200 lines for a simple object (suggests accumulated cruft)
- Multiple commented-out sections (suggests abandoned approaches)
- Nested `difference()` or `union()` deeper than 3 levels
- Variables that shadow or override earlier definitions
- `translate()` chains longer than 3 levels deep

When any of these signals fire AND version count >= 5, suggest: "This model has gone through several iterations and the code is getting complex. Want me to regenerate it from scratch based on what we have now? I'll keep the current version as a backup."

### Anti-Patterns to Avoid
- **Using scale() as the primary scaling method:** scale() changes wall thickness, tolerances, and clearances. Always prefer modifying parametric variables.
- **Auto-rendering after modification:** The user decision explicitly requires asking before rendering. Show the code changes first.
- **Numeric confidence scores:** The user wants natural language ("should work fine", "may need tweaking"), not percentages or tier labels.
- **Overwriting without backup:** Always create a versioned backup before modifying model.scad.
- **Modifying magic numbers in the body:** If dimensions are hardcoded in the model body rather than as variables at the top, refactor them to variables first, then scale.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 3MF creation | Custom 3MF builder from scratch | OpenSCAD export + post-process injection | OpenSCAD already creates valid 3MF; we just inject config |
| Geometry analysis | Custom .scad parser/AST | Claude reading .scad source code | Claude can understand OpenSCAD code semantics better than any parser |
| Print setting profiles | Custom profile database | Hardcoded mapping table in reference file | Finite number of common use cases; a simple lookup table is sufficient |
| File versioning | Custom VCS system | Sequential file copies (model_v1.scad, v2, v3) | Simple, visible, no tooling overhead |
| Overhang detection | Mesh analysis tool | Pattern matching on .scad code | Overhangs come from specific code patterns (steep rotate(), unsupported horizontal surfaces) that Claude can identify from source |

**Key insight:** This phase is almost entirely about SKILL.md prompt engineering and reference file creation. The technical "plumbing" is minimal -- the main work is teaching Claude when and how to modify .scad code, assess printability, and recommend settings.

## Common Pitfalls

### Pitfall 1: scale() Breaking Wall Thickness
**What goes wrong:** Using `scale([0.5, 0.5, 0.5])` on a model halves all dimensions including 2mm walls to 1mm -- below the printable minimum.
**Why it happens:** scale() is a geometric transform that affects everything uniformly.
**How to avoid:** Always modify parametric variables instead. Only use scale() as a last resort for non-parametric models, and always check/enforce minimum wall thickness after.
**Warning signs:** Wall variable value * scale factor < 1.2mm (PLA/PETG) or < 1.6mm (TPU).

### Pitfall 2: 3MF Re-Zipping with Wrong Structure
**What goes wrong:** After unzip/modify/rezip, the 3MF file has the wrong internal path structure (e.g., an extra parent directory) and BambuStudio can't open it.
**Why it happens:** `zip` commands can include or exclude the parent directory depending on how they're invoked.
**How to avoid:** Always `cd` into the extracted directory before zipping. Use `zip -r output.3mf .` (note the dot) to zip from the current directory root.
**Warning signs:** BambuStudio shows "invalid file" or can't load the model.

### Pitfall 3: Config Parameter Name Mismatch
**What goes wrong:** Injecting settings with wrong parameter names (e.g., `infill_density` instead of `sparse_infill_density`) causes BambuStudio to ignore them.
**Why it happens:** BambuStudio uses Slic3r-derived parameter names which don't always match the UI labels.
**How to avoid:** Use the verified parameter names listed in the print-settings.md reference file. Test with a known-good 3MF exported from BambuStudio.
**Warning signs:** Settings don't appear when opening the 3MF in BambuStudio.

### Pitfall 4: Parametric Variable Identification Failure
**What goes wrong:** Claude modifies the wrong variables or misidentifies which variables control outer dimensions vs. wall thickness.
**Why it happens:** Not all .scad files follow the same naming conventions. A variable named `size` could be outer dimension or inner dimension.
**How to avoid:** Read the full .scad file and understand the math before modifying. Look for how variables are used in `cube()`, `cylinder()`, and `difference()` operations. The comment header from Phase 1 generation helps (it labels dimensions and wall thickness).
**Warning signs:** Preview shows unexpected geometry changes after scaling.

### Pitfall 5: Accumulating Cruft in Iterated Models
**What goes wrong:** After 5+ modifications, the .scad file has commented-out code, redundant variables, conflicting modules, and is hard to reason about.
**Why it happens:** Each modification adds/changes code without cleaning up the overall structure.
**How to avoid:** Track version count. At 5+ iterations with messiness signals, suggest regeneration from scratch.
**Warning signs:** File grows significantly per iteration; multiple commented-out blocks; deep nesting.

### Pitfall 6: BambuStudio Overriding Injected Settings
**What goes wrong:** BambuStudio may override injected 3MF settings with its own defaults or user-saved profiles.
**Why it happens:** BambuStudio has a settings priority system where user profiles may take precedence over file-embedded settings.
**How to avoid:** Inform users that embedded settings are recommendations. Tell them to check the settings in BambuStudio before printing. Note this in the output summary.
**Warning signs:** User reports print settings don't match recommendations.

## Code Examples

### Printability Risk Analysis Checklist

Claude should analyze .scad code for these patterns when assessing confidence:

```
RISK INDICATORS (check in .scad source):

HIGH RISK (warn before generating):
- sphere() or complex curves used as primary geometry (organic shapes)
- rotate() with angles creating overhangs > 60 degrees
- Very thin features: any dimension < 1mm
- Unsupported horizontal surfaces spanning > 50mm
- Complex boolean chains: 4+ nested difference()/intersection()
- hull() connecting distant points (unpredictable geometry)

MEDIUM RISK (note after generating):
- rotate() creating 45-60 degree overhangs
- Bridge spans between 30-50mm
- Interlocking parts with tight tolerances (< 0.3mm clearance)
- Features smaller than 2mm in any dimension
- hull() between nearby points

LOW RISK (simple geometry, should work fine):
- Axis-aligned primitives: cube(), cylinder() with no rotation
- Simple difference() operations (holes, cutouts)
- Chamfers and fillets at 45 degrees
- Features > 3mm in all dimensions
- Standard patterns: boxes, brackets, holders, stands
```

### Purpose-to-Settings Mapping

```
PURPOSE-BASED PRINT SETTINGS BASELINE:

Decorative / Display:
  layer_height = 0.12
  wall_loops = 2
  sparse_infill_density = 10%
  top_shell_layers = 5
  bottom_shell_layers = 4
  print_speed = 150
  Note: Fine layers for smooth surface finish

Functional / Mechanical:
  layer_height = 0.2
  wall_loops = 3
  sparse_infill_density = 30%
  top_shell_layers = 4
  bottom_shell_layers = 4
  print_speed = 200
  Note: Strong walls and infill for load-bearing

Quick Prototype / Test Fit:
  layer_height = 0.28
  wall_loops = 2
  sparse_infill_density = 10%
  top_shell_layers = 3
  bottom_shell_layers = 3
  print_speed = 300
  Note: Fast print, minimum material

Storage / Container:
  layer_height = 0.2
  wall_loops = 2
  sparse_infill_density = 15%
  top_shell_layers = 4
  bottom_shell_layers = 3
  print_speed = 250
  Note: Balanced strength and speed

Flexible / TPU:
  layer_height = 0.2
  wall_loops = 3
  sparse_infill_density = 20%
  top_shell_layers = 4
  bottom_shell_layers = 4
  print_speed = 80
  Note: Slow speed critical for TPU

GEOMETRY-BASED ADJUSTMENTS (applied on top of purpose baseline):
- Overhangs > 45 degrees detected: enable_support = 1, support_type = normal(auto)
- Thin walls < 2mm detected: wall_loops += 1
- Bridge spans > 20mm: reduce print_speed for bridge sections
- Large flat top surfaces: top_shell_layers += 1
- Small detailed features: layer_height = min(layer_height, 0.16)
```

### BambuStudio Parameter Reference

Verified parameter names for the INI-style config file (Slic3r/BambuStudio format):

```ini
; Quality
layer_height = 0.2
initial_layer_print_height = 0.2

; Strength - Walls
wall_loops = 2

; Strength - Top/Bottom
top_shell_layers = 4
bottom_shell_layers = 3

; Strength - Infill
sparse_infill_density = 20%
sparse_infill_pattern = grid
; Patterns: grid, triangles, cubic, gyroid, honeycomb, line, rectilinear

; Support
enable_support = 0
support_type = normal(auto)
; Types: normal(auto), tree(auto), normal(manual), tree(manual)

; Speed
print_speed = 250
outer_wall_speed = 150
inner_wall_speed = 250
sparse_infill_speed = 250
top_surface_speed = 150

; Temperature (material-dependent, set by filament profile)
; nozzle_temperature = 220
; bed_temperature = 60
```

### Modification Diff Display

After modifying a .scad file, show changes to the user like this:

```
Changes made to model.scad:
  - width: 80mm -> 96mm (scaled 1.2x)
  - depth: 60mm -> 72mm (scaled 1.2x)
  - height: 40mm -> 48mm (scaled 1.2x)
  - wall: 2mm (preserved)
  - Added: screw_hole_d = 5mm (M5 screw holes)
  - Added: module screw_holes() at lines 45-55

Want me to render this?
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| STL-only export | 3MF with embedded settings | BambuStudio adoption ~2023 | Settings travel with the model file |
| Manual slicer setup | Profile embedded in 3MF | BambuStudio/OrcaSlicer standard | Users get recommended settings automatically |
| Global scale() | Parametric variable modification | OpenSCAD best practice (long-standing) | Wall thickness and tolerances preserved |

**Deprecated/outdated:**
- Slic3r_PE.config: Older config file name from PrusaSlicer era. BambuStudio uses `Metadata/print_profile.config` and `Metadata/project_settings.config`.

## Open Questions

1. **Exact 3MF config file format accepted by BambuStudio**
   - What we know: BambuStudio 3MF files contain `Metadata/print_profile.config` with INI-style key=value pairs. Parameter names derive from Slic3r/PrusaSlicer conventions.
   - What's unclear: Whether BambuStudio reads a standalone `print_profile.config` injected into an OpenSCAD-generated 3MF, or if additional XML references in `[Content_Types].xml` or `_rels/` are required.
   - Recommendation: Test empirically during implementation. Create a known-good 3MF from BambuStudio, examine its structure, use that as the template for injection. If simple injection doesn't work, fall back to recommending settings in the output summary (text) instead of embedding.

2. **BambuStudio settings override behavior**
   - What we know: BambuStudio has a settings priority system. Forum reports indicate 3MF-embedded settings sometimes get overridden by user profiles.
   - What's unclear: Exact priority order and whether there's a way to force 3MF settings.
   - Recommendation: Always inform the user that embedded settings are suggestions. Tell them to review settings in BambuStudio before printing.

3. **Detection of non-parametric .scad files**
   - What we know: Phase 1 generates well-structured parametric code. But users might ask to modify .scad files from other sources.
   - What's unclear: How reliably Claude can identify parametric variables in unfamiliar .scad code.
   - Recommendation: If Claude can't identify clear parametric variables, explain this to the user and offer two options: (a) refactor the code to be parametric first, then scale, or (b) use scale() with a wall thickness warning.

## Sources

### Primary (HIGH confidence)
- OpenSCAD Transformations Manual: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Transformations -- scale(), resize() behavior
- OpenSCAD CLI documentation -- already verified in Phase 1 research
- Phase 1 SKILL.md and reference files -- existing code patterns and conventions

### Secondary (MEDIUM confidence)
- BambuStudio DeepWiki: https://deepwiki.com/bambulab/BambuStudio/2.3-3mf-project-file-handling -- 3MF file structure, config file locations
- OrcaSlicer DeepWiki: https://deepwiki.com/SoftFever/OrcaSlicer/7.1-3mf-format -- 3MF structure, config file names
- OrcaSlicer Wiki (GitHub): https://github.com/OrcaSlicer/OrcaSlicer/wiki/strength_settings_infill -- parameter names (sparse_infill_density, etc.)
- BambuLab Wiki: https://wiki.bambulab.com/en/software/bambu-studio/parameter/strength-advance-settings -- wall_loops, sparse_infill_density confirmation
- 3MF.io specification: https://3mf.io/ -- core 3MF format (ZIP + XML)
- Polyvia3D 3MF overview: https://www.polyvia3d.com/formats/3mf -- ISO 25422:2025 standardization

### Tertiary (LOW confidence)
- Exact `print_profile.config` INI format -- derived from multiple sources but needs empirical validation with BambuStudio
- BambuStudio settings override priority -- based on forum reports, not official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new tools needed, extends Phase 1 stack
- Architecture (SKILL.md extensions): HIGH -- Clear pattern from Phase 1, straightforward additions
- Modification/scaling patterns: HIGH -- OpenSCAD parametric approach is well-documented and standard
- Printability analysis: HIGH -- Based on well-known 3D printing principles (overhangs, thin walls, bridges)
- 3MF metadata injection: MEDIUM -- Format is understood but exact BambuStudio acceptance needs empirical testing
- BambuStudio parameter names: MEDIUM -- Derived from multiple consistent sources but not from official parameter documentation

**Discretion decisions made:**
- **Versioning scheme:** Sequential v1, v2, v3 -- easier to reference in conversation than timestamps
- **Messiness detection:** Combination of iteration count (>= 5) and code quality signals (file length, nesting depth, commented-out blocks)
- **Printability analysis:** Code-pattern-based checklist that Claude applies by reading .scad source -- no external parser needed
- **3MF metadata format:** INI-style config file injected into Metadata/print_profile.config via bash unzip/inject/rezip

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable domain, 30-day validity)
