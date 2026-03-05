# Material Design Parameters

Reference for material-specific design values when generating OpenSCAD code.

## PLA (Polylactic Acid)

The default material. Recommend unless the user specifies otherwise or the use case suggests different.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.2 mm | 2 perimeters at 0.4mm nozzle + infill |
| Tolerance/clearance | 0.3 mm per side | For interlocking/mating parts |
| Recommended $fn | 60 | Good balance of quality and speed |
| Bed temp | 60C | Not relevant to code gen, but useful context |
| Max service temp | ~55C | Deforms in hot environments |

**Good for:** Rigid parts, desk organizers, display items, prototypes, brackets, cases, holders, decorative items.

**Avoid:** High-temperature environments (car dashboards, near heat sources), outdoor long-term use (UV degradation), food-contact items (layer lines harbor bacteria).

**Code implications:**
```openscad
wall = 2;            // mm - safe default (above 1.2mm minimum)
clearance = 0.3;     // mm - per side for mating parts
$fn = 60;
```

## PETG (Polyethylene Terephthalate Glycol)

Stronger and more heat-resistant than PLA. Good all-rounder for functional parts.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.2 mm | Same as PLA |
| Tolerance/clearance | 0.35 mm per side | Slightly more than PLA due to stringing |
| Recommended $fn | 60 | Same as PLA |
| Max service temp | ~75C | Better than PLA for warm environments |

**Good for:** Mechanical parts, water-resistant items, outdoor use, functional brackets, tool holders, parts needing impact resistance.

**Avoid:** Parts needing precise dimensional accuracy (PETG strings more, slightly less precise than PLA), parts requiring fine surface detail.

**Code implications:**
```openscad
wall = 2;            // mm - safe default
clearance = 0.35;    // mm - slightly more than PLA
$fn = 60;
```

## TPU (Thermoplastic Polyurethane)

Flexible material. Use when the part needs to bend, flex, or absorb impact.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.6 mm | Thicker minimum due to flexibility |
| Tolerance/clearance | 0.4 mm per side | More clearance needed |
| Recommended $fn | 60 | Same as others |
| Shore hardness | 95A typical | Firm but flexible |

**Good for:** Phone cases, bumpers, gaskets, seals, flexible mounts, vibration dampeners, grips, protective covers.

**Avoid:** Rigid structural parts, precise dimensional work, parts under constant load (creeps over time), tall thin structures (wobble during print).

**Code implications:**
```openscad
wall = 2.4;          // mm - thicker for flexible material
clearance = 0.4;     // mm - more clearance needed
$fn = 60;
```

## How Material Choice Affects Generated Code

When generating OpenSCAD, set these variables based on the user's material choice:

```openscad
// Material-dependent parameters
// Set these based on user's material choice:

// PLA (default)
wall = 2;            // mm (min 1.2)
clearance = 0.3;     // mm per side

// PETG
wall = 2;            // mm (min 1.2)
clearance = 0.35;    // mm per side

// TPU
wall = 2.4;          // mm (min 1.6)
clearance = 0.4;     // mm per side
```

### Additional Material Considerations

1. **Structural reinforcement:** PETG and TPU parts can have thinner gussets/ribs than PLA due to higher impact resistance. PLA parts under load benefit from thicker walls or added ribbing.

2. **Overhangs:** All materials handle 45-degree overhangs without supports. For steeper overhangs, add chamfers or redesign.

3. **Bridging:** PLA bridges best (up to ~50mm). PETG bridges moderately (~30mm). TPU bridges poorly -- avoid unsupported spans over 15mm.

4. **Fine detail:** PLA produces the best fine detail. PETG is slightly less precise. TPU cannot produce fine details reliably.

## Default Recommendation Logic

If the user does not specify a material:
1. **Default to PLA** -- it is the most common, easiest to print, and works for most use cases
2. **Suggest PETG if:** the use case involves water, outdoor exposure, mechanical stress, or temperatures above 50C
3. **Suggest TPU if:** the user explicitly wants flexibility, or the item is a case, bumper, gasket, or grip
