#!/usr/bin/env python3
"""Generate test fixtures for Blender audit/repair tests.

Outputs:
  cube.stl         — 20mm manifold cube (12 triangles)
  non_manifold.stl — same cube with one face removed (non-manifold edges)
  large.stl        — 1000 triangle "organic" blob for triangle-count tests
"""
from pathlib import Path
import struct

FIXTURES_DIR = Path(__file__).parent


def write_binary_stl(path: Path, triangles: list[tuple[tuple[float, float, float], ...]]) -> None:
    """Write a binary STL file from a list of (v1, v2, v3) triangles."""
    with open(path, "wb") as f:
        f.write(b"\x00" * 80)  # 80-byte header
        f.write(struct.pack("<I", len(triangles)))
        for tri in triangles:
            # Normal = (0, 0, 0) — slicer will recompute
            f.write(struct.pack("<fff", 0.0, 0.0, 0.0))
            for v in tri:
                f.write(struct.pack("<fff", *v))
            f.write(b"\x00\x00")  # attribute byte count


def cube_triangles(size: float = 20.0) -> list[tuple[tuple[float, float, float], ...]]:
    """12 triangles forming a manifold cube of the given edge length."""
    s = size
    # 8 corners
    v = [
        (0, 0, 0), (s, 0, 0), (s, s, 0), (0, s, 0),
        (0, 0, s), (s, 0, s), (s, s, s), (0, s, s),
    ]
    # 6 faces, 2 triangles each, CCW-from-outside
    return [
        # bottom (z=0)
        (v[0], v[2], v[1]), (v[0], v[3], v[2]),
        # top (z=s)
        (v[4], v[5], v[6]), (v[4], v[6], v[7]),
        # front (y=0)
        (v[0], v[1], v[5]), (v[0], v[5], v[4]),
        # right (x=s)
        (v[1], v[2], v[6]), (v[1], v[6], v[5]),
        # back (y=s)
        (v[2], v[3], v[7]), (v[2], v[7], v[6]),
        # left (x=0)
        (v[3], v[0], v[4]), (v[3], v[4], v[7]),
    ]


def make_cube():
    write_binary_stl(FIXTURES_DIR / "cube.stl", cube_triangles())


def make_non_manifold_cube():
    tris = cube_triangles()
    # Remove top face (2 triangles) — leaves 4 edges with only 1 linked face
    tris_open = [t for i, t in enumerate(tris) if i not in (2, 3)]
    write_binary_stl(FIXTURES_DIR / "non_manifold.stl", tris_open)


def make_large():
    # Generate a high-triangle-count "blob": subdivided icosphere-ish cube
    # Simple approach: 10x10x10 grid of tiny cubes = 6000 triangles
    tris = []
    for ix in range(10):
        for iy in range(10):
            for iz in range(10):
                ox, oy, oz = ix * 2.5, iy * 2.5, iz * 2.5
                for tri in cube_triangles(2.0):
                    shifted = tuple(
                        (v[0] + ox, v[1] + oy, v[2] + oz) for v in tri
                    )
                    tris.append(shifted)
    write_binary_stl(FIXTURES_DIR / "large.stl", tris)


if __name__ == "__main__":
    FIXTURES_DIR.mkdir(exist_ok=True)
    make_cube()
    make_non_manifold_cube()
    make_large()
    print(f"Fixtures written to {FIXTURES_DIR}")
