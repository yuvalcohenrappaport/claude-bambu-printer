---
name: print
description: >
  Generate 3D printable models from natural language descriptions,
  search MakerWorld for existing models, and send files to BambuLab printers.
  Use when the user wants to 3D print something, create a model,
  design a part, find an existing model, download from MakerWorld,
  send to printer, check print status, or control a running print.
allowed-tools: Bash, Read, Write, Glob, Grep
---

# 3D Print Model Generator

Generate print-ready 3MF files from natural language descriptions using OpenSCAD, search MakerWorld for existing models to download, and send files to BambuLab printers.

**IMPORTANT RULES -- follow these without exception:**
- Do NOT skip the clarification step. Always ask about dimensions, use case, and material first.
- Do NOT auto-open BambuStudio. Always ask the user if they want to open it.
- Do NOT generate code without asking about dimensions, use case, and material first.
- Do NOT proceed with generation until OpenSCAD is confirmed installed.
- Do NOT auto-download models from MakerWorld. Always ask the user to confirm their selection first.
- Do NOT send to printer without showing confirmation summary first.
- Do NOT cancel a print without user confirmation.
- Do NOT auto-setup printer. Always ask user before running setup flow.

## Step 0a: Check Blender Setup (runs lazily)

This step is **triggered on demand** — only when the user's request hits a Blender-backed branch (organic generation, hero render, or mesh audit/repair). It is NOT run at the start of every conversation.

Run the setup status script:

```bash
python3 ~/.claude/skills/print/scripts/blender_setup.py status
```

Parse the JSON output. Three flags:

1. `blender_installed: false` → Tell user: "Blender isn't installed. Install via `brew install --cask blender`?" If yes, run `brew install --cask blender` and re-check. If no, fall back to the OpenSCAD path for the current request.

2. `mcp_venv: false` → Tell user: "The Blender MCP Python package isn't installed yet. I'll create a venv at `~/.claude/skills/print/.venv-blender/` and install it — proceed?" If yes, run `python3 ~/.claude/skills/print/scripts/blender_setup.py install`. If no, continue without MCP (direct CLI fallback — still works, just no prompts.yml grounding).

3. `mcp_registered: false` → Tell user: "I can register the Blender MCP server in `~/.claude/settings.json` so future conversations can use `execute_python` / `execute_blender_background` tools directly. Proceed?" If yes, run `python3 ~/.claude/skills/print/scripts/blender_setup.py register`. If no, continue without registration (direct CLI fallback).

**Important:** flags 2 and 3 are **optional** — the skill's Blender branches work via direct CLI even when both are false. Only flag 1 (Blender itself) is a hard requirement.

After handling any missing pieces, continue to the step that triggered the check (generation, render, or validate).

---

## Step 0: Detect Intent

Before anything else, determine whether the user wants to **search for an existing model**, **generate a new one**, or **interact with their printer**.

**Search indicators** (trigger search flow -- Steps S1-S3):
- "find", "search", "look for", "download", "get me", "existing", "browse", "MakerWorld", "from makerworld"

**Generate indicators** (trigger generation flow -- Steps 1-12):
- "make", "create", "generate", "design", "build", "print me"

**Printer indicators** (trigger printer flow -- Steps P1-P5):
- "send to printer", "print this", "start printing", "send to bambu", "print it"
- "printer status", "how's the print", "check printer", "print progress"
- "pause print", "resume print", "cancel print", "stop print"
- "setup printer", "connect printer", "configure printer"

**Validate indicators** (trigger validate flow -- Steps V1-V2):
- "check", "audit", "validate", "inspect", "is this printable", "is this file ok", "mesh check", "non-manifold", "will this print"

**Ambiguous** (neither set of indicators is clearly present, or both are present):
- Ask: "Would you like me to search MakerWorld for an existing model, or generate a custom one from scratch?"
- Wait for user response before proceeding.

**Routing:**
- Search intent detected --> go to **Step S1** (search flow).
- Generate intent detected --> go to **Step 1** (generation flow, unchanged).
- Printer intent detected --> go to **Step P1** (printer flow).
- Validate intent detected --> go to **Step V1** (validate flow). Requires Step 0a (Blender setup check) first.

---

## Search Flow (Steps S1-S3)

### Step S1: Check Playwright Installation

Before searching MakerWorld, verify Playwright is available.

```bash
python3 -c "from playwright.sync_api import sync_playwright; print('OK')" 2>/dev/null
```

**If NOT OK:**
1. Tell the user: "MakerWorld search requires Playwright (a browser automation tool) which isn't installed yet."
2. Ask: "Would you like me to install it? (`pip install playwright && playwright install chromium`)"
3. If user agrees: run the install commands and verify.
4. If user declines: offer to generate the model from scratch instead (go to Step 1).

### Step S2: Search MakerWorld

Run the search script:

```bash
python3 ~/.claude/skills/print/scripts/makerworld_search.py search "<user's description>" --limit 3
```

Parse the JSON output.

**If status is "error":**
- Tell the user the search failed and why (from the `error` field).
- Offer: "Would you like me to try again, or generate a custom model from scratch instead?"
- If generate: go to Step 1.

**If status is "ok" but results are empty:**
- Tell the user: "I couldn't find any matching models on MakerWorld for '<query>'."
- Offer: "Would you like me to generate a custom model for you instead?"
- If yes: go to Step 2 (clarification) with the original description.

**If status is "ok" with results:**

Present results as a numbered list. The script returns results ranked by combined score (60% rating + 40% downloads). The top result is marked as `recommended: true` in the JSON.

```
I found 3 models on MakerWorld:

1. Phone Stand - Adjustable
   Rating: 4.8/5 | Downloads: 12,500
   License: CC BY-SA 4.0
   Dimensions: 120 x 80 x 45 mm
   Thumbnail: https://makerworld.bblmw.com/...
   MakerWorld: https://makerworld.com/en/models/2461740
   >> Recommended: Highest rated with 12k+ downloads

2. Minimal Phone Holder
   Rating: 4.5/5 | Downloads: 8,200
   License: CC BY 4.0
   Dimensions: 95 x 70 x 30 mm
   Thumbnail: https://makerworld.bblmw.com/...
   MakerWorld: https://makerworld.com/en/models/3521890

3. Universal Phone Dock
   Rating: 4.2/5 | Downloads: 3,100
   License: Not specified
   Thumbnail: https://makerworld.bblmw.com/...
   MakerWorld: https://makerworld.com/en/models/1892345

Which one would you like to download? (or say "generate" to create a custom model instead)
```

The recommended model gets a `>> Recommended: <reason>` line beneath it (use the `recommendation_reason` field from the JSON).

- **License**: Display the `license` field from JSON. If empty string, show "License: Not specified".
- **Dimensions**: Only display if the `dimensions` field exists in the JSON. Format as "W x H x D mm" if width/height/depth are present, or show the raw value. Omit the line entirely if no dimensions data.

**Always ask the user to confirm selection -- never auto-download.**

### Step S3: Download Selected Model

After the user picks a model (by number or name):

Derive the folder name from the MakerWorld model name (not the search query). Slugify: lowercase, replace spaces with hyphens, remove special characters.

```bash
python3 ~/.claude/skills/print/scripts/makerworld_search.py download <model_id> --name "<model_name>" --output-dir "$HOME/3d-prints/<model-name-slug>"
```

Parse the JSON output.

**If status is "error":** Tell the user the download failed and why. Offer to try a different model or generate instead.

**If status is "ok":** Present a summary:

```
Downloaded to: ~/3d-prints/phone-stand-adjustable/
Files:
  - phone-stand.3mf (3MF)
  - phone-stand-plate2.3mf (3MF)

Source: https://makerworld.com/en/models/2461740
```

Then go to **Step 8** (offer to open in BambuStudio). Use the first 3MF file for the BambuStudio open command. If only STL files were downloaded, still offer to open in BambuStudio (it handles STL too).

**Notes for downloaded models:**

- **Scaling:** Since there is no .scad source file, suggest the user resize in BambuStudio directly rather than trying to import into OpenSCAD.
- **Print settings (Step 12):** Can still be applied if a 3MF was downloaded. For STL-only downloads, tell the user to configure settings in BambuStudio.
- **Modification (Step 9):** Not applicable to downloaded models (no .scad source). If the user asks to modify a downloaded model, explain this and offer to generate a similar model from scratch instead.

**Automatic mesh audit (new):** Before proceeding to Step 8, run the audit on the first 3MF/STL file that was downloaded:

1. Trigger Step 0a (Blender setup check) if not already completed in this session.
2. Run: `python3 ~/.claude/skills/print/scripts/blender_audit.py "<downloaded_file_path>"`
3. Parse the JSON. The `result` object has `dimensions_mm`, `triangle_count`, `non_manifold_edges`, `flipped_normals`, and `issues`.

Present the audit inline with the download summary:

```
Mesh audit:
  Dimensions: 118 × 76 × 44 mm
  Triangles:  84,230
  Manifold:   ✓ yes
  Normals:    ✓ consistent
```

If the JSON has `"needs_repair": true`, show the issues and immediately offer repair (go to **Step V2**). If `needs_repair` is false but there are advisory-only issues (high triangle count, etc.), list them as informational and continue to Step 8.

**If the audit fails** (status: error): do NOT block the download flow. Show a one-line warning: "Couldn't audit this file — [error]. Proceeding anyway." and continue to Step 8.

---

## Generation Flow (Steps 1-12)

## Step 1: Check OpenSCAD Installation

Before anything else, verify OpenSCAD is available.

```bash
OPENSCAD="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
if [ ! -f "$OPENSCAD" ]; then
    OPENSCAD=$(which openscad 2>/dev/null)
fi

if [ -z "$OPENSCAD" ] || [ ! -f "$OPENSCAD" ]; then
    echo "NOT_FOUND"
else
    echo "FOUND: $OPENSCAD"
fi
```

**If NOT_FOUND:**
1. Tell the user: "OpenSCAD is required for 3D model generation but isn't installed on your system."
2. Ask: "Would you like me to install it via Homebrew? (`brew install --cask openscad`)"
3. If user agrees: run `brew install --cask openscad` and verify the installation succeeded.
4. If user declines: explain they need to install OpenSCAD manually from https://openscad.org/downloads.html and stop.
5. Do NOT proceed with any generation until OpenSCAD is confirmed available.

Store the confirmed path in `$OPENSCAD` for all subsequent commands.

## Step 2: Clarify the Request

ALWAYS ask clarifying questions before generating. This step is mandatory, even if the user's request seems detailed.

Ask about:

1. **Dimensions**: "What dimensions do you need?" -- ask for specific measurements (width, height, depth, diameter, etc.) relevant to the object. If the user is unsure, suggest reasonable defaults based on the object type.

2. **Use case**: "What will you use this for?" -- understanding the use case helps with structural decisions (wall thickness, mounting holes, reinforcement).

3. **Material**: "What material will you print with? (PLA is the default if you're not sure)" -- material determines wall thickness and tolerance values per @reference/materials.md.

**If the description is too vague** (e.g., "make me something cool", "print something useful"):
- Do NOT guess or generate a random object.
- Ask: "What do you need? What would you use it for?"
- Probe until you have enough information to generate something useful.

**Once you have answers**, confirm your understanding before generating:
- Summarize what you'll create, the dimensions, and the material.
- Ask if that sounds right before proceeding.

## Step 3: Generate OpenSCAD Code

Reference @reference/openscad-guide.md for code patterns, templates, and best practices.
Reference @reference/materials.md for material-specific design parameters.

Generate well-structured OpenSCAD code following these rules:

1. **Comment header** at the top:
   ```openscad
   // [Object Name]
   // Material: [PLA/PETG/TPU] | Wall: [X]mm | Tolerance: [Y]mm
   // Description: [what the user asked for]
   ```

2. **Parametric variables section** -- ALL dimensions as named variables at the top. No magic numbers anywhere.
   - Use OpenSCAD Customizer annotations: `/* [Group Name] */` above variable groups.

3. **Quality setting**: `$fn = 60;` (default). Adjust only if the model is very simple (increase) or very complex (decrease for render speed).

4. **Material-appropriate values**:
   - PLA: wall >= 1.2mm, clearance = 0.3mm
   - PETG: wall >= 1.2mm, clearance = 0.35mm
   - TPU: wall >= 1.6mm, clearance = 0.4mm

5. **Separate modules** for distinct components (e.g., `module base()`, `module lid()`).

6. **Anti-pattern avoidance**:
   - Extend all CSG subtractions by 0.1mm beyond surfaces (no non-manifold geometry).
   - No zero-thickness walls.
   - Center objects at origin, use explicit `translate()`.
   - Add tolerance/clearance for all interlocking parts.

**For complex models** that may be beyond reliable generation accuracy:
- Try anyway -- do your best.
- But warn the user: "This is a complex model. The generated geometry may need manual adjustment in the .scad file. I recommend checking the preview carefully."

**Show the generated OpenSCAD code to the user** so they can review and learn from it.

## Step 4: Save Files

Create the output directory and save the .scad file:

```bash
OUTPUT_DIR="$HOME/3d-prints/<descriptive-name>"
mkdir -p "$OUTPUT_DIR"
```

- Use **lowercase-hyphenated** descriptive names derived from the user's request.
  - Examples: `phone-stand`, `cable-organizer`, `wall-bracket`, `storage-box`
- Save the generated code as `model.scad` in the output directory.

Write the .scad file to `$OUTPUT_DIR/model.scad`.

## Step 5: Render Preview and Export 3MF

Run OpenSCAD CLI to render a preview and export the 3MF file.

### Preview PNG

```bash
"$OPENSCAD" \
    --imgsize 800,600 \
    --projection p \
    --render \
    --colorscheme DeepOcean \
    --autocenter \
    --viewall \
    -o "$OUTPUT_DIR/preview.png" \
    "$OUTPUT_DIR/model.scad" \
    2>"$OUTPUT_DIR/openscad.log"
```

### Export 3MF

```bash
"$OPENSCAD" \
    -o "$OUTPUT_DIR/model.3mf" \
    "$OUTPUT_DIR/model.scad" \
    2>>"$OUTPUT_DIR/openscad.log"
```

## Step 6: Error Handling and Retry

If OpenSCAD returns a non-zero exit code on either the preview or export step:

1. Read the error log: `cat "$OUTPUT_DIR/openscad.log"`
2. Analyze the error (see @reference/openscad-guide.md "Common Error Patterns" section).
3. Fix the .scad code based on the error.
4. Save the fixed version to `$OUTPUT_DIR/model.scad`.
5. Explain to the user what was wrong and what you fixed.
6. Retry the render/export.

**Retry up to 3 total attempts.** On each retry, explain the error and fix.

**After 3 failed attempts:**
- Show the error to the user.
- Show the current .scad code.
- Explain: "I wasn't able to fix this automatically. You can edit the .scad file directly at `$OUTPUT_DIR/model.scad` and run OpenSCAD manually."
- Provide the manual OpenSCAD command they'd need to run.

## Step 7: Output Summary

After successful render and export, present a summary to the user:

1. **Preview image**: Reference the preview.png path so the user can see the rendered model.
   ```
   Preview: $OUTPUT_DIR/preview.png
   ```

2. **Dimensions**: List the key parametric values from the generated code (width, height, depth, wall thickness, etc.).

3. **Material**: State which material was used and the design parameters applied (wall thickness, clearance).

4. **File path**: Show the full path to the .3mf file.
   ```
   3MF file: $OUTPUT_DIR/model.3mf
   OpenSCAD source: $OUTPUT_DIR/model.scad
   ```

5. **OpenSCAD code**: Show the complete generated code so the user can review, learn, or modify it.

6. **Print settings**: If Step 12 was applied, include the recommended print settings in the summary (purpose, key parameters, and the BambuStudio equivalent preset name).

## Step 8: Offer BambuStudio or Send to Printer

After showing the summary, ask:

```
What would you like to do next?
1. Open in BambuStudio (for manual slicing and printing)
2. Send directly to your printer (cloud print)
3. Done for now
```

- **If option 1**: `open -a BambuStudio "$OUTPUT_DIR/model.3mf"`
- **If option 2**: go to **Step P2** (confirm print) with the current 3MF file.
- **If option 3**: Done. Remind the user where the files are saved.

Do NOT auto-open BambuStudio. Do NOT auto-send to printer. Do NOT skip this question.

---

## Printer Flow (Steps P1-P5)

### Step P1: Check Printer Setup

```bash
python3 -c "import json; json.load(open('$HOME/.claude/bambu-config.json'))" 2>/dev/null && echo "CONFIGURED" || echo "NOT_CONFIGURED"
```

Also check bambu-lab-cloud-api is installed:
```bash
python3 -c "from bambulab import BambuClient; print('OK')" 2>/dev/null
```

**If bambu-lab-cloud-api not installed:**
1. Tell user: "Printer integration requires the bambu-lab-cloud-api package."
2. Ask: "Would you like me to install it? (`pip install bambu-lab-cloud-api`)"
3. If yes: install. If no: stop.

**If NOT_CONFIGURED:**
1. Tell user: "Your BambuLab printer isn't set up yet. Let's connect it now."
2. Run: `python3 ~/.claude/skills/print/scripts/printer_setup.py setup`
3. This is interactive -- the script will prompt for email, password, 2FA code, and printer selection.
4. Parse JSON output. If status is "ok", proceed. If "error", show error and stop.

**If CONFIGURED:**
- Load config to get printer name.
- Route based on what user asked:
  - Setup/configure request --> run setup anyway (re-auth)
  - Status request --> Step P4
  - Control request (pause/resume/cancel) --> Step P5
  - Send/print request --> Step P2

### Step P2: Confirm Print (Send to Printer)

Before sending, always show a confirmation summary.

Determine which file to send:
- If a model was just generated/exported in this session: use that 3MF path
- If user specified a file path: use that
- If neither: ask user which file to send

Show confirmation:
```
Ready to print:
  File: ~/3d-prints/phone-stand/model.3mf
  Printer: My A1 Printer

  Options:
  1. Send to printer (cloud print) -- will slice and upload
  2. Open in BambuStudio (slice and print manually)

Which would you like?
```

- If user picks option 1 --> Step P3
- If user picks option 2 --> run `python3 ~/.claude/skills/print/scripts/printer_control.py open "<file_path>"` and done.

**Preset selection (optional):** If the user mentions settings like "draft quality" or "strong":
```
Available presets:
  - draft: 0.28mm layers, 15% infill, fast
  - standard: 0.20mm layers, 20% infill, balanced
  - quality: 0.12mm layers, 20% infill, detailed
  - strong: 0.20mm layers, 50% infill, durable

Using "standard" preset. Change? (or say "send" to proceed)
```

### Step P3: Send to Printer

Run the send command:
```bash
python3 ~/.claude/skills/print/scripts/printer_control.py send "<file_path>" [--preset <name>]
```

Parse JSON output.

**If status is "error":**
- If `reauth` is true: run `printer_setup.py setup` to re-authenticate, then retry
- If BambuStudio not found: tell user to install it, offer "open in BambuStudio" as fallback
- Otherwise: show error message

**If status is "ok":**
- Tell user: "Print started! Sending to [printer name]."
- Automatically proceed to Step P4 for status monitoring.

### Step P4: Check Printer Status

```bash
python3 ~/.claude/skills/print/scripts/printer_control.py status
```

Parse JSON output and present formatted status:

```
Printer: My A1 Printer
State: Printing
Progress: 45% (layer 120/267)
ETA: 32 minutes remaining
Nozzle: 220C / 220C target
Bed: 60C / 60C target
Speed: 100%
File: phone-stand.3mf
```

**If printer has error:**
```
Printer: My A1 Printer
State: ERROR
Error: [error details]

Suggested actions:
  - [suggestion 1]
  - [suggestion 2]

Would you like to resume, cancel, or troubleshoot?
```

**If token warning present:** show it: "Note: Your login token may be expiring soon. If you see auth errors, I'll help you re-authenticate."

### Step P5: Print Control

For pause/resume/cancel requests:

```bash
# Pause
python3 ~/.claude/skills/print/scripts/printer_control.py pause

# Resume
python3 ~/.claude/skills/print/scripts/printer_control.py resume

# Cancel
python3 ~/.claude/skills/print/scripts/printer_control.py cancel
```

**For cancel:** Always confirm with the user first: "Are you sure you want to cancel the print? This cannot be undone."

After any control command, automatically run Step P4 to show updated status.

---

## Validate Flow (Steps V1-V2)

### Step V1: Run Mesh Audit

Triggered by validate intent in Step 0, or automatically from the Step S3 download hook.

**Prerequisites:** Step 0a (Blender setup check) must have been run. If not, run it now — audit needs Blender installed, but MCP/venv are optional.

**Determine the target file:**
- If invoked from S3: use the downloaded file path.
- If invoked by user intent: parse the file path from their message, or ask: "Which file should I audit? (.stl, .obj, or .3mf path)"

**Run the audit:**
```bash
python3 ~/.claude/skills/print/scripts/blender_audit.py "<file_path>"
```

Parse the JSON output.

**If status is "error":** Show the error to the user. Offer to try a different file. Stop.

**If status is "ok":** Present the audit as a formatted summary:

```
Mesh audit: <filename>
  Dimensions: <x> × <y> × <z> mm  [fits build plate: 256 × 256 × 256]
  Triangles:  <count>
  Manifold:   ✓ yes  (or ⚠ N non-manifold edges)
  Normals:    ✓ consistent  (or ⚠ N flipped)
```

Build-plate fit check: compare each dimension to 256mm (Bambu A1). If any dim > 256, add a line: `⚠ Exceeds Bambu A1 build plate — rotate or scale before printing.`

**If `needs_repair` is true:** go to **Step V2** automatically (but still confirm with user first).

**If `needs_repair` is false but issues list is non-empty:** show issues as advisory, do not offer repair.

**If no issues at all:** say "This file looks clean — manifold, consistent normals, fits the build plate."

### Step V2: Repair (conditional)

Only offered when Step V1 / Step S3 audit flagged fixable issues (non-manifold edges, flipped normals).

Show the repair prompt:

```
Found: <N> non-manifold edges, <M> flipped normals.

Want me to run Blender's cleanup on this file?
  • merge-by-distance (threshold 0.001mm)
  • recalculate normals outside
  • fill holes (max 4 edges)
  • delete loose geometry
Original file will be preserved as `<filename>.original`.
```

**Wait for user confirmation.** Do not auto-repair.

If user confirms:

1. Run: `python3 ~/.claude/skills/print/scripts/blender_repair.py "<file_path>"`
2. Parse JSON. If status is "error", show the error and stop.
3. If status is "ok", re-run the audit (Step V1) on the now-repaired file to show before/after.
4. Present the diff:

```
Repair complete. Backup: <filename>.original

Before:  4 non-manifold edges, 0 flipped normals
After:   0 non-manifold edges, 0 flipped normals
```

If the user declines repair: do nothing, just leave the advisory in place.

---

## Step 9: Modify Existing Model

This step is triggered when the user asks to change a previously generated model (e.g., "add screw holes", "make the walls thicker", "add a slot on the side").

### 1. Locate the Model

Check conversation context for recently generated models. If starting a fresh conversation, browse `~/3d-prints/` directories to find the .scad file the user is referring to.

### 2. Create Versioned Backup Before ANY Edit

Always back up the current model before making changes. Use sequential version numbers.

```bash
OUTPUT_DIR="$HOME/3d-prints/<project-name>"
NEXT_VER=1
while [ -f "$OUTPUT_DIR/model_v${NEXT_VER}.scad" ]; do
    NEXT_VER=$((NEXT_VER + 1))
done
cp "$OUTPUT_DIR/model.scad" "$OUTPUT_DIR/model_v${NEXT_VER}.scad"
```

### 3. Read and Understand the .scad File

Before editing, read the full file. Identify:
- Parametric variables at the top (dimensions, wall thickness, tolerances)
- Module structure (which modules create which parts)
- How dimensions relate (what depends on what)

This understanding is essential for both modification and scaling.

### 4. Apply the Requested Modification

Edit `model.scad` in place:
- **For additions** (holes, screw mounts, features): add new modules and integrate them into the main geometry.
- **For changes** (thicker walls, different dimensions): modify the relevant parametric variables.
- **For removals**: remove modules/geometry, clean up unused variables.

### 5. Show Changes as a Summary Diff -- Do NOT Auto-Render

After editing, present a human-readable summary of what changed. Do NOT run OpenSCAD automatically.

```
Changes made to model.scad:
  - Added: screw_hole_d = 5mm (M5 screw holes)
  - Added: module screw_holes() at lines 45-55
  - Modified: height 40mm -> 50mm
  - Removed: decorative_ridge module (per request)

Want me to render this?
```

Only render after the user confirms.

### 6. Render After User Confirms

Use the same render/export commands from Steps 5-6 (preview PNG + 3MF export).

### 7. Check for Messiness

Reference @reference/printability-checklist.md Section 3 (Messiness Detection).

On every modification, check:
- How many backup versions exist (model_v1.scad, model_v2.scad, etc.)
- If version count >= 5 AND code quality signals fire (file too long, deep nesting, commented-out blocks, shadowed variables), suggest regeneration:

> "This model has gone through several iterations and the code is getting complex. Want me to regenerate it from scratch based on what we have now? I'll keep the current version as a backup."

## Step 10: Scale/Resize Model

This step is triggered when the user asks to resize, scale, or change specific dimensions of an existing model.

### 1. Parse the Scaling Request

Accept both input formats:
- **Relative**: "20% bigger", "half the height", "twice as wide"
- **Absolute**: "set width to 10cm", "make it 150mm tall", "I need the depth to be exactly 80mm"

Determine which axes are affected (all for uniform, specific for per-axis).

### 2. Preferred Approach: Modify Parametric Variables

Read the .scad file and classify variables:
- **Dimension variables** (width, depth, height, diameter, length, etc.) -- these get scaled
- **Wall/structural variables** (wall, clearance, tolerance, fillet_r, etc.) -- these do NOT get scaled

**Uniform scaling** ("make it 20% bigger"):
- Multiply ALL dimension variables by the scale factor
- DO NOT modify wall thickness, clearance, or tolerance variables -- they must stay at their designed values

**Per-axis scaling** ("make it 10cm wider"):
- Modify only the relevant axis variable(s)
- Leave wall and other axes unchanged

**If dimensions are hardcoded** (magic numbers in the body instead of variables at the top):
- Refactor them to parametric variables first
- Then apply the scaling to the new variables

### 3. Fallback: scale() Transform

Only use `scale()` if the parametric approach is impossible (e.g., imported file, heavily procedural code with no clear variables).

When falling back to `scale()`:
1. Explain to the user why parametric scaling isn't possible
2. Offer two options:
   - (a) Refactor to parametric first, then scale properly
   - (b) Use `scale()` with the caveat that wall thickness will change proportionally
3. If user chooses `scale()`: wrap the entire model in `scale([sx, sy, sz]) { ... }` and warn about wall thickness changes

### 4. Auto-Fix Printability After Scaling

After applying any scaling, check:
- Has any wall thickness fallen below the material minimum? (1.2mm for PLA/PETG, 1.6mm for TPU)
- Have any features become smaller than 1mm?

If issues are found, auto-fix them and tell the user:

> "I adjusted wall thickness from 1.0mm back to 1.2mm (PLA minimum) after scaling."

> "The screw hole rim was 0.8mm after scaling -- I bumped it to 1.2mm so it prints solidly."

### 5. Create Backup and Show Diff

Follow the same pattern as Step 9:
- Create versioned backup before editing
- Show a summary of changes
- Ask before rendering

## Step 11: Confidence Assessment

Reference @reference/printability-checklist.md for risk analysis patterns and language templates.

This is NOT a standalone step the user triggers. It is a behavior Claude applies automatically during generation (Step 3) and modification (Step 9).

### During Initial Generation (Step 3)

Before writing OpenSCAD code, mentally scan the user's request against the geometry risk checklist:

- **HIGH RISK items detected**: Warn the user BEFORE generating. Offer a simpler geometric alternative. Explain WHY with a brief technical reason (e.g., "overhangs above 60 degrees sag because there's nothing for the filament to bond to").
- **MEDIUM RISK items detected**: Proceed with generation, then note concerns AFTER showing the code (e.g., "This has a 40mm bridge span -- should print fine but you may see some sag on the underside").
- **LOW RISK only**: No special note needed. Optionally mention "Straightforward geometry, this should print cleanly."

### During Modification (Step 9)

After understanding the requested change, assess whether it introduces new geometry risk:

- A new feature with steep overhangs? Warn before applying.
- Thinning a wall below 2mm? Note after showing the diff.
- Adding simple mounting holes? No special note.

Same warning/note pattern as above.

### Language Guidelines

- Use natural, conversational language -- see @reference/printability-checklist.md Section 2 for templates
- Never use percentages ("80% confidence") or tier labels ("MEDIUM RISK")
- Always explain WHY something is risky with a brief technical reason
- For high-risk geometry, always offer a simpler alternative before proceeding

## Step 12: Recommend Print Settings and Embed in 3MF

This step runs AFTER a successful 3MF export (Step 5 or after re-rendering a modified model). It is NOT optional -- always recommend settings when a 3MF is produced.

### 1. Determine Purpose

Use the use case from Step 2 clarification (or ask if modifying an existing model without known context). Match to the closest profile in @reference/print-settings.md.

### 2. Apply Geometry Adjustments

Analyze the .scad source using @reference/printability-checklist.md risk patterns. Apply relevant geometry-based adjustments from @reference/print-settings.md Section 2 on top of the purpose baseline.

### 3. Show Recommended Settings to User

```
Recommended print settings (based on [purpose] + geometry analysis):
  Layer height: 0.2mm
  Walls: 3
  Top/bottom layers: 4/4
  Infill: 30% grid
  Supports: not needed
  Speed: 200mm/s (outer walls: 150mm/s)

BambuStudio equivalent: Similar to "0.20mm Standard" preset with increased walls
Generic slicer: PrusaSlicer "0.20mm QUALITY" with 3 perimeters

These will be embedded in the 3MF file. Review in BambuStudio before printing --
your saved profiles may override these.
```

### 4. Inject Settings into 3MF

Embed the recommended settings as a print profile config inside the 3MF file:

```bash
THREEMF="$OUTPUT_DIR/model.3mf"
TMPDIR=$(mktemp -d)

# Unzip the 3MF
cd "$TMPDIR"
unzip -q "$THREEMF"

# Create Metadata directory if needed
mkdir -p Metadata

# Write print profile config
cat > Metadata/print_profile.config << 'PROFILE'
; BambuStudio Print Profile
; Generated by Claude Print Skill
; Purpose: [purpose]

layer_height = [value]
initial_layer_print_height = [value]
wall_loops = [value]
top_shell_layers = [value]
bottom_shell_layers = [value]
sparse_infill_density = [value]%
sparse_infill_pattern = [value]
enable_support = [0 or 1]
support_type = [value]
print_speed = [value]
outer_wall_speed = [value]
PROFILE

# Repack the 3MF (IMPORTANT: zip from current dir to avoid nested paths)
rm "$THREEMF"
zip -q -r "$THREEMF" .
cd /
rm -rf "$TMPDIR"
```

Replace all `[value]` placeholders with actual values from the selected profile + geometry adjustments.

### 5. Caveat to User

Always include this caveat after embedding settings:

> "These settings are embedded as recommendations. BambuStudio may override them with your saved profiles -- review the settings before printing."

### 6. Fallback If 3MF Injection Fails

If the unzip/inject/rezip process fails for any reason:

1. Do NOT treat this as a fatal error -- the 3MF file is still valid without embedded settings.
2. Show the settings as text in the output summary (Step 7) instead.
3. Note to the user: "I couldn't embed settings in the 3MF file. Here are the recommended settings to apply manually in BambuStudio."
4. Provide the settings in a copy-pasteable format.

## Reference Files

- @reference/openscad-guide.md -- OpenSCAD code patterns, templates, anti-patterns, CLI reference
- @reference/materials.md -- Material-specific design parameters (PLA, PETG, TPU)
- @reference/printability-checklist.md -- Geometry risk patterns, confidence language, messiness detection
- @reference/print-settings.md -- Purpose-based print profiles, geometry adjustments, BambuStudio parameters
- @scripts/makerworld_search.py -- MakerWorld search and download CLI (Playwright-based)
- @scripts/printer_setup.py -- BambuLab account auth, printer selection, config management
- @scripts/printer_control.py -- Send prints, check status, pause/resume/cancel
- @reference/blender-guide.md -- Blender bpy patterns for organic shapes, 3MF export incantation, CLI reference, common error patterns
- @scripts/blender_setup.py -- Blender install check, venv management, MCP registration
- @scripts/blender_bridge.py -- Shared Blender subprocess wrapper used by all Blender orchestrators
- @scripts/blender_audit.py -- Mesh audit CLI (manifold check, normals, dimensions, triangles)
- @scripts/blender_repair.py -- Mesh repair CLI with backup
