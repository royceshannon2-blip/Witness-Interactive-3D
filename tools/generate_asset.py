#!/usr/bin/env python3
"""
generate_asset.py — Hunyuan3D 2.1 Asset Generator

Submits a reference image to the local Hunyuan3D API server and polls for
completion, saving the resulting GLB to processed/glb/raw/.

API contract (kechiro/hunyuan3d-2.1-cachedstart):
  POST /send         JSON { image: base64, seed, octree_resolution, ... }
                     → { uid: "..." }
  GET  /status/{uid} → { status: "processing"|"texturing"|"completed"|"error",
                          model_base64: "..." }   (model_base64 only when completed)

Usage:
    python tools/generate_asset.py <image_path> <asset_id> [options]

Example:
    python tools/generate_asset.py prompts/asset-templates/prop_ledger_book/ref.png \
        prop_ledger_book --steps 20 --seed 481116
"""

import argparse
import base64
import json
import sys
import time
from pathlib import Path

import requests


HUNYUAN_API = "http://localhost:8081"
POLL_INTERVAL = 10   # seconds between status checks
POLL_TIMEOUT  = 1800 # 30 minutes — textured generation can take a while


def encode_image(image_path: Path) -> str:
    """Return base64-encoded image string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def submit(image_b64: str, args, server: str, view_b64_list: list[str] | None = None) -> str:
    """
    POST to /send and return the uid.

    When ``view_b64_list`` is provided, both the legacy ``image`` field
    (set to the first / primary view) and the new ``images`` list field
    are sent. The patched Witness model_worker uses ``images`` when
    present; the legacy ``image`` is retained so an unpatched worker
    still produces a single-view mesh instead of erroring.
    """
    payload = {
        "image":               image_b64,
        "remove_background":   True,
        "texture":             args.texture,
        "seed":                args.seed,
        "octree_resolution":   args.octree_resolution,
        # No upstream cap exists. The "API max is 20" comment removed
        # here was a documentation artefact; api_server.py and the
        # patched model_worker pass num_inference_steps straight to the
        # pipeline, whose own default is 50 (see
        # hy3dshape/pipelines.py:561). Triple-A quality runs use 50–80
        # — the orchestrator's --steps default is now 50 (see
        # asset_pipeline.py argparse).
        "num_inference_steps": args.steps,
        "guidance_scale":      args.guidance_scale,
        "num_chunks":          args.num_chunks,
        "face_count":          args.face_count,
        "type":                "glb",
    }
    if view_b64_list:
        payload["images"] = view_b64_list
    try:
        r = requests.post(f"{server}/send", json=payload, timeout=60)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"ERROR: POST /send failed: {e}")
        sys.exit(1)

    data = r.json()
    uid = data.get("uid")
    if not uid:
        print(f"ERROR: No uid in response: {data}")
        sys.exit(1)
    return uid


def poll(uid: str, server: str) -> str:
    """Poll /status/{uid} until completed; return model_base64."""
    endpoint = f"{server}/status/{uid}"
    start    = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > POLL_TIMEOUT:
            print(f"ERROR: Timed out after {POLL_TIMEOUT}s")
            sys.exit(1)

        try:
            r = requests.get(endpoint, timeout=15)
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.RequestException as e:
            print(f"  [{elapsed:6.0f}s] WARNING: status fetch failed: {e}")
            time.sleep(POLL_INTERVAL)
            continue

        status = data.get("status", "unknown")
        print(f"  [{elapsed:6.0f}s] {status}")

        if status == "completed":
            model_b64 = data.get("model_base64")
            if not model_b64:
                # api_server.py returns completed+empty when it reads a
                # 0-byte sentinel written by model_worker on shape-gen failure.
                print("ERROR: generation failed on server (status=completed but no mesh data)")
                print("  Check: docker logs witness-hunyuan 2>&1 | grep -v 'GET /status'")
                sys.exit(1)
            return model_b64
        elif status == "error":
            print(f"ERROR: generation failed: {data.get('message', 'unknown')}")
            sys.exit(1)
        else:
            time.sleep(POLL_INTERVAL)


def save_glb(model_b64: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(model_b64))
    print(f"  Saved: {output_path}  ({output_path.stat().st_size // 1024} KB)")


def main():
    p = argparse.ArgumentParser(description="Generate GLB from ref image via Hunyuan3D 2.1")
    p.add_argument("image_path",  help="Path to reference image (PNG/JPG)")
    p.add_argument("asset_id",    help="Asset id, e.g. prop_ledger_book")
    p.add_argument("--steps",           type=int,   default=50,
                   help="Inference steps. Default 50 = upstream "
                        "hy3dshape pipeline default (no API cap exists). "
                        "Triple-A quality target: 50–80.")
    p.add_argument("--seed",            type=int,   default=1234)
    p.add_argument("--octree-resolution", dest="octree_resolution",
                   type=int, default=512,
                   help="Octree resolution. Default 512 (was 256). "
                        "Higher = finer geometric detail at the cost of "
                        "VRAM. 5090 32 GB tolerates 512 across the "
                        "Phase 1 asset set; raise to 768 for hero figures "
                        "if the GPU stays under 28 GB.")
    p.add_argument("--texture",         action="store_true", default=False,
                   help="Enable Hunyuan texture pass (default off; PBR baked separately)")
    p.add_argument("--guidance-scale",  dest="guidance_scale",
                   type=float, default=8.0,
                   help="Classifier-free guidance scale. Default 8.0 "
                        "(was 5.0). Higher = stronger prompt adherence; "
                        "8.0 chosen to push Hunyuan harder on hero "
                        "assets where 5.0 collapsed to depth-card output.")
    p.add_argument("--num-chunks",      dest="num_chunks",
                   type=int,   default=8000)
    p.add_argument("--face-count",      dest="face_count",
                   type=int,   default=40000)
    p.add_argument("--output-dir",      default="processed/glb/raw",
                   help="Directory to write raw GLB (default: processed/glb/raw)")
    p.add_argument("--server",          default=HUNYUAN_API)
    p.add_argument(
        "--view",
        action="append",
        default=None,
        help=(
            "Additional canonical view PNG produced by stage 0.5 (Zero123++). "
            "Repeatable. When supplied, all views are sent to Hunyuan as a "
            "list payload alongside the primary <image_path>; the patched "
            "worker uses them for multi-view shape generation."
        ),
    )
    args = p.parse_args()

    image_path  = Path(args.image_path)
    output_path = Path(args.output_dir) / f"{args.asset_id}.glb"

    if not image_path.exists():
        print(f"ERROR: ref image not found: {image_path}")
        sys.exit(1)
    if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        print(f"ERROR: unsupported image format: {image_path.suffix}")
        sys.exit(1)

    print("━" * 56)
    print("Hunyuan3D 2.1 — Asset Generator")
    print("━" * 56)
    print(f"  Image:      {image_path}")
    print(f"  Asset id:   {args.asset_id}")
    print(f"  Steps:      {args.steps}")
    print(f"  Seed:       {args.seed}")
    print(f"  Octree res: {args.octree_resolution}")
    print(f"  Guidance:   {args.guidance_scale}")
    print(f"  Texture:    {args.texture}")
    print(f"  Output:     {output_path}")
    print("━" * 56)

    print("\n[1/3] Encoding image + submitting to /send …")
    image_b64 = encode_image(image_path)

    view_b64_list: list[str] | None = None
    if args.view:
        view_paths = [Path(v) for v in args.view]
        missing = [str(p) for p in view_paths if not p.exists()]
        if missing:
            print(f"ERROR: --view file(s) not found: {missing}")
            sys.exit(1)
        view_b64_list = [encode_image(p) for p in view_paths]
        print(f"  Multi-view:  {len(view_b64_list)} view(s) attached")

    uid = submit(image_b64, args, args.server, view_b64_list=view_b64_list)
    print(f"  uid: {uid}")

    print("\n[2/3] Polling /status/{uid} …")
    model_b64 = poll(uid, args.server)

    print("\n[3/3] Saving GLB …")
    save_glb(model_b64, output_path)

    print("\nNext steps:")
    print(f"  python tools/optimize_asset.py {output_path} {args.asset_id}")
    print("━" * 56)


if __name__ == "__main__":
    main()
