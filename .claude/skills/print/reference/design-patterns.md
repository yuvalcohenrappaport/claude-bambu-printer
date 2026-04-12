# Design Patterns for 3D Printing

Reference for functional design patterns, tolerances, fastening methods, and print orientation strategies.

## Tolerance and Clearance Reference

### Fit Types

| Fit Type | Clearance (mm) | Use Case |
|----------|----------------|----------|
| Press fit | 0.0 to -0.1 | Permanent joints, pins into holes, bushings |
| Tight/Snug fit | 0.1-0.15 | Semi-permanent, requires force to assemble |
| Sliding fit | 0.2-0.3 | Drawers, telescoping tubes, linear guides |
| Loose fit | 0.4-0.5 | Easy assembly/disassembly, covers, caps |
| Print-in-place | 0.5 minimum | Assemblies printed as one piece |
| Hinge gap | 0.6 minimum | Printed hinges and pivots |

### Rules
- Apply clearance to **one part only** (e.g., keep bolt at 5.0mm, make hole 5.3mm)
- **Holes are always undersized** in FDM -- add 0.1-0.2mm to hole diameters
- General FDM tolerance: +/- 0.25mm minimum
- Always print a tolerance test before committing to large functional prints
- These values assume a calibrated printer with 0.4mm nozzle

## Heat-Set Inserts

Preferred over printed threads for any application requiring repeated assembly or structural loads.

### Common Sizes

| Insert | Hole Diameter | Min Wall Thickness | Hole Depth |
|--------|--------------|-------------------|------------|
| M2 | 3.0mm | 6mm | Insert + 1.5mm |
| M2.5 | 3.5mm | 7mm | Insert + 1.5mm |
| M3 | 3.8-4.0mm | 8mm | Insert + 2mm |
| M4 | 5.0-5.3mm | 10mm | Insert + 2mm |
| M5 | 6.0-6.4mm | 12mm | Insert + 2mm |

### Design Rules
- **Hole wall thickness**: minimum 2x the insert outer diameter
- **Hole depth**: insert length + 1-2mm (relief well for displaced molten plastic)
- **Hole profile**: slightly smaller than insert OD at top, with entry chamfer for alignment
- **Installation temp**: 343-399C (650-750F) with appropriate soldering iron tip
- **Best materials**: PETG, ABS, Nylon, PC
- **Avoid with PLA**: brittle, cracks under heat/stress. If necessary, increase wall thickness significantly

### OpenSCAD Pattern
```openscad
// M3 heat-set insert boss
insert_od = 4.0;
insert_length = 5.7;
insert_hole_d = 3.8;
boss_od = insert_od * 2 + 2;    // wall >= 2x insert OD
boss_height = insert_length + 2; // relief well
chamfer = 0.8;                   // entry chamfer

module insert_boss() {
    difference() {
        cylinder(d = boss_od, h = boss_height);
        // Insert pocket
        translate([0, 0, boss_height - insert_length])
            cylinder(d = insert_hole_d, h = insert_length + 0.1);
        // Relief well
        translate([0, 0, boss_height - insert_length - 1.5])
            cylinder(d = insert_hole_d * 0.8, h = 1.6);
        // Entry chamfer
        translate([0, 0, boss_height - chamfer])
            cylinder(d1 = insert_hole_d, d2 = insert_hole_d + 2*chamfer, h = chamfer + 0.1);
    }
}
```

## Printed Threads

Acceptable for low-strength, low-cycle applications (caps, knobs, prototypes).

### When to Use
- Large threads (M8+) with coarse pitch
- Low-cycle: caps screwed on/off <50 times
- Non-structural: decorative, alignment only

### Design Rules
- Add chamfers at thread start for easier engagement
- Print threads **vertically** (along Z-axis) for best accuracy
- Use finer layer heights (0.1-0.15mm) for thread quality
- Increase clearance by 0.1-0.2mm beyond standard thread specs
- For anything structural or repeated: use heat-set inserts instead

## Snap-Fit Joints

### Cantilever Snap-Fit
```
        ___
       /   |  <-- hook (undercut)
      /    |
     |     |  <-- cantilever beam
     |     |
=====|=====|  <-- base (fillet at root)
```

| Parameter | Value |
|-----------|-------|
| Clearance | 0.5mm |
| Undercut depth | >= 1mm |
| Cantilever base thickness | >= 1mm |
| Root fillet radius | >= 0.5mm |
| Max deflection | 2-5% of beam length |

### Design Rules
- Use **tapered cantilever profiles** (thicker at root, thinner at tip) to distribute stress
- Add **fillets at cantilever root** (r >= 0.5mm) to prevent stress cracking
- Add **locating lugs** on the mating part to share shear loads
- Print cantilevers so flex direction is **NOT along layer lines** (Z-axis is weakest)
- PLA snap-fits are fragile -- prefer PETG or Nylon for repeated use

### OpenSCAD Pattern
```openscad
// Simple cantilever snap-fit
beam_length = 15;
beam_thickness = 1.2;
beam_width = 5;
hook_depth = 1.5;     // undercut
hook_height = 2;
fillet_r = 0.8;

module snap_hook() {
    // Beam
    cube([beam_width, beam_thickness, beam_length]);
    // Hook
    translate([0, 0, beam_length])
        cube([beam_width, beam_thickness + hook_depth, hook_height]);
}
```

## Living Hinges

Thin flexible sections that allow two rigid parts to fold.

### Design Rules
- **Material**: TPU best (1000s+ cycles). Nylon/PETG moderate (100s cycles). PLA poor (<20 cycles).
- **Thickness**: 0.4-0.8mm for PLA, 0.6-1.2mm for PETG/Nylon
- **Width**: Full width of the part for even stress distribution
- **Print orientation**: Hinge aligned so a single bead runs the full length
- **Layer direction**: Print so layers are parallel to the hinge axis
- Make hinges **thicker than injection-molded** equivalents (FDM needs more material)

## Ball Joints

### Design Rules

| Parameter | Value |
|-----------|-------|
| Socket-to-ball offset | ~10% of ball diameter |
| Surface spacing | 0.2mm between cavity and ball |
| Example: 10mm ball | 9mm socket opening, 0.2mm gap |

- Print with supports inside the socket, or design a snap-in assembly
- Use PETG or Nylon for durability (PLA sockets crack)

## Print Orientation Strategy

FDM parts are **anisotropic** -- layer bonds (Z-axis) are 4-5x weaker than in-plane (XY) strength.

### Rules
1. **Orient primary stress parallel to layers** (XY plane), not across them (Z-axis)
2. **Minimize supports** -- reorienting can reduce support volume by up to 94%
3. **Aesthetic surfaces vertical** -- perpendicular to bed minimizes stairstepping
4. **Bed-contact surface** gets a glossy finish; supported surfaces have marks

### Common Orientations

| Part Type | Best Orientation | Why |
|-----------|-----------------|-----|
| Bracket/L-shape | Flat on back | Load in XY, no supports needed |
| Tube/cylinder | Vertical (standing) | Round cross-section preserved |
| Box/container | Open side up | No supports for interior |
| Gear | Flat (teeth in XY) | Teeth strongest in XY plane |
| Hook | Flat on side | Load path in XY |
| Enclosure halves | Split face down | Flat mating surface on bed |

### Horizontal Holes
Horizontal holes print as ovals (squished on the unsupported top). Solutions:
- **Teardrop shape**: Use a teardrop profile instead of a circle (45-degree point at top is self-supporting)
- **Print vertically** if possible (vertical holes are accurate)
- **Oversize by 0.2mm** and ream after printing

```openscad
// Teardrop hole (self-supporting horizontal hole)
module teardrop_hole(d, h) {
    r = d / 2;
    rotate([90, 0, 0])
        linear_extrude(height = h, center = true)
            union() {
                circle(r = r);
                // 45-degree point at top
                translate([0, r * 0.7, 0])
                    rotate([0, 0, 45])
                        square(r * 0.72, center = true);
            }
}
```

## Common Design Mistakes

1. **Ignoring the 45-degree rule** -- unsupported overhangs droop or fail
2. **Walls not multiples of nozzle diameter** (0.4mm) -- causes gaps and weak spots
3. **No chamfer on first layer edge** -- sharp corners lift off bed (warping)
4. **Holes at exact nominal size** -- always undersized in FDM; add 0.1-0.2mm
5. **Fillets on bottom edges** -- start at ~90 degrees, creating unsupported overhang; use chamfers
6. **Too-thin walls** (under 0.8mm) -- slicer may skip them entirely
7. **Ignoring print orientation** -- Z-axis strength is 4-5x weaker than XY
8. **Large flat surfaces on bed** -- prone to elephant's foot and warping; add base chamfer
9. **Not accounting for shrinkage** -- ABS ~0.8%, Nylon ~1-1.5%, PLA ~0.3%
10. **Designing snap-fits with flex along Z** -- layer adhesion fails before material flexes

## Elephant's Foot Mitigation

The first layer squishes slightly wider than designed (elephant's foot). For precision parts:
- Add a 0.4mm 45-degree chamfer to the bottom edge in the model
- Or use slicer's "elephant foot compensation" setting (0.1-0.2mm typical)

```openscad
// Bottom chamfer to prevent elephant's foot
module anti_elephant_foot(size, chamfer = 0.4) {
    difference() {
        cube(size);
        // Chamfer bottom edge on all 4 sides
        for (angle = [0, 90, 180, 270])
            rotate([0, 0, angle])
                translate([-0.1, -0.1, -0.1])
                    rotate([0, 0, 0])
                        linear_extrude(height = chamfer + 0.1)
                            polygon([[0, 0], [chamfer + 0.1, 0], [0, chamfer + 0.1]]);
    }
}
```

## Post-Processing Reference

| Technique | Materials | Notes |
|-----------|-----------|-------|
| Sanding (150-2000 grit) | All | Circular motion, wet sand at high grits |
| Filler primer spray | PLA, ABS, PETG | 2-3 coats, sand 400-600 grit between |
| Acetone vapor smoothing | ABS, ASA only | 10-20 min, eliminates layer lines, reduces accuracy |
| Heat-set inserts | PETG, ABS, Nylon, PC | 343-399C soldering iron, push straight in |
| CA glue bonding | PLA, ABS, PETG | Instant bond, brittle joint |
| Epoxy bonding | All | Strongest joint, gap-filling, 5-min or slow cure |
| Acetone welding | ABS, ASA only | Apply acetone to surfaces, press together |
| Painting | All (after primer) | Filler primer first for smooth finish |

## Quick Reference Cheat Sheet

| Parameter | Value |
|-----------|-------|
| Min wall (0.4mm nozzle) | 0.8mm (1.2mm recommended) |
| Min pin diameter | 3.0mm |
| Min hole diameter | 0.5mm (add 0.1-0.2mm compensation) |
| Max unsupported overhang | 45 degrees from vertical |
| Max bridge length (no support) | 10mm (PLA can do 50mm with sag) |
| Press-fit clearance | 0.0 to -0.1mm |
| Sliding-fit clearance | 0.2-0.3mm |
| Loose-fit clearance | 0.4-0.5mm |
| Snap-fit clearance | 0.5mm |
| Print-in-place gap | 0.5mm minimum |
| Hinge gap | 0.6mm minimum |
| Ball joint offset | ~10% of ball diameter |
| Embossed text min | 16pt bold (horizontal), 10pt (vertical) |
| Heat-set insert wall | 2x insert OD |
| General FDM tolerance | +/- 0.25mm minimum |
