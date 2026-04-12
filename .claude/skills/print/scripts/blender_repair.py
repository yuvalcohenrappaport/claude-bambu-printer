#!/usr/bin/env python3
"""Mesh repair orchestrator for the /print skill.

Usage: blender_repair.py <input_file>

Backs up the input file as `<input>.original` (only if no backup exists yet),
then runs scripts/bpy/repair.py against the file in place.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
BPY_REPAIR = SCRIPT_DIR / "bpy" / "repair.py"

sys.path.insert(0, str(SCRIPT_DIR))
import blender_bridge  # noqa: E402


def backup_original(filepath: str) -> str:
    """Copy `filepath` to `<filepath>.original` if no backup exists. Return backup path.

    Invariant: the backup is the FIRST-EVER version of the file. Subsequent
    repair runs on the same file do NOT overwrite the existing backup, so
    the user can always restore the pre-repair state even after multiple
    repair iterations. This function is not concurrency-safe — two processes
    writing the same backup simultaneously would race, but the skill has no
    concurrent invocation path.
    """
    backup = f"{filepath}.original"
    if not os.path.exists(backup):
        shutil.copy2(filepath, backup)
    return backup


def repair_file(filepath: str) -> dict:
    if not os.path.isfile(filepath):
        return {"status": "error", "error": f"Input file not found: {filepath}"}

    backup = backup_original(filepath)

    try:
        run = blender_bridge.run_bpy_script(str(BPY_REPAIR), [filepath], timeout=120)
    except (blender_bridge.BlenderNotFoundError, FileNotFoundError) as e:
        return {"status": "error", "error": str(e), "backup": backup}

    if run.returncode != 0:
        return {
            "status": "error",
            "error": run.stderr.strip() or f"Blender exited {run.returncode}",
            "backup": backup,
        }

    return {
        "status": "ok",
        "file": filepath,
        "backup": backup,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Repair a 3D mesh file in place")
    parser.add_argument("input", help="Path to .stl or .obj file")
    args = parser.parse_args(argv)

    result = repair_file(args.input)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
