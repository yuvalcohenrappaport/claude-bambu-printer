"""Headless Blender mesh audit script.

Run via: blender --background --python audit.py -- <input_file> <output_json>

Imports the mesh file, runs checks, writes a JSON report to <output_json>,
and prints `BLENDER_OK <output_json>` to stdout on success.

Checks:
  - non_manifold_edges: count of edges with != 2 linked faces
  - triangle_count: total triangles after triangulation
  - dimensions_mm: [x, y, z] bounding box in millimeters
  - flipped_normals: best-effort count of faces with inverted normals
  - issues: list of human-readable problem descriptions
"""

import json
import sys
from pathlib import Path

import bpy
import bmesh


def parse_args():
    """Extract args passed after `--` on the blender CLI."""
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender -b -P audit.py -- <input> <output_json>")
    idx = sys.argv.index("--")
    args = sys.argv[idx + 1 :]
    if len(args) < 2:
        raise SystemExit("Usage: ... -- <input> <output_json>")
    return args[0], args[1]


def reset_scene():
    """Clear default scene and all data blocks."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for item in list(coll):
            coll.remove(item)


def set_mm_units():
    """Switch scene to 1 unit = 1 mm."""
    u = bpy.context.scene.unit_settings
    u.system = "METRIC"
    u.scale_length = 0.001


def import_mesh_file(filepath: str):
    """Dispatch to the right importer based on extension."""
    ext = filepath.lower().rsplit(".", 1)[-1]
    if ext == "stl":
        # Blender 5.1 operator
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
        # 3MF import is version-dependent; try several known operator names
        importers = [
            lambda: bpy.ops.import_mesh.threemf(filepath=filepath),
            lambda: bpy.ops.wm.threemf_import(filepath=filepath),
        ]
        last_err = None
        for fn in importers:
            try:
                fn()
                break
            except AttributeError as e:
                last_err = e
                continue
        else:
            raise RuntimeError(
                f"No 3MF import operator available in this Blender. "
                f"Last error: {last_err}"
            )
    else:
        raise ValueError(f"Unsupported format: .{ext}")


def join_mesh_objects():
    """If multiple mesh objects were imported, join them into one."""
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh objects found after import")
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def count_flipped_normals(bm: bmesh.types.BMesh) -> int:
    """Count faces whose normal was flipped when recalculated-outside was applied.

    Strategy: record pre-recalc normals, run recalc, compare dot-products.
    """
    pre_normals = [f.normal.copy() for f in bm.faces]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    flipped = 0
    for f, pre in zip(bm.faces, pre_normals):
        if f.normal.dot(pre) < 0:
            flipped += 1
    return flipped


def audit(filepath: str) -> dict:
    reset_scene()
    set_mm_units()
    import_mesh_file(filepath)

    # Ensure we're in OBJECT mode BEFORE any operator that requires it
    # (join, origin_set, etc.). reset_scene + import usually leaves us in
    # OBJECT mode, but defense-in-depth here is cheap.
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    obj = join_mesh_objects()

    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)

        # Count flipped normals BEFORE triangulation (triangulation can split
        # quads and change which faces "own" a normal).
        flipped_normals = count_flipped_normals(bm)

        bmesh.ops.triangulate(bm, faces=bm.faces)

        non_manifold_edges = sum(1 for e in bm.edges if len(e.link_faces) != 2)
        triangle_count = len(bm.faces)
    finally:
        bm.free()

    # obj.dimensions is in scene units (mm, since we set scale_length = 0.001
    # AND the STL importer reads the file's raw numbers as units — so a 20mm
    # cube in the STL becomes 20 Blender-units, which is 20mm after scale).
    dims = [round(obj.dimensions[i], 3) for i in range(3)]

    issues = []
    if non_manifold_edges > 0:
        issues.append(f"{non_manifold_edges} non-manifold edges")
    if flipped_normals > 0:
        issues.append(f"{flipped_normals} flipped normals")
    if triangle_count > 500_000:
        issues.append(f"high triangle count ({triangle_count}) — slicer may be slow")

    return {
        "file": filepath,
        "dimensions_mm": dims,
        "triangle_count": triangle_count,
        "non_manifold_edges": non_manifold_edges,
        "flipped_normals": flipped_normals,
        "issues": issues,
    }


def main():
    input_file, output_json = parse_args()
    try:
        result = audit(input_file)
    except Exception as e:
        # Any exception: write error JSON and exit non-zero.
        err_result = {"file": input_file, "error": str(e)}
        Path(output_json).write_text(json.dumps(err_result, indent=2))
        print(f"BLENDER_ERROR {e}", file=sys.stderr)
        sys.exit(1)

    Path(output_json).write_text(json.dumps(result, indent=2))
    print(f"BLENDER_OK {output_json}")


if __name__ == "__main__":
    main()
