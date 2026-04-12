"""Headless Blender mesh repair script.

Run via: blender --background --python repair.py -- <input_file>

Imports the mesh, runs a sequence of cleanup operations, and writes the
repaired result back to <input_file> in the same format.

Operations:
  1. Merge by distance (threshold 0.001mm) — remove duplicate verts
  2. Recalculate normals outside — fix flipped normals
  3. Fill holes (max edges 4) — close small gaps that cause non-manifold
  4. Delete loose geometry — isolated verts/edges that aren't part of any face

The caller is responsible for backing up the original file before invoking
this script.
"""

import sys
from pathlib import Path

import bpy
import bmesh


def parse_args():
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender -b -P repair.py -- <input_file>")
    idx = sys.argv.index("--")
    args = sys.argv[idx + 1 :]
    if len(args) < 1:
        raise SystemExit("Usage: ... -- <input_file>")
    return args[0]


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
            raise RuntimeError("3MF import not available — convert to STL first")
    else:
        raise ValueError(f"Unsupported format: .{ext}")


def export_mesh(filepath: str):
    ext = filepath.lower().rsplit(".", 1)[-1]
    # Select the mesh object(s)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]

    if ext == "stl":
        try:
            bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=True)
        except AttributeError:
            bpy.ops.export_mesh.stl(filepath=filepath, use_selection=True)
    elif ext == "obj":
        try:
            bpy.ops.wm.obj_export(filepath=filepath, export_selected_objects=True)
        except AttributeError:
            bpy.ops.export_scene.obj(filepath=filepath, use_selection=True)
    elif ext == "3mf":
        # version-dependent — fail loudly rather than silently corrupting
        raise RuntimeError("3MF export for repaired files not supported yet — STL only")
    else:
        raise ValueError(f"Unsupported format: .{ext}")


def join_mesh_objects():
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh to repair")
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def repair_mesh(obj):
    """Apply the repair operations in order. Must be called in object mode."""
    # Enter edit mode to use mesh operators
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")

    # 1. Merge by distance (threshold 1 micrometer in scene units)
    bpy.ops.mesh.remove_doubles(threshold=0.001)

    # 2. Recalculate normals outside
    bpy.ops.mesh.normals_make_consistent(inside=False)

    # 3. Fill holes (max 4-edge holes)
    bpy.ops.mesh.fill_holes(sides=4)

    # 4. Delete loose geometry (verts/edges not part of any face)
    bpy.ops.mesh.delete_loose()

    bpy.ops.object.mode_set(mode="OBJECT")


def main():
    filepath = parse_args()
    try:
        reset_scene()
        import_mesh(filepath)
        obj = join_mesh_objects()
        repair_mesh(obj)
        export_mesh(filepath)
    except Exception as e:
        print(f"BLENDER_ERROR {e}", file=sys.stderr)
        sys.exit(1)
    print(f"BLENDER_OK {filepath}")


if __name__ == "__main__":
    main()
