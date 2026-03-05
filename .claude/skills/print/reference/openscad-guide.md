# OpenSCAD Code Generation Guide

Reference for generating well-structured, printable OpenSCAD code from natural language descriptions.

## Code Structure Rules

Every generated .scad file MUST follow this structure:

1. **Comment header** at the top: description, material, key dimensions
2. **Parametric variables section**: all dimensions as named variables (NEVER magic numbers)
3. **Quality settings**: always set `$fn` explicitly
   - `$fn = 60` for general use (good balance of quality and render speed)
   - `$fn = 30` for quick previews during iteration
   - `$fn = 100` or higher for final high-quality renders of simple models
4. **Module definitions**: separate `module` block for each distinct component
5. **Assembly section**: final positioning using `translate()`, `rotate()`, etc.

### Variable Naming Conventions

```openscad
// Dimensions - use descriptive names
width = 80;          // mm - X axis
depth = 60;          // mm - Y axis
height = 40;         // mm - Z axis
wall = 2;            // mm - wall thickness
corner_r = 3;        // mm - corner radius

// Tolerances
clearance = 0.3;     // mm - gap for interlocking parts (material-dependent)

// Quality
$fn = 60;
```

### Spatial Positioning Rules

- Center objects at the origin when practical
- Use explicit `translate()` for all positioning -- never rely on implicit placement
- When assembling multiple modules, position them relative to the origin
- For parts that print separately, offset them in Z (e.g., `translate([0, 0, height + 5])`) so the preview shows them distinctly

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
wall = 2;             // mm
corner_r = 3;         // mm

/* [Lid] */
lid_height = 10;      // mm
lid_clearance = 0.3;  // mm - printing tolerance per side

/* [Quality] */
$fn = 60;

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
$fn = 60;

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
$fn = 60;

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
screw_head_d = 10;     // mm - countersink diameter
screw_inset = 15;      // mm - from edges
num_wall_screws = 2;
num_arm_screws = 2;

/* [Structure] */
gusset_thickness = 4;  // mm
gusset_size = 40;      // mm - triangle size

/* [Quality] */
$fn = 60;

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
                cylinder(d = screw_hole_d, h = wall_plate_thickness + 0.2);
                cylinder(d = screw_head_d, h = 2.5);  // countersink
            }
    }
}

module arm_screw_holes() {
    for (i = [0 : num_arm_screws - 1]) {
        y_pos = wall_plate_thickness + screw_inset + i * (arm_length - 2 * screw_inset) / max(num_arm_screws - 1, 1);
        translate([arm_width / 2, y_pos, -0.1])
            cylinder(d = screw_hole_d, h = arm_thickness + 0.2);
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

### 3. Missing $fn
**Problem:** Default `$fn` produces low-polygon cylinders and spheres that look faceted.
**Fix:** Always set `$fn` at the top of the file.

### 4. Zero-Thickness Walls
**Problem:** Wall thickness below printable minimum (1.2mm for PLA/PETG, 1.6mm for TPU).
**Fix:** Always use material-appropriate wall thickness values. See materials.md.

### 5. Origin Offset Errors
**Problem:** LLMs miscalculate spatial positions, causing parts to overlap or float.
**Fix:** Use separate modules per component, center at origin, use explicit `translate()`. Keep positioning math simple.

### 6. Forgetting Tolerances for Interlocking Parts
**Problem:** Parts designed to fit together are exact size and won't fit when printed.
**Fix:** Add clearance variable. PLA: 0.3mm, PETG: 0.35mm, TPU: 0.4mm per side.

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

### Export 3MF
```bash
"$OPENSCAD" \
    -o "$OUTPUT_DIR/model.3mf" \
    "$OUTPUT_DIR/model.scad" \
    2>>"$OUTPUT_DIR/openscad.log"
```

### Export STL (if ever needed)
```bash
"$OPENSCAD" -o model.stl model.scad
```

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
- Reduce `$fn` (try 30)
- Simplify geometry (fewer boolean operations)
- Split into simpler components
