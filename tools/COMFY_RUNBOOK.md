# ComfyUI + Flux.1 [dev] — Setup & Run Runbook

The operational guide for booting a local ComfyUI server on the RTX 5090 and
driving it from the Witness asset pipeline's stage 0
(`tools/generate_ref_image.py`). Read alongside:

- [`docs/design-docs/ASSET_PIPELINE.md`](../docs/design-docs/ASSET_PIPELINE.md) — full pipeline spec.
- [`.claude/rules/asset-pipeline.md`](../.claude/rules/asset-pipeline.md) — normative rule (decision tree).
- [`tools/HUNYUAN_RUNBOOK.md`](HUNYUAN_RUNBOOK.md) — the sibling stage-1 runbook; ComfyUI shares the same Docker host and GPU.
- [`prompts/_flux_workflows/`](../prompts/_flux_workflows/) — workflow JSON templates.

---

## 0. Pre-flight

```bash
# GPU + driver (sm_120 / Blackwell needs CUDA 12.6+)
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
# Expect: NVIDIA GeForce RTX 5090, 32607 MiB, 595.71.05+

# ComfyUI process running
pgrep -af "ComfyUI/main.py" || echo "not running — see §5 to start"

# Pipeline-side tooling
python3 -c "import requests"               # generate_ref_image.py dependency
```

**VRAM coordination — automated.** `asset_pipeline.py` now calls
`POST /free` (`{"unload_models": true, "free_memory": true}`) at each
stage boundary to evict the previous stage's models before the next
one loads. Specific eviction points:

| Before | Why |
|---|---|
| Stage 1 (Hunyuan, ~20 GB) | Flush Flux/FLUX.2 models (~9–22 GB) so Hunyuan has headroom |
| Stage 2c UV reproject (Blender) | Flush SDXL (~10 GB) so Blender Cycles has VRAM |

Both servers can stay running throughout a full pipeline run.
The only case that still requires manual intervention is a **hero-workflow**
stage 0 at 1536² (~22 GB) overlapping with a simultaneous Hunyuan generate
spike — the automated flush fires before Hunyuan starts, so the window is
closed in practice. If you see OOM during stage 0 itself (not at the
boundary), stop Hunyuan manually first:

```fish
docker stop witness-hunyuan  # before a hero-workflow stage 0 run
```

---

## 1. Model layout

Models are spread across `~/ComfyUI/models/` in the paths ComfyUI was configured to scan.
Note: some directories use non-standard names (`text_encoders/`, `diffusion_models/`) because
ComfyUI was set up before the project conventions were finalised.

```
~/ComfyUI/models/
├── checkpoints/
│   ├── sd_xl_base_1.0.safetensors              #  6.5 GB — SDXL base (stage 2b) ✅
│   ├── stable-audio-open-1.0.safetensors        #  4.6 GB — audio (not yet integrated)
│   └── ltxv-13b-0.9.8-dev.safetensors (symlink) # 27.0 GB — video (not yet integrated)
├── diffusion_models/
│   └── flux-2-klein-base-9b-fp8.safetensors     #  9.0 GB — FLUX.2 [klein] UNet (stage 0.25) ✅
├── text_encoders/
│   ├── qwen_3_8b_fp8mixed.safetensors           #  8.1 GB — Qwen text encoder (stage 0.25) ✅
│   ├── t5xxl_fp16.safetensors (symlink)          #  9.2 GB — T5-XXL fp16 (available) ✅
│   └── t5_base.safetensors                       #  851 MB — T5 base (available) ✅
├── vae/
│   └── flux2-vae.safetensors                    #  321 MB — FLUX.2 VAE (stage 0.25) ✅
└── controlnet/
    └── controlnet-depth-sdxl-1.0.safetensors    #  2.4 GB — depth ControlNet (stage 2b) ✅
```

**Stage 0 (Flux.1 [dev] ref image generation) is not yet active** — the following models
still need to be downloaded:

| Model | Size | Target path |
|---|---|---|
| `flux1-dev.safetensors` | 11.9 GB | `~/ComfyUI/models/unet/flux1-dev.safetensors` |
| `ae.safetensors` (Flux VAE) | 320 MB | `~/ComfyUI/models/vae/ae.safetensors` |
| `clip_l.safetensors` | 246 MB | `~/ComfyUI/models/clip/clip_l.safetensors` |
| `t5xxl_fp8_e4m3fn.safetensors` | 4.9 GB | `~/ComfyUI/models/clip/t5xxl_fp8_e4m3fn.safetensors` |

If you need to re-download the Flux models (HuggingFace gated — accept the licence first):

```bash
huggingface-cli download black-forest-labs/FLUX.1-dev flux1-dev.safetensors \
  --local-dir ~/ComfyUI/models/unet/
huggingface-cli download black-forest-labs/FLUX.1-dev ae.safetensors \
  --local-dir ~/ComfyUI/models/vae/
huggingface-cli download comfyanonymous/flux_text_encoders clip_l.safetensors \
  t5xxl_fp8_e4m3fn.safetensors t5xxl_fp16.safetensors \
  --local-dir ~/ComfyUI/models/clip/
```

---

## 2. Start the API server

ComfyUI runs as a bare-metal Python process (installed at `/home/royce3/ComfyUI/`),
not in Docker. See §5 for start / stop commands.

---

## 3. Verify

```bash
# Liveness — /system_stats returns GPU + VRAM JSON
curl -s http://localhost:8188/system_stats | python3 -m json.tool | head -20

# UI sanity check (browser, optional)
xdg-open http://localhost:8188

# Pipeline-side smoke test — no ComfyUI call, just the prompt builder:
python tools/generate_ref_image.py vegetation_eucalyptus_mature --print-prompt-only
```

If `/system_stats` returns JSON, the server is ready for stage 0.

---

## 4. Run stage 0 against the server

### Full pipeline (recommended — uses `witness.py`):

`witness generate` automatically runs stage 0 when no ref.png exists:

```fish
cd /home/royce3/Desktop/Witness-Interactive-3D

# Generates ref.png via Flux.1 [dev], then continues through all stages
python tools/witness.py generate prop_ledger_book

# Hero ref (1536² / 40 steps) — ComfyUI peaks ~22 GB; stop Hunyuan first
python tools/witness.py generate prop_ledger_book --auto-ref-workflow hero
```

### Stage 0 only (for manual ref review before committing to full pipeline):

```bash
# Single asset
python tools/generate_ref_image.py vegetation_eucalyptus_mature --seed 481109
# writes prompts/asset-templates/vegetation_eucalyptus_mature/ref.png

# Force regenerate
python tools/generate_ref_image.py prop_ledger_book --workflow hero --seed 481110 --force
```

### Batch all Phase 1 assets via witness.py:

```fish
python tools/witness.py batch \
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
  prop_altar_candle
```

---

## 5. Stop / restart the server

ComfyUI runs as a bare-metal Python process (not Docker) on this machine:

```fish
# Find the PID
pgrep -af "ComfyUI/main.py"

# Graceful stop
pkill -f "ComfyUI/main.py"

# Start (background, persists after terminal close)
/home/royce3/ComfyUI/venv/bin/python /home/royce3/ComfyUI/main.py \
  --listen 127.0.0.1 --port 8188 \
  > /tmp/comfyui.log 2>&1 &
disown

# Wait for ready
while not curl -sf http://localhost:8188/system_stats >/dev/null 2>&1
  sleep 2
end
echo "ready"

# Tail logs
tail -f /tmp/comfyui.log
```

---

## 5b. Stage 2b — FLUX.2 [klein] img2img PBR projection

Stage 2b runs automatically as part of `asset_pipeline.py` (enabled by default,
skip with `--no-ai-project`). It calls `tools/texture_asset.py --ai-project`,
which submits `prompts/_pbr_workflows/flux2_klein_pbr.json` to ComfyUI for each
of the 6 canonical view renders produced by `bake_pbr.py`.

Phase D (2026-05-22) replaced the previous SDXL + depth-ControlNet workflow
with FLUX.2 [klein]. FLUX.2's much stronger prompt adherence is the reason for
the swap. The trade-off: no FLUX-compatible depth ControlNet is installed
locally, so depth conditioning is delegated to the beauty render itself —
`bake_pbr.py` (Phase C) emits beauty renders lit with an HDRI + per-camera key,
encoding geometry through shading. The VAE-encoded beauty seeds img2img.

### Model layout

These must exist under `~/ComfyUI/models/` before the first stage 2b run:

| File | Size | Status | Source |
|---|---|---|---|
| `diffusion_models/flux-2-klein-base-9b-fp8.safetensors` | ~9 GB | ✅ present | Black Forest Labs |
| `clip/clip_l.safetensors` | 240 MB | ✅ present | OpenAI CLIP-L |
| `clip/t5xxl_fp8_e4m3fn.safetensors` | 4.9 GB | ✅ present | Google T5-XXL fp8 |
| `vae/flux2-vae.safetensors` | ~330 MB | ✅ present | Black Forest Labs |

### What stage 2b does

For each of the 6 canonical views (front / back / left / right / top / bottom):

1. Uploads `<view>.beauty.png` from `processed/views/<id>/` to ComfyUI.
2. Uploads `<view>.depth.exr` if present (held for future depth-CN swap; the
   current workflow does not consume it).
3. Submits the FLUX.2 klein workflow: VAE-encodes the beauty PNG as the
   starting latent, runs img2img at `--ai-project-denoise` (default 0.62)
   under FluxGuidance 3.5, 28 steps, sampler euler/simple, per-view seed
   = `--ai-project-seed` + view_index.
4. Downloads the projected PBR diffuse map back as `<view>.pbr.png`.
5. Stage 2c (`reproject_views.py`) projects all six PBR maps onto the mesh UV
   to produce the final 8K albedo, replacing the procedural fallback.

### Tunable flags

| Flag | Default | Effect |
|---|---|---|
| `--ai-project-seed` | 481109 | Base seed; per-view seed = base + view_idx. |
| `--ai-project-denoise` | 0.62 | 0.55 preserves more procedural shading, 0.70 gives FLUX more material authority. |

### VRAM budget

FLUX.2 klein fp8 at 1024² draws ~14 GB (9 GB UNET + dual CLIP + VAE + activations).
Hunyuan idles at ~8 GB. Total ≈ 22 GB — safe on the RTX 5090 (32 GB). Stage 2b
runs after stage 1 (Hunyuan) finishes, so there is no simultaneous heavy load.
`flush_comfy_vram()` is still called before Blender UV reproject launches.

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `curl http://localhost:8188/system_stats` → connection refused | ComfyUI process not running. | `pgrep -af "ComfyUI/main.py"` — if empty, start it with the command in §5. Allow ~15 s for model scan on first boot. |
| `generate_ref_image.py` reports `ComfyUI unreachable` | Process not running or port conflict. | Check `pgrep -af "ComfyUI/main.py"`; pass `--server http://localhost:<port>` if you started on a different port. |
| `ComfyUI reported error` with `Could not find weights … flux1-dev.safetensors` | Model file missing from `~/ComfyUI/models/unet/`. | Re-check §1 layout. Each file must be in the exact subdirectory ComfyUI expects. |
| `CUDA error: no kernel image is available for execution on the device` | ComfyUI venv's PyTorch lacks sm_120 kernels. | `~/ComfyUI/venv/bin/pip install --upgrade torch --index-url https://download.pytorch.org/whl/cu128` then restart. |
| `Generation failed: CUDA out of memory` | Hunyuan and Flux both active simultaneously. | Stop the Hunyuan container (`docker stop witness-hunyuan`), run Flux, then restart Hunyuan. Or use the default 1024² workflow instead of hero. |
| Output drifts from `_STYLE_GUIDE.md` palette | Seed/prompt drifted or guidance too high. | Stick with seed defaults; lower `FluxGuidance.guidance` from 3.5 to 2.5 for less saturated output. Edit the workflow JSON. |
| Ref.png exists but `generate_ref_image.py` no-ops | Pipeline default is non-destructive. | Add `--force` to overwrite. |

---

## 7. After a successful run

1. Eyeball the output at `prompts/asset-templates/<id>/ref.png` against
   the per-id description in `<id>.md`. If the photo strays from
   "_STYLE_GUIDE.md", re-run with a different `--seed`.
2. Proceed to stage 1: `python tools/asset_pipeline.py <id> --kind mesh --image prompts/asset-templates/<id>/ref.png`.
   (Or run `--auto-ref` to chain stages 0 → 1 in one call.)
3. Append a one-line entry to `docs/decisions/CHANGELOG_DETAILED.md`
   noting the ref.png + seed used, so the run is reproducible.

---

## 8. Quick reference card

```fish
# ── Server management (use witness.py) ───────────────────────────────────────
python tools/witness.py start              # start ComfyUI + Hunyuan3D
python tools/witness.py start --no-hunyuan # ComfyUI only
python tools/witness.py stop               # stop both
python tools/witness.py status             # health + model inventory

# ── Asset generation ─────────────────────────────────────────────────────────
python tools/witness.py generate <id>                          # full pipeline, all models
python tools/witness.py generate <id> --fast                   # skip SDXL projection
python tools/witness.py generate <id> --multi-view             # Zero123++ shape views
python tools/witness.py generate <id> --refine-strength 0.35   # override FLUX.2 denoise
python tools/witness.py generate <id> --no-refine-ref          # skip FLUX.2 pass
python tools/witness.py generate <id> --auto-ref-workflow hero # 1536² Flux ref
python tools/witness.py batch <id1> <id2> <id3>               # sequential batch

# ── Manual ComfyUI control (if not using witness.py) ─────────────────────────
/home/royce3/ComfyUI/venv/bin/python /home/royce3/ComfyUI/main.py \
  --listen 127.0.0.1 --port 8188 > /tmp/comfyui.log 2>&1 &
disown
while not curl -sf http://localhost:8188/system_stats >/dev/null 2>&1; sleep 2; end
echo "ready"
pkill -f "ComfyUI/main.py"   # stop

# ── Texture only (re-bake existing raw GLB) ───────────────────────────────────
python tools/texture_asset.py <id> \
  --glb processed/glb/raw/<id>.glb \
  --family <leather|wood|stone|cloth|mud_brick|tin|wax|skin|vegetation> \
  --texture-size 4096 --ai-project
```
