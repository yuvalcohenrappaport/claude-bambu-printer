"""Headless Blender hero-render script.

Run via: blender --background --python render_hero.py -- <input_mesh> <output_png>

Imports the mesh, centers it, adds a neutral ground plane, a 3-point light
rig, and a 35mm camera at 30° elevation, then renders with Eevee at 1280x960.

This is the OPT-IN photo-quality render. Step 5b (fast preview during
generation) uses a simpler render pass.
"""

import math
import sys
from pathlib import Path

import bpy


def parse_args():
    if "--" not in sys.argv:
        raise SystemExit("Usage: ... -- <input_mesh> <output_png>")
    idx = sys.argv.index("--")
    args = sys.argv[idx + 1 :]
    if len(args) < 2:
        raise SystemExit("Usage: ... -- <input_mesh> <output_png>")
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
    elif ext == "obj":
        try:
            bpy.ops.wm.obj_import(filepath=filepath)
        except AttributeError:
            bpy.ops.import_scene.obj(filepath=filepath)
    elif ext == "3mf":
        try:
            bpy.ops.import_mesh.threemf(filepath=filepath)
        except AttributeError:
            raise RuntimeError("3MF import not available — export as STL first")
    else:
        raise ValueError(f"Unsupported format: .{ext}")


def center_and_get_bbox():
    """Join all meshes, center at origin, return (bbox_size, bbox_center_z_offset)."""
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh to render")
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active

    # Set origin to bounding box center, then move origin to world origin
    bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_VOLUME")
    obj.location = (0, 0, 0)

    return obj, max(obj.dimensions)


def add_ground_plane(size: float):
    bpy.ops.mesh.primitive_plane_add(size=size * 10, location=(0, 0, -size / 2))
    plane = bpy.context.active_object
    mat = bpy.data.materials.new(name="ground")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.85, 0.85, 0.85, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.6
    plane.data.materials.append(mat)


def add_three_point_lights(size: float):
    # Key light (strong, front-right, above)
    bpy.ops.object.light_add(type="AREA", location=(size * 1.5, -size * 1.5, size * 2))
    key = bpy.context.active_object
    key.data.energy = 800
    key.data.size = size * 2
    key.rotation_euler = (math.radians(45), 0, math.radians(45))

    # Fill light (softer, front-left)
    bpy.ops.object.light_add(type="AREA", location=(-size * 1.5, -size * 1.5, size))
    fill = bpy.context.active_object
    fill.data.energy = 300
    fill.data.size = size * 3

    # Back light (rim, above-behind)
    bpy.ops.object.light_add(type="AREA", location=(0, size * 2, size * 2.5))
    rim = bpy.context.active_object
    rim.data.energy = 500
    rim.data.size = size * 1.5


def add_camera(size: float):
    # 35mm lens, 30° elevation, looking at origin
    distance = size * 3.0
    elevation = math.radians(30)
    bpy.ops.object.camera_add(
        location=(
            distance * math.cos(elevation) * 0.7,
            -distance * math.cos(elevation),
            distance * math.sin(elevation),
        )
    )
    cam = bpy.context.active_object
    cam.data.lens = 35
    # Point camera at origin: compute look-at rotation
    import mathutils
    direction = mathutils.Vector((0, 0, 0)) - cam.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    cam.rotation_euler = rot_quat.to_euler()
    bpy.context.scene.camera = cam


def setup_render(output_png: str):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in scene.bl_rna.properties["render"].fixed_type.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = output_png


def main():
    input_mesh, output_png = parse_args()
    try:
        reset_scene()
        import_mesh(input_mesh)
        obj, size = center_and_get_bbox()
        add_ground_plane(size)
        add_three_point_lights(size)
        add_camera(size)
        setup_render(output_png)
        bpy.ops.render.render(write_still=True)
    except Exception as e:
        print(f"BLENDER_ERROR {e}", file=sys.stderr)
        sys.exit(1)

    if not Path(output_png).exists():
        print(f"BLENDER_ERROR render completed but output missing: {output_png}", file=sys.stderr)
        sys.exit(1)

    print(f"BLENDER_OK {output_png}")


if __name__ == "__main__":
    main()
