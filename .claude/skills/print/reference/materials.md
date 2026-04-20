# Material Design Parameters

Reference for material-specific design values when generating OpenSCAD code.

## PLA (Polylactic Acid)

The default material. Recommend unless the user specifies otherwise or the use case suggests different.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.2 mm | 3 perimeters at 0.4mm nozzle |
| Tolerance/clearance | 0.3 mm per side | For interlocking/mating parts |
| Shrinkage | ~0.3-0.4% | Minimal, generally ignorable |
| Max service temp | ~55C | Deforms in hot environments |
| Bed temp | 60C | |
| Nozzle temp | 190-220C | |

**Good for:** Rigid parts, desk organizers, display items, prototypes, brackets, cases, holders, decorative items.

**Avoid:** High-temperature environments (car dashboards, near heat sources), outdoor long-term use (UV degradation), food-contact items (layer lines harbor bacteria), press-fits in small features (too brittle).

**Bonding:** Super glue (CA) or epoxy. No solvent welding.

**Post-processing:** Sands easily (start 150 grit, progress to 2000). Filler primer + paint works well. Cannot be acetone-smoothed.

**Code implications:**
```openscad
wall = 2;            // mm - safe default (above 1.2mm minimum)
clearance = 0.3;     // mm - per side for mating parts
```

## PETG (Polyethylene Terephthalate Glycol)

Stronger and more heat-resistant than PLA. Good all-rounder for functional parts.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.2 mm | Same as PLA |
| Tolerance/clearance | 0.35 mm per side | Slightly more than PLA due to stringing |
| Shrinkage | ~0.3-0.5% | Slightly more than PLA |
| Max service temp | ~75C | Better than PLA for warm environments |
| Bed temp | 70-80C | |
| Nozzle temp | 220-250C | |

**Good for:** Mechanical parts, water-resistant items, outdoor use, functional brackets, tool holders, parts needing impact resistance. Good for press-fits (deforms slightly without cracking).

**Avoid:** Parts needing precise dimensional accuracy (strings more), parts requiring fine surface detail.

**Bonding:** Super glue (CA) or epoxy. No solvent welding.

**Post-processing:** Sands well but slightly tougher than PLA. Cannot be acetone-smoothed. Use glue stick as **release agent** on PEI beds (prevents PETG from bonding too strongly and ripping the PEI).

**Code implications:**
```openscad
wall = 2;            // mm - safe default
clearance = 0.35;    // mm - slightly more than PLA
```

## TPU (Thermoplastic Polyurethane)

Flexible material. Use when the part needs to bend, flex, or absorb impact.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.6 mm | Thicker minimum due to flexibility |
| Tolerance/clearance | 0.4 mm per side | More clearance needed |
| Shrinkage | ~0.5-1.0% | More significant |
| Shore hardness | 95A typical | Firm but flexible |
| Bed temp | 40-60C | |
| Nozzle temp | 220-250C | |

**Good for:** Phone cases, bumpers, gaskets, seals, flexible mounts, vibration dampeners, grips, protective covers.

**Avoid:** Rigid structural parts, precise dimensional work, tall thin structures (wobble during print), parts under constant load (creeps over time). **Requires direct-drive extruder** (Bowden struggles).

**Bonding:** Flexible CA glue or contact cement.

**Post-processing:** Difficult to sand. Painting adhesion is poor without primer.

**Print speed:** MUST print slow: 20-40 mm/s. Faster speeds cause jams and poor layer adhesion.

**Code implications:**
```openscad
wall = 2.4;          // mm - thicker for flexible material
clearance = 0.4;     // mm - more clearance needed
```

## ABS (Acrylonitrile Butadiene Styrene)

Strong, heat-resistant, acetone-smoothable. **Requires enclosure.**

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.2 mm | Same as PLA |
| Tolerance/clearance | 0.3 mm per side | Similar to PLA |
| Shrinkage | ~0.7-0.8% | Significant -- compensate for tight-tolerance parts |
| Max service temp | ~100C | Excellent heat resistance |
| Bed temp | 95-110C | |
| Nozzle temp | 230-250C | |

**Good for:** Heat-resistant parts, automotive, enclosures, mechanical parts, anything needing acetone smoothing for a glossy finish.

**Avoid:** Printing without an enclosure (warps heavily), large flat surfaces on bed (warping), parts needing UV resistance outdoors.

**Bonding:** Acetone welding (apply acetone to surfaces, press together) or super glue.

**Post-processing:** Acetone vapor smoothing (10-20 min exposure) eliminates layer lines. Sands and paints well.

**Design note:** Add chamfers to bottom edges and avoid large flat first layers to reduce warping. Add mouse ears or brims for adhesion.

**Code implications:**
```openscad
wall = 2;            // mm
clearance = 0.3;     // mm per side
// Add 0.7-0.8% to critical dimensions to compensate for shrinkage
// e.g., for a 100mm part: width = 100 * 1.008;
```

## ASA (Acrylonitrile Styrene Acrylate)

Like ABS but with excellent UV resistance. **Requires enclosure.**

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.2 mm | Same as ABS |
| Tolerance/clearance | 0.3 mm per side | Same as ABS |
| Shrinkage | ~0.5-0.7% | Slightly less than ABS |
| Max service temp | ~95-105C | Similar to ABS |
| Bed temp | 95-110C | |
| Nozzle temp | 235-255C | |

**Good for:** Outdoor parts (planters, mounts, signs), automotive, anything exposed to sunlight long-term.

**Avoid:** Printing without enclosure, food contact.

**Bonding:** Acetone welding or super glue (same as ABS).

**Post-processing:** Acetone vapor smoothing works. Same finishing as ABS.

**Code implications:**
```openscad
wall = 2;            // mm
clearance = 0.3;     // mm per side
```

## Nylon (PA6, PA12)

Extremely tough and fatigue-resistant. **Must be dried before printing. Requires enclosure.**

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.2 mm | Can go thinner due to toughness, but 1.2 is safe |
| Tolerance/clearance | 0.35 mm per side | Slightly more due to warping tendency |
| Shrinkage | ~0.7-1.5% | Significant and variable |
| Max service temp | ~110-180C | Excellent (varies by grade) |
| Bed temp | 70-90C | |
| Nozzle temp | 240-270C | |

**Good for:** Functional mechanical parts, gears, hinges, snap-fits, parts needing fatigue resistance (living hinges last 1000s of cycles), high-temperature applications.

**Avoid:** Printing without drying filament first (absorbs moisture rapidly -- print quality degrades within hours of exposure). Printing without enclosure. Parts needing tight dimensional accuracy.

**Bonding:** Specialized nylon epoxy or mechanical fasteners (hard to glue with CA).

**Post-processing:** Difficult to sand (too tough). Can be dyed. Painting requires specialty primer.

**Code implications:**
```openscad
wall = 2;            // mm
clearance = 0.35;    // mm per side
// Shrinkage compensation critical for nylon:
// Add 1-1.5% to critical dimensions
```

## CF-Nylon (Carbon Fiber Reinforced Nylon)

Stiff, strong, dimensionally stable. **Requires hardened steel nozzle.**

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.2 mm | |
| Tolerance/clearance | 0.3 mm per side | Better dimensional stability than plain nylon |
| Shrinkage | ~0.3-0.5% | Much less than plain nylon |
| Max service temp | ~120-180C | |
| Bed temp | 70-90C | |
| Nozzle temp | 250-270C | |

**Good for:** Stiff structural parts, jigs and fixtures, replacement for aluminum in some cases, drone frames, automotive.

**Avoid:** Standard brass nozzles (carbon fiber is abrasive -- will destroy the nozzle in hours). Parts needing flexibility.

**Code implications:**
```openscad
wall = 2;            // mm
clearance = 0.3;     // mm per side (better accuracy than plain nylon)
```

## CF-PETG (Carbon Fiber Reinforced PETG)

Stiffer than standard PETG with less warping. **Requires hardened steel nozzle.**

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.2 mm | |
| Tolerance/clearance | 0.3 mm per side | Better than plain PETG |
| Shrinkage | ~0.3% | Less than plain PETG |
| Max service temp | ~80-90C | Slightly better than plain PETG |
| Bed temp | 70-80C | |
| Nozzle temp | 230-260C | |

**Good for:** Functional parts needing stiffness without an enclosure, lightweight structural parts, camera mounts.

**Avoid:** Standard brass nozzles. Parts needing flexibility or impact resistance (more brittle than plain PETG).

**Code implications:**
```openscad
wall = 2;            // mm
clearance = 0.3;     // mm per side
```

## PLA Metal (Metallic PLA)

Metallic-finish PLA. Appearance is highly speed-dependent -- consistent speed = consistent shine.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min wall thickness | 1.2 mm | Same as PLA |
| Tolerance/clearance | 0.3 mm per side | Same as PLA |
| Shrinkage | ~0.3-0.4% | Same as PLA |
| Nozzle temp | 230C | Higher temp (5-10C above standard PLA) improves flow and metallic shine |
| Bed temp | 60C | Textured PEI |
| Max volumetric speed | 8-10 mm3/s | Default 21 is too high; lower for even melt |
| Flow ratio | 0.98 | Sweet spot for PLA Metal |
| Retraction | 0.8 mm @ 40 mm/s | Direct drive (Bambu A1); prevents stringing without clogs |
| Travel speed | 300 mm/s | |
| Wipe | enabled | Reduces stringing |
| Outer wall speed | 40-60 mm/s | Most important for aesthetics; 200+ looks matte/dull |
| Inner wall speed | 120-150 mm/s | Faster here to save time |
| Small perimeter speed | 50% of outer wall | |
| Infill speed | 150-200 mm/s | |
| Wall loops | 3-4 | Metallic PLA is more brittle; extra walls add strength |
| Outer wall first | Disabled (Inner/Outer) | Better overhangs and surface quality |

**Good for:** Decorative items, display pieces, cosplay parts, jewelry, anything where metallic appearance matters.

**Avoid:** Same as PLA -- high-temp environments, outdoor long-term, food contact.

**Code implications:**
```openscad
wall = 2;            // mm (min 1.2)
clearance = 0.3;     // mm per side
```

## How Material Choice Affects Generated Code

When generating OpenSCAD, set these variables based on the user's material choice:

```openscad
// Material-dependent parameters

// PLA / PLA Metal / ABS / ASA (default)
wall = 2;            // mm (min 1.2)
clearance = 0.3;     // mm per side

// PETG / Nylon
wall = 2;            // mm (min 1.2)
clearance = 0.35;    // mm per side

// TPU
wall = 2.4;          // mm (min 1.6)
clearance = 0.4;     // mm per side

// CF-Nylon / CF-PETG (better dimensional accuracy)
wall = 2;            // mm (min 1.2)
clearance = 0.3;     // mm per side
```

### Additional Material Considerations

1. **Structural reinforcement:** PETG and Nylon parts can have thinner gussets/ribs than PLA due to higher impact resistance. PLA and ABS parts under load benefit from thicker walls or added ribbing.

2. **Overhangs:** All materials handle 45-degree overhangs without supports. For steeper overhangs, add chamfers or redesign.

3. **Bridging:** PLA bridges best (up to ~50mm). PETG bridges moderately (~30mm). TPU bridges poorly -- avoid spans over 15mm. ABS/ASA bridge ~30-40mm with enclosure.

4. **Fine detail:** PLA produces the best fine detail. PETG/ABS are slightly less precise. TPU cannot produce fine details reliably. CF composites have good detail but matte finish.

5. **Shrinkage compensation:** For tight-tolerance parts:
   - PLA: generally not needed
   - PETG: add ~0.3-0.5% to critical dimensions
   - ABS: add ~0.7-0.8%
   - Nylon: add ~1-1.5%

6. **Enclosure requirements:** ABS, ASA, and Nylon MUST be printed in an enclosure. PLA should NOT be enclosed (overheating causes heat creep). PETG is fine either way.

## Default Recommendation Logic

If the user does not specify a material:
1. **Default to PLA** -- most common, easiest to print, works for most use cases
2. **Suggest PETG if:** water exposure, outdoor use, mechanical stress, temperatures above 50C, press-fits needed
3. **Suggest TPU if:** explicitly wants flexibility, or the item is a case, bumper, gasket, or grip
4. **Suggest ABS/ASA if:** heat resistance above 75C needed, or acetone smoothing desired. ASA for outdoor/UV.
5. **Suggest Nylon if:** fatigue resistance, living hinges, gears, maximum toughness needed
6. **Suggest CF variants if:** maximum stiffness needed, weight is a concern, user has hardened nozzle
7. **Use PLA Metal settings if:** user specifies PLA Metal or metallic PLA
