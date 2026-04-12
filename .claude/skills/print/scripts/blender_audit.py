#!/usr/bin/env python3
"""Mesh audit orchestrator for the /print skill.

Usage: blender_audit.py <input_file>

Wraps scripts/bpy/audit.py. Parses Blender's JSON output and emits a
skill-friendly JSON report with a top-level status flag and `needs_repair`
boolean that the SKILL.md uses to decide whether to offer repair.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
BPY_AUDIT = SCRIPT_DIR / "bpy" / "audit.py"

sys.path.insert(0, str(SCRIPT_DIR))
import blender_bridge  # noqa: E402


def needs_repair(result: dict) -> bool:
    """Return True if the audit found fixable issues that warrant offering repair.

    Advisory-only issues (triangle count, bounding box, thin walls) do NOT
    count — those are informational and the file is still printable.
    """
    if result.get("non_manifold_edges", 0) > 0:
        return True
    if result.get("flipped_normals", 0) > 0:
        return True
    # self-intersection will be added in a future iteration
    return False


def audit_file(input_file: str) -> dict:
    """Run the bpy audit on a file. Returns a skill-ready JSON dict."""
    if not os.path.isfile(input_file):
        return {
            "status": "error",
            "error": f"Input file not found: {input_file}",
        }

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        output_json = tf.name

    try:
        try:
            run = blender_bridge.run_bpy_script(
                str(BPY_AUDIT),
                [input_file, output_json],
            )
        except (blender_bridge.BlenderNotFoundError, FileNotFoundError) as e:
            return {"status": "error", "error": str(e)}

        if not run.success:
            return {
                "status": "error",
                "error": run.stderr.strip() or f"Blender exited {run.returncode}",
            }
        result = run.load_json()
        return {
            "status": "ok",
            "result": result,
            "needs_repair": needs_repair(result),
        }
    finally:
        try:
            os.unlink(output_json)
        except OSError:
            pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a 3D mesh file for print readiness")
    parser.add_argument("input", help="Path to .stl, .obj, or .3mf file")
    args = parser.parse_args(argv)

    report = audit_file(args.input)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
