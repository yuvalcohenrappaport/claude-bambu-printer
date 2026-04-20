# Print Settings Reference

Purpose-based print profiles, geometry-based adjustments, and BambuStudio parameter reference for the /print skill.

## Calibration Order

Before tuning print settings, calibrate in this order (OrcaSlicer has built-in tools under Calibration menu):

1. **Temperature tower** -- affects viscosity and flow
2. **Pressure advance (PA)** -- eliminates corner bulging and line artifacts
3. **Flow rate** -- ensures dimensional accuracy and layer adhesion
4. **Retraction test** -- dials in stringing prevention

## Section 1: Purpose-Based Print Settings

Each profile provides a complete set of BambuStudio print parameters. Select the profile that best matches the user's stated use case.

### Decorative / Display

Fine layers for smooth surface finish. Prioritizes visual quality over speed.

| Parameter | Value |
|-----------|-------|
| layer_height | 0.12 |
| initial_layer_print_height | 0.2 |
| wall_loops | 2 |
| top_shell_layers | 5 |
| bottom_shell_layers | 4 |
| sparse_infill_density | 10% |
| sparse_infill_pattern | grid |
| enable_support | 0 |
| print_speed | 150 |
| outer_wall_speed | 80 |
| ironing | 1 (for flat top surfaces) |

- **Note:** Fine layers give smooth surfaces but increase print time significantly. Good for figurines, vases, display items.
- **Ironing:** Enable for models with large flat top surfaces -- produces ultra-smooth finish at the cost of print time.
- **BambuStudio equivalent:** Similar to "0.12mm Detail" preset
- **Generic slicer:** PrusaSlicer "0.12mm DETAIL"

### Functional / Mechanical

Standard layers with strong walls and infill. Built to handle stress and repeated use.

| Parameter | Value |
|-----------|-------|
| layer_height | 0.2 |
| initial_layer_print_height | 0.2 |
| wall_loops | 3 |
| top_shell_layers | 4 |
| bottom_shell_layers | 4 |
| sparse_infill_density | 30% |
| sparse_infill_pattern | cubic |
| enable_support | 0 |
| print_speed | 200 |
| outer_wall_speed | 150 |
| extrusion_width | 0.45 (wider = stronger) |

- **Note:** 3 walls and 30% cubic infill provide good all-around strength. Suitable for brackets, mounts, enclosures, gears.
- **Key insight (CNC Kitchen):** More wall perimeters contribute more to strength than increasing infill density. 4 walls + 15% infill > 2 walls + 50% infill.
- **Wider extrusion:** 0.45-0.5mm on a 0.4mm nozzle produces stronger parts (better layer bonding from more squish).
- **BambuStudio equivalent:** Similar to "0.20mm Standard" preset with increased walls
- **Generic slicer:** PrusaSlicer "0.20mm QUALITY" with 3 perimeters

### Quick Prototype / Test Fit

Thick layers, minimal infill, maximum speed. For checking dimensions and fit before committing to a quality print.

| Parameter | Value |
|-----------|-------|
| layer_height | 0.28 |
| initial_layer_print_height | 0.28 |
| wall_loops | 2 |
| top_shell_layers | 3 |
| bottom_shell_layers | 3 |
| sparse_infill_density | 10% |
| sparse_infill_pattern | line |
| enable_support | 0 |
| print_speed | 300 |
| outer_wall_speed | 200 |

- **Note:** Fastest possible print. Surface quality is rough but dimensional accuracy is acceptable for fit checks.
- **Adaptive layer height:** Consider using adaptive layers instead -- thick on flat sections, thin on curves. Best speed/quality balance.
- **BambuStudio equivalent:** Similar to "0.28mm Extra Draft" preset
- **Generic slicer:** PrusaSlicer "0.30mm DRAFT"

### Storage / Container

Balanced settings for boxes, bins, organizers. Moderate speed with enough structure to hold items.

| Parameter | Value |
|-----------|-------|
| layer_height | 0.2 |
| initial_layer_print_height | 0.2 |
| wall_loops | 3 |
| top_shell_layers | 4 |
| bottom_shell_layers | 4 |
| sparse_infill_density | 15% |
| sparse_infill_pattern | grid |
| enable_support | 0 |
| print_speed | 250 |
| outer_wall_speed | 150 |

- **Note:** 3 walls provide rigidity for containers. Low infill is fine since containers are mostly hollow anyway.
- **BambuStudio equivalent:** Similar to "0.20mm Standard" preset
- **Generic slicer:** PrusaSlicer "0.20mm QUALITY"

### Flexible / TPU

Slower speed is critical for TPU to prevent extrusion issues. Thicker walls for durability.

| Parameter | Value |
|-----------|-------|
| layer_height | 0.2 |
| initial_layer_print_height | 0.2 |
| wall_loops | 3 |
| top_shell_layers | 4 |
| bottom_shell_layers | 4 |
| sparse_infill_density | 20% |
| sparse_infill_pattern | grid |
| enable_support | 0 |
| print_speed | 80 |
| outer_wall_speed | 40 |

- **Note:** Slow speed is not optional for TPU -- faster speeds cause jams and poor layer adhesion. Direct drive extruders handle TPU better than Bowden.
- **BambuStudio equivalent:** Similar to "0.20mm Standard" with speed reduced to 80mm/s
- **Generic slicer:** PrusaSlicer "0.20mm QUALITY" with speed overrides

### Structural / Load-Bearing

Maximum strength for parts that bear weight or mechanical load. More walls and high infill.

| Parameter | Value |
|-----------|-------|
| layer_height | 0.2 |
| initial_layer_print_height | 0.2 |
| wall_loops | 4 |
| top_shell_layers | 5 |
| bottom_shell_layers | 5 |
| sparse_infill_density | 40% |
| sparse_infill_pattern | gyroid |
| enable_support | 0 |
| print_speed | 200 |
| outer_wall_speed | 150 |
| extrusion_width | 0.5 (wider = stronger) |

- **Note:** 4 walls + 40% gyroid infill gives excellent strength in all directions. Gyroid is preferred over grid/cubic for structural parts due to uniform load distribution.
- **Cooling tradeoff (CNC Kitchen):** Reducing fan speed actually improves layer adhesion strength (layers melt together better). For maximum strength, use 40-60% fan instead of 100%. Trade-off: overhang quality suffers.
- **BambuStudio equivalent:** Similar to "0.20mm Standard" with 4 walls and 40% gyroid
- **Generic slicer:** PrusaSlicer "0.20mm STRUCTURAL" (custom)

### PLA on Bambu A1

Optimized settings for standard PLA on the Bambu A1 (direct drive, high speed capable).

| Parameter | Value |
|-----------|-------|
| nozzle_temperature | 220 |
| bed_temperature | 60 |
| max_volumetric_speed | 18-21 (21 for Bambu/high-speed PLA, 15-18 for generic) |
| flow_ratio | 0.98 |
| cooling_fan_speed | 100% |
| layer_height | 0.2 |
| initial_layer_print_height | 0.2 |
| wall_loops | 3 |
| top_shell_layers | 4 |
| bottom_shell_layers | 4 |
| sparse_infill_density | 20% |
| sparse_infill_pattern | gyroid |
| outer_wall_speed | 200 (100 for showroom quality) |
| inner_wall_speed | 300 |
| sparse_infill_speed | 250-300 |
| initial_layer_speed | 30-50 |
| enable_support | 0 |
| wall_order | Inner/Outer |

- **Note:** Avoid grid infill pattern at high speeds -- nozzle clicks against grid lines, shaking the A1's bed and causing layer shifts. Use gyroid or crosshatch instead.
- **First layer:** Always keep slow (30-50 mm/s) to ensure proper adhesion.
- **BambuStudio equivalent:** "0.20mm Standard" with speed tuned for A1

### PLA Metal on Bambu A1

Metallic PLA requires slower, consistent outer wall speed for uniform shine. Speed changes cause visible finish variation.

| Parameter | Value |
|-----------|-------|
| nozzle_temperature | 230 |
| bed_temperature | 60 |
| max_volumetric_speed | 8-10 |
| flow_ratio | 0.98 |
| retraction_length | 0.8 |
| retraction_speed | 40 |
| travel_speed | 300 |
| wipe | 1 |
| layer_height | 0.2 |
| initial_layer_print_height | 0.2 |
| wall_loops | 3-4 |
| top_shell_layers | 4 |
| bottom_shell_layers | 4 |
| sparse_infill_density | 20% |
| sparse_infill_pattern | gyroid |
| outer_wall_speed | 40-60 |
| inner_wall_speed | 120-150 |
| small_perimeter_speed | 50% of outer wall |
| sparse_infill_speed | 150-200 |
| initial_layer_speed | 30-50 |
| enable_support | 0 |
| wall_order | Inner/Outer |

- **Key principle:** Consistent speed = consistent metallic shine. High outer wall speeds (200+) make metallic PLA look matte/dull.
- **Metallic PLA is more brittle** -- 3-4 wall loops recommended for strength.
- **BambuStudio equivalent:** Custom profile based on "0.20mm Standard" with reduced outer wall speed

## Section 2: Geometry-Based Adjustments

These modifications are applied ON TOP of the purpose-based profile after analyzing the model geometry. Multiple adjustments can stack.

| Geometry Condition | Adjustment | Reason |
|--------------------|------------|--------|
| Overhangs > 45 degrees | enable_support = 1, support_type = normal(auto) | Unsupported angles above 45 degrees will sag or fail |
| Thin walls < 2mm | wall_loops += 1 | Extra perimeters reinforce thin sections |
| Bridge spans > 20mm | bridge_flow = 0.85, bridge_speed = 25 | Less material + slower = less sag on bridges |
| Large flat top surfaces | top_shell_layers += 1, ironing = 1 | Prevents pillow effect; ironing smooths the top |
| Small detailed features (< 2mm) | layer_height = min(layer_height, 0.16) | Finer layers resolve small details more accurately |
| Tall thin structures (height > 5x base width) | sparse_infill_density += 10% | Additional infill prevents wobble and resonance artifacts |
| Horizontal holes | Note: use teardrop profile in model | Standard circles sag at the top; teardrop is self-supporting |
| Large flat first layer | initial_layer_flow = 1.05-1.10 | Extra squish for first layer adhesion |

### Support Type Selection

| Geometry | Support Type | Why |
|----------|-------------|-----|
| Simple overhangs, flat surfaces | Normal (grid) | More stable, predictable |
| Complex organic shapes, internal cavities | Tree supports | 20-40% less filament, easier removal |
| Decorative/cosmetic surfaces | Tree supports | Minimal contact marks |
| Heavy/functional parts with large overhangs | Normal with interface layers | Better stability under weight |

Always use 2-3 **support interface layers** for cleaner contact surfaces regardless of support type.

### Overhang Thresholds
- **< 45 degrees from vertical**: No supports needed
- **45-60 degrees**: Works but surface quality degrades; supports help
- **> 60 degrees**: Almost always needs supports
- **Slicer auto-detect angle**: Set to 55-60 degrees

## Section 3: First Layer Optimization

The first layer is the foundation. Get it right or the whole print fails.

| Parameter | Value | Notes |
|-----------|-------|-------|
| First layer height | 0.2-0.3mm | Thicker than subsequent layers |
| First layer width | 120-150% of nozzle | Wider for adhesion |
| First layer speed | 15-30 mm/s | Slow for accuracy |
| First layer flow | 105-110% | Extra squish |
| First layer bed temp | +5-10C above normal | Extra adhesion (lower after first layer) |

**Bed cleaning:**
- Textured PEI: warm water + dish soap, then IPA 91%+ between prints
- **Never use acetone on textured PEI** -- damages the surface
- Never touch the bed after cleaning (fingerprint oils kill adhesion)
- For PETG on PEI: use glue stick as **release agent**

## Section 4: Infill Pattern Selection

| Pattern | Best For | Strength | Speed | Material |
|---------|----------|----------|-------|----------|
| **Gyroid** | General purpose, best all-rounder | Near-isotropic, excellent shear | Fast | Efficient |
| **Cubic** | Compression resistance | Uniform from all sides | Fast | Moderate |
| **Honeycomb** | Maximum strength functional parts | Excellent load distribution | Slower | Moderate |
| **Triangular** | End-use parts, max strength | Very strong in compression | Moderate | Higher |
| **Lightning** | Non-structural, decorative | Only supports top surfaces | Very fast | Very low |
| **Lines/Zigzag** | Speed priority, low-stress | Weak | Fastest | Lowest |

**Recommendations:**
- Default: Gyroid 15-20%
- Functional: Gyroid or cubic 15-25%
- End-use/structural: Honeycomb or triangular 30-50%
- Decorative: Lightning 10-15%
- **Avoid grid at high speeds on bed-slinger printers** (A1, Prusa MK3/4) -- nozzle impacts cause vibration

## Section 5: BambuStudio INI Parameter Reference

Complete list of verified Slic3r/BambuStudio parameter names for the print profile config file. Use these exact names when writing config files.

### Quality

| Parameter | Type | Description |
|-----------|------|-------------|
| layer_height | float (mm) | Layer height for all layers except the first |
| initial_layer_print_height | float (mm) | First layer height (usually 0.2mm regardless of other layers) |

### Walls

| Parameter | Type | Description |
|-----------|------|-------------|
| wall_loops | int | Number of perimeter walls |

### Top/Bottom

| Parameter | Type | Description |
|-----------|------|-------------|
| top_shell_layers | int | Number of solid top layers |
| bottom_shell_layers | int | Number of solid bottom layers |
| ironing_type | string | Ironing mode: no_ironing, top_surface, topmost_surface, all_solid |

### Infill

| Parameter | Type | Description |
|-----------|------|-------------|
| sparse_infill_density | int (%) | Infill density percentage |
| sparse_infill_pattern | string | Pattern: grid, triangles, cubic, gyroid, honeycomb, line, rectilinear |

### Support

| Parameter | Type | Description |
|-----------|------|-------------|
| enable_support | bool (0/1) | Enable support structures |
| support_type | string | Type: normal(auto), tree(auto), normal(manual), tree(manual) |
| support_interface_top_layers | int | Number of interface layers between support and model |

### Speed

| Parameter | Type | Description |
|-----------|------|-------------|
| print_speed | int (mm/s) | Default print speed |
| outer_wall_speed | int (mm/s) | Outer perimeter speed (lower = smoother surfaces) |
| inner_wall_speed | int (mm/s) | Inner perimeter speed |
| sparse_infill_speed | int (mm/s) | Infill speed |
| top_surface_speed | int (mm/s) | Top surface speed (lower = smoother top) |
| bridge_speed | int (mm/s) | Bridge speed (slower = less sag) |
| initial_layer_speed | int (mm/s) | First layer speed |

### Flow

| Parameter | Type | Description |
|-----------|------|-------------|
| flow_ratio | float | Flow multiplier (0.98 typical) |
| bridge_flow | float | Bridge flow ratio (0.8-0.9 for less sag) |
| initial_layer_flow_ratio | float | First layer flow (1.0-1.1) |

### Temperature

| Parameter | Type | Description |
|-----------|------|-------------|
| nozzle_temperature | int (C) | Nozzle temperature |
| bed_temperature | int (C) | Bed temperature |

**Note on temperature:** Temperature settings are typically controlled by BambuStudio's filament profile and are automatically set when the user selects a filament. Only include temperature parameters in the config if the user has a specific need or has explicitly mentioned a material/temperature requirement. In most cases, omit these and let the filament profile handle it.
