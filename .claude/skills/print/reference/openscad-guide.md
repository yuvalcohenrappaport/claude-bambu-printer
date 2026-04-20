# OpenSCAD Code Generation Guide

Reference for generating well-structured, printable OpenSCAD code from natural language descriptions.

## Code Structure Rules

Every generated .scad file MUST follow this structure:

1. **Comment header** at the top: description, material, key dimensions
2. **Parametric variables section**: all dimensions as named variables (NEVER magic numbers)
3. **Quality settings**: always set resolution explicitly
   - Prefer `$fa` and `$fs` for general resolution: `$fa = 1; $fs = 0.4;` (production), `$fs = 1;` (draft)
   - Reserve `$fn` for specific polygon counts: `$fn = 6` for hexagons, `$fn = 72` for smooth circles where exact segment count matters
   - Values of `$fn` above 100 are rarely needed -- they bloat STL size without visible improvement on a printed part
   - For backwards compatibility with simple models, `$fn = 60` remains acceptable as a quick default
4. **Module definitions**: separate `module` block for each distinct component
5. **Assembly section**: final positioning using `translate()`, `rotate()`, etc.

### Variable Naming Conventions

```openscad
// Dimensions - use descriptive names
width = 80;          // mm - X axis
depth = 60;          // mm - Y axis
height = 40;         // mm - Z axis
wall = 2;            // mm - wall thickness (must be multiple of nozzle diameter: 0.8, 1.2, 1.6, 2.0)
corner_r = 3;        // mm - corner radius

// Tolerances
clearance = 0.3;     // mm - gap for interlocking parts (material-dependent)

// Quality
$fa = 1;             // minimum angle per fragment
$fs = 0.4;           // minimum fragment size (mm)
```

### Wall Thickness Rule

Wall thickness MUST be a multiple of the nozzle diameter (typically 0.4mm):
- 0.8mm = 2 perimeters (absolute minimum for structural walls)
- 1.2mm = 3 perimeters (recommended minimum)
- 1.6mm = 4 perimeters (good for load-bearing)
- 2.0mm = 5 perimeters (safe default)

Non-multiples cause the slicer to leave gaps or create thin fill lines that weaken the part.

### Spatial Positioning Rules

- Center objects at the origin when practical
- Use explicit `translate()` for all positioning -- never rely on implicit placement
- When assembling multiple modules, position them relative to the origin
- For parts that print separately, offset them in Z (e.g., `translate([0, 0, height + 5])`) so the preview shows them distinctly

### Debug Prefixes (Development/Iteration)

When debugging or iterating on geometry, use these OpenSCAD prefixes:
- `#` -- renders a child semi-transparent (ghost view) to debug spatial relationships
- `!` -- shows ONLY this child, hiding everything else (isolate a component)
- `%` -- background modifier, renders as transparent ghost without affecting final geometry
- `*` -- disable modifier, skips this child entirely

These are invaluable during the error-correction loop (Step 6).

## Chamfers vs Fillets

**Use chamfers (45-degree cuts) instead of fillets (rounded edges) on bottom edges.** This is critical for FDM printability:
- A chamfer at 45 degrees is self-supporting
- A fillet starts at nearly 90 degrees from horizontal and creates an unsupported overhang that droops

```openscad
// BAD - fillet on bottom edge (creates overhang)
module bad_fillet() {
    difference() {
        cube([20, 20, 20]);
        translate([0, 0, 0])
            rotate([0, 0, 0])
                cylinder(r = 3, h = 20);  // rounds bottom edge but sags
    }
}

// GOOD - chamfer on bottom edge (self-supporting)
module good_chamfer(size, chamfer) {
    difference() {
        cube([size, size, size]);
        translate([-0.1, -0.1, -0.1])
            rotate([0, 0, 0])
                linear_extrude(height = chamfer + 0.1)
                    polygon([[0, 0], [chamfer + 0.1, 0], [0, chamfer + 0.1]]);
    }
}
```

Fillets are fine on **top edges** and **vertical edges** where overhangs are not an issue.

## Hole Compensation

FDM printers always produce holes that are **smaller than designed** because:
1. STL files approximate circles with triangles (chord error)
2. The nozzle deposits material slightly inward

**Compensation rules:**
- Add 0.1-0.2mm to hole diameters for general fit
- For precise holes (bearing seats, dowel pins), add 0.2mm and plan to ream
- Vertical holes are more accurate than horizontal holes

```openscad
// Compensated hole for M5 bolt (5mm nominal)
bolt_d = 5;
hole_compensation = 0.2;  // FDM hole shrinkage compensation
bolt_hole_d = bolt_d + hole_compensation;  // 5.2mm actual hole
```

## BOSL2 Library

[BOSL2](https://github.com/BelfrySCAD/BOSL2) is a comprehensive library (~71,000 lines) that dramatically improves OpenSCAD productivity. Use it when available.

### Check if BOSL2 is installed:
```bash
ls ~/Documents/OpenSCAD/libraries/BOSL2/ 2>/dev/null || ls /usr/share/openscad/libraries/BOSL2/ 2>/dev/null
```

### Key BOSL2 Features

**Directional shortcuts** (much more readable than raw translate):
```openscad
include <BOSL2/std.scad>

// Instead of: translate([30, 0, 0]) cube([10, 10, 10]);
right(30) cube([10, 10, 10]);

// Instead of: translate([0, 0, 20]) cube([10, 10, 10]);
up(20) cube([10, 10, 10]);

// Available: left(), right(), fwd(), back(), up(), down()
```

**Attachments** (position relative to parent faces):
```openscad
include <BOSL2/std.scad>

cuboid([40, 40, 20])
    attach(TOP) cyl(d = 10, h = 15);  // cylinder centered on top face
```

**Built-in parts:**
```openscad
include <BOSL2/std.scad>
include <BOSL2/screws.scad>
include <BOSL2/gears.scad>

// Pre-built screw holes, gears, hinges, bottle caps, rounded shapes, chamfers
screw_hole("M5", length = 20);
spur_gear(pitch = 2, teeth = 20, thickness = 5);
```

**When to use BOSL2:** Complex assemblies, mechanical parts with screws/gears, any model where spatial positioning is complex. Avoid for simple boxes/brackets where raw OpenSCAD is sufficient.

**Performance note:** BOSL2 geometries can be complex. Use OpenSCAD nightly build with the Manifold backend for up to 1000x faster rendering than the stable release's CGAL backend.

## Template Patterns

### 1. Parametric Box with Lid

Demonstrates: CSG difference, tolerance/clearance, parametric dimensions, lid insert lip.

```openscad
// Parametric Box with Lid
// Material: PLA | Wall: 2mm | Tolerance: 0.3mm
// Description: Storage box with snap-fit lid

/* [Box Dimensions] */
width = 80;           // mm
depth = 60;           // mm
height = 40;          // mm
wall = 2;             // mm (multiple of 0.4mm nozzle)
corner_r = 3;         // mm

/* [Lid] */
lid_height = 10;      // mm
lid_clearance = 0.3;  // mm - printing tolerance per side

/* [Quality] */
$fa = 1;
$fs = 0.4;

module rounded_box(w, d, h, r) {
    hull() {
        for (x = [r, w - r], y = [r, d - r])
            translate([x, y, 0])
                cylinder(h = h, r = r);
    }
}

module box_body() {
    difference() {
        rounded_box(width, depth, height, corner_r);
        translate([wall, wall, wall])
            rounded_box(width - 2*wall, depth - 2*wall, height + 0.1, corner_r);
    }
}

module box_lid() {
    // Outer shell
    difference() {
        rounded_box(width, depth, lid_height, corner_r);
        translate([wall, wall, wall])
            rounded_box(width - 2*wall, depth - 2*wall, lid_height + 0.1, corner_r);
    }
    // Inner lip for snug fit
    translate([wall + lid_clearance, wall + lid_clearance, 0])
        difference() {
            rounded_box(width - 2*wall - 2*lid_clearance,
                        depth - 2*wall - 2*lid_clearance,
                        wall, corner_r);
            translate([wall, wall, -0.1])
                rounded_box(width - 4*wall - 2*lid_clearance,
                            depth - 4*wall - 2*lid_clearance,
                            wall + 0.2, corner_r);
        }
}

// Assembly
box_body();
translate([0, 0, height + 5])
    box_lid();
```

### 2. Phone/Tablet Stand

Demonstrates: angles, structural supports, practical geometry.

```openscad
// Adjustable Phone Stand
// Material: PLA | Wall: 3mm
// Description: Desk phone stand with adjustable viewing angle

/* [Dimensions] */
base_width = 80;      // mm
base_depth = 60;      // mm
base_height = 5;      // mm
support_height = 70;  // mm
support_thickness = 3; // mm
lip_height = 15;      // mm - front lip to hold phone
lip_depth = 8;        // mm

/* [Angle] */
lean_angle = 70;      // degrees from horizontal

/* [Quality] */
$fa = 1;
$fs = 0.4;

module base() {
    cube([base_width, base_depth, base_height]);
}

module back_support() {
    translate([0, base_depth - support_thickness, base_height])
        rotate([90 - lean_angle, 0, 0])
            cube([base_width, support_height, support_thickness]);
}

module front_lip() {
    translate([0, 0, base_height])
        cube([base_width, lip_depth, lip_height]);
}

module side_brace(x_pos) {
    translate([x_pos, lip_depth, base_height])
        linear_extrude(height = support_thickness)
            polygon([
                [0, 0],
                [0, base_depth - lip_depth - support_thickness],
                [0, base_depth - lip_depth - support_thickness]
            ]);
}

// Assembly
base();
back_support();
front_lip();
```

### 3. Cable Organizer

Demonstrates: cylinders, array patterns with `for`, practical cable management.

```openscad
// Desktop Cable Organizer
// Material: PLA | Wall: 2mm
// Description: Holds multiple cables on desk edge

/* [Dimensions] */
num_slots = 5;         // number of cable slots
slot_diameter = 8;     // mm - cable diameter
slot_spacing = 15;     // mm - center-to-center
wall = 2;              // mm
base_height = 15;      // mm
base_depth = 25;       // mm

/* [Mounting] */
clip_depth = 20;       // mm - desk edge clip depth
desk_thickness = 25;   // mm - desk thickness for clip

/* [Quality] */
$fa = 1;
$fs = 0.4;

total_width = (num_slots - 1) * slot_spacing + slot_diameter + 2 * wall;

module cable_slot(x_pos) {
    translate([x_pos, base_depth / 2, base_height])
        rotate([-90, 0, 0]) {
            // Slot hole
            cylinder(d = slot_diameter, h = base_depth + 0.2, center = true);
            // Entry slit from top
            translate([0, slot_diameter / 2, 0])
                cube([slot_diameter * 0.4, slot_diameter, base_depth + 0.2], center = true);
        }
}

module body() {
    difference() {
        // Main body
        cube([total_width, base_depth, base_height + slot_diameter / 2 + wall]);

        // Cable slots
        for (i = [0 : num_slots - 1]) {
            cable_slot(wall + slot_diameter / 2 + i * slot_spacing);
        }
    }
}

module desk_clip() {
    translate([0, base_depth, 0]) {
        cube([total_width, wall, desk_thickness + base_height]);
        translate([0, -clip_depth, desk_thickness + base_height - wall])
            cube([total_width, clip_depth + wall, wall]);
    }
}

// Assembly
body();
desk_clip();
```

### 4. Wall-Mount Bracket

Demonstrates: screw holes, structural geometry, load-bearing design.

```openscad
// Wall-Mount L-Bracket
// Material: PETG | Wall: 3mm
// Description: Heavy-duty wall bracket for shelf or rail

/* [Dimensions] */
arm_length = 100;      // mm - horizontal arm
arm_width = 40;        // mm
arm_thickness = 5;     // mm
wall_plate_height = 80; // mm - vertical plate
wall_plate_thickness = 5; // mm

/* [Screw Holes] */
screw_hole_d = 5;      // mm - M5 screws
hole_compensation = 0.2; // mm - FDM hole shrinkage
screw_head_d = 10;     // mm - countersink diameter
screw_inset = 15;      // mm - from edges
num_wall_screws = 2;
num_arm_screws = 2;

/* [Structure] */
gusset_thickness = 4;  // mm
gusset_size = 40;      // mm - triangle size

/* [Quality] */
$fa = 1;
$fs = 0.4;

module wall_plate() {
    cube([arm_width, wall_plate_thickness, wall_plate_height]);
}

module horizontal_arm() {
    translate([0, wall_plate_thickness, 0])
        cube([arm_width, arm_length, arm_thickness]);
}

module gusset() {
    translate([arm_width / 2 - gusset_thickness / 2, wall_plate_thickness, arm_thickness])
        rotate([0, -90, 0])
            linear_extrude(height = gusset_thickness, center = true)
                polygon([
                    [0, 0],
                    [0, gusset_size],
                    [gusset_size, 0]
                ]);
}

module wall_screw_holes() {
    for (i = [0 : num_wall_screws - 1]) {
        z_pos = screw_inset + i * (wall_plate_height - 2 * screw_inset) / max(num_wall_screws - 1, 1);
        translate([arm_width / 2, -0.1, z_pos])
            rotate([-90, 0, 0]) {
                cylinder(d = screw_hole_d + hole_compensation, h = wall_plate_thickness + 0.2);
                cylinder(d = screw_head_d, h = 2.5);  // countersink
            }
    }
}

module arm_screw_holes() {
    for (i = [0 : num_arm_screws - 1]) {
        y_pos = wall_plate_thickness + screw_inset + i * (arm_length - 2 * screw_inset) / max(num_arm_screws - 1, 1);
        translate([arm_width / 2, y_pos, -0.1])
            cylinder(d = screw_hole_d + hole_compensation, h = arm_thickness + 0.2);
    }
}

// Assembly
difference() {
    union() {
        wall_plate();
        horizontal_arm();
        gusset();
    }
    wall_screw_holes();
    arm_screw_holes();
}
```

### 5. Heat-Set Insert Boss

Demonstrates: proper hole design for heat-set inserts (M3 example).

```openscad
// Heat-Set Insert Boss (M3)
// Material: PETG | Wall: 2mm
// Description: Mounting boss with heat-set insert pocket

/* [Insert Dimensions - M3] */
insert_od = 4.0;       // mm - outer diameter of insert
insert_length = 5.7;   // mm - insert length
insert_hole_d = 3.8;   // mm - slightly smaller than OD for press fit during melting

/* [Boss Dimensions] */
boss_od = insert_od * 2 + 2;  // mm - wall >= 2x insert OD
boss_height = insert_length + 2;  // mm - 2mm deeper than insert
relief_depth = 1.5;    // mm - relief well for displaced plastic
chamfer = 0.8;         // mm - entry chamfer for alignment

/* [Quality] */
$fa = 1;
$fs = 0.3;

module insert_boss() {
    difference() {
        // Outer boss
        cylinder(d = boss_od, h = boss_height);

        // Insert pocket (top)
        translate([0, 0, boss_height - insert_length])
            cylinder(d = insert_hole_d, h = insert_length + 0.1);

        // Relief well (bottom of pocket)
        translate([0, 0, boss_height - insert_length - relief_depth])
            cylinder(d = insert_hole_d * 0.8, h = relief_depth + 0.1);

        // Entry chamfer
        translate([0, 0, boss_height - chamfer])
            cylinder(d1 = insert_hole_d, d2 = insert_hole_d + 2 * chamfer, h = chamfer + 0.1);
    }
}

insert_boss();
```

## Anti-Patterns to Avoid

### 1. Non-Manifold Geometry
**Problem:** Subtracting a shape where surfaces are perfectly flush creates zero-thickness walls.
**Fix:** Always extend subtracted shapes by 0.1mm beyond the parent surface.
```openscad
// BAD - flush surfaces
difference() {
    cube([10, 10, 10]);
    translate([2, 2, 2]) cube([6, 6, 8]);  // top surface is flush
}

// GOOD - extended cut
difference() {
    cube([10, 10, 10]);
    translate([2, 2, 2]) cube([6, 6, 8.1]);  // extends 0.1mm beyond top
}
```

### 2. Hardcoded Magic Numbers
**Problem:** Dimensions embedded directly in geometry calls make modification impossible.
```openscad
// BAD
cube([80, 60, 40]);
translate([2, 2, 2]) cube([76, 56, 38.1]);

// GOOD
width = 80;
depth = 60;
height = 40;
wall = 2;
cube([width, depth, height]);
translate([wall, wall, wall]) cube([width - 2*wall, depth - 2*wall, height - wall + 0.1]);
```

### 3. Missing Resolution Settings
**Problem:** Default resolution produces low-polygon cylinders and spheres that look faceted.
**Fix:** Always set `$fa`/`$fs` or `$fn` at the top of the file.

### 4. Zero-Thickness Walls
**Problem:** Wall thickness below printable minimum (1.2mm for PLA/PETG, 1.6mm for TPU).
**Fix:** Always use material-appropriate wall thickness values. See materials.md.

### 5. Origin Offset Errors
**Problem:** LLMs miscalculate spatial positions, causing parts to overlap or float.
**Fix:** Use separate modules per component, center at origin, use explicit `translate()`. Keep positioning math simple.

### 6. Forgetting Tolerances for Interlocking Parts
**Problem:** Parts designed to fit together are exact size and won't fit when printed.
**Fix:** Add clearance variable. PLA: 0.3mm, PETG: 0.35mm, TPU: 0.4mm per side.

### 7. Fillets on Bottom Edges
**Problem:** Fillets on the first layer create unsupported overhangs (start at ~90 degrees).
**Fix:** Use 45-degree chamfers on bottom edges. Fillets are fine on top and vertical edges.

### 8. Walls Not Multiples of Nozzle Diameter
**Problem:** 1.5mm wall with 0.4mm nozzle = 3.75 perimeters. Slicer rounds to 3 or 4, leaving gaps or over-extrusion.
**Fix:** Always use wall thickness that's a multiple of nozzle diameter (0.8, 1.2, 1.6, 2.0mm for 0.4mm nozzle).

## text() and import() Usage

### text()
Useful for labels but generates high polygon counts. Keep resolution reasonable.

```openscad
// Embossed text on a surface
module label(text_str, size = 8, depth = 1) {
    linear_extrude(height = depth)
        text(text_str, size = size, font = "Liberation Sans:style=Bold",
             halign = "center", valign = "center");
}

// Minimum sizes for readability after printing:
// Embossed: 1mm width, 0.5mm height, 16pt bold on horizontal, 10pt on vertical
// Debossed: 1mm width, 0.3mm depth
```

### import()
For bringing in external meshes. Use sparingly.

```openscad
// Import STL (opaque geometry -- cannot reliably difference() against it)
import("external_part.stl");

// Prefer importing DXF for 2D profiles, then extruding:
linear_extrude(height = 5)
    import("profile.dxf");
```

## OpenSCAD CLI Reference

### Binary Path (macOS)
```
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD
```
Fallback: `which openscad`

### Render Preview PNG
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

Flags:
- `--imgsize 800,600` -- output image resolution
- `--projection p` -- perspective projection (use `o` for orthographic)
- `--render` -- full CGAL render (required for correct geometry, works headless)
- `--colorscheme DeepOcean` -- dark background with good contrast
- `--autocenter` -- automatically center the model in view
- `--viewall` -- zoom to fit entire model
- `-o preview.png` -- output file (format inferred from extension)

### Validation Pass (catch errors before export)
```bash
"$OPENSCAD" --hardwarnings -o /dev/null "$OUTPUT_DIR/model.scad" 2>"$OUTPUT_DIR/openscad.log"
```
`--hardwarnings` stops on the first warning -- useful for catching non-manifold geometry early.

### Export 3MF
```bash
"$OPENSCAD" \
    -o "$OUTPUT_DIR/model.3mf" \
    "$OUTPUT_DIR/model.scad" \
    2>>"$OUTPUT_DIR/openscad.log"
```

### Override Variables from CLI
```bash
"$OPENSCAD" -D 'width=100' -D 'height=50' -o model.3mf model.scad
```
Variables **must be initialized in the .scad file** or the override silently fails.

### Export STL (if ever needed)
```bash
"$OPENSCAD" -o model.stl model.scad
```
Note: CLI defaults to ASCII STL. Use `--export-format binstl` for smaller binary files.

## Common Error Patterns

### Syntax Errors
```
ERROR: Parser error: syntax error, unexpected '}', expecting ';'
```
**Fix:** Check for missing semicolons, unmatched braces, or missing commas in lists.

### Non-Manifold Warnings
```
WARNING: Object may not be a valid 2-manifold and target format may not support
```
**Fix:** Extend all CSG subtraction shapes by 0.1mm beyond surfaces. Ensure no zero-thickness geometry.

### CGAL Errors
```
ERROR: CGAL error in CGALUtils::applyOperator3D: CGAL ERROR: assertion violation!
```
**Fix:** Usually caused by degenerate geometry (zero-area faces, self-intersecting surfaces). Simplify the model, check for coincident faces.

### Undefined Variable
```
WARNING: Ignoring unknown variable 'wall_thicknes'
```
**Fix:** Check for typos in variable names. OpenSCAD silently ignores undefined variables (returns `undef`).

### Recursion Depth
```
ERROR: Recursion detected
```
**Fix:** Check for modules calling themselves without a base case, or circular `use`/`include` statements.

### Render Timeout (not an error, but a problem)
If OpenSCAD CLI hangs for more than 60 seconds:
- Reduce `$fs` (try 1.0) or set `$fn = 30`
- Simplify geometry (fewer boolean operations)
- Split into simpler components
- Consider using OpenSCAD nightly with Manifold backend for complex models
