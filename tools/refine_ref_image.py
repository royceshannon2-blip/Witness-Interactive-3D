#!/usr/bin/env python3
"""
refine_ref_image.py — Stage 0.25 of the Witness Asset Pipeline

Refines the asset's `ref.png` through FLUX.2 [klein] 9B Base img2img, so
that hand-picked reference photos (or weaker Flux.1 [dev] outputs from
stage 0) inherit the Digital Diorama palette + 1994-Rwanda documentary
look before Zero123++ multi-view and Hunyuan3D shape inference see them.

Why this stage exists:

* Hand-picked refs from the open web rarely match the project's
  desaturated-documentary palette. Letting them flow into stage 1
  produces meshes whose baked PBR is tonally off, which then ripples
  through every renderer pass.
* Pure-Flux generation (stage 0) is style-consistent but sometimes loses
  regional specificity (Rwandan 1994 Bisesero Hills) and falls back to
  generic-African-village tropes.
* Hybrid (hand-pick OR Flux + a low-strength FLUX.2 [klein] pass) preserves
  regional accuracy while normalising the style. The denoise strength is
  tuned per-category by the orchestrator — vegetation gets pushed harder
  (0.60), structures lighter (0.40) so their geometry survives.

Pipeline position:

    Stage 0     (Flux → ref.png OR hand-drop ref.png)
       │
       ▼
    Stage 0.25  (this script: ref.png → refined ref.png)   ← you are here
       │
       ▼
    Stage 0.5   (Zero123++: ref.png → 6 view PNGs)
       │
       ▼
    Stage 1     (Hunyuan3D: views[] → raw .glb)

Idempotency / archive scheme:

* First run: copy `ref.png` → `ref.original.png`, then overwrite `ref.png`
  with the refined output. `ref.original.png` is the audit / rollback copy
  and is never touched again by this script.
* Re-runs read from `ref.original.png` if it exists (so we keep refining
  the original, not the already-refined output). Without `--force`, the
  script no-ops when `ref.original.png` exists — passing the same workflow
  + seed + strength twice would just re-do work.

Usage:

    python tools/refine_ref_image.py <asset_id> [options]

Example:

    python tools/refine_ref_image.py vegetation_eucalyptus_mature \\
        --strength 0.6 --seed 481109

Exit codes:

  0  refined ref.png written; ref.original.png preserved
  1  validation failure (no template, no ref.png, bad workflow)
  2  ComfyUI submission / poll / download failed
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSET_TEMPLATES = REPO_ROOT / "prompts" / "asset-templates"
FLUX_WORKFLOWS = REPO_ROOT / "prompts" / "_flux_workflows"

COMFY_DEFAULT = "http://localhost:8188"
POLL_INTERVAL = 3   # seconds — FLUX.2 klein at 1024² takes ~15-25 s on a 5090
POLL_TIMEOUT = 600  # seconds — leaves headroom for cold-load of the 9B checkpoint

# Stage 0.25 prompt suffix. This is intentionally *shorter* than the
# generate_ref_image.py STYLE_SUFFIX (which is built to push a blank-canvas
# Flux output all the way to Digital Diorama style). For img2img we're
# nudging an existing image — we want the model to keep the subject and
# its composition, and only shift palette + materials + lighting.
REFINE_PROMPT_SUFFIX = (
    "Restyle this photograph to match the Digital Diorama look: "
    "filmic desaturated palette, tactile weathered realism, hyper-realistic "
    "PBR materials with micro-bump and roughness variation, 1994 Rwanda "
    "documentary photography aesthetic. Preserve the subject's geometry, "
    "pose, and composition exactly. Overcast 5000 K diffuse daylight, "
    "neutral mid-grey background, no harsh shadows, no people other than "
    "any already present, no watermarks, no captions."
)


# ---------------------------------------------------------------------------
# error / log helpers
# ---------------------------------------------------------------------------


def die(msg: str, code: int = 1) -> None:
    """Print an error to stderr and exit with the given code."""
    sys.stderr.write(f"ERROR: {msg}\n")
    sys.exit(code)


def info(msg: str) -> None:
    """Indented status line that nests under asset_pipeline.py's log."""
    sys.stdout.write(f"  {msg}\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# prompt construction — re-use stage 0's parser so prompts stay consistent
# ---------------------------------------------------------------------------


def build_refine_prompt(asset_id: str, suffix_override: str | None) -> str:
    """
    Compose the FLUX.2 klein img2img prompt for one asset.

    The body comes from the same `## Reference image` section that stage 0
    reads, so the two stages describe the *same* subject — only the trailing
    style block differs (stage 0 builds the look from scratch, stage 0.25
    nudges the existing photo).
    """
    # Local import: generate_ref_image.py owns the template parser. Keeping
    # the import lazy means `--help` doesn't pay its cost, and we avoid a
    # circular dep if a future refactor splits the parser out.
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    from generate_ref_image import (  # type: ignore[import-not-found]
        extract_reference_section,
        parse_template,
        strip_markdown,
    )

    template_path = ASSET_TEMPLATES / f"{asset_id}.md"
    if not template_path.exists():
        die(f"template not found: {template_path.relative_to(REPO_ROOT)}")

    _, body = parse_template(template_path)
    ref_section = extract_reference_section(body)
    base = strip_markdown(ref_section)
    suffix = suffix_override if suffix_override else REFINE_PROMPT_SUFFIX
    return f"{base} {suffix}"


# ---------------------------------------------------------------------------
# workflow + ComfyUI
# ---------------------------------------------------------------------------


def load_workflow(
    workflow_name: str,
    prompt: str,
    seed: int,
    strength: float,
    ref_filename: str,
) -> dict[str, Any]:
    """
    Load a refine workflow JSON and substitute the four placeholders.

    Placeholders:
      __PROMPT__        — natural-language prompt (CLIP)
      __SEED__          — RandomNoise seed (int)
      __STRENGTH__      — BasicScheduler.denoise (float 0..1)
      __REF_FILENAME__  — LoadImage filename (already in ComfyUI input dir)
    """
    path = FLUX_WORKFLOWS / f"{workflow_name}.json"
    if not path.exists():
        die(f"workflow not found: {path.relative_to(REPO_ROOT)}")
    raw = path.read_text()
    raw = raw.replace("__PROMPT__", json.dumps(prompt)[1:-1])
    raw = raw.replace('"__SEED__"', str(seed))
    raw = raw.replace('"__STRENGTH__"', f"{strength:.4f}")
    raw = raw.replace("__REF_FILENAME__", ref_filename)
    try:
        workflow = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"workflow JSON invalid after substitution: {exc}")
    workflow.pop("_comment", None)
    return workflow


def upload_ref(source: Path, server: str, asset_id: str) -> str:
    """
    POST the ref image to ComfyUI's /upload/image endpoint.

    Returns the filename ComfyUI stored it under (which we then pass to
    LoadImage). We force a deterministic name (`witness_refine_<id>.png`)
    so repeat runs reuse the same upload slot — ComfyUI keeps an input/
    directory that grows otherwise.
    """
    target_name = f"witness_refine_{asset_id}.png"
    try:
        with source.open("rb") as fh:
            r = requests.post(
                f"{server}/upload/image",
                files={"image": (target_name, fh, "image/png")},
                data={"subfolder": "", "type": "input", "overwrite": "true"},
                timeout=60,
            )
            r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        die(f"POST /upload/image failed: {exc}", code=2)
    data = r.json()
    name = data.get("name") or target_name
    return name


def submit_workflow(workflow: dict[str, Any], server: str, client_id: str) -> str:
    """POST a workflow to ComfyUI and return the prompt_id for polling."""
    payload = {"prompt": workflow, "client_id": client_id}
    try:
        r = requests.post(f"{server}/prompt", json=payload, timeout=30)
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        die(f"POST /prompt failed: {exc}", code=2)
    data = r.json()
    if "prompt_id" not in data:
        die(f"no prompt_id in /prompt response: {data}", code=2)
    return data["prompt_id"]


def poll_history(prompt_id: str, server: str) -> dict[str, Any]:
    """Poll /history/{id} until ComfyUI reports outputs; return them."""
    endpoint = f"{server}/history/{prompt_id}"
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > POLL_TIMEOUT:
            die(f"Timed out after {POLL_TIMEOUT}s polling /history", code=2)
        try:
            r = requests.get(endpoint, timeout=15)
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.RequestException as exc:
            info(f"[{elapsed:6.0f}s] status fetch failed: {exc}")
            time.sleep(POLL_INTERVAL)
            continue
        if prompt_id in data:
            entry = data[prompt_id]
            outputs = entry.get("outputs") or {}
            if outputs:
                info(f"[{elapsed:6.0f}s] outputs received")
                return outputs
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                msgs = status.get("messages") or []
                die(f"ComfyUI reported error: {msgs}", code=2)
        info(f"[{elapsed:6.0f}s] pending")
        time.sleep(POLL_INTERVAL)


def find_first_image(outputs: dict[str, Any]) -> dict[str, str]:
    """Return the first {filename, subfolder, type} record across all nodes."""
    for node_outputs in outputs.values():
        for img in node_outputs.get("images", []) or []:
            return {
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
            }
    die("ComfyUI history contained no images", code=2)
    raise SystemExit(2)  # unreachable, satisfies type checker


def download_image(record: dict[str, str], server: str, dest: Path) -> None:
    """GET /view?... and write the bytes to dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
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
    dest.write_bytes(r.content)


def health_check(server: str) -> None:
    """Ping ComfyUI's /system_stats; fail fast with a clear error if down."""
    try:
        r = requests.get(f"{server}/system_stats", timeout=5)
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        die(
            f"ComfyUI unreachable at {server} — start it per tools/COMFY_RUNBOOK.md "
            f"(detail: {exc})",
            code=2,
        )


# ---------------------------------------------------------------------------
# archive-and-swap
# ---------------------------------------------------------------------------


def pick_source(asset_dir: Path) -> Path:
    """
    Decide which file feeds the refine pass.

    Re-runs (where `ref.original.png` already exists) read the *original*,
    not the previously-refined output — otherwise denoise compounds across
    runs and the asset drifts further from the source each time.
    """
    original = asset_dir / "ref.original.png"
    if original.exists():
        return original
    candidate = asset_dir / "ref.png"
    if not candidate.exists():
        die(
            f"no ref.png at {candidate.relative_to(REPO_ROOT)}; "
            f"run stage 0 first or drop a hand-picked reference."
        )
    return candidate


def ensure_archive(asset_dir: Path) -> None:
    """
    On first run, copy ref.png → ref.original.png. No-op afterwards.

    Why a copy (not a move): if the refine pass dies between the move and
    the download, we'd be left with no ref.png on disk and a confused
    pipeline. Copy-then-overwrite is crash-safe.
    """
    original = asset_dir / "ref.original.png"
    if original.exists():
        return
    ref = asset_dir / "ref.png"
    if not ref.exists():
        return  # caller will have already died in pick_source
    shutil.copy2(ref, original)
    info(f"archived original → {original.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 0.25 — refine ref.png via ComfyUI + FLUX.2 [klein] 9B Base.",
    )
    parser.add_argument("asset_id", help="Snake_case asset id (must have ref.png + <id>.md template)")
    parser.add_argument(
        "--workflow",
        default="refine",
        help="Workflow name in prompts/_flux_workflows/ (default: refine)",
    )
    parser.add_argument(
        "--strength",
        type=float,
        required=True,
        help=(
            "Denoise strength 0..1. The orchestrator computes a per-category "
            "default (vegetation 0.60, prop/figure 0.50, structure 0.40); "
            "passing --refine-ref-strength overrides it. Lower = preserve more "
            "of the original ref; higher = push harder toward Digital Diorama."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=481109,
        help="FLUX.2 klein noise seed (default 481109 — matches stage 0)",
    )
    parser.add_argument(
        "--server",
        default=COMFY_DEFAULT,
        help="ComfyUI HTTP server URL (default %(default)s)",
    )
    parser.add_argument(
        "--prompt-suffix",
        default=None,
        help=(
            "Override the canonical Digital Diorama refine suffix. Use only "
            "for one-off experiments — for permanent changes, edit "
            "REFINE_PROMPT_SUFFIX in this file and _STYLE_GUIDE.md together."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-refine even if ref.original.png already exists. Without this, "
            "the script no-ops on re-runs (the archive copy is treated as the "
            "completion marker)."
        ),
    )
    parser.add_argument(
        "--print-prompt-only",
        action="store_true",
        help="Print the composed prompt and exit (no ComfyUI call). For debugging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not (0.0 < args.strength < 1.0):
        die(f"--strength must be in (0, 1); got {args.strength}")

    asset_dir = ASSET_TEMPLATES / args.asset_id
    if not asset_dir.exists():
        die(f"asset directory not found: {asset_dir.relative_to(REPO_ROOT)}")

    prompt = build_refine_prompt(args.asset_id, args.prompt_suffix)
    if args.print_prompt_only:
        sys.stdout.write(prompt + "\n")
        return 0

    original = asset_dir / "ref.original.png"
    if original.exists() and not args.force:
        info(
            f"refine skip — ref.original.png present at "
            f"{original.relative_to(REPO_ROOT)} (use --force to re-refine)"
        )
        return 0

    source = pick_source(asset_dir)
    info(f"asset:    {args.asset_id}")
    info(f"workflow: {args.workflow}")
    info(f"strength: {args.strength:.2f}")
    info(f"seed:     {args.seed}")
    info(f"server:   {args.server}")
    info(f"source:   {source.relative_to(REPO_ROOT)}")
    info(f"prompt:   {prompt[:140] + ('...' if len(prompt) > 140 else '')}")

    health_check(args.server)

    # Archive *before* we touch ComfyUI so a download failure can't leave
    # the original on disk with no record of having been refined.
    ensure_archive(asset_dir)

    ref_filename = upload_ref(source, args.server, args.asset_id)
    info(f"uploaded → ComfyUI input/{ref_filename}")

    workflow = load_workflow(
        args.workflow,
        prompt,
        args.seed,
        args.strength,
        ref_filename,
    )
    client_id = f"witness-refine-{uuid.uuid4().hex[:8]}"
    prompt_id = submit_workflow(workflow, args.server, client_id)
    info(f"prompt_id: {prompt_id}")

    outputs = poll_history(prompt_id, args.server)
    record = find_first_image(outputs)
    dest = asset_dir / "ref.png"
    download_image(record, args.server, dest)

    info(f"wrote {dest.relative_to(REPO_ROOT)} ({dest.stat().st_size // 1024} KB)")
    info(
        "next: python tools/asset_pipeline.py "
        + args.asset_id
        + " --kind mesh --multi-view"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
