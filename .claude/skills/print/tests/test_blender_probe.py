"""Unit tests for blender_probe.py — mocked blender_bridge."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import blender_probe  # noqa: E402
import blender_bridge  # noqa: E402


def test_probe_stores_discovered_operator(tmp_path, monkeypatch):
    cache = tmp_path / "cache.txt"
    monkeypatch.setattr(blender_probe, "CACHE_PATH", str(cache))

    fake = MagicMock(success=True, returncode=0,
                     stdout=f"BLENDER_OK {cache}\n",
                     stderr="", marker_path=str(cache))
    # The bpy script writes the operator name into cache directly
    cache.write_text("bpy.ops.wm.threemf_export")

    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        result = blender_probe.probe()

    assert result["status"] == "ok"
    assert result["operator"] == "bpy.ops.wm.threemf_export"


def test_probe_returns_none_when_no_3mf_operator_found(tmp_path, monkeypatch):
    cache = tmp_path / "cache.txt"
    monkeypatch.setattr(blender_probe, "CACHE_PATH", str(cache))

    fake = MagicMock(success=True, returncode=0,
                     stdout=f"BLENDER_OK {cache}\n",
                     stderr="", marker_path=str(cache))
    cache.write_text("NONE")

    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        result = blender_probe.probe()

    assert result["status"] == "ok"
    assert result["operator"] is None
    assert "stl" in result["fallback"].lower()


def test_probe_caches_result(tmp_path, monkeypatch):
    cache = tmp_path / "cache.txt"
    cache.write_text("bpy.ops.wm.threemf_export")
    monkeypatch.setattr(blender_probe, "CACHE_PATH", str(cache))

    # Should NOT invoke Blender — read from cache
    with patch.object(blender_bridge, "run_bpy_script") as mock_run:
        result = blender_probe.get_cached_operator()
    mock_run.assert_not_called()
    assert result == "bpy.ops.wm.threemf_export"


def test_get_cached_operator_returns_none_when_cache_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(blender_probe, "CACHE_PATH", str(tmp_path / "nope.txt"))
    assert blender_probe.get_cached_operator() is None
