# Hunyuan3D 2.1 server patches

The upstream `kechiro/hunyuan3d-2.1-cachedstart` API server has two
behavioural bugs that surface as `generate_asset.py: ERROR: Timed out
after 1800s` on this project's RTX 5090 host. This directory holds a
patched `model_worker.py` that we bind-mount over the upstream copy at
container start.

## What the patches change

`model_worker.py` is a near-verbatim copy of the file shipped in the
image at `/workspace/Hunyuan3D-2.1-CachedStart/model_worker.py`. The
two delta points (see the module docstring at the top of the file for
the full rationale):

1. **Respect `params['texture']`.** Upstream calls
   `self.paint_pipeline(...)` unconditionally. Our client always sends
   `texture: false` because PBR is baked downstream in Blender Cycles,
   so the paint pass is wasted work. It also crashes on RTX 5090
   (sm_120 / Blackwell) with `CUDA error: no kernel image is available
   for execution on the device` because the `hy3dpaint` custom
   rasterizer kernels were compiled for older compute capabilities.
2. **Always publish `{uid}_textured.glb`.** `api_server.py`'s
   `/status/{uid}` endpoint only returns `completed` when that exact
   filename exists. Upstream's `except` block leaves only
   `{uid}_initial.glb`, so the status endpoint reports `processing`
   forever and the client hits its 30-minute timeout. We copy the
   untextured mesh to the textured filename whenever the paint pass is
   skipped or fails, so the existing status logic detects completion.
3. **Lazy-init the paint pipeline.** Upstream constructs
   `Hunyuan3DPaintPipeline(conf)` in `ModelWorker.__init__`. The
   constructor reaches Real-ESRGAN's GPU binding (`hy3dpaint/utils/
   image_super_utils.py:25`) and crashes the entire process with the
   same sm_120 kernel error — the server never reaches "Uvicorn
   running". We defer construction to the first textured request via
   `_get_paint_pipeline()`. Untextured workloads (the project default)
   never touch the paint stack and the server boots cleanly.

We do **not** touch `api_server.py`. The status endpoint's filename
contract is the public surface; patching the worker keeps the change
local and survives any future upstream rewrite that preserves the
endpoint behaviour.

## How it is applied

`HUNYUAN_RUNBOOK.md` §2 runs the container with:

```bash
-v "$PWD/tools/hunyuan_patch/model_worker.py:/workspace/Hunyuan3D-2.1-CachedStart/model_worker.py:ro"
```

The bind-mount is read-only and survives `docker stop` + fresh
`docker run` because the file lives in the host repo. If you skip the
mount, the upstream bugs return.

## Refreshing against a new upstream

If the image is updated and the worker changes upstream:

```bash
docker run --rm kechiro/hunyuan3d-2.1-cachedstart:latest \
  cat /workspace/Hunyuan3D-2.1-CachedStart/model_worker.py \
  > tools/hunyuan_patch/model_worker.py.upstream
diff tools/hunyuan_patch/model_worker.py.upstream tools/hunyuan_patch/model_worker.py
```

Re-apply the two deltas described above against the new upstream and
delete the `.upstream` snapshot when done.
