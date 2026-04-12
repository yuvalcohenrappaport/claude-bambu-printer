"""Integration tests for bpy/audit.py — runs real Blender against fixture STLs.

Marked @pytest.mark.integration so they're opt-in: run with `pytest -m integration`.
Each test is ~5-15s because Blender startup is slow.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
BPY_AUDIT = ROOT / "scripts" / "bpy" / "audit.py"
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"

# Module-level skip if Blender isn't installed at the expected path.
# Integration tests spawn real Blender; without it they produce confusing
# subprocess errors rather than a clean skip.
if not Path(BLENDER).exists():
    pytest.skip(
        f"Blender not found at {BLENDER}; install via brew install --cask blender",
        allow_module_level=True,
    )


def run_audit(input_file: Path, output_json: Path) -> subprocess.CompletedProcess:
    cmd = [
        BLENDER,
        "--background",
        "--factory-startup",
        "--python",
        str(BPY_AUDIT),
        "--",
        str(input_file),
        str(output_json),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


@pytest.mark.integration
def test_audit_cube_is_manifold(tmp_path):
    out = tmp_path / "audit.json"
    proc = run_audit(FIXTURES / "cube.stl", out)
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert "BLENDER_OK" in proc.stdout

    result = json.loads(out.read_text())
    assert result["non_manifold_edges"] == 0
    assert result["triangle_count"] == 12
    # Cube is 20mm on a side
    dims = result["dimensions_mm"]
    assert all(abs(d - 20.0) < 0.01 for d in dims), f"dims: {dims}"
    assert result["issues"] == []


@pytest.mark.integration
def test_audit_non_manifold_flags_edges(tmp_path):
    out = tmp_path / "audit.json"
    proc = run_audit(FIXTURES / "non_manifold.stl", out)
    assert proc.returncode == 0

    result = json.loads(out.read_text())
    # Cube with top face removed → 4 edges now have only 1 linked face
    assert result["non_manifold_edges"] == 4
    assert result["triangle_count"] == 10
    assert any("non-manifold" in issue for issue in result["issues"])


@pytest.mark.integration
def test_audit_large_triangle_count_reported(tmp_path):
    out = tmp_path / "audit.json"
    proc = run_audit(FIXTURES / "large.stl", out)
    assert proc.returncode == 0

    result = json.loads(out.read_text())
    assert result["triangle_count"] == 12000  # 1000 cubes * 12 tris
