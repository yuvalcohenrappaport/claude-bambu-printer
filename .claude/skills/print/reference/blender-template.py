"""Blender generation template — copied and filled in for organic models.

Usage: blender --background --python model.py -- <output_3mf_path>

Replace the PARAMETERS block and the build_model() function with your shape.
Keeps the same parametric discipline as OpenSCAD model.scad files.

This template demonstrates a lofted vase — a shape expressible only with
organic lofting, not OpenSCAD cylinders. The solidify modifier adds wall
thickness so the print has an interior cavity.
"""

import math
import sys
from pathlib import Path

import bpy
import bmesh


# ---- PARAMETERS ----
OBJECT_NAME = "example_vase"
MATERIAL = "PLA"
WALL = 1.2    # mm — wall thickness via solidify modifier
HEIGHT = 120.0
BASE_RADIUS = 30.0
TOP_RADIUS = 45.0
# --------------------


def parse_args():
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender --background --python model.py -- <output_3mf>")
    args = sys.argv[sys.argv.index("--") + 1 :]
    if not args:
        raise SystemExit("Usage: blender --background --python model.py -- <output_3mf>")
    return args[0]


def reset_scene():
    """Clear the default scene — every one-shot script must start clean."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(coll):
            coll.remove(item)


def set_mm_units():
    """Set scene units to mm so dimensions in build_model() match real mm."""
    u = bpy.context.scene.unit_settings
    u.system = "METRIC"
    u.scale_length = 0.001


def build_model():
    """Construct the mesh. Replace this entire function with your shape.

    Returns the created Blender object (must be active + selected for export).
    """
    # Example: lofted vase via bmesh
    bm = bmesh.new()
    n_rings = 16
    n_segments = 32
    rings = []
    for i in range(n_rings):
        t = i / (n_rings - 1)
        z = t * HEIGHT
        # Radius with a sinusoidal bulge in the middle
        r = BASE_RADIUS + (TOP_RADIUS - BASE_RADIUS) * t + 3.0 * math.sin(t * math.pi * 2)
        ring = []
        for j in range(n_segments):
            theta = j * 2 * math.pi / n_segments
            v = bm.verts.new((r * math.cos(theta), r * math.sin(theta), z))
            ring.append(v)
        rings.append(ring)

    # Side faces — quad strips between rings
    for i in range(n_rings - 1):
        for j in range(n_segments):
            a = rings[i][j]
            b = rings[i][(j + 1) % n_segments]
            c = rings[i + 1][(j + 1) % n_segments]
            d = rings[i + 1][j]
            bm.faces.new([a, b, c, d])

    # Bottom cap
    bm.faces.new(list(reversed(rings[0])))

    me = bpy.data.meshes.new(OBJECT_NAME)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(OBJECT_NAME, me)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Solidify modifier adds wall thickness (creates interior cavity for a vase)
    mod = obj.modifiers.new("solidify", "SOLIDIFY")
    mod.thickness = WALL
    mod.offset = -1  # inward
    bpy.ops.object.modifier_apply(modifier="solidify")

    return obj


def export_3mf_or_stl(obj, output_path: str) -> str:
    """Export the selected object to 3MF, falling back to STL if unavailable.

    Reads the operator name from the cache written by blender_probe.py.
    Returns the actual output path (may differ if STL fallback is used).
    """
    # Read cached operator name written by blender_probe.py
    cache = Path.home() / ".claude/skills/print/.blender-3mf-op.txt"
    op_path = None
    if cache.is_file():
        content = cache.read_text().strip()
        if content and content != "NONE":
            op_path = content

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    if op_path:
        # Walk the operator path: "bpy.ops.wm.threemf_export" → bpy.ops.wm.threemf_export
        try:
            parts = op_path.split(".")[1:]  # drop leading "bpy"
            op = bpy
            for p in parts:
                op = getattr(op, p)
            op(filepath=output_path)
            return output_path
        except (AttributeError, RuntimeError) as e:
            # Operator resolves at attribute level but may not be callable at runtime
            print(f"NOTE: 3MF operator {op_path!r} failed ({e}), falling back to STL",
                  file=sys.stderr)

    # Fallback: export STL next to the requested 3MF path
    stl_path = output_path.rsplit(".", 1)[0] + ".stl"
    try:
        bpy.ops.wm.stl_export(filepath=stl_path)
    except AttributeError:
        bpy.ops.export_mesh.stl(filepath=stl_path, use_selection=True)
    print(
        f"NOTE: 3MF operator not available, exported STL instead: {stl_path}",
        file=sys.stderr,
    )
    return stl_path


def main():
    output = parse_args()
    try:
        reset_scene()
        set_mm_units()
        obj = build_model()
        actual_output = export_3mf_or_stl(obj, output)
    except Exception as e:
        print(f"BLENDER_ERROR {e}", file=sys.stderr)
        sys.exit(1)

    print(f"BLENDER_OK {actual_output}")


if __name__ == "__main__":
    main()
