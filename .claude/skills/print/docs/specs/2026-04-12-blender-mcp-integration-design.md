# Design: Blender MCP Integration for /print Skill

**Date:** 2026-04-12
**Status:** Approved, ready for implementation plan
**Scope:** Extend the existing `/print` skill (~/.claude/skills/print/SKILL.md) with Blender-backed generation, rendering, and mesh validation. OpenSCAD flow remains the default; Blender is added as a parallel path for use cases OpenSCAD cannot handle well.

## Motivation

The current `/print` skill generates all models through OpenSCAD, which is excellent for parametric mechanical parts but fights the user on three things:

1. **Organic / sculpted shapes** — curves, lofts, sweeps, ergonomic grips, drone fairings. OpenSCAD's CSG model makes these painful.
2. **Photo-quality previews** — the OpenSCAD DeepOcean PNG is functional but matte. For hero shots, documentation, or sanity-checking complex assemblies, a real rendered image is useful.
3. **Mesh validation / repair on downloaded files** — MakerWorld STLs are routinely non-manifold, have flipped normals, or have thin-wall issues that only surface at slice time. The skill currently has no way to catch this before filament is wasted.

Blender handles all three natively. The official Blender MCP server (`projects.blender.org/lab/blender_mcp`) provides a stdio bridge that exposes `execute_python`, `execute_blender_background`, and `get_summary`, plus `prompts.yml` with Blender API / manual excerpts injected at connection time — useful grounding for Claude when writing `bpy` code.

## Design Decisions (approved)

1. **Blender routing on generation:** Claude silently checks the clarified request against an organic-shape heuristic after Step 2. If it fires, Claude proposes Blender as a non-default choice with one line of reasoning. User confirms y/n. If the heuristic does not fire, OpenSCAD is used with no interruption.
2. **Blender rendering:** opt-in only. Added as a new menu item in the Step 8 summary, and triggered on hero-render keywords ("render it nicely", "show me what it looks like"). OpenSCAD's fast matte preview remains the default.
3. **Mesh validation on downloads:** automatic audit on every MakerWorld download in Step S3. If issues are found, the skill offers repair with a backup of the original. The same audit function is also exposed as a standalone `/print check <path>` entry point for any user-supplied file.
4. **Invocation mode:** Blender is invoked exclusively in **background mode** (`blender --background --python`), never via a live Blender window. Every operation is one-shot and stateless, matching how the skill already treats OpenSCAD. The MCP's `execute_blender_background` tool is used when available; a direct CLI fallback is used when MCP is not registered.

## Architecture

### Components

- **Blender 5.1** (already installed at `/Applications/Blender.app/Contents/MacOS/Blender`)
- **`blender_mcp` Python package** in a dedicated venv at `~/.claude/skills/print/.venv-blender/`, installed via `pip install git+https://projects.blender.org/lab/blender_mcp.git`
- **MCP server registration** in `~/.claude/settings.json` → `mcpServers.blender_mcp`, stdio transport, command = `~/.claude/skills/print/.venv-blender/bin/blender-mcp`
- **Direct CLI fallback:** `blender --background --python <script>` invoked via the existing Bash tool if MCP is not registered
- **New reference file** `~/.claude/skills/print/reference/blender-guide.md` — Blender API patterns for organic shapes, 3MF export incantation, CLI reference, common errors. Read via `@reference/blender-guide.md` in SKILL.md, same pattern as existing references.

### Invocation mode: background only

The Blender MCP exposes two execution tools. This skill uses only one:

| Tool | Mode | Used here? | Why |
|---|---|---|---|
| `execute_python` | Sends code to a running Blender instance via TCP socket (needs addon enabled) | No | Requires persistent Blender window and addon install; adds state to manage |
| `execute_blender_background` | Spawns a headless `blender --background --python` subprocess | Yes | Stateless, one-shot, matches OpenSCAD-CLI pattern already in the skill |
| `get_summary` | Scene inspection in running instance | No | Only relevant if we used the live instance |

Background mode means: no "please enable the plugin" step for the user, no persistent Blender window, no process management. Every skill operation is a subprocess that exits.

### MCP vs direct CLI

The MCP server is preferred because `prompts.yml` injects Blender API + manual excerpts into the LLM context at connection time, which grounds the `bpy` code Claude writes. If MCP registration fails or the user declines it, the skill falls back to `blender --background --python` invoked from Bash. The fallback does not have the same grounding, so the `blender-guide.md` reference file compensates. Both paths use the same headless subprocess underneath.

### Install check flow (new Step 0a)

Runs on first invocation of any Blender-backed branch (generation, preview, or validation). Each step gated on user confirmation, same pattern as the OpenSCAD/Playwright checks already in the skill.

1. **Blender installed?** Check `/Applications/Blender.app/Contents/MacOS/Blender`. If missing, offer `brew install --cask blender`.
2. **`blender_mcp` Python package installed?** Check `~/.claude/skills/print/.venv-blender/bin/blender-mcp`. If missing, offer to create the venv and run `pip install git+https://projects.blender.org/lab/blender_mcp.git`.
3. **MCP server registered in `~/.claude/settings.json`?** If missing, offer to add the `mcpServers.blender_mcp` entry.
4. **If user declines MCP registration but Blender is present:** proceed with direct CLI fallback. Skill prints a one-line note: "Using direct Blender CLI (MCP not registered). Grounding from `blender-guide.md` instead."

## Flow Changes to SKILL.md

### Step 0: Detect Intent (extended)

Add one new branch and one new keyword set:

- **Validate indicators** (new — trigger validate flow): "check", "audit", "validate", "is this printable", "is this file ok", "inspect", "mesh check", "non-manifold"
- **Preview/render indicators** (keyword trigger for Step 8): "render it nicely", "show me what it looks like", "hero shot", "photo-quality", "pretty picture"

Routing: validate intent → **Step V1** (new). Render keywords mid-conversation → jump to the render branch of Step 8 without re-entering generation.

### Step 2b: Generation routing (new, between Step 2 and Step 3)

After Step 2 confirms dimensions/use-case/material, Claude runs a silent organic-shape check. Heuristic:

- **Shape vocabulary:** curve, organic, smooth, ergonomic, flowing, sculpted, fairing, shell, hood, pod, lofted, swept, natural, blob
- **Object type:** grip, handle, figurine, miniature, decorative vase, planter-with-curves, cosplay prop, sculpture, toy, aerodynamic part
- **Geometric signal:** the shape cannot be expressed as a combination of boxes, cylinders, linear extrusions, or simple revolutions

If none fire → proceed silently to Step 3 (OpenSCAD) as today. If any fire → one-line proposal:

> "This shape sounds organic — Blender handles curves and sculpted surfaces better than OpenSCAD. Want me to use Blender instead? (y/n)"

- `y` → go to **Step 3b** (Blender generation)
- `n` → go to **Step 3** (OpenSCAD generation) as today

User can always force either path with "use blender" / "use openscad" in the original request, bypassing the heuristic.

### Step 3b: Generate Blender bpy Script (new, parallel to Step 3)

Generates a `model.py` file — a self-contained `bpy` script that, when executed via `blender --background --python model.py -- <output_3mf_path>`, produces the 3MF. This is the text-source-of-truth analog to the existing `model.scad`.

**Script requirements:**

1. **Comment header:**
   ```python
   # [Object Name]
   # Material: [PLA/PETG/...] | Wall: [X]mm
   # Description: [what the user asked for]
   ```
2. **Parameters section** at the top — ALL dimensions as named variables, same discipline as the OpenSCAD flow. No magic numbers in the body.
3. **Scene reset** — clear default cube/light/camera so the script is idempotent.
4. **Construction** — use `bpy.ops.mesh.primitive_*`, `bmesh` for edits, modifiers for bevels/mirrors/arrays/subdivision, boolean mod for CSG.
5. **Export 3MF** — `bpy.ops.export_mesh.threejs_3mf(filepath=...)` (or the equivalent export operator in Blender 5.1; verified during implementation).
6. **Accepts output path via `sys.argv`** after the `--` separator, same pattern as standard Blender scripting.

**Reference file driving the code:** `@reference/blender-guide.md` covers:

- Common bmesh patterns for organic shapes (loft, sweep, subdivision surface, metaballs)
- Modifier stack recipes (bevel → solidify → mirror → boolean)
- 3MF export incantation (and fallback to STL if the 3MF exporter isn't present)
- CLI invocation reference with `--` arg passing
- Common error patterns (missing operator, RNA errors, non-manifold from booleans)

**Material-appropriate defaults** — same wall/clearance table as Step 3 (pulled from `@reference/materials.md`), applied as script parameters.

### Step 5b: Render Blender Model (new, parallel to Step 5)

Validate → preview → export. Same three-stage pattern as the OpenSCAD flow.

1. **Validate:** dry-run `blender --background --python model.py -- /dev/null` — catches `bpy` errors before the full export run.
2. **Fast preview PNG:** a second headless call imports `model.py`'s output, uses a minimal default light and camera (no hero rig), renders Eevee at 800×600 with low-quality settings, writes `$OUTPUT_DIR/preview.png`. Same filename as the OpenSCAD flow so Step 7 summary works unchanged. This is the functional-equivalent of OpenSCAD's matte preview — "is this the right shape", not "is this photogenic". Target: ~3–5s.
3. **Export 3MF:** `blender --background --python model.py -- $OUTPUT_DIR/model.3mf`.

**Distinction from Step 8.3:** the Step 5b preview is a fast, unstyled shape-check render run automatically on every generation. Step 8.3 is an opt-in, styled, higher-resolution hero render with a 3-point light rig. They write to different files (`preview.png` vs `render.png`) and serve different purposes.

### Step 6b: Error Handling and Retry (new, parallel to Step 6)

Identical pattern to Step 6: on non-zero exit, read stderr, Claude analyzes the error, fixes the `.py`, retries up to 3 attempts. After 3 failed attempts, show the current `.py`, the error, and tell the user they can edit it manually.

### Step 8: Menu extended

Current:
```
1. Open in BambuStudio
2. Send directly to your printer
3. Done for now
```

New:
```
1. Open in BambuStudio
2. Send directly to your printer
3. Generate a photo-quality render (Blender)   ← new
4. Done for now
```

Option 3 is also triggered mid-conversation by the hero-render keywords from Step 0.

### Step 8.3: Blender Hero Render (new)

Runs a headless Blender script that:

- Imports `$OUTPUT_DIR/model.3mf` (or `model.stl` if 3MF is not present)
- Parents it to an empty at the bounding-box center
- Drops it on a neutral infinite-floor material (subtle gradient)
- Adds a 3-point soft light rig
- Aims a 35mm camera from a 30° elevation angle at the bounding-box center
- Renders Eevee at 1280×960
- Writes `$OUTPUT_DIR/render.png` **alongside** the existing `preview.png` (does not replace it)

Estimated runtime: ~10–15s on Apple Silicon. The render script is source-agnostic — it works for both OpenSCAD-generated and Blender-generated outputs, and also for any 3MF downloaded from MakerWorld in Step S3.

Writes to `render.png` so that:
- `preview.png` = fast, matte, "is this the right shape" (used during iteration)
- `render.png` = slow, photo-quality, "hero shot" (used for sharing / documentation)

Both files coexist; neither is removed.

### Step S3 extended: Mesh audit on download

After a successful MakerWorld download, run the **audit function** (defined below) on the first 3MF in the download. Present results inline with the existing download summary:

```
Downloaded to: ~/3d-prints/phone-stand-adjustable/
Files: phone-stand.3mf (3MF)
Source: https://makerworld.com/en/models/2461740

Mesh audit:
  Dimensions: 118 × 76 × 44 mm  (fits Bambu A1 build plate: 256 × 256 × 256)
  Triangles:  84,230
  Manifold:   ✓ yes
  Normals:    ✓ consistent
  Thin walls: ⚠ 3 areas below 0.8mm — may print incorrectly at the edges
```

If any of {non-manifold, flipped normals, self-intersecting faces} are present, immediately offer repair (see Step V2 below). If only advisory flags fire (thin walls, high triangle count, oversized bounding box), show them but don't interrupt the flow.

### Step V1: Validate / Audit (new entry point)

Triggered by validate intent in Step 0. Accepts any `.3mf` / `.stl` / `.obj` path.

**Audit function** — a headless Blender script that imports the file and computes:

| Check | Method | Output |
|---|---|---|
| Manifold status | Count edges with `len(e.link_faces) != 2` via bmesh | Edge count or ✓ |
| Normals consistency | Count faces with inverted normals vs. recalculated | Flipped count or ✓ |
| Self-intersection | `bmesh.ops.find_doubles` + BVH overlap | Intersecting face count or ✓ |
| Bounding box | `obj.dimensions` in mm | X × Y × Z plus "fits build plate" flag |
| Triangle count | `len(bm.faces)` after triangulation | Count; flag if >500k |
| Thin walls (best-effort) | Min face-to-face distance sample | Count of thin regions or ✓ |

Output is a JSON blob the skill parses into a human summary. Same function is called from the Step S3 hook and from Step V1.

### Step V2: Repair (new, conditional)

Offered when the audit finds fixable issues (non-manifold, flipped normals, self-intersection). Not offered for advisory-only flags.

```
Found: 12 non-manifold edges, 4 flipped normals.

Want me to run Blender's cleanup on this file?
  • merge-by-distance (threshold 0.001mm)
  • recalculate normals outside
  • fill holes (max edges 4)
  • make manifold
Original file will be preserved as `<filename>.original`.
```

User confirms → the repair script backs up the original, runs the operations via `bmesh.ops.remove_doubles`, `bpy.ops.mesh.normals_make_consistent`, `bpy.ops.mesh.fill_holes`, plus a manifold-fixing pass, writes the cleaned file back, re-runs the audit, and shows before/after. User declines → nothing happens; advisory info remains in the output.

## Modification and Scaling (Steps 9 and 10)

For Blender-generated models (`model.py` + `model.3mf`):

- **Step 9 (modify):** identical flow to OpenSCAD. Edit parametric variables or module bodies in `model.py`, create `model_v1.py` backup, show diff, confirm, re-run Blender. The "5+ versions → suggest regeneration" messiness check from Step 9.7 applies unchanged.
- **Step 10 (scale):** same classify-variables approach. Dimension variables (width, depth, height) get scaled; wall/clearance/tolerance variables do not. Fallback to `bpy.ops.transform.resize` if the script is not parametric.

For downloaded-and-repaired models (no `.py` source): modification not applicable. If the user asks to modify, the skill explains there is no script source and offers to generate a similar model from scratch (existing Step 9 behavior for downloaded models, unchanged).

## File Layout Impact

Output directory for a Blender-generated model:
```
~/3d-prints/<slug>/
├── model.py          ← new: bpy script source-of-truth
├── model.3mf         ← exported mesh
├── preview.png       ← fast preview
├── render.png        ← only if user opted into hero render
└── blender.log       ← new: stderr from the last Blender run
```

Output directory for an OpenSCAD-generated model with hero render:
```
~/3d-prints/<slug>/
├── model.scad
├── model.3mf
├── preview.png       ← OpenSCAD DeepOcean
├── render.png        ← Blender hero shot (new, optional)
└── openscad.log
```

Output directory for a MakerWorld download with repair:
```
~/3d-prints/<slug>/
├── phone-stand.3mf            ← cleaned version
├── phone-stand.3mf.original   ← backup
├── render.png                 ← if user opted in
└── audit.json                 ← new: last audit result
```

## Non-Goals (YAGNI)

- **Live Blender interactive editing.** The `execute_python` path against a running instance is not used. Every operation is one-shot background.
- **Blender as a replacement for OpenSCAD.** OpenSCAD stays the default; Blender is additive.
- **Automatic repair without confirmation.** Mesh surgery can break intended geometry; always ask.
- **Custom Blender addon beyond the MCP's own.** No skill-specific `.blend` templates or addon packaging.
- **Rendering during iteration loops.** The hero render is opt-in and one-shot, never on every Step 5 call.
- **GPU Cycles rendering.** Eevee only; Cycles would add minutes per render and isn't needed for "does this look roughly right."

## Testing Plan

Physical printing is out of scope for this design, but each new path needs a smoke test:

1. **Install flow:** fresh state, run `/print make a phone stand in blender`, verify venv creation, pip install, settings.json edit, first successful generation.
2. **Organic detection:** `/print make an ergonomic pen grip` — heuristic should fire, propose Blender. `/print make a 40mm cube with a 20mm hole` — heuristic should not fire, go straight to OpenSCAD.
3. **Blender generation round-trip:** generate a simple sculpted shape (a lofted vase), confirm `model.py` + `model.3mf` + `preview.png` all produced, `model.3mf` opens cleanly in BambuStudio.
4. **Hero render:** generate an OpenSCAD model, opt into render in Step 8, confirm `render.png` appears next to `preview.png` and looks photo-quality.
5. **MakerWorld audit:** download a known-non-manifold model, confirm audit flags it, confirm repair offer, confirm cleaned file is manifold per a re-run audit.
6. **`/print check` standalone:** point at a random STL from disk, confirm audit runs and reports.
7. **MCP fallback:** deliberately remove the MCP registration, confirm the direct-CLI path still produces the same outputs for all of the above.
8. **Modification round-trip on Blender model:** generate, then ask for "walls thicker by 2mm", confirm `model_v1.py` backup, confirm re-render works.

## Open Questions to Resolve During Implementation

- **3MF export operator name in Blender 5.1.** `bpy.ops.export_mesh.threejs_3mf` may not exist under that name — might be `bpy.ops.wm.save_as_mainfile` + external tool, or a different operator in 5.x. Verify with `blender --background --python -c "import bpy; help(bpy.ops.export_mesh)"` during implementation. Fallback: export STL and convert via `meshio` or a tiny Python 3MF writer.
- **Exact venv location vs. reusing an existing Python.** The spec says `~/.claude/skills/print/.venv-blender/` to isolate dependencies. Verify this doesn't conflict with the existing Playwright install in the search flow.
- **MCP server command path portability.** The `~/.claude/settings.json` entry hardcodes the venv path. If the user moves their home or reinstalls the skill, this breaks. Consider a setup script that regenerates the settings.json entry on demand.
