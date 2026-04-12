# Blender Guide for the /print Skill

This file is loaded by SKILL.md via `@reference/blender-guide.md`. Use it when generating `model.py` files for Blender-backed models, or when writing ad-hoc `bpy` scripts for audit / repair / render.

## Invocation

Blender is invoked in background mode exclusively:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
    --background \
    --factory-startup \
    --python <script.py> \
    -- <arg1> <arg2> ...
```

Args after `--` are passed to the script as `sys.argv[sys.argv.index("--") + 1:]`. Blender's own args (file to open, `--factory-startup`) come before `--`.

Prefer `--factory-startup` to ignore the user's preferences and get a clean environment.

## Unit scale gotcha

Blender's default unit scale is **1 unit = 1 meter**. 3D printing files use millimeters. Two options:

1. **Leave the scene at default and multiply dimensions**: a 120mm cube becomes a 0.120 Blender-unit cube. Less code, but mental-model friction.
2. **Set unit scale to 0.001 at the top of every script**:

```python
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 0.001
```

With option 2, you write dimensions in mm directly. **This plan uses option 2 everywhere** for consistency with OpenSCAD.

## Scene reset pattern

Every one-shot script starts by clearing the default scene so it's idempotent:

```python
import bpy

# Delete everything
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Also clear orphaned data
for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    for item in collection:
        collection.remove(item)
```

## Importing files

| Format | Operator | Notes |
|---|---|---|
| STL | `bpy.ops.wm.stl_import(filepath=...)` | Blender 4.0+ moved this from `import_mesh.stl` (available in 5.x as well) |
| OBJ | `bpy.ops.wm.obj_import(filepath=...)` | Blender 5.1 name |
| 3MF | Varies by Blender version — verified at runtime by `scripts/bpy/probe_3mf.py` | May require a bundled extension enable |

If a 3MF operator is unavailable, convert the 3MF to STL externally (e.g., `meshio`) or ask the user to export as STL from BambuStudio.

## Exporting 3MF

Blender 5.1 ships a 3MF exporter but the operator name has changed across versions. Use the probe script result (stored at `~/.claude/skills/print/.blender-3mf-op.txt` after Phase 4 Task 4.1 runs) rather than hardcoding. If the cache file does not exist (e.g., the probe hasn't run yet in Phase 1 or 2), treat the operator as unavailable and use the STL fallback below. Fallback: export STL via `bpy.ops.wm.stl_export(filepath=...)` and convert externally with `meshio` if a 3MF is strictly required.

## Organic shape patterns

### Loft (skin a series of curve cross-sections)

```python
import bpy, bmesh
from math import cos, sin, pi

# Prerequisite: ensure unit scale is set before this block — see "Unit scale gotcha" section above.
# Dimensions below (z, r) are written in mm and assume scale_length = 0.001 has been applied.

bm = bmesh.new()
# Create 8 rings stacked along Z, each a circle of varying radius
rings = []
for i in range(8):
    z = i * 10  # mm
    r = 20 + 5 * sin(i * pi / 7)  # mm
    ring = []
    for j in range(24):
        theta = j * 2 * pi / 24
        v = bm.verts.new((r * cos(theta), r * sin(theta), z))
        ring.append(v)
    rings.append(ring)

# Side faces: quads between consecutive rings
for i in range(len(rings) - 1):
    a, b = rings[i], rings[i + 1]
    for j in range(24):
        bm.faces.new([a[j], a[(j + 1) % 24], b[(j + 1) % 24], b[j]])

# Cap top and bottom with a fan triangulation (avoids n-gons, stays manifold)
def cap_ring(ring, reverse=False):
    cx = sum(v.co.x for v in ring) / len(ring)
    cy = sum(v.co.y for v in ring) / len(ring)
    cz = sum(v.co.z for v in ring) / len(ring)
    center = bm.verts.new((cx, cy, cz))
    for j in range(len(ring)):
        tri = [center, ring[j], ring[(j + 1) % len(ring)]]
        if reverse:
            tri.reverse()
        bm.faces.new(tri)

cap_ring(rings[0], reverse=True)   # bottom — normal points -Z
cap_ring(rings[-1], reverse=False) # top — normal points +Z

me = bpy.data.meshes.new("loft")
bm.to_mesh(me)
bm.free()
obj = bpy.data.objects.new("loft", me)
bpy.context.collection.objects.link(obj)
```

### Subdivision-surface for smoothness

```python
bpy.context.view_layer.objects.active = obj
mod = obj.modifiers.new("subsurf", 'SUBSURF')
mod.levels = 2
mod.render_levels = 3
bpy.ops.object.modifier_apply(modifier="subsurf")
```

### Boolean CSG (faster than OpenSCAD for complex meshes)

```python
bpy.context.view_layer.objects.active = obj
mod = obj.modifiers.new("bool", 'BOOLEAN')
mod.object = other_obj
mod.operation = 'DIFFERENCE'
bpy.ops.object.modifier_apply(modifier="bool")
bpy.data.objects.remove(other_obj, do_unlink=True)
```

### Bevel edges (fillets for organic transitions)

```python
bpy.context.view_layer.objects.active = obj
mod = obj.modifiers.new("bevel", 'BEVEL')
mod.width = 1.0  # mm (with unit scale 0.001)
mod.segments = 4
bpy.ops.object.modifier_apply(modifier="bevel")
```

## Common error patterns

| Error text | Cause | Fix |
|---|---|---|
| `AttributeError: Calling operator "bpy.ops.wm.stl_import" error, could not be found` | Old operator name | Use `bpy.ops.import_mesh.stl` on Blender <4.0 |
| `RuntimeError: Operator bpy.ops.object.modifier_apply.poll() failed, context is incorrect` | No active object | `bpy.context.view_layer.objects.active = obj` before calling |
| `bmesh: vertices ... share an edge` (when creating faces) | Duplicate vert | Use `bmesh.ops.remove_doubles` first |
| Script runs but produces no output file | Missing `-- <output>` arg | Check `sys.argv` parsing |
| Non-manifold after boolean | Coplanar faces | Offset one object by 0.001mm before boolean |

## Exit codes and stdout

`bpy` scripts should:
1. Print a machine-readable success marker as the last stdout line, e.g., `BLENDER_OK <output_path>`.
2. Print errors to stderr (not stdout).
3. Call `sys.exit(1)` on unrecoverable errors so the subprocess returns non-zero.

Orchestrators in `scripts/` parse stdout for the marker and fall back to the returncode for error detection.
