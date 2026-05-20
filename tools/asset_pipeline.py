#!/usr/bin/env python3
"""
asset_pipeline.py — Single Entry Point for the Witness Asset Pipeline

Runs the full chain for any of the supported asset kinds and writes a single
registry row at the end. Per `.claude/rules/asset-pipeline.md`, this is the
canonical entry point — direct calls to the underlying scripts
(generate_asset.py, optimize_asset.py, etc.) are only for iteration.

Kinds (see the rule for the decision tree):
  mesh      Hunyuan3D mesh, PBR-baked, Draco + KTX2, 3 LODs, collision hull.
  splat     Gaussian splat capture (.ply / .splat / .spz / .sog) — normalised + registered.
  tileset   3D Tileset reference — registers the root tileset.json URL/path.
  navmesh   Navigation mesh built from one or more terrain GLBs.
  nme       Node Material Editor JSON — registered as a material asset.
  animated  Hunyuan3D mesh + Blender skeletal rig + animation export.

Usage:
  python tools/asset_pipeline.py <id> --kind mesh \
      --image prompts/asset-templates/<id>/ref.png [--steps 50] [--era past|present|shared]

  # Stage 0 + stage 1 chained — ComfyUI/Flux generates ref.png first:
  python tools/asset_pipeline.py <id> --kind mesh --auto-ref \
      [--auto-ref-workflow hero] [--auto-ref-seed <n>] [--era past|present|shared]

  python tools/asset_pipeline.py <id> --kind splat \
      --source captures/<id>.spz [--era shared]

  python tools/asset_pipeline.py <id> --kind tileset \
      --root https://example/3dtiles/<id>/tileset.json [--era shared]

  python tools/asset_pipeline.py <id> --kind navmesh \
      --terrain processed/glb/structure_terrain.glb [--era shared]

  python tools/asset_pipeline.py <id> --kind nme \
      --source materials/source/<id>.nme.json [--era shared]

  python tools/asset_pipeline.py <id> --kind animated \
      --image prompts/asset-templates/<id>/ref.png \
      --rig prompts/asset-templates/<id>/rig.blend [--era past]

Every successful run appends a row to `docs/asset-index.md` and copies the
runtime artefact under `witness-interactive-vite/public/assets/`.

Exit codes:
  0  full chain succeeded
  1  validation failed (bad inputs, unknown kind, missing tools)
  2  generation / processing failed (Hunyuan, Draco, KTX2, recast, ...)
  3  registration / export step failed
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
PROCESSED = REPO_ROOT / "processed"
PUBLIC_ASSETS = REPO_ROOT / "witness-interactive-vite" / "public" / "assets"
ASSET_INDEX = REPO_ROOT / "docs" / "asset-index.md"

VALID_KINDS = ("mesh", "splat", "tileset", "navmesh", "nme", "animated")
VALID_ERAS = ("present", "past", "shared")
SPLAT_EXTS = (".ply", ".splat", ".spz", ".sog", ".sogs")

# Stage 0.5 (Zero123++) needs `diffusers` + `torch`. The project default
# points at ComfyUI's venv since it already carries the CUDA-wheel torch
# used by stage 0 (Flux). Override per-invocation with --multi-view-python
# or persistently with the WITNESS_MULTI_VIEW_PYTHON env var.
MULTI_VIEW_PYTHON_DEFAULT = "/home/royce3/ComfyUI/venv/bin/python"

# Stage 0.25 (FLUX.2 [klein] refine) — per-category denoise strength.
# Lower preserves the source's geometry; higher pushes harder toward the
# Digital Diorama palette. Tuned against the asset categories actually
# present in PHASE1_ASSET_LIST.md:
#   vegetation — needs strong palette restyle (foliage colour varies wildly
#                across stock photos); silhouette tolerance is high.
#   structure  — buildings: protect geometry hard so doorways/roof pitches
#                survive; the palette nudge is enough.
#   prop       — hero objects (ledger, candle, frame): mid; we want both
#                the surface materials and the geometry to stay close.
#   figure     — hands / people: mid; same reasoning as prop but with extra
#                care for anatomy (denoise much higher and limbs warp).
#   animated   — fallback for assets passed with --kind animated whose
#                category prefix doesn't match the table.
# Override per-run with --refine-ref-strength.
REFINE_STRENGTH_BY_CATEGORY = {
    "vegetation": 0.60,
    "structure":  0.40,
    "prop":       0.50,
    "figure":     0.50,
    "animated":   0.50,
}
DEFAULT_REFINE_STRENGTH = 0.50


def refine_strength_for(asset_id: str) -> float:
    """
    Resolve the per-asset refine strength via the category prefix.

    The asset id pattern is `<category>_<name>[_<variant>]` (validated by
    `validate_id`), so the category is everything before the first `_`.
    Unknown categories fall back to `DEFAULT_REFINE_STRENGTH` so a new
    asset family doesn't break the orchestrator before its tuning lands
    in the table.
    """
    head = asset_id.split("_", 1)[0]
    return REFINE_STRENGTH_BY_CATEGORY.get(head, DEFAULT_REFINE_STRENGTH)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def die(msg: str, code: int = 1) -> None:
    sys.stderr.write(f"ERROR: {msg}\n")
    sys.exit(code)


def info(msg: str) -> None:
    sys.stdout.write(f"  {msg}\n")


def step(label: str) -> None:
    sys.stdout.write(f"\n[step] {label}\n")


def banner(title: str) -> None:
    bar = "━" * 56
    sys.stdout.write(f"\n{bar}\n{title}\n{bar}\n")


def run_step(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a subprocess and surface its exit status."""
    info(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or REPO_ROOT)
    if result.returncode != 0:
        die(f"Subcommand failed: {' '.join(cmd)} (exit {result.returncode})", code=2)


def ensure_tools(*names: str) -> None:
    missing = [n for n in names if shutil.which(n) is None]
    if missing:
        die(
            "Missing required executables: "
            + ", ".join(missing)
            + ". Install them before running this pipeline.",
            code=1,
        )


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def validate_id(asset_id: str) -> None:
    """Snake_case <category>_<name>_<variant?> per ASSET_PIPELINE.md §4.1."""
    if not asset_id:
        die("asset id is required")
    if asset_id != asset_id.lower():
        die(f"asset id must be lowercase: {asset_id}")
    if " " in asset_id or "-" in asset_id:
        die(f"asset id must be snake_case (no spaces / dashes): {asset_id}")
    if "_" not in asset_id:
        die(
            f"asset id must follow <category>_<name>[_<variant>]: {asset_id}",
        )


def append_index_row(row: str) -> None:
    """Append one markdown table row, creating the file if needed."""
    ensure_dir(ASSET_INDEX.parent)
    if not ASSET_INDEX.exists():
        ASSET_INDEX.write_text(
            textwrap.dedent(
                """\
                # Asset Index

                Auto-managed by `tools/asset_pipeline.py`. Do not hand-edit rows
                — re-run the pipeline to refresh metadata.

                | Asset ID | Kind | Path | Era | Source | Registered |
                |---|---|---|---|---|---|
                """
            )
        )
    with ASSET_INDEX.open("a") as fh:
        fh.write(row.rstrip("\n") + "\n")


def copy_to_public(src: Path, dest_name: str) -> Path:
    ensure_dir(PUBLIC_ASSETS)
    dest = PUBLIC_ASSETS / dest_name
    shutil.copy2(src, dest)
    info(f"public/assets/{dest_name} ← {src.relative_to(REPO_ROOT)}")
    return dest


# ---------------------------------------------------------------------------
# context object
# ---------------------------------------------------------------------------


@dataclass
class PipelineContext:
    asset_id: str
    kind: str
    era: str
    source: str  # human-readable provenance string for the registry
    today: str

    def row(self, path: Path | str) -> str:
        rel = path if isinstance(path, str) else str(path.relative_to(REPO_ROOT))
        return (
            f"| {self.asset_id} | {self.kind} | {rel} | {self.era} | "
            f"{self.source} | {self.today} |"
        )


# ---------------------------------------------------------------------------
# branches
# ---------------------------------------------------------------------------


def maybe_auto_ref(args: argparse.Namespace, ctx: PipelineContext) -> None:
    """
    Stage 0 — run generate_ref_image.py when `--auto-ref` is set.

    Idempotent: if a `ref.png`/`ref.jpg` already exists for the asset, the
    stage 0 script will no-op. Use `--auto-ref-force` to override and
    regenerate. On success, the caller's `args.image` is set to the
    produced path so the mesh branch picks it up without a second flag.
    """
    if args.kind not in ("mesh", "animated"):
        return
    if not args.auto_ref:
        return

    asset_dir = REPO_ROOT / "prompts" / "asset-templates" / ctx.asset_id
    template = REPO_ROOT / "prompts" / "asset-templates" / f"{ctx.asset_id}.md"
    if not template.exists():
        die(
            f"--auto-ref requires prompts/asset-templates/{ctx.asset_id}.md; "
            "author the template before running stage 0.",
            code=1,
        )

    existing = next(
        (asset_dir / f"ref{ext}" for ext in (".png", ".jpg", ".jpeg") if (asset_dir / f"ref{ext}").exists()),
        None,
    )
    if existing and not args.auto_ref_force:
        info(f"stage 0 skip — ref already at {existing.relative_to(REPO_ROOT)}")
        args.image = str(existing)
        return

    step("0/5 generate ref image (ComfyUI + Flux.1 [dev])")
    cmd = [
        sys.executable,
        str(TOOLS_DIR / "generate_ref_image.py"),
        ctx.asset_id,
        "--workflow",
        args.auto_ref_workflow,
        "--seed",
        str(args.auto_ref_seed),
        "--server",
        args.comfy_server,
    ]
    if args.auto_ref_force:
        cmd.append("--force")
    run_step(cmd)

    produced = asset_dir / "ref.png"
    if not produced.exists():
        die(f"stage 0 reported success but ref.png missing at {produced}", code=2)
    args.image = str(produced)


def maybe_refine_ref(args: argparse.Namespace, ctx: PipelineContext) -> None:
    """
    Stage 0.25 — run refine_ref_image.py to push ref.png through FLUX.2 [klein].

    Always-on for `--kind mesh|animated` unless the caller passed
    `--no-refine-ref`. Idempotent: the refine script no-ops when
    `ref.original.png` already exists, so running the orchestrator twice
    against the same asset does not double-refine.

    Strength resolution:
      1. If `--refine-ref-strength` is set on the CLI, use it.
      2. Otherwise look up the per-category default in
         `REFINE_STRENGTH_BY_CATEGORY`.
      3. Fallback to `DEFAULT_REFINE_STRENGTH` for unknown categories.

    Downstream stages (multi-view, Hunyuan) continue to read `ref.png` —
    they're oblivious to whether stage 0.25 ran. The audit copy lives at
    `ref.original.png` (created by refine_ref_image.py).
    """
    if args.kind not in ("mesh", "animated"):
        return
    if args.no_refine_ref:
        return

    asset_dir = REPO_ROOT / "prompts" / "asset-templates" / ctx.asset_id
    ref = asset_dir / "ref.png"
    if not ref.exists():
        die(
            f"stage 0.25 requires {ref.relative_to(REPO_ROOT)}; "
            "either drop a hand-picked ref.png or pass --auto-ref to "
            "synthesise one in stage 0 first.",
            code=1,
        )

    strength = (
        args.refine_ref_strength
        if args.refine_ref_strength is not None
        else refine_strength_for(ctx.asset_id)
    )
    step(f"0.25/5 refine ref image (FLUX.2 [klein], denoise={strength:.2f})")
    cmd = [
        sys.executable,
        str(TOOLS_DIR / "refine_ref_image.py"),
        ctx.asset_id,
        "--strength",
        f"{strength:.4f}",
        "--seed",
        str(args.refine_ref_seed),
        "--server",
        args.comfy_server,
    ]
    if args.refine_ref_force:
        cmd.append("--force")
    if args.refine_ref_prompt_suffix:
        cmd.extend(["--prompt-suffix", args.refine_ref_prompt_suffix])
    run_step(cmd)

    # refine_ref_image.py writes the refined output back to ref.png and
    # leaves an audit copy at ref.original.png. branch_mesh will keep
    # using `args.image` (which still points at ref.png), so nothing to
    # rewrite here.


def maybe_multi_view(args: argparse.Namespace, ctx: PipelineContext) -> list[Path]:
    """
    Stage 0.5 — Zero123++ multi-view synthesis from the ref.png.

    Runs only when ``--multi-view`` is set. Emits six 320² view PNGs to
    ``prompts/asset-templates/<id>/views/view_{0..5}.png``. The returned
    list is empty when the stage is skipped — callers fall back to the
    single-image path in that case.

    Idempotent: if six views already exist the script no-ops (use
    ``--multi-view-force`` to regenerate).
    """
    if not args.multi_view:
        return []
    if args.kind not in ("mesh", "animated"):
        return []

    asset_dir = REPO_ROOT / "prompts" / "asset-templates" / ctx.asset_id
    ref = asset_dir / "ref.png"
    if not ref.exists():
        die(
            f"--multi-view requires {ref.relative_to(REPO_ROOT)}; "
            "run stage 0 first (or pass --auto-ref).",
            code=1,
        )

    step("0.5/5 multi-view synthesis (Zero123++ v1.2)")
    mv_python = Path(args.multi_view_python)
    if not mv_python.exists():
        die(
            f"--multi-view-python {mv_python} does not exist. Install "
            "diffusers + torch into a venv (project default expects "
            f"{MULTI_VIEW_PYTHON_DEFAULT}) or pass --multi-view-python "
            "<path-to-python>.",
            code=1,
        )
    cmd = [
        str(mv_python),
        str(TOOLS_DIR / "generate_multi_views.py"),
        ctx.asset_id,
        "--seed",
        str(args.multi_view_seed),
        "--steps",
        str(args.multi_view_steps),
        "--guidance",
        str(args.multi_view_guidance),
        "--dtype",
        args.multi_view_dtype,
    ]
    if args.multi_view_force:
        cmd.append("--force")
    run_step(cmd)

    views_dir = asset_dir / "views"
    views = sorted(views_dir.glob("view_*.png"))
    if not views:
        die(f"stage 0.5 reported success but no view_*.png in {views_dir}", code=2)
    info(f"stage 0.5 produced {len(views)} views")
    return views


def branch_mesh(args: argparse.Namespace, ctx: PipelineContext) -> Path:
    """Hunyuan3D → bake → Draco/KTX2 → LODs → collision → export."""
    maybe_auto_ref(args, ctx)
    if not args.image:
        die("--kind mesh requires --image <path> (or --auto-ref to generate one)")
    image = Path(args.image).resolve()
    if not image.exists():
        die(f"reference image not found: {image}")

    # Stage 0.25 runs between ref acquisition and multi-view synthesis. It
    # rewrites ref.png in place (archiving the source as ref.original.png)
    # so the rest of branch_mesh keeps reading the same path it was about
    # to read anyway.
    maybe_refine_ref(args, ctx)

    views = maybe_multi_view(args, ctx)

    glb_dir = PROCESSED / "glb"
    ensure_dir(glb_dir)
    raw_dir = glb_dir / "raw"
    ensure_dir(raw_dir)

    step("1/5 generate (Hunyuan3D 2.1)")
    gen_cmd = [
        sys.executable,
        str(TOOLS_DIR / "generate_asset.py"),
        str(image),
        ctx.asset_id,
        "--steps",
        str(args.steps),
        "--server",
        args.server,
        "--output-dir",
        str(raw_dir),
    ]
    if views:
        # Pass the multi-view list to generate_asset.py via a repeated
        # --view flag. The first positional arg (image) is still required
        # so generate_asset.py can fall back to single-image submit when
        # the worker rejects the list payload.
        for v in views:
            gen_cmd.extend(["--view", str(v)])
    run_step(gen_cmd)
    raw_glb = raw_dir / f"{ctx.asset_id}.glb"
    if not raw_glb.exists():
        die(f"expected raw GLB at {raw_glb} but it was not produced", code=2)

    bake_input = raw_glb
    if args.auto_texture:
        step("1.5/5 PBR bake (Blender Cycles)")
        textured = glb_dir / f"{ctx.asset_id}.textured.glb"
        bake_cmd = [
            sys.executable,
            str(TOOLS_DIR / "texture_asset.py"),
            ctx.asset_id,
            "--glb",
            str(raw_glb),
            "--family",
            args.texture_family,
            "--texture-size",
            str(args.texture_size),
            "--view-size",
            str(args.view_size),
            "--samples",
            str(args.bake_samples),
            "--output-glb",
            str(textured),
        ]
        if args.skip_views:
            bake_cmd.append("--skip-views")
        if args.ai_project:
            bake_cmd.extend(["--ai-project", "--comfy-server", args.comfy_server])
        run_step(bake_cmd)
        if not textured.exists():
            die(f"Stage 2 reported success but {textured.name} missing", code=2)
        bake_input = textured

    step("2/5 optimize (Draco + KTX2)")
    optimized = glb_dir / f"{ctx.asset_id}.glb"
    run_step(
        [
            sys.executable,
            str(TOOLS_DIR / "optimize_asset.py"),
            str(bake_input),
            "--draco-level",
            str(args.draco_level),
        ]
    )
    # optimize_asset.py writes <stem>.optimized.glb beside the input — promote
    # it to <id>.glb so downstream tools and runtime use a single canonical name.
    optimized_intermediate = bake_input.with_stem(bake_input.stem + ".optimized")
    if optimized_intermediate.exists():
        shutil.move(str(optimized_intermediate), str(optimized))
    elif bake_input.exists() and not optimized.exists():
        # optimizer was a no-op (tool missing); still promote so the rest of
        # the chain has a stable filename to work from.
        shutil.copy2(str(bake_input), str(optimized))

    step("3/5 LOD generation (placeholder)")
    info("LOD0 stored as <id>.glb. lod1/lod2 require generate_lods.py (TBD).")
    info(
        "Until generate_lods.py lands, the runtime AssetLibrary tolerates "
        "missing LODs (warns, uses LOD0)."
    )

    step("4/5 collision hull (placeholder)")
    info("V-HACD step requires generate_collision.py (TBD).")
    info("AssetLibrary callers can fall back to mesh.checkCollisions = true.")

    if args.validation_renders:
        step("4.5/5 validation renders (Blender Cycles, 3-point + HDRI)")
        renders_dir = REPO_ROOT / "processed" / "renders" / ctx.asset_id
        render_cmd = [
            shutil.which("blender") or "blender",
            "--background",
            "--factory-startup",
            "--python",
            str(TOOLS_DIR / "blender" / "render_validation.py"),
            "--",
            "--glb",
            str(bake_input),  # textured GLB if stage 2 ran, raw otherwise
            "--asset-id",
            ctx.asset_id,
            "--renders-dir",
            str(renders_dir),
            "--samples",
            str(args.render_samples),
            "--resolution",
            str(args.render_resolution),
        ]
        if args.hdri:
            render_cmd.extend(["--hdri", args.hdri])
        run_step(render_cmd)

    step("5/5 register + export")
    run_step(
        [
            sys.executable,
            str(TOOLS_DIR / "register_asset.py"),
            ctx.asset_id,
            ctx.era,
            "--glb-path",
            str(optimized),
        ]
    )
    public_path = copy_to_public(optimized, f"{ctx.asset_id}.glb")
    return public_path


def branch_animated(args: argparse.Namespace, ctx: PipelineContext) -> Path:
    """Mesh branch + skeletal rig embed."""
    if not args.image:
        die("--kind animated requires --image <path>")
    if not args.rig:
        die("--kind animated requires --rig <path-to-blend-or-fbx>")
    rig = Path(args.rig).resolve()
    if not rig.exists():
        die(f"rig file not found: {rig}")
    info("animated branch: running mesh branch first")
    public_path = branch_mesh(args, ctx)
    step("animated extras: embed skeleton + AnimationGroups")
    info(
        "Skeleton + AnimationGroup embedding requires Blender headless export. "
        "Run `python tools/blender_animate.py` (TBD) on the produced GLB. "
        "Without it, the GLB ships geometry-only — runtime will see no animations."
    )
    return public_path


def branch_splat(args: argparse.Namespace, ctx: PipelineContext) -> Path:
    """Normalise a Gaussian splat capture and copy into the runtime tree."""
    if not args.source:
        die("--kind splat requires --source <path-to-.ply|.splat|.spz|.sog>")
    src = Path(args.source).resolve()
    if not src.exists():
        die(f"splat source not found: {src}")
    if src.suffix.lower() not in SPLAT_EXTS:
        die(f"splat source must be one of {SPLAT_EXTS}: {src}")

    splats_dir = PROCESSED / "splats"
    ensure_dir(splats_dir)
    dest = splats_dir / f"{ctx.asset_id}{src.suffix.lower()}"
    shutil.copy2(src, dest)
    info(f"copied splat → {dest.relative_to(REPO_ROOT)}")

    # Babylon's splat loader auto-detects format from file extension; nothing
    # to convert at this stage. A future pass can normalise everything to
    # .spz via splat-transform (see ASSET_PIPELINE.md §3.2 link).
    public_dest = copy_to_public(dest, dest.name)

    append_index_row(ctx.row(dest))
    return public_dest


def branch_tileset(args: argparse.Namespace, ctx: PipelineContext) -> Path:
    """Register a 3D Tileset reference (root URL or local tileset.json)."""
    if not args.root:
        die("--kind tileset requires --root <url-or-path-to-tileset.json>")

    tilesets_dir = PROCESSED / "tilesets"
    ensure_dir(tilesets_dir)
    record = {
        "asset_id": ctx.asset_id,
        "kind": "tileset",
        "era": ctx.era,
        "root": args.root,
        "registered": ctx.today,
    }
    record_path = tilesets_dir / f"{ctx.asset_id}.tileset.json"
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    info(f"wrote tileset record → {record_path.relative_to(REPO_ROOT)}")

    public_dest = copy_to_public(record_path, f"{ctx.asset_id}.tileset.json")
    append_index_row(ctx.row(record_path))
    return public_dest


def branch_navmesh(args: argparse.Namespace, ctx: PipelineContext) -> Path:
    """
    Record the navmesh source GLBs + parameters. Actual recast computation
    runs in the browser (RecastJSPlugin); the runtime can serialise the result
    via NavigationPlugin.getNavmeshData() and we cache it as `<id>.nav.bin`
    via `engine/Navigation.ts` (deferred — script writes the manifest only).
    """
    if not args.terrain:
        die("--kind navmesh requires at least one --terrain <glb-path>")

    sources: list[str] = []
    for t in args.terrain:
        p = Path(t).resolve()
        if not p.exists():
            die(f"terrain GLB not found: {p}")
        sources.append(str(p.relative_to(REPO_ROOT)))

    navmesh_dir = PROCESSED / "navmeshes"
    ensure_dir(navmesh_dir)
    record_path = navmesh_dir / f"{ctx.asset_id}.navmesh.json"
    record = {
        "asset_id": ctx.asset_id,
        "kind": "navmesh",
        "era": ctx.era,
        "sources": sources,
        "recastParameters": {
            "cs": 0.2,
            "ch": 0.2,
            "walkableSlopeAngle": 35,
            "walkableHeight": 2,
            "walkableClimb": 1,
            "walkableRadius": 1,
            "maxEdgeLen": 12,
            "maxSimplificationError": 1.3,
            "minRegionArea": 8,
            "mergeRegionArea": 20,
            "maxVertsPerPoly": 6,
            "detailSampleDist": 6,
            "detailSampleMaxError": 1,
        },
        "registered": ctx.today,
    }
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    info(f"wrote navmesh record → {record_path.relative_to(REPO_ROOT)}")

    public_dest = copy_to_public(record_path, f"{ctx.asset_id}.navmesh.json")
    append_index_row(ctx.row(record_path))
    return public_dest


def branch_nme(args: argparse.Namespace, ctx: PipelineContext) -> Path:
    """Register a Node Material Editor JSON snapshot."""
    if not args.source:
        die("--kind nme requires --source <path-to-.nme.json>")
    src = Path(args.source).resolve()
    if not src.exists():
        die(f"NME source not found: {src}")
    if src.suffix.lower() != ".json":
        die(f"NME source must end in .json: {src}")

    materials_dir = PROCESSED / "materials"
    ensure_dir(materials_dir)
    dest = materials_dir / f"{ctx.asset_id}.nme.json"
    try:
        json.loads(src.read_text())
    except json.JSONDecodeError as exc:
        die(f"NME source is not valid JSON: {exc}")
    shutil.copy2(src, dest)
    info(f"copied NME → {dest.relative_to(REPO_ROOT)}")

    public_dest = copy_to_public(dest, dest.name)
    append_index_row(ctx.row(dest))
    return public_dest


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single entry point for the Witness Interactive 3D asset pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("asset_id", help="Snake_case asset id (e.g. prop_jerrycan_weathered)")
    parser.add_argument(
        "--kind",
        required=True,
        choices=VALID_KINDS,
        help="Asset kind. See `.claude/rules/asset-pipeline.md` for the decision tree.",
    )
    parser.add_argument(
        "--era",
        default="shared",
        choices=VALID_ERAS,
        help="Era scope tag applied at instantiate time (default: shared)",
    )
    parser.add_argument(
        "--source",
        help="Source artefact (image / splat / NME JSON / etc.) depending on kind",
    )

    # mesh / animated
    parser.add_argument("--image", help="Reference image (mesh, animated)")
    parser.add_argument("--steps", type=int, default=20, help="Hunyuan inference steps (API max: 20)")
    parser.add_argument(
        "--server",
        default="http://localhost:8081",
        help="Hunyuan3D Docker server URL",
    )
    parser.add_argument("--draco-level", type=int, default=7)
    parser.add_argument("--rig", help="Skeletal rig blend/fbx (animated kind only)")

    # stage 3 (Blender validation renders)
    parser.add_argument(
        "--validation-renders",
        action="store_true",
        help="Run stage 3 (Blender 3-point + HDRI) to emit 4 turntable + 1 hero PNG.",
    )
    parser.add_argument(
        "--hdri",
        default=None,
        help="HDRI/EXR path for stage 3 world environment (omit for procedural Sky Texture).",
    )
    parser.add_argument("--render-samples", type=int, default=256)
    parser.add_argument("--render-resolution", type=int, default=1024)

    # stage 2 (Blender Cycles PBR bake + optional AI projection)
    parser.add_argument(
        "--auto-texture",
        action="store_true",
        help="Run stage 2 (Blender Cycles PBR bake) on the raw GLB before optimisation.",
    )
    parser.add_argument(
        "--texture-family",
        default="auto",
        help="Material family override for stage 2 (default: auto-pick from asset_id).",
    )
    parser.add_argument("--texture-size", type=int, default=8192, help="PBR map size (default 8192).")
    parser.add_argument("--view-size", type=int, default=1024, help="Per-view render resolution for stage 2b.")
    parser.add_argument("--bake-samples", type=int, default=128, help="Cycles samples per bake/view.")
    parser.add_argument("--skip-views", action="store_true", help="Skip the 6-view render during stage 2 (faster iteration).")
    parser.add_argument(
        "--ai-project",
        action="store_true",
        default=True,
        help="Run stage 2b (SDXL + ControlNet depth) AI texture projection. Requires ComfyUI. ON by default.",
    )
    parser.add_argument(
        "--no-ai-project",
        dest="ai_project",
        action="store_false",
        help="Skip the SDXL AI projection step (procedural bake only, faster).",
    )

    # stage 0 (ComfyUI + Flux.1 [dev])
    parser.add_argument(
        "--auto-ref",
        action="store_true",
        help="Run stage 0 (ComfyUI + Flux.1 [dev]) to generate ref.png before Hunyuan if no ref exists.",
    )
    parser.add_argument(
        "--auto-ref-force",
        action="store_true",
        help="With --auto-ref, regenerate ref.png even if one already exists.",
    )
    parser.add_argument(
        "--auto-ref-workflow",
        default="default",
        help="Flux workflow name in prompts/_flux_workflows/ (default: default; hero: 1536² / 40 steps).",
    )
    parser.add_argument(
        "--auto-ref-seed",
        type=int,
        default=481109,
        help="Flux noise seed used by stage 0 (default: 481109).",
    )
    parser.add_argument(
        "--comfy-server",
        default="http://localhost:8188",
        help="ComfyUI HTTP server URL for stage 0 (default: %(default)s).",
    )

    # stage 0.25 (FLUX.2 [klein] ref refinement — always on for mesh/animated)
    parser.add_argument(
        "--no-refine-ref",
        action="store_true",
        help=(
            "Skip stage 0.25 (FLUX.2 [klein] img2img refinement of ref.png). "
            "By default the orchestrator pushes every mesh/animated ref through "
            "FLUX.2 klein with a per-category denoise strength to normalise the "
            "Digital Diorama look. Pass --no-refine-ref when iterating on a "
            "ref.png that is already on-style and you do not want compounding."
        ),
    )
    parser.add_argument(
        "--refine-ref-force",
        action="store_true",
        help=(
            "Re-run stage 0.25 even when ref.original.png already exists. "
            "Without this, the refine script treats the archive copy as a "
            "completion marker and no-ops."
        ),
    )
    parser.add_argument(
        "--refine-ref-strength",
        type=float,
        default=None,
        help=(
            "Override the per-category default denoise strength (0..1). "
            "Defaults: vegetation 0.60, prop/figure 0.50, structure 0.40. "
            "Higher pushes harder toward Digital Diorama at the cost of "
            "geometric fidelity to the source ref."
        ),
    )
    parser.add_argument(
        "--refine-ref-seed",
        type=int,
        default=481109,
        help="FLUX.2 klein noise seed for stage 0.25 (default: 481109).",
    )
    parser.add_argument(
        "--refine-ref-prompt-suffix",
        default=None,
        help=(
            "Override the canonical Digital Diorama refine suffix for stage "
            "0.25. Use only for one-off experiments — for permanent changes, "
            "edit REFINE_PROMPT_SUFFIX in tools/refine_ref_image.py and "
            "_STYLE_GUIDE.md together."
        ),
    )

    # stage 0.5 (Zero123++ multi-view synthesis)
    parser.add_argument(
        "--multi-view",
        action="store_true",
        help=(
            "Run stage 0.5 (Zero123++ v1.2) to synthesise 6 canonical views "
            "from ref.png and feed them to Hunyuan as a list. Produces more "
            "complete geometry (less flat-top, fewer missing facets) than "
            "single-view conditioning. Requires diffusers + torch."
        ),
    )
    parser.add_argument(
        "--multi-view-force",
        action="store_true",
        help="With --multi-view, regenerate view PNGs even if six already exist.",
    )
    parser.add_argument(
        "--multi-view-seed",
        type=int,
        default=481109,
        help="Zero123++ noise seed (default: 481109, matches stage 0).",
    )
    parser.add_argument(
        "--multi-view-steps",
        type=int,
        default=75,
        help="Zero123++ diffusion steps (default: 75; range 50-100).",
    )
    parser.add_argument(
        "--multi-view-guidance",
        type=float,
        default=4.0,
        help="Zero123++ guidance scale (default: 4.0).",
    )
    parser.add_argument(
        "--multi-view-dtype",
        default="fp16",
        choices=("fp16", "bf16", "fp32"),
        help="Zero123++ pipeline dtype (default: fp16).",
    )
    parser.add_argument(
        "--multi-view-python",
        default=os.environ.get("WITNESS_MULTI_VIEW_PYTHON", MULTI_VIEW_PYTHON_DEFAULT),
        help=(
            "Python interpreter used to run stage 0.5. Must have diffusers + "
            "torch installed (Zero123++ depends on both). Default: ComfyUI's "
            "venv since it already carries the CUDA-wheel torch from stage 0. "
            "Persistent override: env var WITNESS_MULTI_VIEW_PYTHON."
        ),
    )

    # tileset
    parser.add_argument("--root", help="3D Tileset root URL or local tileset.json (tileset kind)")

    # navmesh
    parser.add_argument(
        "--terrain",
        action="append",
        help="Terrain/ground GLB(s) to seed the navmesh (navmesh kind, repeatable)",
    )

    return parser.parse_args(argv)


def make_source_string(args: argparse.Namespace) -> str:
    if args.kind in ("mesh", "animated"):
        return Path(args.image).name if args.image else "(no source)"
    if args.kind == "splat":
        return Path(args.source).name if args.source else "(no source)"
    if args.kind == "tileset":
        return args.root or "(no root)"
    if args.kind == "navmesh":
        return ", ".join(args.terrain or []) or "(no terrain)"
    if args.kind == "nme":
        return Path(args.source).name if args.source else "(no source)"
    return "(unknown)"


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(list(argv) if argv is not None else None)
    validate_id(args.asset_id)

    today = datetime.now().strftime("%Y-%m-%d")
    ctx = PipelineContext(
        asset_id=args.asset_id,
        kind=args.kind,
        era=args.era,
        source=make_source_string(args),
        today=today,
    )

    banner(
        f"Witness Asset Pipeline\n"
        f"  id:    {ctx.asset_id}\n"
        f"  kind:  {ctx.kind}\n"
        f"  era:   {ctx.era}\n"
        f"  src:   {ctx.source}"
    )

    branches = {
        "mesh": branch_mesh,
        "animated": branch_animated,
        "splat": branch_splat,
        "tileset": branch_tileset,
        "navmesh": branch_navmesh,
        "nme": branch_nme,
    }
    fn = branches[args.kind]
    artefact = fn(args, ctx)

    banner("done")
    info(f"runtime artefact: {artefact.relative_to(REPO_ROOT)}")
    info(f"registry:         {ASSET_INDEX.relative_to(REPO_ROOT)}")
    info("next: import via the appropriate runtime library")
    info("  mesh / animated → AssetLibrary.preload([\"" + ctx.asset_id + "\"])")
    info("  splat           → splatLibrary.load(\"" + ctx.asset_id + "\")")
    info("  tileset         → tilesetMount.attach(\"" + ctx.asset_id + "\", root)")
    info("  navmesh         → engine/Navigation.ts (build at scene init)")
    info("  nme             → MaterialLibrary.loadNode(\"" + ctx.asset_id + "\")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
