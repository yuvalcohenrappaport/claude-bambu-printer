"""Unit tests for blender_bridge.py — mocked subprocess, no real Blender calls."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Path fudge so tests can import the script without installing it
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import blender_bridge  # noqa: E402


def test_find_blender_returns_macos_app_when_present(tmp_path, monkeypatch):
    fake_blender = tmp_path / "Blender.app/Contents/MacOS/Blender"
    fake_blender.parent.mkdir(parents=True)
    fake_blender.write_text("#!/bin/bash\necho fake\n")
    fake_blender.chmod(0o755)
    monkeypatch.setattr(blender_bridge, "MACOS_BLENDER_PATH", str(fake_blender))
    assert blender_bridge.find_blender() == str(fake_blender)


def test_find_blender_raises_when_not_installed(monkeypatch):
    monkeypatch.setattr(blender_bridge, "MACOS_BLENDER_PATH", "/nonexistent/Blender")
    with patch("shutil.which", return_value=None):
        with pytest.raises(blender_bridge.BlenderNotFoundError):
            blender_bridge.find_blender()


def test_run_bpy_script_success_parses_stdout_marker(tmp_path):
    script = tmp_path / "fake.py"
    script.write_text("print('BLENDER_OK /tmp/out.json')")

    fake_result = MagicMock(returncode=0,
                            stdout="some logs\nBLENDER_OK /tmp/out.json\n",
                            stderr="")
    with patch.object(blender_bridge, "find_blender", return_value="/fake/blender"):
        with patch("subprocess.run", return_value=fake_result) as mock_run:
            result = blender_bridge.run_bpy_script(str(script), ["/tmp/out.json"])

    assert result.success is True
    assert result.marker_path == "/tmp/out.json"
    assert result.returncode == 0
    called_cmd = mock_run.call_args[0][0]
    assert "--background" in called_cmd
    assert "--python" in called_cmd
    assert "--" in called_cmd
    assert "/tmp/out.json" in called_cmd


def test_run_bpy_script_nonzero_returncode_sets_success_false(tmp_path):
    script = tmp_path / "fake.py"
    script.write_text("import sys; sys.exit(1)")

    fake_result = MagicMock(returncode=1,
                            stdout="",
                            stderr="Traceback: ValueError: nope")
    with patch.object(blender_bridge, "find_blender", return_value="/fake/blender"):
        with patch("subprocess.run", return_value=fake_result):
            result = blender_bridge.run_bpy_script(str(script), [])

    assert result.success is False
    assert result.returncode == 1
    assert "ValueError: nope" in result.stderr


def test_run_bpy_script_missing_script_raises():
    with patch.object(blender_bridge, "find_blender", return_value="/fake/blender"):
        with pytest.raises(FileNotFoundError):
            blender_bridge.run_bpy_script("/nonexistent/script.py", [])


def test_json_marker_loads_output_file(tmp_path):
    out = tmp_path / "out.json"
    out.write_text(json.dumps({"k": "v"}))

    fake_result = MagicMock(returncode=0,
                            stdout=f"BLENDER_OK {out}\n",
                            stderr="")
    script = tmp_path / "s.py"
    script.write_text("# noop")
    with patch.object(blender_bridge, "find_blender", return_value="/fake/b"):
        with patch("subprocess.run", return_value=fake_result):
            result = blender_bridge.run_bpy_script(str(script), [str(out)])

    assert result.load_json() == {"k": "v"}


def test_run_bpy_script_timeout_returns_str_stdout(tmp_path):
    """TimeoutExpired.stdout is bytes — handler must decode to str."""
    script = tmp_path / "slow.py"
    script.write_text("import time; time.sleep(10)")

    # TimeoutExpired carries bytes in .stdout/.stderr even when text=True
    exc = subprocess.TimeoutExpired(
        cmd=["fake"],
        timeout=1,
        output=b"partial output before timeout\n",
        stderr=b"partial stderr",
    )
    with patch.object(blender_bridge, "find_blender", return_value="/fake/blender"):
        with patch("subprocess.run", side_effect=exc):
            result = blender_bridge.run_bpy_script(str(script), [], timeout=1)

    assert result.success is False
    assert result.returncode == -1
    assert isinstance(result.stdout, str), f"stdout is {type(result.stdout).__name__}"
    assert isinstance(result.stderr, str), f"stderr is {type(result.stderr).__name__}"
    assert "partial output before timeout" in result.stdout
    assert "timeout after 1s" in result.stderr


def test_load_json_raises_blender_output_error_when_marker_missing():
    """BlenderRunResult.load_json should raise a custom exception, not RuntimeError."""
    r = blender_bridge.BlenderRunResult(
        success=False, returncode=0, stdout="", stderr="", marker_path=None,
    )
    with pytest.raises(blender_bridge.BlenderOutputError):
        r.load_json()
