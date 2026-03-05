---
name: print
description: >
  Generate 3D printable models from natural language descriptions.
  Use when the user wants to 3D print something, create a model,
  design a part, or make something for their printer.
  Handles OpenSCAD code generation, preview rendering, and 3MF export.
allowed-tools: Bash, Read, Write, Glob, Grep
---

# 3D Print Model Generator

Generate print-ready 3MF files from natural language descriptions using OpenSCAD.

**IMPORTANT RULES -- follow these without exception:**
- Do NOT skip the clarification step. Always ask about dimensions, use case, and material first.
- Do NOT auto-open BambuStudio. Always ask the user if they want to open it.
- Do NOT generate code without asking about dimensions, use case, and material first.
- Do NOT proceed with generation until OpenSCAD is confirmed installed.

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

## Step 8: Offer BambuStudio

After showing the summary, ask:

> "Want me to open this in BambuStudio?"

- **If yes**: `open -a BambuStudio "$OUTPUT_DIR/model.3mf"`
- **If no**: Done. Remind the user where the files are saved.

Do NOT auto-open BambuStudio. Do NOT skip this question.

## Reference Files

- @reference/openscad-guide.md -- OpenSCAD code patterns, templates, anti-patterns, CLI reference
- @reference/materials.md -- Material-specific design parameters (PLA, PETG, TPU)
