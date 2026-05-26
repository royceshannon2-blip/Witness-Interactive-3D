#!/usr/bin/env python3
"""
texture_asset.py — Stage 2 of the Witness Asset Pipeline.

Wraps `tools/blender/bake_pbr.py` (headless Blender Cycles) to produce
8K PBR maps + a textured GLB from a raw Hunyuan output. Optionally drives
ComfyUI's SDXL + ControlNet (depth) workflow to project AI-generated
material maps onto the 6 canonical views before the bake.

Flow:

    raw GLB ──► [Blender headless]
                  ├─► 6-view render (beauty + 16-bit depth EXR)  ─►  processed/views/<id>/
                  ├─► Smart UV unwrap (if missing)
                  ├─► family-aware procedural Principled BSDF
                  ├─► bake Albedo / MR / Normal / AO @ 8K        ─►  processed/textures/<id>/
                  └─► export textured GLB                         ─►  processed/glb/<id>.textured.glb

    --ai-project adds an intermediate step:
        for each view PNG: ComfyUI SDXL + ControlNet (depth conditioning,
        prompt = asset description) → PBR-styled diffuse maps that
        replace the procedural Albedo at re-bake time. Toggle is off by
        default until DreamMat-style UV reprojection lands; the view
        renders are emitted regardless so the projector can be wired in
        without re-running the bake.

Usage:
    python tools/texture_asset.py <asset_id> \\
        --glb processed/glb/raw/<asset_id>.glb \\
        [--family <auto|...>] [--texture-size 8192] \\
        [--ai-project] [--comfy-server http://localhost:8188]

Exit codes:
  0  textures + GLB produced
  1  validation failed (missing GLB, unknown family, Blender absent)
  2  Blender bake failed / AI projection failed
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = REPO_ROOT / "processed"
BLENDER_BAKE = REPO_ROOT / "tools" / "blender" / "bake_pbr.py"
BLENDER_REPROJECT = REPO_ROOT / "tools" / "blender" / "reproject_views.py"
PBR_WORKFLOWS = REPO_ROOT / "prompts" / "_pbr_workflows"
ASSET_TEMPLATES = REPO_ROOT / "prompts" / "asset-templates"

CANONICAL_VIEWS = ("front", "back", "left", "right", "top", "bottom")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def die(msg: str, code: int = 1) -> None:
    sys.stderr.write(f"ERROR: {msg}\n")
    sys.exit(code)


def info(msg: str) -> None:
    sys.stdout.write(f"  {msg}\n")


def find_blender() -> str:
    """Locate the Blender binary; default to PATH lookup."""
    path = shutil.which("blender")
    if path:
        return path
    die("Blender not on PATH — install Blender 4.x or 5.x and re-run.")
    raise SystemExit(1)  # unreachable


def load_family_module():
    """Import material_families.py from the tools/blender/ subdir."""
    sys.path.insert(0, str(REPO_ROOT / "tools" / "blender"))
    import material_families  # noqa: WPS433 — intentional dynamic path
    return material_families


# ---------------------------------------------------------------------------
# stage 2a — Blender bake
# ---------------------------------------------------------------------------


def run_bake(
    asset_id: str,
    glb_path: Path,
    family: str,
    texture_size: int,
    view_size: int,
    textures_dir: Path,
    views_dir: Path,
    output_glb: Path,
    samples: int,
    skip_views: bool,
) -> None:
    """Invoke Blender headless to bake PBR + render views."""
    blender = find_blender()
    cmd: list[str] = [
        blender,
        "--background",
        "--factory-startup",
        "--python",
        str(BLENDER_BAKE),
        "--",
        "--glb",
        str(glb_path),
        "--asset-id",
        asset_id,
        "--family",
        family,
        "--texture-size",
        str(texture_size),
        "--view-size",
        str(view_size),
        "--textures-dir",
        str(textures_dir),
        "--views-dir",
        str(views_dir),
        "--output-glb",
        str(output_glb),
        "--samples",
        str(samples),
    ]
    if skip_views:
        cmd.append("--skip-views")
    info(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        die(f"Blender bake failed (exit {result.returncode})", code=2)


def run_reproject(
    asset_id: str,
    textured_glb: Path,
    views_dir: Path,
    textures_dir: Path,
    texture_size: int,
    output_glb: Path,
    samples: int = 32,
    detail_view: str = "",
    detail_weight: float = 2.5,
) -> None:
    """
    Call Blender to UV-reproject the stage 2b AI view maps onto the mesh UV
    and re-export the GLB with the blended AI albedo replacing the procedural one.

    When ``detail_view`` is set, the matching ``<view>.detail.pbr.png`` is
    blended in at ``detail_weight`` so the hero region wins its texels.
    """
    blender = find_blender()
    cmd: list[str] = [
        blender,
        "--background",
        "--factory-startup",
        "--python",
        str(BLENDER_REPROJECT),
        "--",
        "--glb", str(textured_glb),
        "--asset-id", asset_id,
        "--views-dir", str(views_dir),
        "--textures-dir", str(textures_dir),
        "--output-glb", str(output_glb),
        "--texture-size", str(texture_size),
        "--samples", str(samples),
    ]
    if detail_view:
        cmd += ["--detail-view", detail_view, "--detail-weight", f"{detail_weight:g}"]
    info(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        die(f"UV reprojection failed (exit {result.returncode})", code=2)


def normalise_view_filenames(views_dir: Path) -> None:
    """
    Rename Blender composite outputs to stable names.

    The Compositor File Output node suffixes filenames with the frame
    number (e.g. ``front_beauty_0001.png``). We strip the suffix so
    downstream consumers (`tools/texture_asset.py --ai-project` and any
    future Babylon previewer) can use predictable names.
    """
    for view in CANONICAL_VIEWS:
        for kind, ext in (("beauty", "png"), ("depth", "exr")):
            matches = sorted(views_dir.glob(f"{view}_{kind}_*.{ext}"))
            if not matches:
                continue
            target = views_dir / f"{view}.{kind}.{ext}"
            if target.exists():
                target.unlink()
            matches[-1].rename(target)
            # Clean up any older suffixed copies.
            for stale in matches[:-1]:
                stale.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# stage 2b — AI projection (depth-controlled SDXL via ComfyUI)
# ---------------------------------------------------------------------------


def build_pbr_prompt(asset_id: str) -> str:
    """
    Compose the SDXL prompt that drives the depth-controlled projection.

    Strategy: read the asset's `<id>.md`, take the first ~280 characters
    of the body description (SDXL has a shorter useful prompt window than
    Flux), append PBR-material modifiers + the Digital Diorama suffix.
    """
    template = ASSET_TEMPLATES / f"{asset_id}.md"
    if not template.exists():
        return (
            "hyper-realistic PBR material, tactile weathered surface, "
            "filmic desaturated palette, overcast soft daylight"
        )
    text = template.read_text()
    if "---" in text:
        end = text.find("\n---\n", 4)
        body = text[end + 5 :] if end > 0 else text
    else:
        body = text
    snippet = " ".join(body.split())[:280]
    return (
        f"{snippet}. "
        "hyper-realistic PBR material, micro-bump roughness variation, "
        "tactile weathered surface, filmic desaturated palette, "
        "overcast soft daylight, no people, no captions"
    )


def load_pbr_workflow(
    prompt: str,
    view_filename: str,
    seed: int,
    denoise: float,
) -> dict:
    """
    Substitute prompt + view filename + seed + denoise into the FLUX.2
    klein PBR projection workflow.

    Phase D (2026-05-22) replaced the SDXL+ControlNet workflow with
    FLUX.2 [klein]. FLUX.2 prompt adherence is the reason for the swap;
    the trade-off is that the local install has no FLUX-compatible depth
    ControlNet, so depth conditioning is delegated to the beauty image
    itself: bake_pbr.py (Phase C) emits beauty renders lit with an HDRI
    + per-camera key, encoding geometry through shading. The VAE-encoded
    latent of that beauty pass seeds img2img; the prompt re-styles to
    PBR material at `denoise` strength.

    The depth EXRs continue to be emitted alongside the beauty PNGs so a
    future FLUX depth-ControlNet (or DreamMat-style UV reproject) can be
    swapped in without re-baking; this function intentionally takes no
    `depth_filename` argument because the current workflow doesn't
    consume one.
    """
    path = PBR_WORKFLOWS / "flux2_klein_pbr.json"
    if not path.exists():
        die(
            f"PBR projection workflow not found: {path.relative_to(REPO_ROOT)} — "
            "Phase D ships flux2_klein_pbr.json; was it deleted?",
            code=2,
        )
    raw = path.read_text()
    raw = raw.replace("__PROMPT__", json.dumps(prompt)[1:-1])
    raw = raw.replace("__VIEW_FILENAME__", view_filename)
    raw = raw.replace("__SEED__", str(int(seed)))
    raw = raw.replace("__DENOISE__", f"{float(denoise):.4f}")
    try:
        workflow = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"PBR workflow JSON invalid after substitution: {exc}", code=2)
    workflow.pop("_comment", None)
    return workflow


def flush_comfy_vram(server: str, wait: float = 5.0) -> None:
    """
    Ask ComfyUI to unload all models from VRAM.

    Called after stage 2b (SDXL ~10 GB) and before stage 2c (Blender Cycles
    UV reproject). Without this, SDXL + Blender GPU memory can push past 32 GB.
    """
    try:
        r = requests.post(
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
        info(f"ComfyUI VRAM flush skipped: {exc}")


def ai_project(
    asset_id: str,
    views_dir: Path,
    comfy_server: str,
    seed: int = 481109,
    denoise: float = 0.62,
) -> None:
    """
    For each canonical view, submit the FLUX.2 [klein] img2img workflow
    to ComfyUI and save the projected PBR diffuse beside the beauty.

    Output layout::

        processed/views/<id>/
            front.beauty.png       (Blender render — Phase C lit)
            front.depth.exr        (Blender depth pass — kept for future CN)
            front.pbr.png          (FLUX.2 klein projection)
            ...

    Seed advances per-view by index so the six panels don't share noise
    structure (otherwise FLUX's denoise can produce sibling artefacts
    across faces of the same mesh). `denoise=0.62` is the empirical sweet
    spot: low enough that the encoded geometry survives, high enough that
    procedural-bake material character is overwritten by the prompt.

    The final UV reprojection step (PBR views → 8K Albedo) is a separate
    Blender pass — see `reproject_views.py`.
    """
    prompt = build_pbr_prompt(asset_id)
    info(f"FLUX.2 klein projection prompt: {prompt[:140] + ('...' if len(prompt) > 140 else '')}")
    info(f"  base seed: {seed}    denoise: {denoise:.2f}")
    for idx, view in enumerate(CANONICAL_VIEWS):
        beauty = views_dir / f"{view}.beauty.png"
        depth = views_dir / f"{view}.depth.exr"
        if not beauty.exists():
            info(f"skip {view} — bake_pbr.py beauty render missing")
            continue
        upload_image(beauty, comfy_server, f"witness_{asset_id}_{view}_beauty.png")
        if depth.exists():
            # Upload anyway — future depth-CN workflow will pick it up
            # without re-running the bake. Current FLUX.2 graph ignores it.
            upload_image(depth, comfy_server, f"witness_{asset_id}_{view}_depth.exr")

        workflow = load_pbr_workflow(
            prompt=prompt,
            view_filename=f"witness_{asset_id}_{view}_beauty.png",
            seed=seed + idx,
            denoise=denoise,
        )
        prompt_id = submit_workflow(workflow, comfy_server)
        outputs = poll_history(prompt_id, comfy_server)
        record = first_image_output(outputs)
        download_image(record, comfy_server, views_dir / f"{view}.pbr.png")
        info(f"projected {view} → {(views_dir / f'{view}.pbr.png').relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# stage 2b-detail — hero detail projection (one high-priority view)
# ---------------------------------------------------------------------------


def read_template_frontmatter(asset_id: str) -> dict:
    """Parse the YAML frontmatter of ``<id>.md`` into a dict (``{}`` if none)."""
    template = ASSET_TEMPLATES / f"{asset_id}.md"
    if not template.exists():
        return {}
    text = template.read_text()
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    try:
        data = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def resolve_detail_spec(asset_id: str, args: argparse.Namespace) -> "dict | None":
    """
    Resolve the hero detail-pass spec from CLI overrides + template frontmatter.

    Returns ``None`` when no detail view is requested, else
    ``{"view", "reference": Path | None, "weight": float, "denoise": float}``.

    The detail pass re-projects a single canonical view at higher blend weight
    so a hero region (a face, hands) survives the six-view average. ``reference``
    — when supplied — is the img2img init for that view and MUST be framed to
    match the canonical view (a front close-up for ``front``); otherwise the
    view's beauty render is used.
    """
    fm = read_template_frontmatter(asset_id)
    view = args.detail_view or fm.get("detail_view")
    if not view:
        return None
    if view not in CANONICAL_VIEWS:
        info(f"detail view '{view}' not in {CANONICAL_VIEWS} — ignoring detail pass")
        return None

    ref_rel = args.detail_reference or fm.get("detail_reference")
    ref_path = None
    if ref_rel:
        rp = Path(ref_rel)
        ref_path = rp if rp.is_absolute() else (ASSET_TEMPLATES / ref_rel)

    weight = args.detail_weight if args.detail_weight is not None else float(fm.get("detail_weight", 2.5))
    denoise = args.detail_denoise if args.detail_denoise is not None else float(fm.get("detail_denoise", 0.45))
    return {"view": view, "reference": ref_path, "weight": float(weight), "denoise": float(denoise)}


def project_detail(
    asset_id: str,
    views_dir: Path,
    comfy_server: str,
    spec: dict,
    seed: int,
) -> None:
    """
    Run one extra FLUX.2 [klein] img2img projection for the hero detail view,
    saved as ``<view>.detail.pbr.png`` for the reprojector to blend at higher
    weight.

    Init image is the detail reference when present (it must be framed to match
    the canonical view so the projection lands on the right region) else the
    view's beauty render. A lower denoise than the standard pass preserves more
    of the reference structure.
    """
    view = spec["view"]
    ref = spec.get("reference")
    denoise = float(spec.get("denoise", 0.45))

    if ref is not None and ref.exists():
        src = ref
        info(f"detail init: detail_reference {ref.name} (must match '{view}' framing)")
    else:
        if ref is not None:
            info(f"detail_reference {ref} missing — falling back to beauty render")
        src = views_dir / f"{view}.beauty.png"
        info(f"detail init: beauty render {src.name}")
    if not src.exists():
        info(f"detail pass skipped — no init image at {src}")
        return

    prompt = build_pbr_prompt(asset_id)
    upload_name = f"witness_{asset_id}_{view}_detail_init.png"
    upload_image(src, comfy_server, upload_name)
    workflow = load_pbr_workflow(prompt=prompt, view_filename=upload_name, seed=seed, denoise=denoise)
    prompt_id = submit_workflow(workflow, comfy_server)
    outputs = poll_history(prompt_id, comfy_server)
    record = first_image_output(outputs)
    dest = views_dir / f"{view}.detail.pbr.png"
    download_image(record, comfy_server, dest)
    info(f"detail projected → {dest.relative_to(REPO_ROOT)}  (denoise {denoise:.2f})")


def upload_image(local_path: Path, server: str, dest_name: str) -> None:
    """POST a file to ComfyUI's /upload/image so the workflow can read it."""
    with local_path.open("rb") as fh:
        files = {"image": (dest_name, fh, "application/octet-stream")}
        try:
            r = requests.post(f"{server}/upload/image", files=files, timeout=60)
            r.raise_for_status()
        except requests.exceptions.RequestException as exc:
            die(f"upload {local_path.name} failed: {exc}", code=2)


def submit_workflow(workflow: dict, server: str) -> str:
    """POST a workflow to ComfyUI and return the prompt_id."""
    try:
        r = requests.post(f"{server}/prompt", json={"prompt": workflow}, timeout=30)
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        die(f"POST /prompt failed: {exc}", code=2)
    data = r.json()
    if "prompt_id" not in data:
        die(f"no prompt_id in /prompt response: {data}", code=2)
    return data["prompt_id"]


def poll_history(prompt_id: str, server: str) -> dict:
    """Poll until the prompt_id appears in /history with outputs."""
    import time

    endpoint = f"{server}/history/{prompt_id}"
    deadline = 600
    start = time.time()
    while True:
        if time.time() - start > deadline:
            die(f"Timed out polling /history for {prompt_id}", code=2)
        try:
            r = requests.get(endpoint, timeout=15)
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.RequestException:
            time.sleep(3)
            continue
        if prompt_id in data:
            entry = data[prompt_id]
            if entry.get("outputs"):
                return entry["outputs"]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                die(f"ComfyUI error: {status.get('messages')}", code=2)
        time.sleep(3)


def first_image_output(outputs: dict) -> dict[str, str]:
    """Return the first {filename, subfolder, type} record across nodes."""
    for node_outputs in outputs.values():
        for img in node_outputs.get("images", []) or []:
            return {
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
            }
    die("ComfyUI history contained no images", code=2)
    raise SystemExit(2)  # unreachable


def download_image(record: dict, server: str, dest: Path) -> None:
    """GET /view → write bytes to dest."""
    params = {
        "filename": record["filename"],
        "subfolder": record["subfolder"],
        "type": record["type"],
    }
    try:
        r = requests.get(f"{server}/view", params=params, timeout=60)
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        die(f"GET /view failed: {exc}", code=2)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("asset_id")
    p.add_argument("--glb", help="Raw GLB. Default: processed/glb/raw/<asset_id>.glb")
    p.add_argument("--family", default="auto")
    p.add_argument("--texture-size", type=int, default=8192)
    p.add_argument("--view-size", type=int, default=1024)
    p.add_argument("--samples", type=int, default=128, help="Cycles samples per bake / view render.")
    p.add_argument("--skip-views", action="store_true", help="Skip 6-view render (faster iteration on the bake).")
    p.add_argument(
        "--ai-project",
        action="store_true",
        help="Run stage 2b FLUX.2 [klein] PBR projection (requires ComfyUI).",
    )
    p.add_argument(
        "--ai-project-seed",
        type=int,
        default=481109,
        help="Base seed for FLUX.2 klein img2img. Per-view seed = base + view_index (0..5).",
    )
    p.add_argument(
        "--ai-project-denoise",
        type=float,
        default=0.62,
        help="img2img denoise strength. 0.55–0.70 is the workable band — lower preserves "
             "more of the procedural bake, higher gives FLUX more material authority.",
    )
    p.add_argument("--comfy-server", default="http://localhost:8188")
    p.add_argument(
        "--detail-view",
        default=None,
        help="Canonical view for the hero detail pass (overrides template detail_view).",
    )
    p.add_argument(
        "--detail-reference",
        default=None,
        help="Close-up init image for the detail pass; must be framed to match the "
             "detail view. Relative to prompts/asset-templates/ (overrides template).",
    )
    p.add_argument(
        "--detail-weight",
        type=float,
        default=None,
        help="Blend-weight multiplier for the detail view (default 2.5 / template).",
    )
    p.add_argument(
        "--detail-denoise",
        type=float,
        default=None,
        help="img2img denoise for the detail pass (default 0.45 / template).",
    )
    p.add_argument("--textures-dir")
    p.add_argument("--views-dir")
    p.add_argument("--output-glb")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    asset_id = args.asset_id
    families = load_family_module()
    family = args.family if args.family != "auto" else families.pick_family(asset_id)
    if family not in families.FAMILIES:
        die(f"unknown material family: {family}")

    glb_path = Path(args.glb).resolve() if args.glb else PROCESSED / "glb" / "raw" / f"{asset_id}.glb"
    if not glb_path.exists():
        die(f"raw GLB not found: {glb_path}")

    textures_dir = Path(args.textures_dir).resolve() if args.textures_dir else PROCESSED / "textures" / asset_id
    views_dir = Path(args.views_dir).resolve() if args.views_dir else PROCESSED / "views" / asset_id
    output_glb = Path(args.output_glb).resolve() if args.output_glb else PROCESSED / "glb" / f"{asset_id}.textured.glb"

    info(f"asset_id:      {asset_id}")
    info(f"family:        {family}")
    info(f"raw glb:       {glb_path.relative_to(REPO_ROOT)}")
    info(f"textures →     {textures_dir.relative_to(REPO_ROOT)}")
    info(f"views →        {views_dir.relative_to(REPO_ROOT)}")
    info(f"textured glb → {output_glb.relative_to(REPO_ROOT)}")

    run_bake(
        asset_id=asset_id,
        glb_path=glb_path,
        family=family,
        texture_size=args.texture_size,
        view_size=args.view_size,
        textures_dir=textures_dir,
        views_dir=views_dir,
        output_glb=output_glb,
        samples=args.samples,
        skip_views=args.skip_views,
    )
    normalise_view_filenames(views_dir)

    if args.ai_project:
        info("stage 2b: AI projection via ComfyUI FLUX.2 [klein] img2img")
        ai_project(
            asset_id,
            views_dir,
            args.comfy_server,
            seed=args.ai_project_seed,
            denoise=args.ai_project_denoise,
        )

        # Optional hero detail pass — one high-priority view (a face, hands).
        detail_spec = resolve_detail_spec(asset_id, args)
        if detail_spec:
            info(f"stage 2b-detail: hero detail projection for view '{detail_spec['view']}'")
            project_detail(
                asset_id,
                views_dir,
                args.comfy_server,
                detail_spec,
                seed=args.ai_project_seed + 100,
            )

        # Free FLUX.2 klein (~9 GB fp8 + dual CLIP + VAE ≈ 14 GB resident)
        # from VRAM before Blender UV reproject launches. Both processes
        # fight for the same 32 GB pool; FLUX wins if not evicted.
        flush_comfy_vram(args.comfy_server)

        detail_view = detail_spec["view"] if detail_spec else ""
        detail_weight = detail_spec["weight"] if detail_spec else 2.5
        has_detail = bool(detail_view) and (views_dir / f"{detail_view}.detail.pbr.png").exists()

        pbr_files = [views_dir / f"{v}.pbr.png" for v in CANONICAL_VIEWS]
        if any(p.exists() for p in pbr_files) or has_detail:
            info("stage 2c: UV reprojection of AI maps onto mesh UV")
            run_reproject(
                asset_id=asset_id,
                textured_glb=output_glb,
                views_dir=views_dir,
                textures_dir=textures_dir,
                texture_size=args.texture_size,
                output_glb=output_glb,
                samples=min(args.samples, 64),
                detail_view=detail_view,
                detail_weight=detail_weight,
            )
        else:
            info("stage 2c: skip — no .pbr.png files produced by stage 2b")

    info("stage 2 complete")
    info(f"next: python tools/optimize_asset.py {output_glb.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
