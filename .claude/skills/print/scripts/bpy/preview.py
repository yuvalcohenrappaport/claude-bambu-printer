"""Fast matte preview render — NOT the hero render.

Run via: blender --background --python preview.py -- <input_mesh> <output_png>

Goal: a 3-5 second shape-check render that replaces the OpenSCAD DeepOcean PNG
for Blender-generated models. Minimal lighting (1 sun lamp), default camera,
800x600 Eevee.
"""

import math
import sys
from pathlib import Path

import bpy


def parse_args():
    if "--" not in sys.argv:
        raise SystemExit("Usage: ... -- <input> <output>")
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) < 2:
        raise SystemExit("Usage: ... -- <input> <output>")
    return args[0], args[1]


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(coll):
            coll.remove(item)


def import_mesh(filepath: str):
    ext = filepath.lower().rsplit(".", 1)[-1]
    if ext == "stl":
        try:
            bpy.ops.wm.stl_import(filepath=filepath)
        except AttributeError:
            bpy.ops.import_mesh.stl(filepath=filepath)
    elif ext == "3mf":
        try:
            bpy.ops.import_mesh.threemf(filepath=filepath)
        except AttributeError:
            raise RuntimeError("3MF import unavailable")
    else:
        raise ValueError(f"Unsupported: .{ext}")


def _eevee_engine_name() -> str:
    """Return the correct Eevee engine identifier for the running Blender version."""
    scene = bpy.context.scene
    try:
        items = scene.bl_rna.properties["render"].fixed_type.bl_rna.properties["engine"].enum_items
        ids = [e.identifier for e in items]
    except Exception:
        ids = []
    if "BLENDER_EEVEE_NEXT" in ids:
        return "BLENDER_EEVEE_NEXT"
    return "BLENDER_EEVEE"


def main():
    input_file, output_png = parse_args()
    try:
        reset_scene()
        import_mesh(input_file)

        # Join + center
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        if not meshes:
            raise RuntimeError("No mesh")
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.select_all(action="DESELECT")
        for m in meshes:
            m.select_set(True)
        if len(meshes) > 1:
            bpy.ops.object.join()
        obj = bpy.context.view_layer.objects.active
        bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_VOLUME")
        obj.location = (0, 0, 0)
        size = max(obj.dimensions) or 1.0

        # One sun lamp
        bpy.ops.object.light_add(type="SUN", location=(size, -size, size * 2))
        bpy.context.active_object.data.energy = 3.0

        # Camera
        import mathutils
        cam_loc = (size * 2, -size * 2, size * 1.5)
        bpy.ops.object.camera_add(location=cam_loc)
        cam = bpy.context.active_object
        cam.data.lens = 50
        direction = mathutils.Vector((0, 0, 0)) - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.camera = cam

        # Render settings — fast Eevee (detect engine name at runtime)
        scene = bpy.context.scene
        scene.render.engine = _eevee_engine_name()
        scene.render.resolution_x = 800
        scene.render.resolution_y = 600
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = output_png
        bpy.ops.render.render(write_still=True)
    except Exception as e:
        print(f"BLENDER_ERROR {e}", file=sys.stderr)
        sys.exit(1)

    if not Path(output_png).exists():
        print("BLENDER_ERROR no output file", file=sys.stderr)
        sys.exit(1)
    print(f"BLENDER_OK {output_png}")


if __name__ == "__main__":
    main()
