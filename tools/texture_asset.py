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
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = REPO_ROOT / "processed"
BLENDER_BAKE = REPO_ROOT / "tools" / "blender" / "bake_pbr.py"
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


def load_pbr_workflow(prompt: str, depth_filename: str | None, view_filename: str) -> dict:
    """Substitute prompt + view filenames into the PBR projection workflow."""
    # When depth is absent (Blender 5.x dropped depth EXR output) fall back
    # to the beauty-only workflow which uses the view image as both the
    # reference and the ControlNet input.
    workflow_name = "sdxl_depth_pbr.json" if depth_filename else "sdxl_beauty_pbr.json"
    path = PBR_WORKFLOWS / workflow_name
    if not path.exists():
        # If the beauty-only workflow hasn't been authored yet, fall back to
        # depth workflow with a dummy filename — ComfyUI will skip the depth
        # node gracefully if the image is absent.
        path = PBR_WORKFLOWS / "sdxl_depth_pbr.json"
        depth_filename = depth_filename or view_filename
    if not path.exists():
        die(f"PBR projection workflow not found: {path.relative_to(REPO_ROOT)}", code=2)
    raw = path.read_text()
    raw = raw.replace("__PROMPT__", json.dumps(prompt)[1:-1])
    raw = raw.replace("__DEPTH_FILENAME__", depth_filename or view_filename)
    raw = raw.replace("__VIEW_FILENAME__", view_filename)
    try:
        workflow = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"PBR workflow JSON invalid after substitution: {exc}", code=2)
    workflow.pop("_comment", None)
    return workflow


def ai_project(asset_id: str, views_dir: Path, comfy_server: str) -> None:
    """
    For each canonical view, submit the SDXL+ControlNet workflow to
    ComfyUI and save the projected diffuse beside the original beauty.

    Output layout::

        processed/views/<id>/
            front.beauty.png       (Blender render)
            front.depth.exr        (Blender depth pass)
            front.pbr.png          (AI projection — NEW)
            ...

    The final UV reprojection step (PBR views → 8K Albedo) is a separate
    Blender pass that is **not** wired in this revision — see the design
    doc's "Follow-ups" section.
    """
    prompt = build_pbr_prompt(asset_id)
    info(f"AI projection prompt: {prompt[:140] + ('...' if len(prompt) > 140 else '')}")
    for view in CANONICAL_VIEWS:
        beauty = views_dir / f"{view}.beauty.png"
        depth = views_dir / f"{view}.depth.exr"
        if not beauty.exists():
            info(f"skip {view} — bake_pbr.py beauty render missing")
            continue
        # Depth EXR is optional — bake_pbr.py no longer emits it in
        # Blender 5.x (compositor API changed). When absent the workflow
        # runs without depth conditioning; results are still usable.
        upload_image(beauty, comfy_server, f"witness_{asset_id}_{view}_beauty.png")
        if depth.exists():
            upload_image(depth, comfy_server, f"witness_{asset_id}_{view}_depth.exr")

        workflow = load_pbr_workflow(
            prompt=prompt,
            depth_filename=f"witness_{asset_id}_{view}_depth.exr" if depth.exists() else None,
            view_filename=f"witness_{asset_id}_{view}_beauty.png",
        )
        prompt_id = submit_workflow(workflow, comfy_server)
        outputs = poll_history(prompt_id, comfy_server)
        record = first_image_output(outputs)
        download_image(record, comfy_server, views_dir / f"{view}.pbr.png")
        info(f"projected {view} → {(views_dir / f'{view}.pbr.png').relative_to(REPO_ROOT)}")


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
    p.add_argument("--ai-project", action="store_true", help="Run stage 2b SDXL projection (requires ComfyUI).")
    p.add_argument("--comfy-server", default="http://localhost:8188")
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
        info("stage 2b: AI projection via ComfyUI SDXL + ControlNet (depth)")
        ai_project(asset_id, views_dir, args.comfy_server)

    info("stage 2 complete")
    info(f"next: python tools/optimize_asset.py {output_glb.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
