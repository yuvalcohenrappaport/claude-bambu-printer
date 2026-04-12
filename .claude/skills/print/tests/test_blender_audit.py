"""Unit tests for blender_audit.py — mocked blender_bridge, no real Blender."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import blender_audit  # noqa: E402
import blender_bridge  # noqa: E402


def make_fake_result(success=True, data=None, stderr=""):
    """Build a BlenderRunResult-like object with a load_json that returns `data`."""
    r = MagicMock()
    r.success = success
    r.returncode = 0 if success else 1
    r.stdout = "BLENDER_OK /tmp/x.json\n" if success else ""
    r.stderr = stderr
    r.marker_path = "/tmp/x.json" if success else None
    r.load_json = MagicMock(return_value=data or {})
    return r


def test_audit_returns_ok_json_on_clean_cube(tmp_path, capsys):
    fake = make_fake_result(success=True, data={
        "file": "/tmp/cube.stl",
        "dimensions_mm": [20.0, 20.0, 20.0],
        "triangle_count": 12,
        "non_manifold_edges": 0,
        "flipped_normals": 0,
        "issues": [],
    })
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_audit.main(["/tmp/cube.stl"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["result"]["triangle_count"] == 12
    assert out["needs_repair"] is False


def test_audit_sets_needs_repair_when_issues_present(tmp_path, capsys):
    fake = make_fake_result(success=True, data={
        "file": "/tmp/bad.stl",
        "dimensions_mm": [20.0, 20.0, 20.0],
        "triangle_count": 10,
        "non_manifold_edges": 4,
        "flipped_normals": 0,
        "issues": ["4 non-manifold edges"],
    })
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_audit.main(["/tmp/bad.stl"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["needs_repair"] is True
    assert out["result"]["non_manifold_edges"] == 4


def test_audit_returns_error_on_blender_failure(tmp_path, capsys):
    fake = make_fake_result(success=False, stderr="ImportError: bpy not found")
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_audit.main(["/tmp/x.stl"])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "ImportError" in out["error"]


def test_audit_missing_input_file_returns_error(capsys):
    rc = blender_audit.main(["/nonexistent/file.stl"])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "not found" in out["error"].lower()


def test_needs_repair_flags_only_fixable_issues():
    # Advisory-only issues (triangle count, thin walls) should NOT trigger repair
    assert blender_audit.needs_repair({
        "non_manifold_edges": 0,
        "flipped_normals": 0,
        "issues": ["high triangle count (800000)"],
    }) is False
    # Non-manifold should
    assert blender_audit.needs_repair({
        "non_manifold_edges": 4,
        "flipped_normals": 0,
        "issues": ["4 non-manifold edges"],
    }) is True
    # Flipped normals should
    assert blender_audit.needs_repair({
        "non_manifold_edges": 0,
        "flipped_normals": 2,
        "issues": ["2 flipped normals"],
    }) is True
