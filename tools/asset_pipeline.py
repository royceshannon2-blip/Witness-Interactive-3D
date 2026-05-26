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
import time
from dataclasses import dataclass, field
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

# Validation gates share the ComfyUI venv (trimesh + PIL + numpy +
# optional torch for CLIP) because all three are CPU-cheap and the
# project Python already has a venv pinned for the rest of the
# pipeline. If WITNESS_GATE_PYTHON is set, that takes precedence so
# CI / Docker can swap in a minimal trimesh-only venv to keep image
# size down.
GATE_PYTHON = os.environ.get("WITNESS_GATE_PYTHON", MULTI_VIEW_PYTHON_DEFAULT)
DIAGNOSTICS_DIR = PROCESSED / "diagnostics"

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


def flush_comfy_vram(server: str, wait: float = 5.0) -> None:
    """
    Ask ComfyUI to unload all models from VRAM before the next GPU-heavy stage.

    Calls POST /free with unload_models=True. Without this, Flux/FLUX.2 models
    (~14-22 GB) remain in VRAM when Hunyuan or Blender start, causing OOM on the
    32 GB RTX 5090. The `wait` sleep gives the CUDA runtime time to actually
    release pages after PyTorch drops the tensors.
    """
    try:
        import requests as _req  # optional dep — only needed for flush
        r = _req.post(
            f"{server}/free",
            json={"unload_models": True, "free_memory": True},
            timeout=15,
        )
        if r.status_code == 200:
            info(f"ComfyUI VRAM flushed — waiting {wait:.0f}s for CUDA release")
            time.sleep(wait)
        else:
            info(f"ComfyUI /free returned {r.status_code} — proceeding anyway")
    except Exception as exc:
        info(f"ComfyUI VRAM flush skipped (ComfyUI not reachable): {exc}")


def run_step(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a subprocess and surface its exit status."""
    info(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or REPO_ROOT)
    if result.returncode != 0:
        die(f"Subcommand failed: {' '.join(cmd)} (exit {result.returncode})", code=2)


def run_gate(
    label: str,
    cmd: list[str],
    asset_id: str,
    skip_gates: bool,
) -> int:
    """
    Run one validation gate as a subprocess and return its exit code.

    Unlike `run_step`, this does NOT call `die()` on failure — the
    caller decides whether a gate failure halts the pipeline (default)
    or feeds the retry harness (Phase F). When `skip_gates` is set the
    gate is logged-and-skipped, so an operator can force a build past
    a known false-positive without ripping out the wiring.
    """
    if skip_gates:
        info(f"gate '{label}' skipped (--skip-gates) for {asset_id}")
        return 0
    info(f"[gate] {label} :: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def emit_diagnostic_report(asset_id: str) -> int:
    """
    Run `diagnostic_report.py` to aggregate whatever sidecars exist.

    Always invoked at end-of-branch so the operator gets a unified
    artefact even when an earlier gate halted the pipeline. The
    aggregator's exit code is returned so the orchestrator can
    propagate it as the final pipeline status.
    """
    cmd = [
        GATE_PYTHON,
        str(TOOLS_DIR / "diagnostic_report.py"),
        asset_id,
        "--diagnostics-dir",
        str(DIAGNOSTICS_DIR),
    ]
    info(f"[report] {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


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

                | Asset ID | Kind | Path | Era | Source | Registered | Faces | Gates |
                |---|---|---|---|---|---|---|---|
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
    # Phase E (multi-seed ensemble) populates these inside branch_mesh after
    # run_stage1_ensemble returns. Surfaced via Gate 2's geometry sidecar so
    # the aggregate report and the Phase F retry harness can see every
    # candidate's score, not just the winner.
    ensemble_records: list[dict] = field(default_factory=list)
    ensemble_winning_seed: int | None = None

    def row(self, path: Path | str) -> str:
        rel = path if isinstance(path, str) else str(path.relative_to(REPO_ROOT))
        return (
            f"| {self.asset_id} | {self.kind} | {rel} | {self.era} | "
            f"{self.source} | {self.today} | n/a | n/a |"
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

    # Flush ComfyUI VRAM before Zero123++: stages 0 and 0.25 may have left
    # Flux/FLUX.2 models in VRAM (~11-22 GB). Zero123++ fp16 needs ~3-4 GB;
    # on a 32 GB card with the Hunyuan daemon also loaded (~15 GB) there is
    # no headroom without this flush.
    flush_comfy_vram(args.comfy_server, wait=8.0)

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

    # Gate 1 — pre-Hunyuan synth-view validation. Catches a bad
    # Zero123++ run (black / flat-grey / over-noised views) BEFORE we
    # spend 5–10 minutes feeding garbage into Hunyuan. The sidecar key
    # is `synth_views` (distinct from the post-bake `views`) so the
    # diagnostic aggregator can show both stages in the same report.
    ensure_dir(DIAGNOSTICS_DIR)
    synth_cmd = [
        GATE_PYTHON,
        str(TOOLS_DIR / "validate_views.py"),
        str(views_dir),
        "--asset-id",
        ctx.asset_id,
        "--indexed",
        "--report",
        str(DIAGNOSTICS_DIR / f"{ctx.asset_id}.synth_views.json"),
        # CLIP semantic gate runs here on purpose: a slab-source / wrong-
        # subject synth view (which the cheap luminance/coverage stats pass)
        # is exactly what we want to catch BEFORE the 5–10 min Hunyuan
        # ensemble. CLIP_MODEL_ID downloads once (~600 MB) then is cached;
        # inference on 6 views is ~1 s on-GPU — negligible vs the stage it gates.
    ]
    if run_gate("Gate 1 (synth views)", synth_cmd, ctx.asset_id, args.skip_gates) != 0:
        emit_diagnostic_report(ctx.asset_id)
        die(
            f"Gate 1 failed for {ctx.asset_id} — see "
            f"processed/diagnostics/{ctx.asset_id}.report.md. Zero123++ "
            "synth views are unfit for Hunyuan conditioning; halting "
            "before stage 1 to save GPU time. Re-run stage 0.5 with a "
            "different --multi-view-seed or fix the ref.png upstream.",
            code=2,
        )
    return views


def _detect_real_views(args: argparse.Namespace, ctx: PipelineContext) -> list[Path]:
    """
    Locate a real multi-angle capture set, if the author supplied one.

    Source precedence: explicit ``--real-views DIR`` first, else the
    convention dir ``prompts/asset-templates/<id>/real_views/``. Returns the
    sorted image files (png/jpg) or [] when none are present. Real views are
    the highest-fidelity input for all-angle accuracy — observed, not
    hallucinated — so when present we feed them straight to Hunyuan and skip
    Zero123++ synthesis.
    """
    src: Path | None = None
    if getattr(args, "real_views", None):
        src = Path(args.real_views).resolve()
        if not src.is_dir():
            die(f"--real-views {src} is not a directory", code=1)
    else:
        auto = REPO_ROOT / "prompts" / "asset-templates" / ctx.asset_id / "real_views"
        if auto.is_dir():
            src = auto
    if src is None:
        return []
    return sorted(
        p for p in src.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )


def resolve_views(
    args: argparse.Namespace, ctx: PipelineContext, real_views: list[Path]
) -> list[Path]:
    """
    Produce the multi-view set fed to Hunyuan.

    Real views (when supplied) win over synthesis: they are staged into the
    canonical views/ dir as view_0..N.png, validated by the same Gate 1 the
    synth path uses (now count-flexible), and returned — Zero123++ is skipped
    entirely. Otherwise fall back to ``maybe_multi_view`` (synthesis, gated on
    --multi-view).
    """
    if not real_views:
        return maybe_multi_view(args, ctx)
    if args.kind not in ("mesh", "animated"):
        return []

    step(
        f"0.5/5 real multi-view — {len(real_views)} supplied angle(s); "
        "skipping Zero123++ synthesis"
    )
    src_dir = real_views[0].parent  # _detect_real_views returns files from one dir
    asset_dir = REPO_ROOT / "prompts" / "asset-templates" / ctx.asset_id
    views_dir = asset_dir / "views"

    # Clean + frame the captures via generate_multi_views, run under the ML venv
    # so rembg is importable — the orchestrator itself runs under the system
    # python (no rembg). This applies the SAME background removal + framing as
    # synthesis; staging raw photos would carry their real-world backgrounds
    # into Hunyuan and reproduce the slab artefact we fixed for the synth path.
    mv_python = Path(args.multi_view_python)
    if not mv_python.exists():
        die(
            f"real views need {mv_python} for background removal (rembg lives in "
            "the ML venv). Install diffusers/rembg there or pass "
            "--multi-view-python <path>.",
            code=1,
        )
    stage_cmd = [
        str(mv_python),
        str(TOOLS_DIR / "generate_multi_views.py"),
        ctx.asset_id,
        "--real-views",
        str(src_dir),
        "--force",
    ]
    if getattr(args, "no_remove_bg", False):
        stage_cmd.append("--no-remove-bg")
    run_step(stage_cmd)

    staged = sorted(views_dir.glob("view_*.png"))
    if not staged:
        die(f"real-view staging produced no view_*.png in {views_dir}", code=2)
    info(f"staged {len(staged)} real view(s) → {views_dir.relative_to(REPO_ROOT)}")

    # Gate 1 — same semantic/quality validation the synth path uses (now
    # count-flexible). A black or corrupt real capture still fails fast.
    ensure_dir(DIAGNOSTICS_DIR)
    gate_cmd = [
        GATE_PYTHON,
        str(TOOLS_DIR / "validate_views.py"),
        str(views_dir),
        "--asset-id",
        ctx.asset_id,
        "--indexed",
        "--report",
        str(DIAGNOSTICS_DIR / f"{ctx.asset_id}.synth_views.json"),
    ]
    if run_gate("Gate 1 (real views)", gate_cmd, ctx.asset_id, args.skip_gates) != 0:
        emit_diagnostic_report(ctx.asset_id)
        die(
            f"Gate 1 failed for {ctx.asset_id} — one or more supplied real "
            f"views are unfit (see processed/diagnostics/{ctx.asset_id}.report.md). "
            "Replace the bad capture(s) and re-run.",
            code=2,
        )
    return staged


# ---------------------------------------------------------------------------
# Stage 1 ensemble — multi-seed Hunyuan + best-candidate selection (Phase E)
# ---------------------------------------------------------------------------


def _score_candidate(metrics: dict) -> float:
    """
    Composite quality score for one Hunyuan candidate (higher is better).

    Why a composite: the geometry validator's binary `valid` boolean already
    halts on hard failures (depth-card bbox, missing manifold under
    strict-manifold). For *picking among passes*, we want a continuous
    score that rewards:

      * depth ratio further above the threshold (more "3D-ness");
      * face count closer to the template target (the ratio is centred at 1.0);
      * lower centroid offset (better-centred output, easier to bake);
      * watertight bonus (manifold meshes survive Draco compression cleanly).

    Weights are picked so depth ratio dominates (it's the single failure
    mode that has cost the project most rebake time per the canary
    diagnostics), centroid is a small tiebreaker, and the manifold bonus
    is binary (+0.10).
    """
    score = 0.0
    depth = float(metrics.get("bbox_depth_ratio", 0.0))
    score += depth * 3.0
    face_window = metrics.get("face_budget_window") or [0, 0]
    face_count = float(metrics.get("face_count", 0))
    if face_window[1] > 0:
        midpoint = (face_window[0] + face_window[1]) / 2.0
        ratio = face_count / midpoint if midpoint else 0.0
        # Penalise distance from the midpoint of the budget window. A
        # candidate hitting the centre of the window scores 1.0; one at
        # 2× or 0.5× scores ~0.5.
        score += max(0.0, 1.0 - abs(ratio - 1.0)) * 1.0
    offsets = metrics.get("centroid_offset_ratios") or []
    if offsets:
        score += (1.0 - min(max(max(offsets), 0.0), 1.0)) * 0.4
    if metrics.get("manifold"):
        score += 0.10
    return score


def run_stage1_ensemble(
    gen_cmd_template: list[str],
    asset_id: str,
    raw_dir: Path,
    base_seed: int,
    ensemble_size: int,
    strict_manifold: bool,
    skip_gates: bool,
) -> tuple[Path, int, list[dict]]:
    """
    Run Hunyuan N times with distinct seeds, score each candidate, return
    the winner.

    `gen_cmd_template` is the full `generate_asset.py` argv *without* the
    seed argument; this function appends `--seed <n>` per iteration. Each
    candidate is generated into ``raw_dir/.ensemble/<asset_id>/seed_<n>.glb``;
    on completion the winner is copied to ``raw_dir/<asset_id>.glb`` so
    downstream stages remain blissfully unaware of the ensemble.

    Returns (winning_glb_path, winning_seed, ensemble_records) where
    ensemble_records is a list of dicts with keys
    {seed, glb, valid, score, metrics, failures} — one per attempt. The
    caller writes that list into the geometry sidecar so the diagnostic
    report and the Phase F retry harness can both see what happened.

    A single candidate (ensemble_size=1) still flows through this path —
    the geometry validator runs once, the winner is the only entry, and
    the .ensemble/ archive is populated for consistency. This keeps the
    Phase F retry semantics uniform.
    """
    sys.path.insert(0, str(TOOLS_DIR))
    import validate_geometry  # noqa: E402 — late import keeps tool deps optional

    ensemble_dir = raw_dir / ".ensemble" / asset_id
    ensure_dir(ensemble_dir)

    records: list[dict] = []
    info(f"  ensemble: {ensemble_size} seed(s) starting at {base_seed}")
    for idx in range(ensemble_size):
        seed = base_seed + idx
        candidate_glb = ensemble_dir / f"seed_{seed}.glb"
        info(f"  ── candidate {idx + 1}/{ensemble_size}: seed={seed}")
        cmd = list(gen_cmd_template) + [
            "--seed", str(seed),
            "--output-dir", str(ensemble_dir),
        ]
        # generate_asset.py writes to <output-dir>/<asset_id>.glb; rename
        # to the per-seed name immediately so the next iteration doesn't
        # clobber it. This is simpler than threading a custom output path
        # through generate_asset.py.
        produced = ensemble_dir / f"{asset_id}.glb"
        if produced.exists():
            produced.unlink()
        run_step(cmd)
        if not produced.exists():
            records.append({
                "seed": seed,
                "glb": str(candidate_glb),
                "valid": False,
                "score": float("-inf"),
                "metrics": {},
                "failures": [f"generate_asset.py produced no GLB for seed {seed}"],
            })
            continue
        produced.rename(candidate_glb)

        report = validate_geometry.validate_geometry(
            candidate_glb,
            asset_id=asset_id,
            strict_manifold=strict_manifold,
        )
        score = _score_candidate(report.metrics) if report.valid else float("-inf")
        records.append({
            "seed": seed,
            "glb": str(candidate_glb),
            "valid": report.valid,
            "score": score,
            "metrics": report.metrics,
            "failures": list(report.failures),
        })
        verdict = "PASS" if report.valid else "FAIL"
        info(f"     → seed {seed}: {verdict}  score={score:.4f}")

    valid_records = [r for r in records if r["valid"]]
    if not valid_records and not skip_gates:
        # Every candidate failed Gate 2. Pick the highest-bbox one so the
        # diagnostic report has something to chew on, but emit a clear
        # FAIL for the caller / Phase F retry harness.
        fallback = max(
            records,
            key=lambda r: float(r["metrics"].get("bbox_depth_ratio", -1.0)),
            default=records[0] if records else None,
        )
        if fallback is None:
            die(f"Stage 1 ensemble produced zero candidates for {asset_id}", code=2)
        winner_path = Path(fallback["glb"])
        winning_seed = fallback["seed"]
        info(f"  ⚠ all {ensemble_size} candidates failed Gate 2; surfacing seed {winning_seed} for diagnosis")
    else:
        pool = valid_records or records
        winner = max(pool, key=lambda r: r["score"])
        winner_path = Path(winner["glb"])
        winning_seed = winner["seed"]
        info(f"  ✓ winner: seed {winning_seed}  score={winner['score']:.4f}")

    final_path = raw_dir / f"{asset_id}.glb"
    if final_path.exists():
        final_path.unlink()
    shutil.copy2(winner_path, final_path)
    return final_path, winning_seed, records


def _run_generate_and_texture(
    args: argparse.Namespace, ctx: PipelineContext, glb_dir: Path, raw_dir: Path
) -> Path:
    """Stages 0–1.5: ref-gen → Hunyuan → PBR bake. Returns bake_input path."""
    maybe_auto_ref(args, ctx)
    # Real multi-view: when the author dropped a real angle-capture set, the
    # first view doubles as the primary image if --image was not given, and
    # these real angles replace Zero123++ synthesis downstream.
    real_views = _detect_real_views(args, ctx)
    if real_views and not args.image:
        args.image = str(real_views[0])
        info(f"--image omitted; using first real view as primary: {real_views[0].name}")

    if not args.image:
        die("--kind mesh requires --image <path> (or --auto-ref to generate one)")
    image = Path(args.image).resolve()
    if not image.exists():
        die(f"reference image not found: {image}")

    # Stage 0.25 (FLUX.2 refine) rewrites a *synthetic* ref.png in place
    # (archiving the source as ref.original.png). Real captures are ground
    # truth — refining them would alter the very angles we trust — so skip
    # refinement entirely when real views are supplied.
    if not real_views:
        maybe_refine_ref(args, ctx)

    views = resolve_views(args, ctx, real_views)

    # Flush ComfyUI VRAM before Hunyuan: stages 0, 0.25, 0.5 may have left
    # Flux/FLUX.2 models in VRAM (~9-22 GB). Hunyuan needs ~20 GB. On a
    # 32 GB card the two together would OOM without this flush.
    flush_comfy_vram(args.comfy_server)

    step(f"1/5 generate (Hunyuan3D 2.1) — multi-seed ensemble × {args.ensemble_size}")
    gen_cmd_template = [
        sys.executable,
        str(TOOLS_DIR / "generate_asset.py"),
        str(image),
        ctx.asset_id,
        "--steps",
        str(args.steps),
        "--server",
        args.server,
        # NOTE: --seed and --output-dir are appended per-iteration by
        # run_stage1_ensemble(); do not add them here.
    ]
    if args.octree_resolution is not None:
        gen_cmd_template.extend(["--octree-resolution", str(args.octree_resolution)])
    if args.guidance_scale is not None:
        gen_cmd_template.extend(["--guidance-scale", str(args.guidance_scale)])
    if views:
        # Pass the multi-view list to generate_asset.py via a repeated
        # --view flag. The first positional arg (image) is still required
        # so generate_asset.py can fall back to single-image submit when
        # the worker rejects the list payload.
        for v in views:
            gen_cmd_template.extend(["--view", str(v)])

    raw_glb, winning_seed, ensemble_records = run_stage1_ensemble(
        gen_cmd_template,
        asset_id=ctx.asset_id,
        raw_dir=raw_dir,
        base_seed=args.ensemble_base_seed,
        ensemble_size=args.ensemble_size,
        strict_manifold=args.strict_manifold,
        skip_gates=args.skip_gates,
    )
    if not raw_glb.exists():
        die(f"expected raw GLB at {raw_glb} but it was not produced", code=2)
    # Stash ensemble metadata on ctx so Gate 2's sidecar can include it.
    ctx.ensemble_records = ensemble_records
    ctx.ensemble_winning_seed = winning_seed

    # Gate 2 — post-Hunyuan geometry. Halts here when Hunyuan produced a
    # depth-card or otherwise-malformed mesh, because every downstream
    # stage (bake → projection → optimize → publish) wastes hours on a
    # mesh that's already known unfit. The diagnostic report is emitted
    # at end-of-branch so the operator sees the full picture.
    ensure_dir(DIAGNOSTICS_DIR)
    geom_cmd = [
        GATE_PYTHON,
        str(TOOLS_DIR / "validate_geometry.py"),
        str(raw_glb),
        "--asset-id",
        ctx.asset_id,
        "--report",
        str(DIAGNOSTICS_DIR / f"{ctx.asset_id}.geometry.json"),
    ]
    if args.strict_manifold:
        geom_cmd.append("--strict-manifold")
    geom_exit = run_gate("Gate 2 (geometry)", geom_cmd, ctx.asset_id, args.skip_gates)

    # Merge ensemble candidates into the geometry sidecar so the aggregate
    # report (and the Phase F retry harness) sees every seed that was
    # tried, not just the winner. validate_geometry.py wrote the sidecar
    # for the winner already; we annotate it in place.
    geom_sidecar = DIAGNOSTICS_DIR / f"{ctx.asset_id}.geometry.json"
    if geom_sidecar.exists():
        try:
            sidecar = json.loads(geom_sidecar.read_text())
        except json.JSONDecodeError:
            sidecar = {}
        sidecar["ensemble"] = {
            "size": args.ensemble_size,
            "base_seed": args.ensemble_base_seed,
            "winning_seed": ctx.ensemble_winning_seed,
            "candidates": ctx.ensemble_records,
        }
        geom_sidecar.write_text(json.dumps(sidecar, indent=2) + "\n")

    if geom_exit != 0:
        emit_diagnostic_report(ctx.asset_id)
        die(
            f"Gate 2 failed for {ctx.asset_id} — see "
            f"processed/diagnostics/{ctx.asset_id}.report.md. Pipeline "
            "halted before stage 2 to save bake time. Override with "
            "--skip-gates after triage.",
            code=2,
        )

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
            bake_cmd.extend([
                "--ai-project",
                "--comfy-server", args.comfy_server,
                "--ai-project-seed", str(args.ai_project_seed),
                "--ai-project-denoise", str(args.ai_project_denoise),
            ])
        run_step(bake_cmd)
        if not textured.exists():
            die(f"Stage 2 reported success but {textured.name} missing", code=2)

        # Gate 3 — multi-view beauty renders. Catches the documented
        # bake_pbr.render_views() lighting bug where back/bottom views
        # render as pure black, which then poisons stage 2b SDXL
        # conditioning. Skip gracefully when --skip-views was passed
        # (no view directory exists in that case).
        views_dir = PROCESSED / "views" / ctx.asset_id
        if views_dir.exists():
            views_cmd = [
                GATE_PYTHON,
                str(TOOLS_DIR / "validate_views.py"),
                str(views_dir),
                "--asset-id",
                ctx.asset_id,
                "--report",
                str(DIAGNOSTICS_DIR / f"{ctx.asset_id}.views.json"),
            ]
            if run_gate("Gate 3 (views)", views_cmd, ctx.asset_id, args.skip_gates) != 0:
                emit_diagnostic_report(ctx.asset_id)
                die(
                    f"Gate 3 failed for {ctx.asset_id} — see "
                    f"processed/diagnostics/{ctx.asset_id}.report.md. "
                    "Beauty renders are unfit to ship; the textured GLB "
                    "may also be poisoned by black conditioning.",
                    code=2,
                )
        else:
            info(f"Gate 3 skipped — no views dir at {views_dir.relative_to(REPO_ROOT)}")

        # Gate 5 — PBR texture contract. Catches the documented
        # half-projected albedo failure (large fraction of pixels at the
        # default-fill colour) and channel-packing violations. Runs even
        # when --skip-views was passed because the bake still writes
        # the texture set.
        textures_dir = PROCESSED / "textures" / ctx.asset_id
        if textures_dir.exists():
            pbr_cmd = [
                GATE_PYTHON,
                str(TOOLS_DIR / "validate_pbr.py"),
                "--textures-dir",
                str(textures_dir),
                "--asset-id",
                ctx.asset_id,
                "--report",
                str(DIAGNOSTICS_DIR / f"{ctx.asset_id}.pbr.json"),
            ]
            if args.gate_resolution_floor is not None:
                pbr_cmd.extend(["--resolution-floor", str(args.gate_resolution_floor)])
            if run_gate("Gate 5 (pbr)", pbr_cmd, ctx.asset_id, args.skip_gates) != 0:
                emit_diagnostic_report(ctx.asset_id)
                die(
                    f"Gate 5 failed for {ctx.asset_id} — see "
                    f"processed/diagnostics/{ctx.asset_id}.report.md. "
                    "PBR maps violate the OpenPBR contract or the albedo "
                    "has uncovered UV regions.",
                    code=2,
                )
        else:
            info(
                f"Gate 5 skipped — no textures dir at "
                f"{textures_dir.relative_to(REPO_ROOT)}"
            )

        bake_input = textured

    return bake_input


def branch_mesh(args: argparse.Namespace, ctx: PipelineContext) -> Path:
    """Hunyuan3D → bake → Draco/KTX2 → LODs → collision → export."""
    glb_dir = PROCESSED / "glb"
    ensure_dir(glb_dir)
    raw_dir = glb_dir / "raw"

    if getattr(args, "skip_generate", False):
        # Checkpoint resume: skip stages 0–1.5 (generation + texturing) and
        # resume from an existing GLB. Prefer the textured output; fall back
        # to the raw canonical path then the ensemble-subdirectory path.
        textured_cand = glb_dir / f"{ctx.asset_id}.textured.glb"
        raw_cand      = glb_dir / "raw" / f"{ctx.asset_id}.glb"
        ensemble_cand = (
            glb_dir / "raw" / ".ensemble" / ctx.asset_id / f"{ctx.asset_id}.glb"
        )
        bake_input = next(
            (c for c in (textured_cand, raw_cand, ensemble_cand) if c.exists()), None
        )
        if bake_input is None:
            die(
                f"--skip-generate: no existing GLB found for {ctx.asset_id}.\n"
                f"  Searched:\n"
                f"    {textured_cand.relative_to(REPO_ROOT)}\n"
                f"    {raw_cand.relative_to(REPO_ROOT)}\n"
                f"    {ensemble_cand.relative_to(REPO_ROOT)}\n"
                "Run the full pipeline first (without --skip-generate).",
                code=1,
            )
        step("checkpoint resume — skipping generation + texturing")
        info(f"resuming from: {bake_input.relative_to(REPO_ROOT)}")
    else:
        ensure_dir(raw_dir)
        bake_input = _run_generate_and_texture(args, ctx, glb_dir, raw_dir)

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

    step("3/5 LOD generation (gltf-transform simplify)")
    if args.generate_lods:
        # Build LODs from the pre-KTX2 textured GLB, not the optimized LOD0:
        # gltf-transform resize cannot downsize already-KTX2 textures, so the
        # per-tier texture caps (1K / 512) only take effect when the source
        # still has PNG maps. Same reason the collision step avoids the
        # optimized GLB. generate_lods strips the .textured suffix, so outputs
        # still land at <id>.lod1.glb / <id>.lod2.glb.
        lod_source = bake_input if bake_input.exists() else optimized
        lod_rc = subprocess.run(
            [
                sys.executable,
                str(TOOLS_DIR / "generate_lods.py"),
                str(lod_source),
                "--draco-level",
                str(args.draco_level),
            ],
            cwd=REPO_ROOT,
        ).returncode
        if lod_rc == 0:
            lod1 = glb_dir / f"{ctx.asset_id}.lod1.glb"
            lod2 = glb_dir / f"{ctx.asset_id}.lod2.glb"
            for lod in (lod1, lod2):
                if lod.exists():
                    copy_to_public(lod, lod.name)
        else:
            info(
                "LOD generation returned non-zero — runtime AssetLibrary "
                "will fall back to LOD0 only."
            )
    else:
        info("LOD generation skipped (--no-lods). Runtime uses LOD0 only.")

    step("4/5 collision hull (trimesh convex decomposition)")
    if args.generate_collision:
        # Use the pre-Draco textured GLB as the collision source: trimesh
        # cannot decode Draco-compressed buffers, so the optimized LOD0
        # (which has Draco) produces all-zero vertex coordinates.
        collision_source = bake_input if bake_input.exists() else optimized
        coll_rc = subprocess.run(
            [
                sys.executable,
                str(TOOLS_DIR / "generate_collision.py"),
                str(collision_source),
                "--asset-id",
                ctx.asset_id,
                "--max-hulls",
                str(args.collision_max_hulls),
            ],
            cwd=REPO_ROOT,
        ).returncode
        if coll_rc == 0:
            collision_glb = PROCESSED / "collisions" / f"{ctx.asset_id}.collision.glb"
            if collision_glb.exists():
                copy_to_public(collision_glb, collision_glb.name)
        else:
            info(
                "Collision hull generation returned non-zero — "
                "runtime falls back to mesh.checkCollisions = true."
            )
    else:
        info("Collision generation skipped (--no-collision).")

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
            "--kind",
            ctx.kind,
            "--source",
            ctx.source,
            "--diagnostics-dir",
            str(DIAGNOSTICS_DIR),
        ]
    )
    public_path = copy_to_public(optimized, f"{ctx.asset_id}.glb")

    # End-of-branch diagnostic aggregation. Always runs (even on success)
    # so the operator has one canonical artefact per asset run. The
    # markdown report lands at processed/diagnostics/<id>.report.md.
    emit_diagnostic_report(ctx.asset_id)
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
    parser.add_argument(
        "--steps",
        type=int,
        default=50,
        help=(
            "Hunyuan inference steps. Default 50 — upstream hy3dshape "
            "pipeline default; no API cap exists (the prior `min(steps, 20)` "
            "in generate_asset.py was a documentation artefact). "
            "Triple-A quality runs use 50–80; speed iteration can drop to 20."
        ),
    )
    parser.add_argument(
        "--octree-resolution",
        type=int,
        default=None,
        help=(
            "Hunyuan octree resolution override. Default uses "
            "generate_asset.py's own default (512). Hero figures can push "
            "to 768; speed-first iteration can drop to 256."
        ),
    )
    parser.add_argument(
        "--guidance-scale",
        type=float,
        default=None,
        help=(
            "Hunyuan classifier-free guidance override. Default uses "
            "generate_asset.py's own default (8.0). Range 5–12."
        ),
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8081",
        help="Hunyuan3D Docker server URL",
    )
    parser.add_argument(
        "--ensemble-size",
        type=int,
        default=3,
        help=(
            "Number of independent Hunyuan seeds to generate per asset (Phase E). "
            "Default 3. The winner is picked by Gate 2's composite geometry score "
            "(bbox depth weighted 3×, face-budget proximity, manifold bonus). "
            "Set to 1 for speed iteration; raise for hero assets that have failed "
            "previous runs."
        ),
    )
    parser.add_argument(
        "--ensemble-base-seed",
        type=int,
        default=481109,
        help=(
            "Starting seed for the multi-seed ensemble. Per-candidate seed = "
            "base + index. Override if a particular base hits a known-bad mode."
        ),
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
        default=True,
        help="Run stage 2 (Blender Cycles PBR bake) on the raw GLB before optimisation. ON by default.",
    )
    parser.add_argument(
        "--no-texture",
        dest="auto_texture",
        action="store_false",
        help="Skip the Blender bake (shape + optimize only, faster).",
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
        help="Run stage 2b (FLUX.2 [klein] img2img) PBR projection. Requires ComfyUI. ON by default.",
    )
    parser.add_argument(
        "--no-ai-project",
        dest="ai_project",
        action="store_false",
        help="Skip the FLUX.2 klein PBR projection step (procedural bake only, faster).",
    )
    parser.add_argument(
        "--ai-project-seed",
        type=int,
        default=481109,
        help="Base seed for FLUX.2 klein img2img (per-view seed = base + view_index).",
    )
    parser.add_argument(
        "--ai-project-denoise",
        type=float,
        default=0.62,
        help="img2img denoise strength for stage 2b. 0.55–0.70 is the safe band.",
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
    # Default ON as of Phase B2 (2026-05-22). The opt-in regime produced
    # the documented "white flat squares" failure on figure_grandfather_hands
    # because single-image conditioning gave Hunyuan no Z information,
    # so the network collapsed the output to a depth card. Multi-view
    # synthesis is the cheapest fix that survives across seeds.
    parser.add_argument(
        "--multi-view",
        dest="multi_view",
        action="store_true",
        default=True,
        help=(
            "Run stage 0.5 (Zero123++ v1.2) to synthesise 6 canonical views "
            "from ref.png and feed them to Hunyuan. Default: ON. "
            "Disable with --no-multi-view (NOT recommended — single-image "
            "conditioning collapses Hunyuan to depth-card output for "
            "anything more complex than a coin or a tile)."
        ),
    )
    parser.add_argument(
        "--no-multi-view",
        dest="multi_view",
        action="store_false",
        help=(
            "Disable Phase B2 multi-view synthesis. Use only when the "
            "asset is intentionally planar (signage, posters) and the "
            "extra synthesis time is wasted."
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
    parser.add_argument(
        "--real-views",
        dest="real_views",
        default=None,
        metavar="DIR",
        help=(
            "Directory of REAL multi-angle captures (photos or renders) of the "
            "asset. When supplied — or when prompts/asset-templates/<id>/real_views/ "
            "exists — these are fed to Hunyuan's multi-view mode verbatim and "
            "Zero123++ synthesis is SKIPPED: observed angles beat synthesised "
            "ones for all-angle accuracy. Any count, png/jpg; the first doubles "
            "as the primary image when --image is omitted."
        ),
    )

    # validation gates (Phase A)
    parser.add_argument(
        "--skip-gates",
        action="store_true",
        help=(
            "Skip the geometry / views / PBR validation gates. They normally "
            "hard-fail the run when a stage produces unusable output (flat "
            "depth-card mesh, unlit views, half-projected albedo). Use only "
            "when intentionally rerunning a known-broken asset for debugging."
        ),
    )
    parser.add_argument(
        "--strict-manifold",
        action="store_true",
        help=(
            "Escalate non-watertight mesh from warning to hard failure in "
            "Gate 2. Use for closed props (ledger, candle) where open edges "
            "indicate a bad bake; do not use for hero figures or fabric."
        ),
    )
    parser.add_argument(
        "--gate-resolution-floor",
        type=int,
        default=None,
        help=(
            "Override Gate 5's per-asset texture resolution floor. Default "
            "reads target_texture_resolution from the template; if absent, "
            "falls back to 1024."
        ),
    )

    # checkpoint resume
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        dest="skip_generate",
        default=False,
        help=(
            "Skip Hunyuan generation (stage 1) and PBR texturing (stage 1.5); "
            "resume from an existing textured or raw GLB. Useful when generation "
            "succeeded but optimization/export failed mid-pipeline. "
            "Searched in order: <id>.textured.glb → raw/<id>.glb → "
            "raw/.ensemble/<id>/<id>.glb."
        ),
    )

    # stage 4: LOD generation
    parser.add_argument(
        "--generate-lods",
        action="store_true",
        default=True,
        help=(
            "Run LOD generation (gltf-transform simplify) after optimize. "
            "ON by default. Produces <id>.lod1.glb (50%%) + <id>.lod2.glb (15%%)."
        ),
    )
    parser.add_argument(
        "--no-lods",
        dest="generate_lods",
        action="store_false",
        help="Skip LOD generation (geometry-only or speed-iteration runs).",
    )

    # stage 5: collision hull generation
    parser.add_argument(
        "--generate-collision",
        action="store_true",
        default=True,
        help=(
            "Run collision hull generation (trimesh convex decomposition) after LODs. "
            "ON by default. Produces <id>.collision.glb."
        ),
    )
    parser.add_argument(
        "--no-collision",
        dest="generate_collision",
        action="store_false",
        help="Skip collision hull generation.",
    )
    parser.add_argument(
        "--collision-max-hulls",
        type=int,
        default=16,
        help="Maximum number of convex hulls in the collision GLB (default: 16).",
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
