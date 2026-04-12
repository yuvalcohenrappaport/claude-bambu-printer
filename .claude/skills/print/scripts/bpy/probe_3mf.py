"""Probe which 3MF export operator is available in this Blender.

Writes the operator name (or the literal string "NONE") to <output_path>.
"""
import sys
from pathlib import Path

import bpy


CANDIDATES = [
    "bpy.ops.wm.threemf_export",
    "bpy.ops.export_mesh.threemf",
    "bpy.ops.export_scene.threemf",
]


def parse_args():
    if "--" not in sys.argv:
        raise SystemExit("Usage: ... -- <output_path>")
    idx = sys.argv.index("--")
    args = sys.argv[idx + 1:]
    if not args:
        raise SystemExit("Usage: ... -- <output_path>")
    return args[0]


def resolve_op(path: str):
    """Walk bpy.ops.<a>.<b> attribute chain; return True if callable, False otherwise."""
    parts = path.split(".")[1:]  # drop "bpy"
    obj = bpy
    for p in parts:
        obj = getattr(obj, p, None)
        if obj is None:
            return False
    return True


def main():
    output = parse_args()
    found = next((c for c in CANDIDATES if resolve_op(c)), None)
    Path(output).write_text(found if found else "NONE")
    print(f"BLENDER_OK {output}")


if __name__ == "__main__":
    main()
