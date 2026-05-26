#!/usr/bin/env python3
"""
generate_multi_views.py — Stage 0.5 of the Witness Asset Pipeline

Takes the single-view reference image written by stage 0
(`prompts/asset-templates/<id>/ref.png`) and synthesises 6 canonical
novel views via Zero123++ v1.2. The views feed stage 1 (Hunyuan3D) as a
list payload, which produces a noticeably more complete mesh — fewer flat
caps, fewer missing facets — than single-image conditioning.

Why a standalone diffusers script, not a ComfyUI workflow:

* Zero123++ ships as a diffusers custom-pipeline
  (``sudo-ai/zero123plus-v1.2`` + ``sudo-ai/zero123plus-pipeline``). The
  ComfyUI integration ("ComfyUI-3D-Pack") pulls in heavy native deps and
  pins specific torch/CUDA versions that fight our Flux fp8 install.
* Zero123++ is a single-shot inference — there's no graph to compose, so
  ComfyUI adds no value.
* Running it in its own process makes VRAM coordination obvious: Flux
  exits ComfyUI's worker → this script loads/runs Zero123++ → it exits →
  the Hunyuan container picks up the resulting PNGs. The 5090 (32 GB)
  never has to hold two big models at once.

Pipeline position:

    Stage 0  (Flux → ref.png)
       │
       ▼
    Stage 0.5  (this script: ref.png → 6 view PNGs)        ← you are here
       │
       ▼
    Stage 1  (Hunyuan3D: views[] → raw .glb)

Output layout:

    prompts/asset-templates/<id>/ref.png            (input, from stage 0)
    prompts/asset-templates/<id>/views/view_0.png   (front)
    prompts/asset-templates/<id>/views/view_1.png   (front-right ~60°)
    prompts/asset-templates/<id>/views/view_2.png   (back-right ~120°)
    prompts/asset-templates/<id>/views/view_3.png   (back ~180°)
    prompts/asset-templates/<id>/views/view_4.png   (back-left ~240°)
    prompts/asset-templates/<id>/views/view_5.png   (front-left ~300°)
    prompts/asset-templates/<id>/views/grid.png     (raw 2×3 320² grid)

Zero123++ v1.2 outputs a fixed pose set:

    elevations: [30°, -20°, 30°, -20°, 30°, -20°]
    azimuths:   [30°, 90°, 150°, 210°, 270°, 330°]

(See https://huggingface.co/sudo-ai/zero123plus-v1.2 — the elevations
alternate so the model sees the top and bottom hemisphere in pairs.)

Usage:

    python tools/generate_multi_views.py <asset_id> [options]

Example:

    python tools/generate_multi_views.py vegetation_eucalyptus_mature \\
        --seed 481109

Exit codes:

  0  6 view PNGs (and the grid) written
  1  validation failure (no ref.png, bad asset id)
  2  diffusers/CUDA failure during inference
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSET_TEMPLATES = REPO_ROOT / "prompts" / "asset-templates"

# Zero123++ v1.2 emits a 2-row × 3-col grid of 320×320 views. The
# checkpoint is fixed-pose, so these constants encode that contract — do
# not edit without re-validating against the upstream model card.
ZERO123_GRID_ROWS = 2
ZERO123_GRID_COLS = 3
ZERO123_TILE_PX = 320
ZERO123_VIEW_COUNT = ZERO123_GRID_ROWS * ZERO123_GRID_COLS  # 6

# Subject framing. Zero123++ assumes a centred subject occupying a consistent
# fraction of a square frame (its conditioning is pose-relative to frame
# centre). An off-centre, edge-touching, or tiny subject makes the model guess
# scale and yields misaligned novel views. After background removal we have a
# clean alpha, so we crop to the subject, centre it on a square, and scale it to
# SUBJECT_FRAME_FILL of the frame's long side.
ZERO123_INPUT_PX = 512        # square canvas fed to the pipeline (it resizes internally)
SUBJECT_FRAME_FILL = 0.85     # subject's longer side fills this fraction of the square


def die(msg: str, code: int = 1) -> None:
    """Print an error to stderr and exit with the given code."""
    sys.stderr.write(f"ERROR: {msg}\n")
    sys.exit(code)


def info(msg: str) -> None:
    """Indented status line that nests cleanly under asset_pipeline.py."""
    sys.stdout.write(f"  {msg}\n")
    sys.stdout.flush()


def existing_views(views_dir: Path) -> list[Path]:
    """Return view_*.png files already on disk, sorted by view index."""
    return sorted(views_dir.glob("view_*.png"))


def load_pipeline(device: str, dtype_str: str):
    """
    Load the Zero123++ v1.2 diffusers custom pipeline.

    Imports are local because diffusers + torch are heavy and we want the
    `--help` path to stay fast and not require GPU libs.
    """
    try:
        import torch  # noqa: F401
        from diffusers import DiffusionPipeline, EulerAncestralDiscreteScheduler
    except ImportError as exc:
        die(
            f"diffusers + torch required for stage 0.5 (pip install diffusers torch): {exc}",
            code=2,
        )

    import torch
    from diffusers import DiffusionPipeline, EulerAncestralDiscreteScheduler

    dtype = {
        "fp16": torch.float16,
        "bf16": torch.bfloat16,
        "fp32": torch.float32,
    }.get(dtype_str)
    if dtype is None:
        die(f"unknown --dtype {dtype_str!r} (expected fp16|bf16|fp32)")

    info(f"loading sudo-ai/zero123plus-v1.2 (dtype={dtype_str}, device={device})…")
    try:
        # trust_remote_code: Zero123++ ships a custom pipeline.py at
        # sudo-ai/zero123plus-pipeline. diffusers ≥ 0.30 refuses to execute
        # remote code without explicit opt-in. We trust this repo because
        # it's the upstream-recommended path on the model card; if you want
        # to audit-and-pin, set revision="<commit-hash>" on both sides.
        pipe = DiffusionPipeline.from_pretrained(
            "sudo-ai/zero123plus-v1.2",
            custom_pipeline="sudo-ai/zero123plus-pipeline",
            torch_dtype=dtype,
            trust_remote_code=True,
        )
    except Exception as exc:  # noqa: BLE001 — surface any download/init failure verbatim
        die(f"failed to load Zero123++ pipeline: {exc}", code=2)

    # The upstream model card recommends Euler-Ancestral for v1.2. Without
    # this override, the default scheduler over-smooths the back views.
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(
        pipe.scheduler.config,
        timestep_spacing="trailing",
    )

    import gc
    gc.collect()
    torch.cuda.empty_cache()

    try:
        pipe.to(device)
    except Exception as exc:  # noqa: BLE001
        die(f"failed to move pipeline to {device}: {exc}", code=2)

    return pipe


def frame_subject(rgba, fill: float = SUBJECT_FRAME_FILL, out_px: int = ZERO123_INPUT_PX):
    """
    Centre a cut-out subject on a square white canvas at a consistent scale.

    Crops to the alpha bounding box, then pastes it centred on a square white
    matte sized so the subject's longer side occupies ``fill`` of the frame.
    This normalises subject scale/position before Zero123++, whose pose
    conditioning is relative to frame centre — an off-centre or edge-touching
    subject otherwise produces misaligned novel views. Returns RGBA (caller
    flattens to RGB). If the alpha is empty (rembg removed everything) the input
    is returned unchanged so the caller can surface the failure downstream.
    """
    from PIL import Image

    bbox = rgba.split()[-1].getbbox()
    if bbox is None:
        info("WARN: subject alpha is empty after cut-out — skipping framing")
        return rgba
    cut = rgba.crop(bbox)
    w, h = cut.size
    canvas_px = max(1, int(round(max(w, h) / fill)))
    canvas = Image.new("RGBA", (canvas_px, canvas_px), (255, 255, 255, 255))
    canvas.paste(cut, ((canvas_px - w) // 2, (canvas_px - h) // 2), cut)
    if out_px and canvas_px != out_px:
        canvas = canvas.resize((out_px, out_px), Image.LANCZOS)
    info(f"subject framed: {w}×{h} cut-out → {out_px}×{out_px} square @ {fill:.0%} fill")
    return canvas


def remove_background(img, enabled: bool):
    """
    Strip the reference background so Zero123++ sees an isolated subject.

    Zero123++ is trained on objects on a plain background. A busy background —
    e.g. a photographic plate of hands resting on a wooden table — gets carried
    into the synthesised novel views and then fused by Hunyuan into a *slab*
    (the documented "triangular prism" failure: the table plane is modelled as
    a block with the subject in shallow relief). Isolating the subject here is
    the single biggest determinant of a clean multi-view set.

    Uses rembg (u2net) when available, then re-frames the cut-out via
    ``frame_subject`` (centred on a square white matte — the plain background
    v1.2 expects, and white avoids dark edge-halo bleed). If rembg is not
    installed, emits a prominent warning with the install command and returns
    the image unchanged — the run still completes, but the mesh is at high risk
    of the slab artefact. The fallback is loud, not silent.
    """
    if not enabled:
        info("background removal disabled (--no-remove-bg) — feeding raw ref to Zero123++")
        return img.convert("RGB")
    try:
        from rembg import remove as rembg_remove
    except ImportError:
        info("")
        info("  *** WARNING: rembg not installed — background NOT removed. ***")
        info("  The subject background will be fused into the mesh as a slab")
        info("  ('triangular prism'). Applies to BOTH synthesised and real-photo")
        info("  view sets — whatever background is present becomes geometry.")
        info("  Fix:  pip install rembg onnxruntime   (into the ML venv)")
        info("  (or pass --no-remove-bg to accept the risk and silence this)")
        info("")
        return img.convert("RGB")

    cut = rembg_remove(img.convert("RGBA"))
    info("background removed via rembg (u2net)")
    framed = frame_subject(cut)
    return framed.convert("RGB")


def run_inference(pipe, ref_path: Path, seed: int, steps: int, guidance: float,
                  remove_bg: bool = True):
    """
    Run Zero123++ on the reference image and return the (960×640) grid PIL.

    The model emits a fixed 2×3 grid; we slice it after this returns. The
    reference background is removed first (see ``remove_background``) unless
    disabled — feeding a background-laden plate is the root cause of the slab
    artefact.
    """
    try:
        import torch
        from PIL import Image
    except ImportError as exc:  # already imported by load_pipeline, but be defensive
        die(f"PIL/torch import failed: {exc}", code=2)

    ref = Image.open(ref_path).convert("RGBA")
    ref = remove_background(ref, remove_bg)
    info(f"input: {ref.size[0]}×{ref.size[1]} {ref_path.name}")

    generator = torch.Generator(device=pipe.device).manual_seed(seed)
    info(f"sampling: steps={steps} guidance={guidance} seed={seed}")
    try:
        result = pipe(
            ref,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=generator,
        )
    except Exception as exc:  # noqa: BLE001
        die(f"Zero123++ inference failed: {exc}", code=2)

    grid = result.images[0]
    expected = (ZERO123_GRID_COLS * ZERO123_TILE_PX, ZERO123_GRID_ROWS * ZERO123_TILE_PX)
    if grid.size != expected:
        info(
            f"WARN: grid size {grid.size} ≠ expected {expected}; "
            f"slicing will adapt but verify upstream model didn't change pose layout."
        )
    return grid


def slice_grid(grid, out_dir: Path) -> list[Path]:
    """
    Slice the Zero123++ output grid into individual view_*.png files.

    Order matches the upstream pose ordering (left-to-right, top-to-bottom)
    which yields azimuths 30°, 90°, 150°, 210°, 270°, 330° — see the
    module docstring for the elevation pattern.
    """
    width, height = grid.size
    tile_w = width // ZERO123_GRID_COLS
    tile_h = height // ZERO123_GRID_ROWS
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    idx = 0
    for row in range(ZERO123_GRID_ROWS):
        for col in range(ZERO123_GRID_COLS):
            box = (col * tile_w, row * tile_h, (col + 1) * tile_w, (row + 1) * tile_h)
            view = grid.crop(box)
            view_path = out_dir / f"view_{idx}.png"
            view.save(view_path)
            paths.append(view_path)
            idx += 1

    # Stash the raw grid alongside the views so a human can sanity-check
    # the model output without re-running inference.
    grid.save(out_dir / "grid.png")
    return paths


def stage_real_views(asset_dir: Path, src_dir: Path, remove_bg: bool, force: bool) -> int:
    """
    Stage author-supplied real photographs as the canonical view set, applying
    the SAME background removal + framing the synthesis path uses.

    Real captures are the highest-fidelity multi-view input — observed, not
    hallucinated — but they arrive with real-world backgrounds. Feeding those
    straight to Hunyuan reproduces the slab artefact that motivated
    ``remove_background``: the table/wall plane fuses into a block. So each
    photo is cut out and centred here, exactly like a synthesised view, before
    Hunyuan fuses them. Zero123++ is never loaded in this mode.

    Framing is per-view, so shoot the angles at a roughly consistent distance
    (turntable style) — that keeps apparent scale matched across views, which
    is what Hunyuan's multi-view fusion expects.
    """
    from PIL import Image

    srcs = sorted(
        p for p in src_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )
    if not srcs:
        die(f"--real-views {src_dir} contains no .png/.jpg/.jpeg images", code=1)

    views_dir = asset_dir / "views"
    existing = existing_views(views_dir)
    if existing and not force:
        info(
            f"{len(existing)} view PNG(s) already present in {views_dir} — "
            "skipping (use --force to restage)"
        )
        return 0

    views_dir.mkdir(parents=True, exist_ok=True)
    for old in views_dir.glob("view_*.png"):
        old.unlink()

    info(
        f"staging {len(srcs)} real view(s) from {src_dir.name}/ "
        f"(background removal {'ON' if remove_bg else 'OFF — --no-remove-bg'})"
    )
    for idx, src in enumerate(srcs):
        img = Image.open(src).convert("RGBA")
        cleaned = remove_background(img, remove_bg)
        out = views_dir / f"view_{idx}.png"
        cleaned.save(out)
        info(f"  view_{idx}: {src.name} → {out.name} ({out.stat().st_size // 1024} KB)")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 0.5 — Zero123++ multi-view synthesis from a ref.png.",
    )
    parser.add_argument("asset_id", help="Snake_case asset id (must have a ref.png from stage 0)")
    parser.add_argument(
        "--seed",
        type=int,
        default=481109,
        help="Zero123++ noise seed (default 481109 — matches stage 0)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=75,
        help="Diffusion steps (default 75 — upstream model card recommends 50-100)",
    )
    parser.add_argument(
        "--guidance",
        type=float,
        default=4.0,
        help="Classifier-free-guidance scale (default 4.0 — v1.2 sweet spot)",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        help="Torch device (default cuda)",
    )
    parser.add_argument(
        "--dtype",
        default="fp16",
        choices=("fp16", "bf16", "fp32"),
        help="Torch dtype for the pipeline weights (default fp16; bf16 if your VRAM is tight)",
    )
    parser.add_argument(
        "--real-views",
        dest="real_views",
        default=None,
        help=(
            "Stage real photographs from this directory as the view set instead "
            "of synthesising with Zero123++. Each image is background-removed + "
            "framed (same cleanup as synthesis) and written as view_N.png."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing view_*.png files. Without this, the script no-ops when 6 views exist.",
    )
    parser.add_argument(
        "--no-remove-bg",
        action="store_true",
        help=(
            "Feed the raw reference to Zero123++ without background removal. "
            "Off by default: a background-laden ref is the root cause of slab "
            "('triangular prism') meshes. Only set this when the ref is already "
            "cleanly isolated on a plain background."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import os
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    args = parse_args(argv)

    asset_dir = ASSET_TEMPLATES / args.asset_id
    if not asset_dir.exists():
        die(f"asset directory not found: {asset_dir.relative_to(REPO_ROOT)}")

    # Real-view staging mode: clean + frame supplied photographs, no synthesis.
    # No ref.png is required — the photos ARE the views.
    if args.real_views:
        src_dir = Path(args.real_views).resolve()
        if not src_dir.is_dir():
            die(f"--real-views {src_dir} is not a directory", code=1)
        return stage_real_views(
            asset_dir, src_dir, remove_bg=not args.no_remove_bg, force=args.force
        )

    ref_path = asset_dir / "ref.png"
    if not ref_path.exists():
        die(
            f"ref.png missing for {args.asset_id}; "
            f"run `python tools/generate_ref_image.py {args.asset_id}` first."
        )

    views_dir = asset_dir / "views"
    existing = existing_views(views_dir)
    if len(existing) >= ZERO123_VIEW_COUNT and not args.force:
        info(
            f"{len(existing)} view PNG(s) already present in "
            f"{views_dir.relative_to(REPO_ROOT)} — skipping (use --force to regenerate)"
        )
        return 0

    info(f"asset:    {args.asset_id}")
    info(f"ref:      {ref_path.relative_to(REPO_ROOT)}")
    info(f"out_dir:  {views_dir.relative_to(REPO_ROOT)}")

    pipe = load_pipeline(args.device, args.dtype)
    grid = run_inference(
        pipe,
        ref_path,
        seed=args.seed,
        steps=args.steps,
        guidance=args.guidance,
        remove_bg=not args.no_remove_bg,
    )

    paths = slice_grid(grid, views_dir)
    for p in paths:
        info(f"wrote {p.relative_to(REPO_ROOT)} ({p.stat().st_size // 1024} KB)")

    info(
        "next: python tools/asset_pipeline.py "
        + args.asset_id
        + " --kind mesh --multi-view"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
