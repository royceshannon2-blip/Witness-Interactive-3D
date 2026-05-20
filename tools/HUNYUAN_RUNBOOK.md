# Hunyuan3D 2.1 — Setup & Run Runbook

The operational guide for booting the local Hunyuan3D 2.1 server and running
the Witness asset pipeline against it. Read alongside:

- [`docs/design-docs/ASSET_PIPELINE.md`](../docs/design-docs/ASSET_PIPELINE.md) — pipeline spec.
- [`docs/design-docs/PHASE1_ASSET_LIST.md`](../docs/design-docs/PHASE1_ASSET_LIST.md) — catalogue + status.
- [`.claude/rules/asset-pipeline.md`](../.claude/rules/asset-pipeline.md) — normative rule (decision tree, forbidden shortcuts).
- [`prompts/asset-templates/_STYLE_GUIDE.md`](../prompts/asset-templates/_STYLE_GUIDE.md) — Digital Diorama style.

---

## 0. Pre-flight

Run these once before the first session to confirm the box is ready.

```bash
# GPU + driver
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
# Expect: NVIDIA GeForce RTX 5090, 32607 MiB, 595.71.05 (or newer)

# Docker + NVIDIA container toolkit
docker info | grep -i runtime              # should list "nvidia"
nvidia-container-toolkit -version          # ≥ 1.17

# Image present locally
docker image inspect kechiro/hunyuan3d-2.1-cachedstart:latest --format='{{.Id}}'
# If "No such image", pull it:
#   docker pull kechiro/hunyuan3d-2.1-cachedstart:latest   # ~12 GB

# Pipeline-side tooling
which gltf-pipeline                        # ~/.npm-global/bin/gltf-pipeline
which toktx        || echo "toktx missing — install via 'paru -S ktx-software-bin' (optional)"
python3 -c "import requests"               # generate_asset.py dependency
python3 -c "import trimesh"                # optimize_asset.py detached-island strip

# Stage 0.5 (Zero123++) — only needed when you'll pass `--multi-view`.
# The orchestrator defaults to ComfyUI's venv since it already carries the
# CUDA-wheel torch from stage 0. Override per-run with --multi-view-python
# or persistently with the env var WITNESS_MULTI_VIEW_PYTHON.
/home/royce3/ComfyUI/venv/bin/python -c "import diffusers, accelerate, torch; print(diffusers.__version__, torch.__version__, torch.cuda.is_available())"
# Expect: diffusers ≥ 0.30, torch ≥ 2.0+cuXXX, True

# Stage 0.25 (FLUX.2 [klein] ref refinement) — runs ALWAYS for mesh/animated
# kinds unless --no-refine-ref is passed. Needs three files (verified against
# ComfyUI's official FLUX.2 Klein 9B template, 2026-05):
ls -lh /home/royce3/ComfyUI/models/diffusion_models/flux-2-klein-base-9b-fp8.safetensors 2>/dev/null \
  || echo "MISSING diffusion model — see the huggingface-cli block below"
ls -lh /home/royce3/ComfyUI/models/text_encoders/qwen_3_8b_fp8mixed.safetensors 2>/dev/null \
  || echo "MISSING text encoder — see the huggingface-cli block below"
ls -lh /home/royce3/ComfyUI/models/vae/flux2-vae.safetensors 2>/dev/null \
  || echo "MISSING VAE — see the huggingface-cli block below"
```

### Downloading FLUX.2 [klein] 9B Base FP8 (one-time, ~12 GB total)

FLUX.2 Klein has a different encoder contract than FLUX.1 — single
**Qwen 3 8B** text encoder (not the dual CLIP-L + T5-XXL pair) and a
dedicated `flux2-vae.safetensors` (not Flux.1's `ae.safetensors`). The
files live under ComfyUI's `diffusion_models/`, `text_encoders/`, and
`vae/` directories respectively. Three repos:

```bash
# Authenticate once if you haven't. FLUX.2 weights are gated — you must
# also visit https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9b-fp8
# in a browser, click "Agree and access repository", *then* download.
#
# Interactive (asks for token via getpass):
hf auth login
# Non-interactive (use this under fish, since fish's getpass is unreliable —
# it silently aborts the prompt and leaves you unauthenticated):
hf auth login --token "<paste-token-from-huggingface.co/settings/tokens>"

# 1. The 9B Base diffusion model, FP8-quantized (~9 GB). The undistilled
#    base preserves the full training signal, which is what we want for
#    img2img refinement — distilled variants over-commit at low denoise.
mkdir -p /home/royce3/ComfyUI/models/diffusion_models
hf download black-forest-labs/FLUX.2-klein-base-9b-fp8 \
  flux-2-klein-base-9b-fp8.safetensors \
  --local-dir /home/royce3/ComfyUI/models/diffusion_models/ \
  --local-dir-use-symlinks False

# 2. The Qwen 3 8B FP8-mixed text encoder (~8.7 GB). The repo name is
#    spelled "encorder" (typo on HF Hub, do not correct it).
mkdir -p /home/royce3/ComfyUI/models/text_encoders
hf download Comfy-Org/vae-text-encorder-for-flux-klein-9b \
  split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors \
  --local-dir /home/royce3/ComfyUI/models/text_encoders/ \
  --local-dir-use-symlinks False
mv /home/royce3/ComfyUI/models/text_encoders/split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors \
   /home/royce3/ComfyUI/models/text_encoders/qwen_3_8b_fp8mixed.safetensors 2>/dev/null \
  && rm -rf /home/royce3/ComfyUI/models/text_encoders/split_files

# 3. The FLUX.2 VAE (~320 MB) — different from FLUX.1's ae.safetensors,
#    do NOT alias the two. Lives in the Comfy-Org flux2-dev release.
mkdir -p /home/royce3/ComfyUI/models/vae
hf download Comfy-Org/flux2-dev \
  split_files/vae/flux2-vae.safetensors \
  --local-dir /home/royce3/ComfyUI/models/vae/ \
  --local-dir-use-symlinks False
mv /home/royce3/ComfyUI/models/vae/split_files/vae/flux2-vae.safetensors \
   /home/royce3/ComfyUI/models/vae/flux2-vae.safetensors 2>/dev/null \
  && rm -rf /home/royce3/ComfyUI/models/vae/split_files
```

> If BFL or ComfyUI changes any of the above (filenames, repo IDs, or the
> node class contract for FLUX.2), edit
> [`prompts/_flux_workflows/refine.json`](../prompts/_flux_workflows/refine.json)
> to match in lockstep. The workflow is the single source of truth for
> which nodes ComfyUI loads; the orchestrator and the rest of the pipeline
> are oblivious to the swap.

**Host model cache directories.** Two on-host caches are mounted into
every container:

- `model_cache/huggingface/` (~11 GB) — the HuggingFace hub cache used
  by `diffusers`, `transformers`, etc. Mounted at
  `/workspace/model_cache` so `HF_HOME` (set in the image to
  `/workspace/model_cache/huggingface`) hits it.
- `model_cache/hy3dgen/` — the hy3dgen-specific cache that holds the
  Hunyuan3D shape model checkpoint (~7 GB after first download).
  Mounted at `/root/.cache/hy3dgen` because hy3dgen ignores `HF_HOME`
  and hard-codes that path. **First-time downloads take 10–15 minutes**
  and end up here. Once the directory is populated, subsequent
  `docker run` invocations skip the download and reach
  "Uvicorn running" in ~30–60 s.

**Do not delete either directory.** Stopping a container with `--rm`
removes its writable layer, so without the hy3dgen mount you pay the
10-minute download tax on every restart.

---

## 1. Clean stale containers (one-time)

After a host driver bump, old container instances reference stale Nvidia
runtime hook paths and refuse to start (`error during container init:
failed to fulfil mount request: open /usr/lib/libnvidia-gtk3.so.X.Y.Z`).
Wipe them and start fresh:

```bash
# List stale instances of this image
docker ps -a --filter ancestor=kechiro/hunyuan3d-2.1-cachedstart:latest \
  --format "{{.ID}} {{.Names}} {{.Status}}"

# Remove all of them (no data loss — the model_cache is on the host volume)
docker ps -a --filter ancestor=kechiro/hunyuan3d-2.1-cachedstart:latest -q \
  | xargs -r docker rm -f
```

---

## 2. Start the API server

The image's CMD is `/bin/bash`. You **must** override it with the FastAPI
entry point. Two flavours:

### 2a. Foreground (development — see live logs, Ctrl-C to stop)

```bash
cd /home/royce3/Desktop/Witness-Interactive-3D
docker run --rm --gpus all \
  -p 8081:8081 \
  -v "$PWD/model_cache:/workspace/model_cache" \
  -v "$PWD/model_cache/hy3dgen:/root/.cache/hy3dgen" \
  -v "$PWD/tools/hunyuan_patch/model_worker.py:/workspace/Hunyuan3D-2.1-CachedStart/model_worker.py:ro" \
  --name witness-hunyuan \
  kechiro/hunyuan3d-2.1-cachedstart:latest \
  python3 api_server.py
```

Wait for `Uvicorn running on http://0.0.0.0:8081` (~30–60 s with warm
cache, ~12 min cold).

### 2b. Detached (production / batch — runs in background)

```bash
cd /home/royce3/Desktop/Witness-Interactive-3D
docker run --rm -d --gpus all \
  -p 8081:8081 \
  -v "$PWD/model_cache:/workspace/model_cache" \
  -v "$PWD/model_cache/hy3dgen:/root/.cache/hy3dgen" \
  -v "$PWD/tools/hunyuan_patch/model_worker.py:/workspace/Hunyuan3D-2.1-CachedStart/model_worker.py:ro" \
  --name witness-hunyuan \
  kechiro/hunyuan3d-2.1-cachedstart:latest \
  python3 api_server.py

# Follow logs until the server reports ready
docker logs -f witness-hunyuan        # Ctrl-C just stops following; server keeps running
```

### Equivalent start_api.sh

The image also ships `start_api.sh`, which wraps the same entry point with
flag-parseable defaults (`MODEL_PATH`, `SUBFOLDER`, `PORT`, `HOST`, `DEVICE`).
Use it if you want non-default model paths:

```bash
docker run --rm --gpus all -p 8081:8081 \
  -v "$PWD/model_cache:/workspace/model_cache" \
  -v "$PWD/model_cache/hy3dgen:/root/.cache/hy3dgen" \
  -v "$PWD/tools/hunyuan_patch/model_worker.py:/workspace/Hunyuan3D-2.1-CachedStart/model_worker.py:ro" \
  --name witness-hunyuan \
  kechiro/hunyuan3d-2.1-cachedstart:latest \
  bash start_api.sh --port 8081
```

> **The `model_worker.py` bind-mount is required.** It overrides the
> upstream worker with the patched version in
> [`tools/hunyuan_patch/model_worker.py`](hunyuan_patch/model_worker.py)
> so that (a) untextured requests (`texture: false`, the project default)
> actually skip the paint pipeline, (b) the `/status/{uid}` endpoint
> reports `completed` when the paint pipeline is skipped or crashes, and
> (c) the `/send` payload accepts an ``images: [base64, …]`` list for
> multi-view shape generation (stage 0.5, Zero123++). Without the patch
> the RTX 5090 texture-kernel crash leaves the client polling until
> `generate_asset.py` times out at 1800 s, and `--multi-view` runs degrade
> to the single-view path because the unpatched worker ignores ``images``.
> See the patch's module docstring for the full diff against upstream.
> **Restart the container after pulling a new patch** — the bind-mount is
> read at FastAPI import time, not per-request.

---

## 3. Verify

```bash
# Liveness — should return 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8081/docs

# FastAPI's interactive docs page (open in browser)
xdg-open http://localhost:8081/docs   # Linux
# or just visit http://localhost:8081/docs

# GPU is actually being used
docker exec witness-hunyuan nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
# Expect non-zero used memory after first /generate call
```

If `/docs` returns 200, the server is ready.

---

## 4. Run the asset pipeline against the server

Once the server is up, the orchestrator one-liner from
`PHASE1_ASSET_LIST.md` works. Example for the hero ledger prop:

```bash
cd /home/royce3/Desktop/Witness-Interactive-3D

# Drop a reference image at prompts/asset-templates/prop_ledger_book/ref.png
# then:
python tools/asset_pipeline.py prop_ledger_book --kind mesh \
  --image prompts/asset-templates/prop_ledger_book/ref.png \
  --era shared
```

The orchestrator chains: generate → **AI-projected PBR bake** → optimize (detached-island strip +
Draco) → register (writes `docs/asset-index.md`) → export (copies to
`witness-interactive-vite/public/assets/<id>.glb`).

### Stage 2 — AI texture projection (default ON)

After Hunyuan shape generation the pipeline runs `tools/texture_asset.py --ai-project`:

1. **6-view render** — Blender renders beauty + depth EXR for each of 6 canonical views.
2. **SDXL + ControlNet depth** — ComfyUI projects PBR-styled diffuse maps onto each view (requires ComfyUI running on `:8188`).
3. **Blender Cycles bake** — Projected maps drive a Principled BSDF bake at 4K (props) / 8K (hero). Outputs albedo, metallic-roughness (R=unused, G=roughness, B=metallic), and normal maps to `processed/textures/<id>/`.
4. **GLB re-export** — `processed/glb/<id>.textured.glb` is the input to Draco optimization.

To skip the SDXL step and use procedural materials only (faster, lower quality):
```bash
python tools/asset_pipeline.py <id> --kind mesh --no-ai-project
```

### Refining ref images (stage 0.25)

The orchestrator **always** runs stage 0.25 for `--kind mesh|animated`
unless `--no-refine-ref` is passed. The pass pushes the ref through
FLUX.2 [klein] 9B Base img2img to normalise the Digital Diorama palette
+ 1994 Rwanda documentary look, so hand-picked refs from the open web
and Flux.1 [dev] stage-0 outputs both land on the same visual baseline
before stage 0.5 (Zero123++) and stage 1 (Hunyuan3D) see them.

**Per-category denoise defaults** (from
[`tools/asset_pipeline.py`](asset_pipeline.py) `REFINE_STRENGTH_BY_CATEGORY`):

| Category prefix | Denoise | Rationale |
|---|---|---|
| `vegetation_` | 0.60 | Strong palette restyle; foliage colour varies wildly in stock photos and silhouette tolerance is high. |
| `structure_`  | 0.40 | Protect doorways / roof pitches / window placement. A small palette nudge is enough. |
| `prop_`       | 0.50 | Hero objects (ledger, candle, frame). Materials + geometry both stay close. |
| `figure_`     | 0.50 | Hands / people. Higher denoise warps anatomy. |
| (anything else) | 0.50 | Fallback (`DEFAULT_REFINE_STRENGTH`). |

Override per-run with `--refine-ref-strength <0..1>`.

**Archive scheme.** First run copies `ref.png` → `ref.original.png` then
overwrites `ref.png` with the refined output. Re-runs read from
`ref.original.png` so denoise does not compound. The script no-ops when
`ref.original.png` already exists; pass `--refine-ref-force` to re-refine
(useful when changing strength or prompt suffix).

```bash
# Default: per-category strength, no flags needed
python tools/asset_pipeline.py vegetation_eucalyptus_mature --kind mesh \
  --image prompts/asset-templates/vegetation_eucalyptus_mature/ref.png \
  --multi-view --era shared

# Override strength for one asset
python tools/asset_pipeline.py prop_ledger_book --kind mesh \
  --image prompts/asset-templates/prop_ledger_book/ref.png \
  --refine-ref-strength 0.35

# Opt out entirely (ref already on-style, do not push further)
python tools/asset_pipeline.py prop_altar_candle --kind mesh \
  --image prompts/asset-templates/prop_altar_candle/ref.png \
  --no-refine-ref
```

> **VRAM coordination.** Stage 0.25 runs inside ComfyUI (same process as
> stage 0). Make sure the Hunyuan container is up but idle when stage
> 0.25 fires — ComfyUI peaks ~22 GB loading FLUX.2 klein at fp8, and the
> 5090's 32 GB cannot also hold Hunyuan's shape model. The orchestrator
> calls stage 0.25 → ComfyUI exits → stage 0.5 (Zero123++) → its venv
> exits → stage 1 (Hunyuan) — only one big model resident at a time.

### Multi-view (stage 0.5) for assets that benefit from it

Single-view Hunyuan inference sometimes flattens silhouette caps — most
visible on the crowns of trees and the tops of tall objects. Pass
`--multi-view` to insert stage 0.5 (Zero123++ v1.2): the orchestrator
synthesises six canonical views from `ref.png` and sends all of them to
the patched worker as a list payload.

```bash
python tools/asset_pipeline.py vegetation_eucalyptus_mature --kind mesh \
  --image prompts/asset-templates/vegetation_eucalyptus_mature/ref.png \
  --multi-view --era shared
```

Sequential VRAM coordination: Flux ComfyUI exits → Zero123++ runs in its
own process → Hunyuan container picks up the views. The 5090's 32 GB
holds at most one of these at a time.

> **Interpreter selection.** Stage 0.5 needs `diffusers + torch` (plus
> `accelerate`). The orchestrator runs `generate_multi_views.py` under the
> path in `--multi-view-python` (default `/home/royce3/ComfyUI/venv/bin/python`,
> persistently overridable via `WITNESS_MULTI_VIEW_PYTHON`). If neither the
> default nor the override points at a venv with diffusers installed,
> stage 0.5 fails fast with the missing-import error — `asset_pipeline.py`
> aborts before stage 1 fires, so no half-built GLB lands in `processed/`.

### Batch all Phase 1 assets

After every reference image is in place, this loop walks the catalogue.
Run from the repo root; failures continue to the next id but exit non-zero
overall:

```bash
set -e
for id in \
  structure_rugo_main_house \
  structure_rugo_tin_roof \
  structure_rugo_door \
  structure_compound_gate \
  structure_well_stone_ring \
  structure_well_cover_plank \
  structure_family_shrine_slab \
  vegetation_eucalyptus_mature \
  vegetation_eucalyptus_sapling \
  vegetation_elephant_grass \
  prop_ledger_book \
  prop_altar_photo_frame \
  prop_altar_candle ; do
    img="prompts/asset-templates/$id/ref.png"
    [ -f "$img" ] || { echo "skip $id (no ref.png)"; continue; }
    echo "── $id ──"
    python tools/asset_pipeline.py "$id" --kind mesh --image "$img" --era shared || echo "FAIL $id"
done
```

The two `figure_*_hands` assets use `--kind animated` and require an
additional `--rig <path>.blend`, so they stay out of the bulk loop until
the Blender rig pass lands.

---

## 5. Stop the server

```bash
# Foreground: Ctrl-C in the terminal running the container
# Detached:
docker stop witness-hunyuan
# (--rm in the run command auto-removes the container; cache survives on host)
```

To free GPU memory between large batch runs without unloading the model,
the API doesn't currently expose a "release memory" endpoint — stop +
restart is the only path. Subsequent startups are ~30 s thanks to the
warm cache.

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `docker start <name>` **or** `docker run` fails with `open /usr/lib/libnvidia-gtk3.so.X.Y.Z: no such file` | After a host driver upgrade the nvidia-container-toolkit hook cache still references the old driver path — affects both stale `start` calls **and** fresh `docker run` calls. | 1. Remove all stale containers: `docker ps -a --filter ancestor=<image> -q \| xargs -r docker rm -f`. 2. Regenerate the toolkit hook: `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`. 3. `docker run --gpus all ...` fresh. The toolkit reconfigure is mandatory after every driver bump. |
| `curl http://localhost:8081/docs` → connection refused | Server still warming up (model load takes 30 s warm, 12 min cold) **or** port already in use. | Wait, or `lsof -i :8081` to find a conflicting listener. The orchestrator's `--server` flag overrides the URL if you bind to a different port. |
| `generate_asset.py` reports `POST /send failed` (connection refused / timeout) | Server not running or port mapping wrong. | `docker ps --filter name=witness-hunyuan` — should show `0.0.0.0:8081->8081/tcp`. |
| `--multi-view` ran but the GLB still has a flat cap / single-view geometry | The patched `model_worker.py` wasn't picked up (bind-mount missing or container started before the patch landed), so the worker ignored `params['images']` and used only the primary image. Alternatively the installed `hy3dshape` build rejected the list and the worker silently fell back. | 1. `docker logs witness-hunyuan \| grep -i "multi-view"` — a successful list submit logs `Multi-view shape generation from 6 views`. 2. If absent, stop + restart the container so the bind-mount is re-read at FastAPI import time. 3. If the log says `hy3dshape pipeline rejected list input`, the installed `hy3dshape` is older than the upstream list-supporting version; pin a newer image or generate views one at a time. |
| `--multi-view` aborts with `No module named 'diffusers'` or `--multi-view-python <path> does not exist` | The orchestrator's stage 0.5 interpreter is missing diffusers/torch, or `--multi-view-python` points at a non-existent path. | 1. Confirm the venv: `/home/royce3/ComfyUI/venv/bin/python -c "import diffusers, torch"`. 2. If diffusers is missing, install it: `/home/royce3/ComfyUI/venv/bin/pip install "diffusers>=0.30" accelerate`. 3. To use a different interpreter persistently, `export WITNESS_MULTI_VIEW_PYTHON=/path/to/venv/bin/python` (or pass `--multi-view-python <path>` per-run). |
| Stage 0.25 reports `unet_name flux-2-klein-base-9b-fp8.safetensors not found` (or `qwen_3_8b_fp8mixed.safetensors` / `flux2-vae.safetensors` not found) | One or more of the FLUX.2 Klein files is missing. They live under three separate ComfyUI directories — `diffusion_models/`, `text_encoders/`, `vae/` — and need three separate downloads. | Run the §0 three-step `hf download` block. Common gotcha: the VAE ships at `split_files/vae/flux2-vae.safetensors` inside `Comfy-Org/flux2-dev` and must be moved to the root of `vae/` (the §0 block does the `mv` automatically). |
| Stage 0.25 succeeds but the refined ref looks identical / wildly different from the original | Denoise strength is wrong for this category. Identical ≈ strength too low; warped ≈ strength too high. | Override with `--refine-ref-strength <0..1>` (default per-category table is in `tools/asset_pipeline.py`). To re-refine without losing the audit copy, also pass `--refine-ref-force` — the script otherwise no-ops once `ref.original.png` exists. |
| Stage 0.25 fails with `POST /upload/image failed: 413` or similar size error | Source ref.png larger than ComfyUI's default upload limit. | Pre-downscale the ref to ≤ 2048² before re-running. The refine pass writes at 1024² regardless, so a > 2K source is wasted bandwidth anyway. |
| `optimize_asset.py` skips the cleanup step with `trimesh not installed` | The new detached-island strip relies on `trimesh`. | `pip install trimesh` (in the same Python env that runs the orchestrator). The pipeline still completes — Draco runs on the raw GLB — but floating islands ship to the runtime. |
| `generate_asset.py` reports `ERROR: Timed out after 1800s` while `/status` keeps returning `processing` | The `model_worker.py` bind-mount is missing, so the upstream worker's silent-fallback bug leaves only `{uid}_initial.glb` in `gradio_cache/`. The `/status/{uid}` endpoint only reports `completed` when `{uid}_textured.glb` exists, so the client polls until timeout. `docker logs witness-hunyuan` shows `Texture generation failed: CUDA error: no kernel image is available for execution on the device` (sm_120 not in `hy3dpaint`'s compiled kernels) followed by `Using untextured mesh as fallback`. | 1. Stop the container. 2. Restart with the `tools/hunyuan_patch/model_worker.py` bind-mount from §2. 3. Optionally recover the stuck job's mesh: `docker cp witness-hunyuan:/workspace/Hunyuan3D-2.1-CachedStart/gradio_cache/<uid>_initial.glb processed/glb/raw/<asset_id>.glb`. |
| `generate_asset.py` reports `ERROR: status=completed but model_base64 missing` (status goes `processing → completed` in ~10 s, but GLB is empty) | PyTorch ≤ 2.5.x was compiled without sm_120 (Blackwell) kernels. `F.conv2d` in the DINOv2 image conditioner crashes immediately, the sentinel 0-byte `_textured.glb` is written, and `api_server.py` returns `completed` with an empty payload. | **One-time fix — upgrade PyTorch inside the container:** `docker exec witness-hunyuan conda run -n hunyuan3d21 pip install --upgrade "torch==2.7.0" "torchvision==0.22.0" --index-url https://download.pytorch.org/whl/cu128` then `docker restart witness-hunyuan`. PyTorch 2.7.0+cu128 is the first release with sm_120 kernels. Note: the container needs ~4 GB of free disk space for the download; if the host drive is full, move `/var/lib/docker` to a larger partition first (see §0 pre-flight). |
| `Generation failed: CUDA out of memory` | 32 GB VRAM exhausted (large `--steps`, multi-batch, or stale state). | Lower `--steps` to 30 (iteration mode) or restart the container to reset CUDA state. The RTX 5090's 32 GB handles `--steps 50` with margin for a single asset. |
| `expected raw GLB at processed/glb/raw/<id>.glb but it was not produced` | Hunyuan completed but wrote to an unexpected path, or the download step silently truncated. | `docker logs witness-hunyuan` — look for a non-200 result download URL. Re-run the orchestrator; the optimize step is idempotent on existing files. |
| Container exits immediately after `docker run` with no error | `--gpus all` requires nvidia-container-toolkit; check `docker info \| grep nvidia`. | `sudo systemctl restart docker` after `sudo nvidia-ctk runtime configure --runtime=docker` if the runtime line is missing. |
| `gltf-pipeline` warns but pipeline still succeeds | Tool installed but `--separate` flag misordered. | Harmless — the optimize step writes `<id>.optimized.glb` either way. The orchestrator promotes it to `<id>.glb`. |
| `toktx` missing → "Skipping KTX2 compression" | Optional dependency absent. | Install via AUR: `paru -S ktx-software-bin`. Pipeline succeeds without it, just larger textures. |
| Generated GLB looks "soft" / lacking detail | Reference image too low-res, too dark, or too saturated. | Re-shoot reference per `prompts/asset-templates/_STYLE_GUIDE.md` (≥ 1024², overcast 5000 K, neutral background, desaturated). Bump `--steps 60` for hero assets. |

---

## 7. What to do after a successful run

1. Confirm registry row in `docs/asset-index.md`.
2. Confirm runtime artefact at
   `witness-interactive-vite/public/assets/<id>.glb`.
3. In `witness-interactive-vite/src/world/locations/FamilyCompound.ts`,
   find the `TODO(asset-pipeline): <id>` block and swap the
   `mk*` primitive call(s) for `assetLibrary.instantiate("<id>")` —
   preserve era tag and anchor identity. (For thin-instanced ids like
   `vegetation_eucalyptus_mature`, swap the loop body to an
   instantiate + `ThinInstance.setBuffer` call.)
4. Tick the row in `docs/design-docs/PHASE1_ASSET_LIST.md`.
5. Append a one-line entry to `docs/decisions/CHANGELOG_DETAILED.md`
   under the active milestone.

---

## 8. Quick reference card

```bash
# Boot
cd /home/royce3/Desktop/Witness-Interactive-3D
docker run --rm -d --gpus all -p 8081:8081 \
  -v "$PWD/model_cache:/workspace/model_cache" \
  -v "$PWD/model_cache/hy3dgen:/root/.cache/hy3dgen" \
  -v "$PWD/tools/hunyuan_patch/model_worker.py:/workspace/Hunyuan3D-2.1-CachedStart/model_worker.py:ro" \
  --name witness-hunyuan \
  kechiro/hunyuan3d-2.1-cachedstart:latest python3 api_server.py
docker logs -f witness-hunyuan    # wait for "Uvicorn running on http://0.0.0.0:8081"

# Health
curl -s http://localhost:8081/docs >/dev/null && echo OK

# Single asset
python tools/asset_pipeline.py <id> --kind mesh \
  --image prompts/asset-templates/<id>/ref.png

# Single asset with multi-view (stage 0.5 — for flat-top assets)
python tools/asset_pipeline.py <id> --kind mesh \
  --image prompts/asset-templates/<id>/ref.png \
  --multi-view

# Shutdown
docker stop witness-hunyuan
```
