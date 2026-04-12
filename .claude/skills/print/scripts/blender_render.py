#!/usr/bin/env python3
"""Hero-render orchestrator for the /print skill.

Usage: blender_render.py <input_mesh> [<output_png>]

If output_png is omitted, writes render.png next to the input file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
BPY_RENDER = SCRIPT_DIR / "bpy" / "render_hero.py"

sys.path.insert(0, str(SCRIPT_DIR))
import blender_bridge  # noqa: E402


def render_file(input_file: str, output_png: Optional[str] = None) -> dict:
    if not os.path.isfile(input_file):
        return {"status": "error", "error": f"Input file not found: {input_file}"}

    if output_png is None:
        output_png = str(Path(input_file).parent / "render.png")

    try:
        run = blender_bridge.run_bpy_script(
            str(BPY_RENDER),
            [input_file, output_png],
            timeout=180,
        )
    except (blender_bridge.BlenderNotFoundError, FileNotFoundError) as e:
        return {"status": "error", "error": str(e)}

    if run.returncode != 0:
        return {
            "status": "error",
            "error": run.stderr.strip() or f"Blender exited {run.returncode}",
        }

    return {"status": "ok", "output": output_png}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a photo-quality render of a 3D model")
    parser.add_argument("input", help="Path to .stl/.obj/.3mf file")
    parser.add_argument("output", nargs="?", default=None,
                        help="Output PNG path (default: <input_dir>/render.png)")
    args = parser.parse_args(argv)

    result = render_file(args.input, args.output)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
