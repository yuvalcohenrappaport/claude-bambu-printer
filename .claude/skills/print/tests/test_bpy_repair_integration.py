"""Integration test: repair a non-manifold cube and verify it becomes manifold."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
BPY_REPAIR = ROOT / "scripts" / "bpy" / "repair.py"
BPY_AUDIT = ROOT / "scripts" / "bpy" / "audit.py"
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"

if not Path(BLENDER).exists():
    pytest.skip("Blender not found at expected path", allow_module_level=True)


def run_bpy(script: Path, *args) -> subprocess.CompletedProcess:
    cmd = [BLENDER, "--background", "--factory-startup", "--python", str(script), "--", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


@pytest.mark.integration
def test_repair_closes_non_manifold_cube(tmp_path):
    # Copy fixture so we don't mutate the checked-in file
    work = tmp_path / "non_manifold.stl"
    shutil.copy(FIXTURES / "non_manifold.stl", work)

    # Pre-audit: should find non-manifold edges
    audit_out = tmp_path / "pre.json"
    proc = run_bpy(BPY_AUDIT, str(work), str(audit_out))
    assert proc.returncode == 0, f"pre-audit failed: {proc.stderr}"
    pre = json.loads(audit_out.read_text())
    assert pre["non_manifold_edges"] > 0

    # Run repair
    proc = run_bpy(BPY_REPAIR, str(work))
    assert proc.returncode == 0, f"repair failed: {proc.stderr}"
    assert "BLENDER_OK" in proc.stdout

    # Post-audit: should be manifold
    post_out = tmp_path / "post.json"
    proc = run_bpy(BPY_AUDIT, str(work), str(post_out))
    assert proc.returncode == 0, f"post-audit failed: {proc.stderr}"
    post = json.loads(post_out.read_text())
    assert post["non_manifold_edges"] == 0, f"still non-manifold: {post}"
