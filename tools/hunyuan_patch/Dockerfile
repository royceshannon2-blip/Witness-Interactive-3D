# Witness Hunyuan3D image — upstream + sm_120 (RTX 5090) PyTorch.
#
# The upstream kechiro/hunyuan3d-2.1-cachedstart image ships
# torch==2.5.1+cu124, whose precompiled kernels stop at sm_90. On a 5090
# every GPU op (shape diffusion, texture pass, even a `torch.randn`)
# crashes with:
#
#   RuntimeError: CUDA error: no kernel image is available for execution
#                 on the device
#
# This Dockerfile swaps the torch/torchvision wheels for the cu128
# channel, which carries sm_75..sm_120 binaries. Build once:
#
#   docker build -t witness-hunyuan:latest \
#       -f tools/hunyuan_patch/Dockerfile tools/hunyuan_patch
#
# The runbook's `docker run` commands then reference
# witness-hunyuan:latest instead of the upstream tag.
#
# The model_worker.py patches live alongside this Dockerfile and are
# still bind-mounted at runtime (see HUNYUAN_RUNBOOK.md §2).

FROM kechiro/hunyuan3d-2.1-cachedstart:latest

RUN pip install --no-cache-dir --upgrade \
    --index-url https://download.pytorch.org/whl/cu128 \
    torch torchvision \
 && python3 -c "import torch; assert 'sm_120' in torch.cuda.get_arch_list(), torch.cuda.get_arch_list()"
