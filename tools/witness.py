#!/usr/bin/env python3
"""
witness — Witness Interactive 3D asset generation CLI.

Commands:
  start      Start ComfyUI and the Hunyuan3D Docker container.
  stop       Stop ComfyUI and the Hunyuan3D Docker container.
  status     Server health, model inventory, and asset state.
  generate   Run the full asset pipeline for one asset ID.
  list       List all available asset templates.
  batch      Run generate sequentially for multiple asset IDs.

Examples:
  # Server management
  python tools/witness.py start
  python tools/witness.py start --no-hunyuan        # ComfyUI only
  python tools/witness.py stop
  python tools/witness.py stop --no-comfy            # Hunyuan only
  python tools/witness.py status

  # Asset generation — common patterns
  python tools/witness.py generate prop_ledger_book
  python tools/witness.py generate vegetation_eucalyptus_mature --multi-view
  python tools/witness.py generate prop_altar_candle --fast
  python tools/witness.py generate structure_rugo_main_house --refine-strength 0.35
  python tools/witness.py generate my_splat --kind splat --source captures/my.spz
  python tools/witness.py generate terrain_tiles --kind tileset --root https://example/tiles/tileset.json
  python tools/witness.py generate compound_nav --kind navmesh --terrain processed/glb/structure_rugo_main_house.glb
  python tools/witness.py generate stone_surface --kind nme --source materials/source/stone.nme.json

  # Batch mode
  python tools/witness.py batch prop_altar_candle prop_altar_photo_frame prop_ledger_book
  python tools/witness.py batch vegetation_eucalyptus_mature vegetation_eucalyptus_sapling --multi-view

  python tools/witness.py list
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
TEMPLATES_DIR = REPO_ROOT / "prompts" / "asset-templates"
PROCESSED_GLB = REPO_ROOT / "processed" / "glb"
DIAGNOSTICS_DIR = REPO_ROOT / "processed" / "diagnostics"

# Phase F retry harness — used in cmd_generate to bump seeds between
# attempts when the aggregate diagnostic recommends `retry_with_new_seed`.
# Stride is large so retries explore a distinct region of seed space
# rather than neighbouring noise patterns.
RETRY_SEED_STRIDE = 10_000

# ComfyUI — bare-metal Python process
COMFYUI_PYTHON = Path("/home/royce3/ComfyUI/venv/bin/python")
COMFYUI_MAIN = Path("/home/royce3/ComfyUI/main.py")
COMFYUI_LOG = Path("/tmp/comfyui.log")
COMFYUI_DEFAULT = "http://localhost:8188"

# Hunyuan3D — Docker container
# Local image has torch 2.11.0+cu128 for RTX 5090 (sm_120) support.
# Rebuild: docker exec witness-hunyuan pip install torch --index-url https://download.pytorch.org/whl/cu128 && docker commit witness-hunyuan witness-hunyuan-sm120:latest
HUNYUAN_IMAGE = "witness-hunyuan-sm120:latest"
HUNYUAN_NAME = "witness-hunyuan"
HUNYUAN_PATCH = REPO_ROOT / "tools" / "hunyuan_patch" / "model_worker.py"
HUNYUAN_DEFAULT = "http://localhost:8081"


# ── colour helpers ────────────────────────────────────────────────────────────

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _ok(s: str)   -> str: return f"{GREEN}✅{RESET} {s}"
def _fail(s: str) -> str: return f"{RED}❌{RESET} {s}"
def _warn(s: str) -> str: return f"{YELLOW}⚠️{RESET}  {s}"
def _head(s: str) -> str: return f"{BOLD}{CYAN}{s}{RESET}"


# ── server helpers ────────────────────────────────────────────────────────────

def _comfy_alive(server: str = COMFYUI_DEFAULT) -> bool:
    if not _HAS_REQUESTS:
        return False
    try:
        r = requests.get(f"{server}/system_stats", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _hunyuan_alive(server: str = HUNYUAN_DEFAULT) -> bool:
    if not _HAS_REQUESTS:
        return False
    try:
        r = requests.get(f"{server}/docs", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _hunyuan_container_running() -> bool:
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name={HUNYUAN_NAME}", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    return HUNYUAN_NAME in result.stdout


def _object_info_list(server: str, node: str, key: str) -> list[str]:
    if not _HAS_REQUESTS:
        return []
    try:
        r = requests.get(f"{server}/object_info/{node}", timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get(node, {}).get("input", {}).get("required", {}).get(key, [[]])[0]
    except Exception:
        return []


def detect_models(server: str = COMFYUI_DEFAULT) -> dict[str, bool]:
    """Return pipeline capability flags based on ComfyUI's installed models."""
    unet_models     = _object_info_list(server, "UNETLoader",           "unet_name")
    ckpt_models     = _object_info_list(server, "CheckpointLoaderSimple", "ckpt_name")
    controlnet_models = _object_info_list(server, "ControlNetLoader",   "control_net_name")

    return {
        "flux1_dev":       "flux1-dev.safetensors"                    in unet_models,
        "flux2_klein":     "flux-2-klein-base-9b-fp8.safetensors"     in unet_models,
    }


# ── template / asset helpers ──────────────────────────────────────────────────

def list_templates() -> list[str]:
    return sorted(
        p.stem for p in TEMPLATES_DIR.glob("*.md")
        if not p.name.startswith("_")
    )


def _asset_ref(asset_id: str) -> Path | None:
    asset_dir = TEMPLATES_DIR / asset_id
    for ext in (".png", ".jpg", ".jpeg"):
        p = asset_dir / f"ref{ext}"
        if p.exists():
            return p
    return None


def _asset_processed(asset_id: str) -> bool:
    return (PROCESSED_GLB / f"{asset_id}.glb").exists()


# ── server management ─────────────────────────────────────────────────────────

def _start_comfyui(server: str) -> int:
    if _comfy_alive(server):
        print(f"{_ok('ComfyUI already running')} at {server}", flush=True)
        return 0
    if not COMFYUI_PYTHON.exists():
        print(_fail(f"ComfyUI venv not found: {COMFYUI_PYTHON}"), flush=True)
        return 1
    if not COMFYUI_MAIN.exists():
        print(_fail(f"ComfyUI main.py not found: {COMFYUI_MAIN}"), flush=True)
        return 1

    print(f"Starting ComfyUI → log: {COMFYUI_LOG}", flush=True)
    with COMFYUI_LOG.open("w") as log_fh:
        proc = subprocess.Popen(
            [str(COMFYUI_PYTHON), str(COMFYUI_MAIN), "--listen", "127.0.0.1", "--port", "8188"],
            stdout=log_fh,
            stderr=log_fh,
            start_new_session=True,
        )
    print(f"  PID {proc.pid} — waiting for server…", flush=True)
    deadline = time.time() + 120
    last_tick = 0.0
    while time.time() < deadline:
        if _comfy_alive(server):
            print(_ok("ComfyUI ready"), flush=True)
            return 0
        now = time.time()
        if now - last_tick >= 10:
            elapsed = int(now - (deadline - 120))
            print(f"  [{elapsed:3d}s] waiting for ComfyUI…", flush=True)
            last_tick = now
        time.sleep(2)
    print(_fail("ComfyUI did not come up within 120 s — check /tmp/comfyui.log"), flush=True)
    return 1


def _start_hunyuan(wait: bool = True) -> int:
    if not shutil.which("docker"):
        print(_fail("docker not on PATH — cannot start Hunyuan3D"), flush=True)
        return 1
    if _hunyuan_container_running():
        print(_ok("Hunyuan3D already running"), flush=True)
        return 0

    model_cache = REPO_ROOT / "model_cache"
    triton_cache = Path.home() / ".triton"
    triton_cache.mkdir(exist_ok=True)
    cmd = [
        "docker", "run", "--rm", "-d", "--gpus", "all",
        "--privileged",                # RTX 5090 / driver 595.71.05: cuInit() fails under
                                       # CDI-only GPU pass-through without full device access.
                                       # --privileged is needed until nvidia-container-runtime
                                       # is registered in /etc/docker/daemon.json (requires
                                       # `sudo nvidia-ctk runtime configure --runtime=docker`
                                       # + Docker daemon restart).
        "-p", "8081:8081",
        "--shm-size=16g",              # model worker IPC; default 64 MB causes stalls
        "-v", f"{model_cache}:/workspace/model_cache",
        "-v", f"{model_cache}/hy3dgen:/root/.cache/hy3dgen",
        # HF model cache — DINOv2 giant + Hunyuan paint models live here;
        # mounting avoids re-downloading and skips slow overlay-fs reads.
        "-v", f"{model_cache}/huggingface:/root/.cache/huggingface",
        # Triton kernel cache — sm_120 kernels compiled on first start are
        # reused on every subsequent start, saving several minutes per restart.
        "-v", f"{triton_cache}:/root/.triton",
        "-v", f"{HUNYUAN_PATCH}:/workspace/Hunyuan3D-2.1-CachedStart/model_worker.py:ro",
        "--name", HUNYUAN_NAME,
        HUNYUAN_IMAGE,
        "python3", "api_server.py",
    ]
    print("Starting Hunyuan3D container…", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if result.returncode != 0:
        print(_fail(f"docker run failed: {result.stderr.strip()}"), flush=True)
        return 1
    short_id = result.stdout.strip()[:12]
    print(f"  Container: {short_id}…", flush=True)

    if not wait:
        print(_warn("Hunyuan3D loading in background (cold start ~12 min) — watch status dots"), flush=True)
        return 0

    print("  Waiting for Hunyuan3D API (30-60 s warm, ~12 min cold)…", flush=True)
    deadline = time.time() + 360  # 6 min — generous for warm start
    last_tick = 0.0
    while time.time() < deadline:
        if _hunyuan_alive():
            print(_ok("Hunyuan3D ready"), flush=True)
            return 0
        now = time.time()
        if now - last_tick >= 15:
            elapsed = int(now - (deadline - 360))
            print(f"  [{elapsed:3d}s] waiting for Hunyuan3D API…", flush=True)
            last_tick = now
        time.sleep(5)
    # Don't fail — cold model load can exceed 6 min; status dots will catch it.
    print(_warn(f"Hunyuan3D still loading — follow: docker logs -f {HUNYUAN_NAME}"), flush=True)
    return 0


def _stop_comfyui() -> None:
    result = subprocess.run(["pgrep", "-af", "ComfyUI/main.py"], capture_output=True, text=True)
    if result.stdout.strip():
        print("Stopping ComfyUI…", flush=True)
        subprocess.run(["pkill", "-f", "ComfyUI/main.py"])
        print(_ok("ComfyUI stopped"), flush=True)
    else:
        print("ComfyUI not running.", flush=True)


def _stop_hunyuan() -> None:
    if not shutil.which("docker"):
        print("docker not on PATH — skipping Hunyuan3D stop.", flush=True)
        return
    if _hunyuan_container_running():
        print("Stopping Hunyuan3D container…", flush=True)
        stop_result = subprocess.run(
            ["docker", "stop", HUNYUAN_NAME],
            capture_output=True, text=True,
        )
        if stop_result.returncode == 0:
            print(_ok("Hunyuan3D stopped"), flush=True)
        else:
            err = (stop_result.stderr or stop_result.stdout).strip()
            if "no such container" in err.lower():
                print(_ok("Hunyuan3D already stopped (container cleaned up)"), flush=True)
            else:
                print(_warn(f"docker stop returned {stop_result.returncode}: {err}"), flush=True)
    else:
        print("Hunyuan3D not running.", flush=True)


# ── subcommands ───────────────────────────────────────────────────────────────

def cmd_start(args: argparse.Namespace) -> int:
    rc = 0
    wait = not getattr(args, "no_wait", False)
    if not args.no_comfy:
        rc |= _start_comfyui(getattr(args, "comfy_server", COMFYUI_DEFAULT))
    if not args.no_hunyuan:
        rc |= _start_hunyuan(wait=wait)
    return rc


def cmd_stop(args: argparse.Namespace) -> int:
    if not args.no_comfy:
        _stop_comfyui()
    if not args.no_hunyuan:
        _stop_hunyuan()
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    server  = getattr(args, "comfy_server", COMFYUI_DEFAULT)
    hunyuan = getattr(args, "hunyuan_server", HUNYUAN_DEFAULT)

    print(_head("\nServers"))
    comfy_up = _comfy_alive(server)
    print(f"  ComfyUI    {_ok(server)   if comfy_up else _fail(server + ' (not running)')}")
    huan_up = _hunyuan_alive(hunyuan)
    print(f"  Hunyuan3D  {_ok(hunyuan)  if huan_up  else _fail(hunyuan + ' (not running)')}")

    print(_head("\nPipeline stages"))
    caps = detect_models(server) if comfy_up else {k: False for k in ("flux1_dev", "flux2_klein")}

    stages = [
        ("Stage 0   ", "Flux.1 [dev] ref image gen",    "flux1_dev",   "flux1-dev.safetensors"),
        ("Stage 0.25", "FLUX.2 [klein] ref refinement", "flux2_klein", "flux-2-klein-base-9b-fp8.safetensors"),
        ("Stage 1   ", "Hunyuan3D shape generation (ensemble N=3)",         None, None),
        ("Stage 2a  ", "Blender Cycles PBR bake (HDRI + key light + depth)", None, None),
        ("Stage 2b  ", "FLUX.2 [klein] PBR projection",  "flux2_klein", "flux-2-klein-base-9b-fp8.safetensors"),
        ("Stage 2c  ", "Blender UV reprojection",        None, None),
    ]
    for label, desc, cap_key, model_name in stages:
        if cap_key is None:
            status = _ok("always runs")
        elif caps.get(cap_key):
            status = _ok(model_name)
        else:
            status = _fail(f"{model_name} not found") if model_name else _warn("unavailable")
        print(f"  {label}  {desc:<40} {status}")

    print(_head("\nAssets"))
    templates = list_templates()
    print(f"  {len(templates)} templates\n")
    for tid in templates:
        ref  = "ref ✅" if _asset_ref(tid)       else "ref ❌"
        proc = "glb ✅" if _asset_processed(tid)  else "glb ❌"
        print(f"  {tid:<42} [{ref}]  [{proc}]")

    return 0


def _build_generate_cmd(args: argparse.Namespace, asset_id: str) -> list[str]:
    """Translate witness.py generate flags into an asset_pipeline.py invocation."""
    server  = getattr(args, "comfy_server",   COMFYUI_DEFAULT)
    hunyuan = getattr(args, "hunyuan_server", HUNYUAN_DEFAULT)

    cmd: list[str] = [
        sys.executable,
        str(TOOLS_DIR / "asset_pipeline.py"),
        asset_id,
        "--kind",  args.kind,
        "--era",   args.era,
        "--comfy-server", server,
        "--server",       hunyuan,
    ]

    # ── kind-specific inputs ──────────────────────────────────────────────────
    if args.kind in ("mesh", "animated"):
        image = getattr(args, "image", None)
        if image:
            cmd.extend(["--image", image])
        else:
            existing = _asset_ref(asset_id)
            if existing:
                cmd.extend(["--image", str(existing)])
            elif not getattr(args, "no_ref", False):
                cmd.append("--auto-ref")
            # if no_ref and no image: asset_pipeline.py will error with a clear message

        if getattr(args, "rig", None):
            cmd.extend(["--rig", args.rig])

    if args.kind in ("splat", "nme") and getattr(args, "source", None):
        cmd.extend(["--source", args.source])

    if args.kind == "tileset" and getattr(args, "root", None):
        cmd.extend(["--root", args.root])

    if args.kind == "navmesh":
        for t in (getattr(args, "terrain", None) or []):
            cmd.extend(["--terrain", t])

    # ── stage 0 ───────────────────────────────────────────────────────────────
    if getattr(args, "auto_ref_force", False):
        cmd.append("--auto-ref-force")
    cmd.extend(["--auto-ref-workflow", getattr(args, "auto_ref_workflow", "default")])
    cmd.extend(["--auto-ref-seed",     str(getattr(args, "auto_ref_seed", 481109))])

    # ── stage 0.25 ────────────────────────────────────────────────────────────
    if getattr(args, "no_refine_ref", False):
        cmd.append("--no-refine-ref")
    strength = getattr(args, "refine_strength", None)
    if strength is not None:
        cmd.extend(["--refine-ref-strength", str(strength)])
    if getattr(args, "refine_force", False):
        cmd.append("--refine-ref-force")
    cmd.extend(["--refine-ref-seed", str(getattr(args, "refine_seed", 481109))])

    # ── stage 0.5 ─────────────────────────────────────────────────────────────
    if getattr(args, "multi_view", False):
        cmd.append("--multi-view")
        cmd.extend(["--multi-view-steps",    str(getattr(args, "mv_steps",    75))])
        cmd.extend(["--multi-view-guidance",  str(getattr(args, "mv_guidance",  4.0))])
        cmd.extend(["--multi-view-seed",      str(getattr(args, "mv_seed",      481109))])

    # ── real multi-view (overrides synthesis when supplied) ───────────────────
    if getattr(args, "real_views", None):
        cmd.extend(["--real-views", str(args.real_views)])

    # ── stage 1 ───────────────────────────────────────────────────────────────
    cmd.extend(["--steps", str(getattr(args, "steps", 50))])
    if getattr(args, "octree_resolution", None) is not None:
        cmd.extend(["--octree-resolution", str(args.octree_resolution)])
    if getattr(args, "guidance_scale", None) is not None:
        cmd.extend(["--guidance-scale", str(args.guidance_scale)])
    cmd.extend(["--ensemble-size",      str(getattr(args, "ensemble_size",      3))])
    cmd.extend(["--ensemble-base-seed", str(getattr(args, "ensemble_base_seed", 481109))])

    # ── stage 2 ───────────────────────────────────────────────────────────────
    if getattr(args, "fast", False):
        cmd.append("--no-ai-project")
    cmd.extend(["--texture-family", getattr(args, "texture_family", "auto")])
    cmd.extend(["--texture-size",   str(getattr(args, "texture_size",  8192))])
    cmd.extend(["--bake-samples",   str(getattr(args, "bake_samples",   128))])
    cmd.extend(["--ai-project-seed",    str(getattr(args, "ai_project_seed",    481109))])
    cmd.extend(["--ai-project-denoise", str(getattr(args, "ai_project_denoise", 0.62))])
    if getattr(args, "skip_views", False):
        cmd.append("--skip-views")

    # ── stages 4–5: LODs + collision ─────────────────────────────────────────
    if getattr(args, "no_lods", False):
        cmd.append("--no-lods")
    if getattr(args, "no_collision", False):
        cmd.append("--no-collision")
    max_hulls = getattr(args, "collision_max_hulls", 16)
    if max_hulls != 16:
        cmd.extend(["--collision-max-hulls", str(max_hulls)])

    # ── checkpoint resume ─────────────────────────────────────────────────────
    if getattr(args, "skip_generate", False):
        cmd.append("--skip-generate")

    # ── advanced ──────────────────────────────────────────────────────────────
    cmd.extend(["--draco-level", str(getattr(args, "draco_level", 7))])
    if getattr(args, "validation_renders", False):
        cmd.append("--validation-renders")

    return cmd


def _read_aggregate_action(asset_id: str) -> tuple[str | None, dict]:
    """
    Inspect ``processed/diagnostics/<id>.aggregate.json`` and return
    ``(recommended_action, full_doc)``.

    Returns ``(None, {})`` if the aggregate is missing — Phase F treats
    a missing aggregate as inconclusive (no auto-retry; surface the
    underlying exit code to the operator).
    """
    import json as _json
    path = DIAGNOSTICS_DIR / f"{asset_id}.aggregate.json"
    if not path.exists():
        return None, {}
    try:
        doc = _json.loads(path.read_text())
    except _json.JSONDecodeError:
        return None, {}
    return doc.get("recommended_action"), doc


def cmd_generate(args: argparse.Namespace) -> int:
    """
    Run the full asset pipeline with Phase F auto-retry.

    Loop semantics:
      * attempt 1 runs at the user-supplied seeds.
      * Each retry bumps `--ensemble-base-seed` and `--ai-project-seed`
        by `RETRY_SEED_STRIDE` so we explore a distinct region of seed
        space rather than neighbouring noise patterns.
      * The loop terminates on:
          - subprocess exit 0 AND aggregate action == "pass"  → success
          - aggregate action == "halt_and_fix_pipeline"        → contract
            violation that won't unstick by re-rolling; surface immediately
          - exhaustion of --max-retries                         → failure
      * A missing aggregate (e.g. pipeline died before any gates ran) is
        treated as inconclusive; we trust the subprocess exit code as-is.
    """
    asset_id = args.asset_id
    server   = getattr(args, "comfy_server", COMFYUI_DEFAULT)

    # Template check for mesh/animated kinds
    if args.kind in ("mesh", "animated"):
        template = TEMPLATES_DIR / f"{asset_id}.md"
        if not template.exists():
            print(_fail(f"No template found: prompts/asset-templates/{asset_id}.md"))
            print("  Run `python tools/witness.py list` to see available assets.")
            return 1

    # Report which AI stages are active
    if _HAS_REQUESTS and _comfy_alive(server):
        caps = detect_models(server)
        active: list[str] = []
        if caps.get("flux1_dev"):
            active.append("Flux.1 [dev] (stage 0)")
        if caps.get("flux2_klein"):
            active.append("FLUX.2 [klein] (stage 0.25 + 2b)")
        if active:
            print(f"  Active AI stages: {', '.join(active)}")
    elif args.kind in ("mesh", "animated"):
        print(_warn("ComfyUI not reachable — AI stages 0 / 0.25 / 2b will be skipped"))

    max_retries = max(1, int(getattr(args, "max_retries", 3)))
    base_ensemble_seed = int(getattr(args, "ensemble_base_seed", 481109))
    base_project_seed  = int(getattr(args, "ai_project_seed",     481109))

    last_rc = 0
    for attempt in range(max_retries):
        # Bump seeds on retries so we genuinely explore new regions.
        args.ensemble_base_seed = base_ensemble_seed + attempt * RETRY_SEED_STRIDE
        args.ai_project_seed    = base_project_seed  + attempt * RETRY_SEED_STRIDE

        cmd = _build_generate_cmd(args, asset_id)

        attempt_label = f"attempt {attempt + 1}/{max_retries}"
        print(_head(f"\nGenerating: {asset_id} ({attempt_label})"))
        print(f"  Kind: {args.kind}  |  Era: {args.era}")
        print(f"  ensemble base seed: {args.ensemble_base_seed}  |  project seed: {args.ai_project_seed}")
        print(f"  {' '.join(cmd[2:])}\n")

        result = subprocess.run(cmd, cwd=REPO_ROOT)
        last_rc = result.returncode
        action, doc = _read_aggregate_action(asset_id)

        if last_rc == 0 and (action in (None, "pass")):
            if action == "pass":
                print(_ok(f"Done: {asset_id} — all gates pass (action={action})"))
            else:
                # Pipeline succeeded but no aggregate was written (likely a
                # non-mesh kind that doesn't run the validators). Trust the
                # exit code and stop retrying.
                print(_ok(f"Done: {asset_id}"))
            return 0

        if action == "halt_and_fix_pipeline":
            print(_fail(
                f"Pipeline halted for {asset_id}: aggregate verdict is "
                f"`halt_and_fix_pipeline` — a contract violation that re-rolling "
                f"will not fix. Inspect processed/diagnostics/{asset_id}.report.md."
            ))
            return last_rc or 2

        # action == "retry_with_new_seed" OR (rc != 0 AND no aggregate)
        # The latter happens when the pipeline died inside generation —
        # the same retry stride still applies; if the problem is a
        # missing tool / unreachable server, the next attempt will fail
        # identically and we'll exit cleanly after max_retries.
        if attempt + 1 < max_retries:
            verdict = action or "no-aggregate"
            print(_warn(
                f"{asset_id} attempt {attempt + 1} failed (rc={last_rc}, "
                f"verdict={verdict}); retrying with seed offset "
                f"{(attempt + 1) * RETRY_SEED_STRIDE}…"
            ))
        else:
            print(_fail(
                f"{asset_id} exhausted {max_retries} attempts; final "
                f"verdict={action or 'unknown'}, rc={last_rc}. See "
                f"processed/diagnostics/{asset_id}.report.md."
            ))

    return last_rc or 2


def cmd_list(args: argparse.Namespace) -> int:
    templates = list_templates()
    print(_head(f"\nAvailable assets ({len(templates)} templates)\n"))
    for tid in templates:
        ref  = "✅" if _asset_ref(tid)      else "❌"
        proc = "✅" if _asset_processed(tid) else "  "
        print(f"  {ref} ref  {proc} glb    {tid}")
    print()
    print("Usage: python tools/witness.py generate <asset_id>")
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    ids = args.asset_ids
    print(_head(f"\nBatch: {len(ids)} assets"))
    failed: list[str] = []
    for i, asset_id in enumerate(ids, 1):
        print(f"\n[{i}/{len(ids)}] {asset_id}")
        gen_args = argparse.Namespace(**{**vars(args), "asset_id": asset_id})
        rc = cmd_generate(gen_args)
        if rc != 0:
            failed.append(asset_id)

    print()
    if failed:
        print(_fail(f"Failed ({len(failed)}): {', '.join(failed)}"))
        return 1
    print(_ok(f"All {len(ids)} assets complete"))
    return 0


# ── argument parser ───────────────────────────────────────────────────────────

def _add_generate_flags(p: argparse.ArgumentParser) -> None:
    """Attach the full set of pipeline flags to a generate or batch subparser."""

    # ── what to generate ─────────────────────────────────────────────────────
    p.add_argument(
        "--kind", default="mesh",
        choices=["mesh", "splat", "tileset", "navmesh", "nme", "animated"],
        help=(
            "Asset kind (default: mesh). "
            "mesh=Hunyuan3D GLB; splat=Gaussian splat; tileset=3D Tiles; "
            "navmesh=pathfinding mesh; nme=Node Material Editor JSON; animated=rigged mesh."
        ),
    )
    p.add_argument(
        "--era", default="shared", choices=["present", "past", "shared"],
        help="ChronosSwitch era scope (default: shared).",
    )

    # ── kind-specific inputs ──────────────────────────────────────────────────
    inp = p.add_argument_group("Inputs (kind-specific)")
    inp.add_argument(
        "--image", metavar="PATH",
        help=(
            "Reference image for mesh/animated (default: auto-detect from "
            "prompts/asset-templates/<id>/ref.png; auto-generate with Flux.1 [dev] if absent)."
        ),
    )
    inp.add_argument(
        "--real-views", dest="real_views", metavar="DIR",
        help=(
            "Directory of REAL multi-angle captures (photos/renders) for "
            "mesh/animated. Each is background-removed + framed (same cleanup "
            "as synthesis), then fed to Hunyuan's multi-view mode; Zero123++ "
            "synthesis is skipped — observed angles beat synthesised ones for "
            "all-angle accuracy. Any count, png/jpg."
        ),
    )
    inp.add_argument(
        "--source", metavar="PATH",
        help="Source file for splat (.ply/.spz/.sog) or nme (.json) kinds.",
    )
    inp.add_argument(
        "--root", metavar="URL",
        help="3D Tileset root URL or local tileset.json path (tileset kind).",
    )
    inp.add_argument(
        "--terrain", action="append", metavar="GLB",
        help="Terrain GLB for navmesh kind (repeatable for multi-mesh navmesh).",
    )
    inp.add_argument(
        "--rig", metavar="PATH",
        help="Skeletal rig .blend/.fbx for animated kind.",
    )

    # ── stage 0: ref generation ───────────────────────────────────────────────
    s0 = p.add_argument_group("Stage 0 — Flux.1 [dev] reference image generation")
    s0.add_argument(
        "--no-ref", action="store_true",
        help="Skip ref.png generation even when none exists (pipeline will error if ref is absent).",
    )
    s0.add_argument(
        "--auto-ref-force", action="store_true",
        help="Regenerate ref.png via Flux even when one already exists.",
    )
    s0.add_argument(
        "--auto-ref-workflow", default="default", choices=["default", "hero"],
        help="'default' = 1024², 20 steps; 'hero' = 1536², 40 steps (stop Hunyuan first for VRAM). Default: default.",
    )
    s0.add_argument(
        "--auto-ref-seed", type=int, default=481109, metavar="N",
        help="Flux noise seed (default: 481109).",
    )

    # ── stage 0.25: ref refinement ────────────────────────────────────────────
    s025 = p.add_argument_group("Stage 0.25 — FLUX.2 [klein] ref refinement (always-on for mesh/animated)")
    s025.add_argument(
        "--no-refine-ref", action="store_true",
        help="Skip ref refinement (use when ref.png is already on the Digital Diorama palette).",
    )
    s025.add_argument(
        "--refine-strength", type=float, default=None, metavar="0.0-1.0",
        help=(
            "Denoise strength override for FLUX.2 [klein] refinement. "
            "Defaults: vegetation=0.60, structure=0.40, prop/figure=0.50."
        ),
    )
    s025.add_argument(
        "--refine-force", action="store_true",
        help="Re-refine even when ref.original.png already exists.",
    )
    s025.add_argument(
        "--refine-seed", type=int, default=481109, metavar="N",
        help="FLUX.2 [klein] noise seed (default: 481109).",
    )

    # ── stage 0.5: multi-view ─────────────────────────────────────────────────
    s05 = p.add_argument_group("Stage 0.5 — Zero123++ multi-view synthesis (optional)")
    s05.add_argument(
        "--multi-view", action="store_true",
        help=(
            "Synthesise 6 canonical views from ref.png for richer Hunyuan shape inference. "
            "Recommended for trees, roofs, and other flat-top assets."
        ),
    )
    s05.add_argument(
        "--mv-steps", type=int, default=75, metavar="N",
        help="Zero123++ diffusion steps (default: 75; range 50-100).",
    )
    s05.add_argument(
        "--mv-guidance", type=float, default=4.0, metavar="F",
        help="Zero123++ guidance scale (default: 4.0).",
    )
    s05.add_argument(
        "--mv-seed", type=int, default=481109, metavar="N",
        help="Zero123++ noise seed (default: 481109).",
    )

    # ── stage 1: Hunyuan3D ────────────────────────────────────────────────────
    s1 = p.add_argument_group("Stage 1 — Hunyuan3D 2.1 shape generation")
    s1.add_argument(
        "--steps", type=int, default=50, metavar="N",
        help=(
            "Hunyuan3D inference steps (default: 50 — the upstream "
            "hy3dshape pipeline default; the prior `min(steps, 20)` "
            "in generate_asset.py was a documentation artefact). "
            "Triple-A runs use 50–80; speed iteration can drop to 20."
        ),
    )
    s1.add_argument(
        "--octree-resolution", dest="octree_resolution", type=int, default=None,
        metavar="N",
        help=(
            "Hunyuan octree resolution (default: 512 inside generate_asset.py). "
            "Higher = finer geometry detail, more VRAM. RTX 5090 tolerates 768 "
            "for hero figures; 512 for standard props; 256 for fast iteration."
        ),
    )
    s1.add_argument(
        "--guidance-scale", dest="guidance_scale", type=float, default=None,
        metavar="F",
        help=(
            "Hunyuan classifier-free guidance scale (default: 8.0 inside "
            "generate_asset.py). Higher = stronger adherence to the reference "
            "image. Workable range 5.0–12.0."
        ),
    )
    s1.add_argument(
        "--hunyuan-server", default=HUNYUAN_DEFAULT, metavar="URL",
        help=f"Hunyuan3D server URL (default: {HUNYUAN_DEFAULT}).",
    )

    # ── stage 1 quality control: ensemble + retry harness ────────────────────
    qc = p.add_argument_group("Stage 1 quality control — multi-seed ensemble + retry harness")
    qc.add_argument(
        "--ensemble-size", type=int, default=3, metavar="N",
        help=(
            "Number of independent Hunyuan seeds per attempt (default: 3, Phase E). "
            "Winner is picked by the composite geometry score. Set to 1 for speed."
        ),
    )
    qc.add_argument(
        "--ensemble-base-seed", type=int, default=481109, metavar="N",
        help="Base seed for the ensemble; per-candidate seed = base + index.",
    )
    qc.add_argument(
        "--max-retries", type=int, default=3, metavar="N",
        help=(
            "Maximum pipeline attempts when the aggregate diagnostic recommends "
            "`retry_with_new_seed` (default: 3, Phase F). Each retry bumps the "
            "ensemble base seed by RETRY_SEED_STRIDE (10000). `halt_and_fix_pipeline` "
            "verdicts skip remaining retries."
        ),
    )
    qc.add_argument(
        "--ai-project-seed", type=int, default=481109, metavar="N",
        help="Base seed for FLUX.2 [klein] stage 2b img2img (per-view = base + view_index).",
    )
    qc.add_argument(
        "--ai-project-denoise", type=float, default=0.62, metavar="0.0-1.0",
        help="FLUX.2 [klein] img2img denoise strength (default 0.62; workable band 0.55–0.70).",
    )

    # ── stage 2: texturing ────────────────────────────────────────────────────
    s2 = p.add_argument_group("Stage 2 — Blender Cycles PBR bake + FLUX.2 [klein] AI projection")
    s2.add_argument(
        "--fast", action="store_true",
        help="Skip FLUX.2 AI projection; use procedural Blender bake only (faster, lower quality).",
    )
    s2.add_argument(
        "--texture-family", default="auto", metavar="FAMILY",
        help=(
            "Material family override (auto-picked from asset_id prefix by default). "
            "Choices: leather, wood, stone, cloth, mud_brick, tin, wax, skin, vegetation."
        ),
    )
    s2.add_argument(
        "--texture-size", type=int, default=8192, metavar="PX",
        help="PBR map resolution in pixels (default: 8192).",
    )
    s2.add_argument(
        "--bake-samples", type=int, default=128, metavar="N",
        help="Cycles samples per bake pass (default: 128).",
    )
    s2.add_argument(
        "--skip-views", action="store_true",
        help="Skip the 6-view render; reuse existing processed/views/<id>/ from a previous run.",
    )

    # ── stages 4–5: LODs + collision ─────────────────────────────────────────
    lods = p.add_argument_group("Stage 4 — LOD generation (gltf-transform simplify, ON by default)")
    lods.add_argument(
        "--no-lods", action="store_true",
        help="Skip LOD1 + LOD2 generation (speed-iteration runs only).",
    )

    coll = p.add_argument_group("Stage 5 — Collision hull generation (trimesh, ON by default)")
    coll.add_argument(
        "--no-collision", action="store_true",
        help="Skip convex hull collision GLB generation.",
    )
    coll.add_argument(
        "--collision-max-hulls", type=int, default=16, metavar="N",
        help="Maximum convex hulls in the collision GLB (default: 16).",
    )

    # ── checkpoint resume ─────────────────────────────────────────────────────
    resume = p.add_argument_group("Checkpoint resume")
    resume.add_argument(
        "--skip-generate",
        action="store_true",
        dest="skip_generate",
        help=(
            "Skip Hunyuan generation + PBR texturing and resume from an existing "
            "textured or raw GLB. Use when generation succeeded but "
            "optimization/export failed mid-pipeline."
        ),
    )

    # ── advanced ──────────────────────────────────────────────────────────────
    adv = p.add_argument_group("Advanced")
    adv.add_argument(
        "--draco-level", type=int, default=7, metavar="1-10",
        help="Draco mesh compression level (default: 7).",
    )
    adv.add_argument(
        "--validation-renders", action="store_true",
        help="Emit 4 turntable + 1 hero PNG via Blender 3-point lighting (adds ~2 min).",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="witness",
        description="Witness Interactive 3D — asset generation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--comfy-server", default=COMFYUI_DEFAULT,
        help=f"ComfyUI API URL (default: {COMFYUI_DEFAULT}).",
    )
    p.add_argument(
        "--hunyuan-server", default=HUNYUAN_DEFAULT,
        help=f"Hunyuan3D API URL (default: {HUNYUAN_DEFAULT}).",
    )

    sub = p.add_subparsers(dest="command", required=True)

    # start
    start = sub.add_parser("start", help="Start ComfyUI and Hunyuan3D servers.")
    start.add_argument("--no-comfy",   action="store_true", help="Skip starting ComfyUI.")
    start.add_argument("--no-hunyuan", action="store_true", help="Skip starting Hunyuan3D.")
    start.add_argument("--no-wait",    action="store_true",
                       help="Fire Hunyuan container and return immediately without polling for readiness."
                            " Useful when a GUI is already polling status independently.")

    # stop
    stop = sub.add_parser("stop", help="Stop ComfyUI and Hunyuan3D servers.")
    stop.add_argument("--no-comfy",   action="store_true", help="Skip stopping ComfyUI.")
    stop.add_argument("--no-hunyuan", action="store_true", help="Skip stopping Hunyuan3D.")

    # status / list
    sub.add_parser("status", help="Server health, model inventory, and asset state.")
    sub.add_parser("list",   help="List available asset templates.")

    # generate
    gen = sub.add_parser(
        "generate",
        help="Full pipeline for one asset (Flux → FLUX.2 → Hunyuan ensemble → Blender → FLUX.2 PBR → export).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    gen.add_argument("asset_id", help="Snake_case asset ID (e.g. prop_ledger_book).")
    _add_generate_flags(gen)

    # batch
    batch = sub.add_parser(
        "batch",
        help="Run generate sequentially for multiple asset IDs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    batch.add_argument("asset_ids", nargs="+", help="One or more asset IDs.")
    _add_generate_flags(batch)

    return p


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "start":    cmd_start,
        "stop":     cmd_stop,
        "status":   cmd_status,
        "generate": cmd_generate,
        "list":     cmd_list,
        "batch":    cmd_batch,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
