#!/usr/bin/env python3
"""
optimize_asset.py — GLB Optimization Pipeline

Three passes, in order:

  1. Detached-component cleanup (trimesh) — drops tiny floating islands
     produced as a side-effect of Hunyuan3D's single-view shape pass.
     Keeps every connected component whose volume is at least
     ``--cleanup-min-volume-ratio`` of the largest component (default 1%).
     Disable with ``--no-cleanup``.
  2. Weld + simplify to ``--target-faces`` (gltf-transform).
  3. Texture downsize (≤ ``--max-texture-size``) + KTX2 compression — UASTC
     for normal maps, ETC1S for albedo / metallic-roughness / AO / emissive.
     Disable with ``--no-ktx2``.
  4. Draco geometry compression (gltf-transform, applied last so the Draco
     and KHR_texture_basisu extensions coexist in the final GLB).

Reduces file size by 70-90% with minimal quality loss.

Usage:
    python optimize_asset.py <glb_path> [--draco-level 7] [--output-suffix .optimized]

Example:
    python optimize_asset.py processed/glb/Jerrycan.glb
    → produces: processed/glb/Jerrycan.optimized.glb
"""

import argparse
import shutil
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


def simplify_mesh(input_glb: Path, output_glb: Path, target_faces: int) -> bool:
    """
    Weld duplicate vertices then simplify to target_faces using gltf-transform.
    Runs before Draco so the compressor works on the reduced mesh.
    Weld is required first — split UV-seam vertices defeat the simplifier.
    """
    if not check_tool("gltf-transform", "@gltf-transform/cli"):
        print("  Skipping simplification (gltf-transform not found)")
        return False

    import json, struct, tempfile
    # Read current face count from GLB JSON chunk
    try:
        data = input_glb.read_bytes()
        json_len = struct.unpack_from("<I", data, 12)[0]
        gltf = json.loads(data[20 : 20 + json_len])
        accessors = gltf.get("accessors", [])
        current_faces = sum(
            accessors[p["indices"]]["count"] // 3
            for m in gltf.get("meshes", [])
            for p in m.get("primitives", [])
            if "indices" in p and p["indices"] < len(accessors)
        )
    except Exception:
        current_faces = None

    if current_faces is not None and current_faces <= target_faces:
        print(f"  Simplification skipped — mesh already at {current_faces:,} faces ≤ target {target_faces:,}")
        return False

    if current_faces:
        ratio = max(0.001, target_faces / current_faces)
        print(f"  Simplifying: {current_faces:,} → ~{target_faces:,} faces (ratio {ratio:.4f})")
    else:
        ratio = 0.05
        print(f"  Simplifying with ratio {ratio} (face count unreadable)")

    with tempfile.NamedTemporaryFile(suffix=".welded.glb", dir=str(input_glb.parent), delete=False) as tf:
        welded_tmp = Path(tf.name)
    try:
        r = subprocess.run(
            ["gltf-transform", "weld", str(input_glb), str(welded_tmp)],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            print(f"  WARN: weld failed ({r.stderr.strip()[:120]}); skipping simplification")
            return False

        r = subprocess.run(
            ["gltf-transform", "simplify", str(welded_tmp), str(output_glb),
             "--ratio", str(round(ratio, 6)), "--error", "0.01"],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            print(f"  WARN: simplify failed ({r.stderr.strip()[:120]}); skipping")
            return False

        print(f"  ✓ Mesh simplified")
        return True
    finally:
        if welded_tmp.exists():
            welded_tmp.unlink()


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


def _run_gt(sub_args: list[str], label: str, timeout: int) -> bool:
    """Run a gltf-transform subcommand; return True on exit 0."""
    try:
        r = subprocess.run(
            ["gltf-transform", *sub_args],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0:
            print(f"  WARN [{label}]: {(r.stderr or r.stdout).strip()[:160]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  WARN [{label}]: timed out after {timeout}s")
        return False
    except FileNotFoundError:
        print(f"  WARN [{label}]: gltf-transform not found")
        return False


def compress_textures(
    input_glb: Path,
    output_glb: Path,
    max_size: int,
    etc1s_quality: int = 160,
    uastc_level: int = 2,
) -> bool:
    """
    Resize textures to ≤ ``max_size`` (power-of-two) and encode to KTX2:
    UASTC for normal maps (block artefacts on normals are visible), ETC1S for
    everything else (albedo / metallic-roughness / AO / emissive). Each step
    falls back to copying its input forward so a single failure never aborts
    the chain — worst case the textures pass through uncompressed.

    Runs entirely through gltf-transform so KHR_texture_basisu is written in a
    way that coexists with the Draco pass that follows. Must run on a
    *non-Draco* mesh (gltf-transform decodes Draco on read), i.e. before the
    Draco stage.

    Returns True if ``output_glb`` was written.
    """
    if not check_tool("gltf-transform", "@gltf-transform/cli"):
        print("  Skipping KTX2 (gltf-transform not found)")
        return False

    tmps: list[Path] = []

    def _mktmp(tag: str) -> Path:
        with tempfile.NamedTemporaryFile(
            suffix=f".{tag}.glb", dir=str(input_glb.parent), delete=False
        ) as t:
            p = Path(t.name)
        tmps.append(p)
        return p

    resized = _mktmp("resize")
    uast = _mktmp("uastc")
    try:
        # 1. Downsize. --width/--height are MAX caps (won't upscale). Do NOT add
        #    --power-of-two: it overrides the explicit caps and pins every map to
        #    a 2048 default. Pass power-of-two sizes (512/1024/2048) and the cap
        #    keeps the result power-of-two on its own (source maps are pow2).
        if _run_gt(
            ["resize", str(input_glb), str(resized),
             "--width", str(max_size), "--height", str(max_size)],
            "resize", 300,
        ):
            print(f"  ✓ Textures resized to ≤ {max_size}px")
        else:
            shutil.copy2(str(input_glb), str(resized))

        # 2. UASTC for normal maps only.
        if _run_gt(
            ["uastc", str(resized), str(uast),
             "--level", str(uastc_level), "--rdo", "--rdo-lambda", "4",
             "--zstd", "18", "--slots", "normalTexture"],
            "uastc(normals)", 900,
        ):
            print("  ✓ Normal map → UASTC")
        else:
            shutil.copy2(str(resized), str(uast))

        # 3. ETC1S for everything except normals (final writer → output_glb).
        if _run_gt(
            ["etc1s", str(uast), str(output_glb),
             "--quality", str(etc1s_quality), "--slots", "!normalTexture"],
            "etc1s(color/mr)", 900,
        ):
            print("  ✓ Albedo / MR / AO → ETC1S")
        else:
            shutil.copy2(str(uast), str(output_glb))

        return output_glb.exists() and output_glb.stat().st_size > 0
    finally:
        for p in tmps:
            try:
                p.unlink()
            except OSError:
                pass


def apply_draco(input_glb: Path, output_glb: Path) -> bool:
    """
    Draco geometry compression via gltf-transform. Used as the final stage so
    it preserves any KHR_texture_basisu (KTX2) textures already in the GLB —
    unlike gltf-pipeline, which does not understand the basisu extension.
    """
    ok = _run_gt(
        ["draco", str(input_glb), str(output_glb),
         "--quantize-position", "14",
         "--quantize-normal", "10",
         "--quantize-texcoord", "12"],
        "draco", 300,
    )
    if ok:
        print("  ✓ Draco compression applied")
    return ok


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
    parser.add_argument('--target-faces', type=int, default=40000,
                        help='Simplify mesh to this face count before Draco (default: 40000). '
                             'Set 0 to disable. Post-UV meshes may not reach the target if '
                             'seam topology is the limiting factor.')
    parser.add_argument('--no-simplify', action='store_true',
                        help='Skip weld + simplify pass (equivalent to --target-faces 0)')
    parser.add_argument('--max-texture-size', type=int, default=2048,
                        help='Cap texture dimensions (px) before KTX2 (default: 2048). '
                             'The 8K bake source is downsized for web delivery; the '
                             'runtime SceneOptimizer drops mips further per profile. '
                             'Set 0 to keep source resolution.')
    parser.add_argument('--no-ktx2', action='store_true',
                        help='Skip texture downsize + KTX2 compression (ship raw PNG textures)')
    parser.add_argument('--etc1s-quality', type=int, default=160,
                        help='ETC1S quality 1-255 for albedo/MR/AO (default: 160)')
    parser.add_argument('--uastc-level', type=int, default=2,
                        help='UASTC level 0-4 for normal maps (default: 2)')

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
    run_simplify = not args.no_simplify and args.target_faces > 0
    print(f"Input:    {input_path}")
    print(f"Size:     {input_size:.2f} MB")
    print(f"Output:   {output_path}")
    print(f"Draco:    Level {args.draco_level}")
    print(f"Cleanup:  {'off' if args.no_cleanup else f'on (≥ {args.cleanup_min_volume_ratio:.1%} of largest)'}")
    print(f"Simplify: {'off' if not run_simplify else f'target {args.target_faces:,} faces (weld + simplify)'}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Stage 1: detached-component cleanup.
    print(f"\n[1/4] Stripping detached components...")
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
            if cleanup_tmp.exists():
                cleanup_tmp.unlink()
            cleanup_tmp = None
    else:
        print("  Cleanup disabled via --no-cleanup")

    # Stage 2: weld + simplify (before Draco so the compressor works on fewer faces).
    simplify_tmp: Path | None = None
    if run_simplify:
        print(f"\n[2/4] Weld + simplify to {args.target_faces:,} faces...")
        with tempfile.NamedTemporaryFile(
            suffix=".simplified.glb",
            dir=str(input_path.parent),
            delete=False,
        ) as tf:
            simplify_tmp = Path(tf.name)
        simplified = simplify_mesh(draco_input, simplify_tmp, args.target_faces)
        if simplified and simplify_tmp.exists() and simplify_tmp.stat().st_size > 0:
            # Drop the cleanup_tmp now that simplify has consumed it.
            if cleanup_tmp is not None and cleanup_tmp.exists():
                cleanup_tmp.unlink()
                cleanup_tmp = None
            draco_input = simplify_tmp
        else:
            if simplify_tmp.exists():
                simplify_tmp.unlink()
            simplify_tmp = None
    else:
        print(f"\n[2/4] Simplify skipped")

    # Stage 3: texture downsize + KTX2 (must run before Draco — gltf-transform
    # decodes Draco on read, so KTX2 is applied to the non-Draco mesh and Draco
    # is re-applied last in stage 4).
    tex_tmp: Path | None = None
    run_ktx2 = not args.no_ktx2 and args.max_texture_size > 0
    if run_ktx2:
        print(f"\n[3/4] Texture downsize (≤ {args.max_texture_size}px) + KTX2...")
        with tempfile.NamedTemporaryFile(
            suffix=".tex.glb", dir=str(input_path.parent), delete=False
        ) as tf:
            tex_tmp = Path(tf.name)
        if compress_textures(
            draco_input, tex_tmp, args.max_texture_size,
            etc1s_quality=args.etc1s_quality, uastc_level=args.uastc_level,
        ) and tex_tmp.stat().st_size > 0:
            # Retire the previous intermediate now that textures consumed it.
            for tmp in (cleanup_tmp, simplify_tmp):
                if tmp is not None and tmp.exists() and tmp != tex_tmp:
                    tmp.unlink()
            cleanup_tmp = simplify_tmp = None
            draco_input = tex_tmp
        else:
            if tex_tmp.exists():
                tex_tmp.unlink()
            tex_tmp = None
            print("  WARN: texture compression failed; shipping uncompressed textures")
    else:
        reason = "--no-ktx2" if args.no_ktx2 else "--max-texture-size 0"
        print(f"\n[3/4] Texture compression skipped ({reason})")

    # Stage 4: Draco geometry compression, last, via gltf-transform so KTX2
    # textures survive. Falls back to gltf-pipeline, then to a plain copy.
    print(f"\n[4/4] Applying Draco compression...")
    draco_ok = apply_draco(draco_input, output_path)
    if not draco_ok:
        print("  gltf-transform draco failed; trying gltf-pipeline...")
        draco_ok = optimize_draco(draco_input, output_path, args.draco_level)
    if not draco_ok and not output_path.exists():
        # Ensure the canonical output exists even if compression was a no-op.
        shutil.copy2(str(draco_input), str(output_path))

    for tmp in (cleanup_tmp, simplify_tmp, tex_tmp):
        if tmp is not None and tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass

    print(f"\n  Optimization complete")
    if output_path.exists():
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
