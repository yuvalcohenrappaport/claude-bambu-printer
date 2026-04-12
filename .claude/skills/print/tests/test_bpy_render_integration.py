"""Integration test: render a cube and verify render.png is created."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
BPY_RENDER = ROOT / "scripts" / "bpy" / "render_hero.py"
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"

# Module-level skip if Blender isn't installed at the expected path.
# Integration tests spawn real Blender; without it they produce confusing
# subprocess errors rather than a clean skip.
if not Path(BLENDER).exists():
    pytest.skip(
        f"Blender not found at {BLENDER}; install via brew install --cask blender",
        allow_module_level=True,
    )


@pytest.mark.integration
def test_render_hero_produces_png(tmp_path):
    out = tmp_path / "render.png"
    cmd = [
        BLENDER, "--background", "--factory-startup",
        "--python", str(BPY_RENDER),
        "--", str(FIXTURES / "cube.stl"), str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert "BLENDER_OK" in proc.stdout
    assert out.exists()
    assert out.stat().st_size > 1000  # non-empty PNG
    # PNG magic bytes
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
