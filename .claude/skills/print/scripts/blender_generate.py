#!/usr/bin/env python3
"""Blender generation orchestrator for the /print skill.

Subcommands:
  execute <model.py> <output.3mf>   — run a user bpy script, exporting a 3MF
  preview <mesh>     <preview.png>  — render a fast matte preview of a mesh

The 'execute' subcommand runs the user's model.py directly (it's a full bpy
script), passing the output 3MF path as the argument after --. The user script
is responsible for calling bpy.ops.{op}(filepath=...) itself, using the
operator name cached by blender_probe.py (read from the cache file).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
BPY_PREVIEW = SCRIPT_DIR / "bpy" / "preview.py"

sys.path.insert(0, str(SCRIPT_DIR))
import blender_bridge  # noqa: E402


def cmd_execute(script: str, output: str) -> dict:
    if not os.path.isfile(script):
        return {"status": "error", "error": f"Script not found: {script}"}

    # Ensure output directory exists
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    try:
        run = blender_bridge.run_bpy_script(script, [output], timeout=180)
    except (blender_bridge.BlenderNotFoundError, FileNotFoundError) as e:
        return {"status": "error", "error": str(e)}

    if run.returncode != 0:
        return {
            "status": "error",
            "error": run.stderr.strip() or f"Blender exited {run.returncode}",
        }
    # Accept whichever file was actually produced: the requested output path OR
    # the path emitted in BLENDER_OK (e.g., STL fallback from the template).
    actual = run.marker_path if (run.marker_path and os.path.isfile(run.marker_path)) else None
    if actual is None and os.path.isfile(output):
        actual = output
    if actual is None:
        return {
            "status": "error",
            "error": f"Script exited 0 but output file not created: {output}",
        }
    return {"status": "ok", "output": actual}


def cmd_preview(mesh: str, output: str) -> dict:
    if not os.path.isfile(mesh):
        return {"status": "error", "error": f"Mesh not found: {mesh}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    try:
        run = blender_bridge.run_bpy_script(
            str(BPY_PREVIEW),
            [mesh, output],
            timeout=60,
        )
    except (blender_bridge.BlenderNotFoundError, FileNotFoundError) as e:
        return {"status": "error", "error": str(e)}

    if run.returncode != 0:
        return {
            "status": "error",
            "error": run.stderr.strip() or f"Blender exited {run.returncode}",
        }
    return {"status": "ok", "output": output}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Blender generation orchestrator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("execute")
    ex.add_argument("script")
    ex.add_argument("output")

    pv = sub.add_parser("preview")
    pv.add_argument("mesh")
    pv.add_argument("output")

    args = parser.parse_args(argv)

    if args.cmd == "execute":
        result = cmd_execute(args.script, args.output)
    else:
        result = cmd_preview(args.mesh, args.output)

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
