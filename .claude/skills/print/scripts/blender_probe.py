#!/usr/bin/env python3
"""Probe & cache the Blender 3MF export operator name.

Usage: blender_probe.py [--force]

Stores the result at ~/.claude/skills/print/.blender-3mf-op.txt so other
scripts can read it without re-running Blender.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
BPY_PROBE = SCRIPT_DIR / "bpy" / "probe_3mf.py"
CACHE_PATH = os.path.expanduser("~/.claude/skills/print/.blender-3mf-op.txt")

sys.path.insert(0, str(SCRIPT_DIR))
import blender_bridge  # noqa: E402


def get_cached_operator() -> Optional[str]:
    """Return the cached operator name, or None if no cache exists."""
    if not os.path.isfile(CACHE_PATH):
        return None
    content = Path(CACHE_PATH).read_text().strip()
    return None if content == "NONE" else content


def probe() -> dict:
    """Run the bpy probe script and update the cache."""
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    try:
        run = blender_bridge.run_bpy_script(str(BPY_PROBE), [CACHE_PATH])
    except (blender_bridge.BlenderNotFoundError, FileNotFoundError) as e:
        return {"status": "error", "error": str(e)}

    if run.returncode != 0:
        return {
            "status": "error",
            "error": run.stderr.strip() or f"probe exited {run.returncode}",
        }

    content = Path(CACHE_PATH).read_text().strip()
    if content == "NONE":
        return {
            "status": "ok",
            "operator": None,
            "fallback": "Export as STL via bpy.ops.wm.stl_export and convert externally",
        }
    return {"status": "ok", "operator": content}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Re-probe even if cache exists")
    args = parser.parse_args(argv)

    if not args.force:
        cached = get_cached_operator()
        if cached:
            print(json.dumps({"status": "ok", "operator": cached, "from_cache": True}))
            return 0

    result = probe()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
