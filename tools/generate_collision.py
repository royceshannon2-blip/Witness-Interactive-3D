#!/usr/bin/env python3
"""
generate_collision.py — Stage 5 collision hull generator.

Produces a low-poly collision GLB with ≤16 convex hulls from the optimized
LOD0 GLB. Each significant connected component gets its own convex hull.
If the optional `coacd` package is installed it is used for approximate
convex decomposition (better for concave hero meshes); otherwise per-component
convex hulls via trimesh's built-in hull algorithm.

Architecture spec: ASSET_PIPELINE.md §3 Stage 5 — V-HACD/CoACD, ≤16 hulls.

Output:
    processed/collisions/<id>.collision.glb

Babylon.js usage:
    Load alongside the LOD0 GLB; toggle mesh.checkCollisions = true on the
    collision scene nodes, keep them invisible (mesh.isVisible = false).

Exit codes:
    0   collision GLB written
    1   missing inputs / trimesh not importable
    2   hull generation failed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLISIONS_DIR = REPO_ROOT / "processed" / "collisions"
# trimesh lives in ComfyUI venv; validate_geometry uses the same constant.
GATE_PYTHON_DEFAULT = "/home/royce3/ComfyUI/venv/bin/python"


# ---------------------------------------------------------------------------
# core logic (runs when called directly from the pipeline venv which has
# trimesh available via GATE_PYTHON; see main() which self-forks if needed)
# ---------------------------------------------------------------------------


def _generate(glb_path: Path, asset_id: str, max_hulls: int) -> int:
    try:
        import trimesh  # noqa: PLC0415
        import numpy as np  # noqa: F401,PLC0415
    except ImportError:
        print(
            "ERROR: trimesh not importable — "
            "run via GATE_PYTHON (/home/royce3/ComfyUI/venv/bin/python)",
            flush=True,
        )
        return 1

    # Face budget for collision computation: hull algorithms are O(n²) in
    # face count. High-poly baked meshes (100K–900K faces) would take many
    # minutes. Decimate to at most COLLISION_FACE_BUDGET faces first.
    COLLISION_FACE_BUDGET = 8_000

    print(f"  Loading {glb_path.name}…", flush=True)
    try:
        scene = trimesh.load(str(glb_path), force="scene", process=False)
    except Exception as exc:
        print(f"ERROR: trimesh load failed: {exc}", flush=True)
        return 1

    # Collect all geometry from the scene graph
    geoms = list(getattr(scene, "geometry", {}).values())
    if not geoms and hasattr(scene, "vertices"):
        geoms = [scene]  # single-mesh GLB
    if not geoms:
        print("ERROR: no geometry found in GLB", flush=True)
        return 2

    # Concatenate into one mesh for decomposition
    if len(geoms) == 1:
        combined = geoms[0]
    else:
        combined = trimesh.util.concatenate(geoms)

    face_count = len(combined.faces)
    print(f"  {face_count:,} faces", flush=True)

    # Decimate to COLLISION_FACE_BUDGET before hull computation so the
    # algorithm runs in seconds rather than minutes. The collision hull
    # only needs the rough convex shape, not PBR-quality geometry.
    if face_count > COLLISION_FACE_BUDGET:
        print(
            f"  Decimating {face_count:,} → ~{COLLISION_FACE_BUDGET:,} faces "
            "for hull computation…",
            flush=True,
        )
        try:
            # Requires `pip install fast-simplification` in GATE_PYTHON venv.
            # Falls back gracefully: convex_hull on the full mesh still works
            # fast because it only needs the convex vertex set, not all faces.
            decimated = combined.simplify_quadric_decimation(
                face_count=COLLISION_FACE_BUDGET
            )
            combined = decimated
            print(f"  After decimate: {len(combined.faces):,} faces", flush=True)
        except Exception as exc:
            print(
                f"  WARN: decimate unavailable ({type(exc).__name__}); "
                "proceeding at full resolution — install fast-simplification "
                "in GATE_PYTHON venv to speed this step",
                flush=True,
            )

    # Try CoACD first (approximate convex decomp, better for concave shapes)
    hulls: list = []
    method = "unknown"
    try:
        import coacd  # noqa: PLC0415

        mesh_c = coacd.Mesh(combined.vertices, combined.faces)
        parts = coacd.run_coacd(mesh_c, max_convex_hull=max_hulls)
        for verts, faces in parts[:max_hulls]:
            hulls.append(trimesh.Trimesh(vertices=verts, faces=faces))
        method = "coacd"
    except ImportError:
        pass
    except Exception as exc:
        print(f"  WARN: coacd failed ({exc}); falling back to component hulls", flush=True)

    if not hulls:
        # Per-component convex hull fallback. After decimation the mesh has
        # far fewer vertices and split() completes quickly.
        try:
            # process=True to merge near-duplicate verts before splitting
            welded = trimesh.Trimesh(
                vertices=combined.vertices,
                faces=combined.faces,
                process=True,
            )
            components = welded.split(only_watertight=False)
        except Exception:
            components = [combined]

        # Sort by volume descending; drop micro-components (<1% of largest)
        try:
            components = sorted(components, key=lambda m: abs(m.volume), reverse=True)
            if len(components) > 1:
                ref_vol = abs(components[0].volume)
                components = [c for c in components if abs(c.volume) >= 0.01 * ref_vol]
        except Exception:
            pass

        # If split still returns the original count (disconnected tris), fall
        # back to one hull for the whole decimated mesh.
        if len(components) >= len(combined.faces) // 2:
            components = [combined]

        components = components[:max_hulls]
        for comp in components:
            try:
                hulls.append(comp.convex_hull)
            except Exception as exc:
                print(f"  WARN: hull failed for component: {exc}", flush=True)
        method = "convex_hull_per_component"

    if not hulls:
        print("ERROR: no collision hulls could be generated", flush=True)
        return 2

    print(f"  {len(hulls)} hulls via {method}", flush=True)

    # Export as GLB scene with named nodes (Babylon imports them individually)
    hull_scene = trimesh.Scene()
    for i, h in enumerate(hulls):
        hull_scene.add_geometry(h, node_name=f"collision_hull_{i:02d}")

    COLLISIONS_DIR.mkdir(parents=True, exist_ok=True)
    out = COLLISIONS_DIR / f"{asset_id}.collision.glb"
    hull_scene.export(str(out))
    size_kb = out.stat().st_size // 1024
    print(f"  → {out.relative_to(REPO_ROOT)} ({size_kb} KB)", flush=True)
    return 0


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(
        description="Generate collision hull GLB for a Witness asset."
    )
    p.add_argument("lod0_glb", help="Path to the optimized LOD0 GLB.")
    p.add_argument("--asset-id", required=True, help="Asset ID (e.g. prop_ledger_book).")
    p.add_argument("--max-hulls", type=int, default=16)
    p.add_argument(
        "--gate-python",
        default=None,
        help=(
            "Python interpreter with trimesh available. "
            "When omitted this script self-forks via GATE_PYTHON_DEFAULT "
            "if the current interpreter lacks trimesh."
        ),
    )
    args = p.parse_args()

    glb = Path(args.lod0_glb)
    if not glb.exists():
        print(f"ERROR: GLB not found: {glb}", flush=True)
        return 1

    # Self-fork into the gate venv when trimesh is absent in the calling venv.
    try:
        import trimesh  # noqa: F401
        has_trimesh = True
    except ImportError:
        has_trimesh = False

    if not has_trimesh:
        import os
        import subprocess
        gate_python = args.gate_python or os.environ.get(
            "WITNESS_GATE_PYTHON", GATE_PYTHON_DEFAULT
        )
        cmd = [
            gate_python,
            str(Path(__file__).resolve()),
            str(glb),
            "--asset-id", args.asset_id,
            "--max-hulls", str(args.max_hulls),
        ]
        return subprocess.run(cmd, cwd=REPO_ROOT).returncode

    return _generate(glb, args.asset_id, args.max_hulls)


if __name__ == "__main__":
    sys.exit(main())
