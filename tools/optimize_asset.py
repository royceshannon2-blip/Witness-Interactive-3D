#!/usr/bin/env python3
"""
optimize_asset.py — GLB Optimization Pipeline

Three passes, in order:

  1. Detached-component cleanup (trimesh) — drops tiny floating islands
     produced as a side-effect of Hunyuan3D's single-view shape pass.
     Keeps every connected component whose volume is at least
     ``--cleanup-min-volume-ratio`` of the largest component (default 1%).
     Disable with ``--no-cleanup``.
  2. Draco mesh compression (gltf-pipeline).
  3. KTX2 texture compression (toktx; currently a no-op placeholder).

Reduces file size by 70-90% with minimal quality loss.

Usage:
    python optimize_asset.py <glb_path> [--draco-level 7] [--output-suffix .optimized]

Example:
    python optimize_asset.py processed/glb/Jerrycan.glb
    → produces: processed/glb/Jerrycan.optimized.glb
"""

import argparse
import sys
import subprocess
import tempfile
from pathlib import Path


def check_tool(tool_name, npm_package=None):
    """Check if a tool is installed; suggest installation if not."""
    try:
        subprocess.run([tool_name, '--version'],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL,
                      timeout=5)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        if npm_package:
            print(f"WARNING: {tool_name} not found. Install with: npm install -g {npm_package}")
        else:
            print(f"WARNING: {tool_name} not found.")
        return False


def strip_detached_components(input_glb: Path, output_glb: Path, min_volume_ratio: float) -> bool:
    """
    Remove floating mesh islands by keeping only connected components whose
    volume is at least ``min_volume_ratio`` * largest_component_volume.

    Why this exists: Hunyuan3D 2.1 single-view inference occasionally
    produces a clean main body plus a handful of tiny disconnected shells
    (silhouette-bleed reconstructions of background pixels). These islands
    are invisible in screenshots but inflate face counts, break LOD
    pipelines, and confuse V-HACD collision generation. Stripping them
    here keeps every downstream stage honest.

    Returns True on success (or on a graceful no-op where nothing was
    stripped). Returns False if trimesh is missing or the load fails — in
    that case the caller should skip this pass and proceed to Draco.
    """
    try:
        import trimesh
    except ImportError:
        print("  trimesh not installed; skipping detached-component cleanup")
        print("  (pip install trimesh to enable)")
        return False

    try:
        scene_or_mesh = trimesh.load(str(input_glb), force="scene", process=False)
    except Exception as exc:  # noqa: BLE001 — surface verbatim and skip
        print(f"  WARN: trimesh load failed ({exc}); skipping cleanup")
        return False

    # GLBs always load as a Scene in trimesh ≥3.20; fall back to single-mesh API
    # for older versions just in case.
    geometries = list(getattr(scene_or_mesh, "geometry", {}).values())
    if not geometries and hasattr(scene_or_mesh, "vertices"):
        geometries = [scene_or_mesh]
    if not geometries:
        print("  WARN: GLB contained no geometry; skipping cleanup")
        return False

    total_dropped = 0
    total_kept = 0
    modified = False
    for mesh in geometries:
        # split() returns one Trimesh per connected component. With
        # only_watertight=False we keep open shells too (Hunyuan output is
        # rarely watertight).
        try:
            components = mesh.split(only_watertight=False)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN: split failed on a sub-mesh ({exc}); leaving it intact")
            total_kept += 1
            continue

        if len(components) <= 1:
            total_kept += 1
            continue

        # Volume can be negative for non-watertight meshes — use absolute.
        volumes = [abs(float(c.volume)) if c.volume is not None else 0.0 for c in components]
        max_vol = max(volumes) if volumes else 0.0
        if max_vol <= 0.0:
            # Degenerate geometry — keep everything; better to ship a noisy
            # mesh than silently delete the whole thing.
            total_kept += 1
            continue

        threshold = max_vol * min_volume_ratio
        kept = [c for c, v in zip(components, volumes) if v >= threshold]
        dropped = len(components) - len(kept)
        total_dropped += dropped
        total_kept += len(kept)

        if dropped > 0:
            modified = True
            # trimesh.util.concatenate preserves materials when they match;
            # Hunyuan output is a single material so this is safe.
            combined = trimesh.util.concatenate(kept) if len(kept) > 1 else kept[0]
            # Re-attach to the scene under the same node name. The Scene API
            # is slightly clunky — easiest path is to rebuild via a fresh
            # scene with one node per kept geometry, but for single-geometry
            # output (the common case) we can swap in-place.
            name = next(
                (n for n, g in scene_or_mesh.geometry.items() if g is mesh),
                None,
            )
            if name is not None:
                scene_or_mesh.geometry[name] = combined

    if not modified:
        print(f"  No detached components found (threshold {min_volume_ratio:.1%})")
        return True

    try:
        scene_or_mesh.export(str(output_glb))
    except Exception as exc:  # noqa: BLE001
        print(f"  WARN: trimesh export failed ({exc}); skipping cleanup")
        return False

    print(
        f"  ✓ Stripped {total_dropped} detached island(s), kept {total_kept} "
        f"(threshold ≥ {min_volume_ratio:.1%} of largest)"
    )
    return True


def optimize_draco(input_glb, output_glb, compression_level=7):
    """Apply Draco compression via gltf-pipeline."""
    if not check_tool('gltf-pipeline', '@gltf-transform/cli'):
        print("  Skipping Draco compression")
        return False

    cmd = [
        'gltf-pipeline',
        '-i', str(input_glb),
        '-o', str(output_glb),
        '--draco.compressionLevel', str(compression_level),
    ]

    try:
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"  ERROR: Draco compression failed")
            print(f"  {result.stderr}")
            return False
        print(f"  ✓ Draco compression applied")
        return True
    except subprocess.TimeoutExpired:
        print(f"  ERROR: Draco compression timed out")
        return False


def optimize_ktx2(glb_path):
    """Note KTX2 conversion process."""
    if not check_tool('toktx', 'ktx-tools'):
        print("  Skipping KTX2 compression")
        return False

    print(f"  KTX2 compression requires texture extraction:")
    print(f"    Convert PNG/JPG: toktx --t2 --bcmp output.ktx2 input.png")
    print(f"    Repack GLB with KTX2 textures")
    return True


def get_file_size(path):
    """Get file size in MB."""
    return path.stat().st_size / (1024 * 1024)


def main():
    parser = argparse.ArgumentParser(
        description="Optimize GLB with Draco and KTX2 compression"
    )
    parser.add_argument('glb_path', help='Path to GLB file')
    parser.add_argument('--draco-level', type=int, default=7,
                        help='Draco compression level 0-10 (default: 7)')
    parser.add_argument('--output-suffix', default='.optimized',
                        help='Suffix for output file (default: .optimized)')
    parser.add_argument('--in-place', action='store_true',
                        help='Overwrite input file instead of creating new file')
    parser.add_argument('--no-cleanup', action='store_true',
                        help='Skip detached-component cleanup (default: enabled)')
    parser.add_argument('--cleanup-min-volume-ratio', type=float, default=0.01,
                        help=('Drop connected components whose volume is below '
                              'this fraction of the largest component (default: 0.01 = 1%%)'))

    args = parser.parse_args()

    input_path = Path(args.glb_path)
    if not input_path.exists():
        print(f"ERROR: GLB file not found: {input_path}")
        sys.exit(1)
    if input_path.suffix.lower() != '.glb':
        print(f"ERROR: File must be .glb, got: {input_path.suffix}")
        sys.exit(1)

    if args.in_place:
        output_path = input_path
    else:
        output_path = input_path.with_stem(input_path.stem + args.output_suffix)

    input_size = get_file_size(input_path)

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"GLB Optimization")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Input:    {input_path}")
    print(f"Size:     {input_size:.2f} MB")
    print(f"Output:   {output_path}")
    print(f"Draco:    Level {args.draco_level}")
    print(f"Cleanup:  {'off' if args.no_cleanup else f'on (≥ {args.cleanup_min_volume_ratio:.1%} of largest)'}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Stage 1: detached-component cleanup. Writes a temporary GLB if the
    # cleanup pass actually modifies geometry, otherwise we pass the input
    # straight through to Draco.
    print(f"\n[1/3] Stripping detached components...")
    draco_input = input_path
    cleanup_tmp: Path | None = None
    if not args.no_cleanup:
        with tempfile.NamedTemporaryFile(
            suffix=".cleaned.glb",
            dir=str(input_path.parent),
            delete=False,
        ) as tf:
            cleanup_tmp = Path(tf.name)
        ok = strip_detached_components(input_path, cleanup_tmp, args.cleanup_min_volume_ratio)
        if ok and cleanup_tmp.exists() and cleanup_tmp.stat().st_size > 0:
            draco_input = cleanup_tmp
        else:
            # Either skipped (no modification) or failed — drop the tmp file
            # so we don't leave debris behind.
            if cleanup_tmp.exists():
                cleanup_tmp.unlink()
            cleanup_tmp = None
    else:
        print("  Cleanup disabled via --no-cleanup")

    print(f"\n[2/3] Applying Draco compression...")
    draco_ok = optimize_draco(draco_input, output_path, args.draco_level)

    # Best-effort cleanup of the intermediate cleaned GLB now that Draco
    # has read it.
    if cleanup_tmp is not None and cleanup_tmp.exists():
        try:
            cleanup_tmp.unlink()
        except OSError:
            pass

    print(f"\n[3/3] Optimization complete")
    if draco_ok and output_path.exists():
        output_size = get_file_size(output_path)
        ratio = (1 - output_size / input_size) * 100
        print(f"  Input:  {input_size:.2f} MB")
        print(f"  Output: {output_size:.2f} MB")
        print(f"  Saved:  {ratio:.1f}%")
    else:
        print(f"  No compression applied")

    print(f"\n  Next: python tools/register_asset.py <asset_name> <era>")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == '__main__':
    main()
