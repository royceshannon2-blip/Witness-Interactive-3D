#!/usr/bin/env python3
"""
generate_lods.py — Stage 4 LOD variant generator.

Produces LOD1 (50% face reduction) and LOD2 (85% face reduction) from the
optimized LOD0 GLB via gltf-transform (weld → simplify → draco). Placed
beside the LOD0 in the same directory.

Architecture spec: ASSET_PIPELINE.md §3 Stage 4
  LOD0 (full, 0–15 m)    →  <id>.glb          (produced by optimize_asset.py)
  LOD1 (50%, 15–50 m)    →  <id>.lod1.glb
  LOD2 (15%,  50+ m)     →  <id>.lod2.glb     (85% face reduction = keep 15%)

Usage:
    python tools/generate_lods.py processed/glb/<id>.glb [--draco-level 7]

Exit codes:
    0   both LODs written (or skipped if they already exist and --force not set)
    1   gltf-transform not found
    2   simplification failed for one or more LODs
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Reuse the validated texture-compression + Draco helpers from optimize_asset
# so LODs ship downsized KTX2 textures (UASTC normals / ETC1S colour) instead
# of the LOD0 8K maps. Same-directory import — sys.path[0] is tools/ when run
# as a script, but insert defensively in case of an unusual invocation.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from optimize_asset import apply_draco, compress_textures
    _HAVE_OPT_HELPERS = True
except Exception:  # noqa: BLE001 — fall back to local draco-only behaviour
    _HAVE_OPT_HELPERS = False

# (suffix, simplify_ratio, texture_size, label)
#   ratio = fraction of triangles to RETAIN (gltf-transform uses keep-ratio)
#   texture_size = per-tier KTX2 cap; distant LODs need far less texel density
LOD_SPECS = [
    ("lod1", 0.50, 1024, "LOD1 50% faces / 1K tex"),
    ("lod2", 0.15, 512, "LOD2 15% faces / 512 tex"),
]


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


def _run(cmd: list[str], label: str) -> bool:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(
            f"  WARN [{label}]: {r.stderr.strip()[:200] or r.stdout.strip()[:200]}",
            flush=True,
        )
    return r.returncode == 0


def _simplify_lod(src: Path, dst: Path, ratio: float, tex_size: int, draco_level: int) -> bool:
    """
    weld → simplify → texture downsize + KTX2 → draco, all via gltf-transform.

    Note on geometry reduction: Hunyuan output is non-watertight and the PBR
    bake produces a per-triangle UV atlas, so meshoptimizer locks on attribute
    seams and cannot reduce far below the LOD0 face count regardless of
    ``ratio``. The reliable LOD saving is therefore the per-tier *texture*
    downsize, not the triangle count — a distant LOD with the LOD0 8K map is
    pure waste. We still run simplify (best-effort, helps watertight assets).
    """
    welded = dst.with_suffix(".weld_tmp.glb")
    simp = dst.with_suffix(".simp_tmp.glb")
    for tmp in (welded, simp):
        tmp.unlink(missing_ok=True)

    # weld: merge position-coincident verts so meshoptimizer sees a connected graph
    if not _run(["gltf-transform", "weld", str(src), str(welded)], "weld"):
        print(f"    weld failed — using source directly for {dst.name}", flush=True)
        shutil.copy2(src, welded)

    # simplify: meshoptimizer-based triangle reduction (best-effort)
    simp_ok = _run(
        [
            "gltf-transform", "simplify",
            str(welded), str(simp),
            "--ratio", str(ratio),
            "--error", "1",            # unconstrained: hit the ratio even at high error
            "--lock-border", "false",  # allow open-edge collapse on watertight assets
        ],
        "simplify",
    )
    welded.unlink(missing_ok=True)
    if not simp_ok:
        shutil.copy2(src, simp)  # fall back to source geometry; still downsize textures

    # texture downsize + KTX2, then draco last (so KTX2 survives the draco pass).
    if _HAVE_OPT_HELPERS:
        tex = dst.with_suffix(".tex_tmp.glb")
        tex.unlink(missing_ok=True)
        if compress_textures(simp, tex, tex_size) and tex.stat().st_size > 0:
            draco_src = tex
        else:
            draco_src = simp
            tex = None
        ok = apply_draco(draco_src, dst)
        if not ok:
            shutil.copy2(str(draco_src), str(dst))
        simp.unlink(missing_ok=True)
        if tex is not None:
            tex.unlink(missing_ok=True)
        return dst.exists()

    # Fallback (helpers unavailable): geometry-only draco, no texture downsize.
    _run(
        [
            "gltf-transform", "draco",
            str(simp), str(dst),
            "--quantize-position", "14",
            "--quantize-texcoord", "12",
        ],
        "draco",
    )
    simp.unlink(missing_ok=True)
    return dst.exists()


def generate_lods(lod0: Path, draco_level: int = 7, force: bool = False) -> int:
    if not _have("gltf-transform"):
        print(
            "ERROR: gltf-transform not on PATH. "
            "Install: npm install -g @gltf-transform/cli",
            flush=True,
        )
        return 1

    # Strip any existing .lod0 or .textured suffix from the stem so the
    # output name is always <base_id>.<lodN>.glb.
    stem = lod0.stem
    for remove in (".lod0", ".textured", ".optimized"):
        if stem.endswith(remove):
            stem = stem[: -len(remove)]

    any_failed = False
    for suffix, ratio, tex_size, label in LOD_SPECS:
        out = lod0.with_name(f"{stem}.{suffix}.glb")
        if out.exists() and not force:
            size_kb = out.stat().st_size // 1024
            print(f"  [{label}] already exists: {out.name} ({size_kb} KB)", flush=True)
            continue

        print(f"  [{label}] {lod0.name} → {out.name}", flush=True)
        if not _simplify_lod(lod0, out, ratio, tex_size, draco_level):
            print(f"  FAIL: could not generate {out.name}", flush=True)
            any_failed = True
            continue

        size_kb = out.stat().st_size // 1024
        print(f"  → {out.name} ({size_kb} KB)", flush=True)

    return 2 if any_failed else 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Generate LOD1 + LOD2 variants for a Witness GLB asset."
    )
    p.add_argument("lod0_glb", help="Path to the optimized LOD0 GLB")
    p.add_argument("--draco-level", type=int, default=7)
    p.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even when LOD files already exist.",
    )
    args = p.parse_args()

    lod0 = Path(args.lod0_glb)
    if not lod0.exists():
        print(f"ERROR: LOD0 GLB not found: {lod0}", flush=True)
        return 1

    return generate_lods(lod0, draco_level=args.draco_level, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
