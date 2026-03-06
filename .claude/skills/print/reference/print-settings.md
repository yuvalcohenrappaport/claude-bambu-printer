# Print Settings Reference

Purpose-based print profiles, geometry-based adjustments, and BambuStudio parameter reference for the /print skill.

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

- **Note:** Fine layers give smooth surfaces but increase print time significantly. Good for figurines, vases, display items.
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

- **Note:** 3 walls and 30% cubic infill provide good all-around strength. Suitable for brackets, mounts, enclosures, gears.
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

- **Note:** 4 walls + 40% gyroid infill gives excellent strength in all directions. Gyroid is preferred over grid/cubic for structural parts due to uniform load distribution.
- **BambuStudio equivalent:** Similar to "0.20mm Standard" with 4 walls and 40% gyroid
- **Generic slicer:** PrusaSlicer "0.20mm STRUCTURAL" (custom)

## Section 2: Geometry-Based Adjustments

These modifications are applied ON TOP of the purpose-based profile after analyzing the model geometry. Multiple adjustments can stack.

| Geometry Condition | Adjustment | Reason |
|--------------------|------------|--------|
| Overhangs > 45 degrees | enable_support = 1, support_type = normal(auto) | Unsupported angles above 45 degrees will sag or fail |
| Thin walls < 2mm | wall_loops += 1 | Extra perimeters reinforce thin sections |
| Bridge spans > 20mm | Note: reduce bridge speed in slicer | Long bridges droop without speed reduction |
| Large flat top surfaces | top_shell_layers += 1 | Prevents pillow effect on wide flat tops |
| Small detailed features (< 2mm) | layer_height = min(layer_height, 0.16) | Finer layers resolve small details more accurately |
| Tall thin structures (height > 5x base width) | sparse_infill_density += 10% | Additional infill prevents wobble and resonance artifacts |

## Section 3: BambuStudio INI Parameter Reference

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

### Speed

| Parameter | Type | Description |
|-----------|------|-------------|
| print_speed | int (mm/s) | Default print speed |
| outer_wall_speed | int (mm/s) | Outer perimeter speed (lower = smoother surfaces) |
| inner_wall_speed | int (mm/s) | Inner perimeter speed |
| sparse_infill_speed | int (mm/s) | Infill speed |
| top_surface_speed | int (mm/s) | Top surface speed (lower = smoother top) |

### Temperature

| Parameter | Type | Description |
|-----------|------|-------------|
| nozzle_temperature | int (C) | Nozzle temperature |
| bed_temperature | int (C) | Bed temperature |

**Note on temperature:** Temperature settings are typically controlled by BambuStudio's filament profile and are automatically set when the user selects a filament. Only include temperature parameters in the config if the user has a specific need or has explicitly mentioned a material/temperature requirement. In most cases, omit these and let the filament profile handle it.
