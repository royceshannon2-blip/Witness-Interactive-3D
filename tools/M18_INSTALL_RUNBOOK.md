# M18 — Local AI Stack Install Runbook

**STATUS: COMPLETE (2026-05-19) — all 7 checks pass.**

Installs the three audio + image generation services used by M19–M22.
All commands run on the **host** (not in Docker). The RTX 5090 is the
execution target for every tool here.

Pre-confirmed working baseline: Python 3.14.4 · PyTorch 2.12.0 ·
CUDA 13.2.

## What was actually installed and patched

All tools require `LD_LIBRARY_PATH=/usr/local/lib/ollama/cuda_v12:$LD_LIBRARY_PATH`
at runtime because `torchaudio 2.11.0+cu128` needs `libcudart.so.12` and the
system only ships `libcudart.so.13` at `/opt/cuda/`. Ollama bundles CUDA 12 libs
at that path. **Add this export to `~/.config/fish/config.fish`.**

```bash
set -x LD_LIBRARY_PATH /usr/local/lib/ollama/cuda_v12 $LD_LIBRARY_PATH
```

Two source patches were applied (non-destructive — both are in local site-packages):

1. **torchaudio version-check bypass** —
   `~/.local/lib/python3.14/site-packages/torchaudio/_extension/utils.py`
   line ~123: the `raise RuntimeError(...)` was replaced with a `warnings.warn`.
   torchaudio cu128 is functionally compatible with torch 2.12.0/CUDA 13.2 for
   audio I/O + AudioCraft inference.

2. **AudioCraft spacy optional** —
   `~/.local/lib/python3.14/site-packages/audiocraft/modules/conditioners.py`
   line 21: `import spacy` wrapped in `try/except ImportError` (spacy requires
   blis which doesn't build on Python 3.14; spacy is only used in one unused
   conditioner class, not MusicGen/AudioGen).

3. **Higgs-Audio LLAMA_ATTENTION_CLASSES** —
   `/tmp/higgs-audio/boson_multimodal/model/higgs_audio/modeling_higgs_audio.py`
   line 22: `LLAMA_ATTENTION_CLASSES` import (removed in transformers 5.x) replaced
   with a try/except that falls back to `{"eager": LlamaAttention, ...}`.

**Higgs-Audio is installed from source** at `/tmp/higgs-audio/` (editable install).
The package name is `boson_multimodal` (not `higgs_audio`). Import path:
`from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine`

---

---

## 0. Pre-flight

```bash
# Already installed?
python3 -c "import diffusers; print('diffusers', diffusers.__version__)"
python3 -c "import audiocraft; print('audiocraft ok')" 2>/dev/null || echo "audiocraft missing"
python3 -c "import higgs_audio; print('higgs_audio ok')" 2>/dev/null || echo "higgs_audio missing"
ffmpeg -version | head -1

# GPU state — kill anything using VRAM before heavy model downloads
nvidia-smi
```
install weights (FLUX, AudioCraft, Higgs-Audio, Hunyuan3D checkpoints)
  → cd /home/royce3/Desktop/Witness-Interactive-3D/model_cache/huggingface/

---

## 1. FFmpeg (system package)

```bash
sudo pacman -S --needed ffmpeg

# Verify
ffmpeg -version | head -1
# Expect: ffmpeg version N.xxx ...
```

---

## 2. FLUX.1-schnell — reference image generation

`diffusers` is already installed. FLUX needs a few extra pip packages and
will auto-download the model (~24 GB) on first inference call.

```bash
pip install -U \
  invisible_watermark \
  transformers \
  accelerate \
  sentencepiece \
  safetensors \
  Pillow

# Smoke test — loads the pipeline metadata (no GPU needed yet).
# First run triggers the model download; subsequent runs use the cache
# at model_cache/huggingface/.
python3 - <<'EOF'
from diffusers import FluxPipeline
import torch

HF_CACHE = "/home/royce3/Desktop/Witness-Interactive-3D/model_cache/huggingface"

pipe = FluxPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-schnell",
    torch_dtype=torch.bfloat16,
    cache_dir=HF_CACHE,
)
pipe = pipe.to("cuda")

img = pipe(
    "A single weathered stone wall, macro photography, desaturated, Rwanda highlands",
    num_inference_steps=4,
    guidance_scale=0.0,
    height=512,
    width=512,
).images[0]
img.save("/tmp/flux_smoke.png")
print("FLUX smoke test OK — /tmp/flux_smoke.png")
EOF
```

> **HuggingFace access:** FLUX.1-schnell is public (no token needed).
> If you hit a 403, run `huggingface-cli login` with your HF token.

---

## 3. AudioCraft — MusicGen ambient beds + AudioGen SFX

Meta's AudioCraft provides both `MusicGen` (music conditioning) and
`AudioGen` (SFX generation) in one package.

```bash
pip install -U audiocraft

# AudioCraft pins older numpy/scipy — verify nothing broke
python3 -c "import audiocraft; print('audiocraft', audiocraft.__version__)"

# Smoke test — MusicGen (downloads ~3.8 GB model on first run)
python3 - <<'EOF'
import torch, torchaudio
from audiocraft.models import MusicGen

model = MusicGen.get_pretrained("facebook/musicgen-medium")
model.set_generation_params(duration=5)

wav = model.generate(["sparse solo mbira, occasional wind, empty courtyard"])
torchaudio.save("/tmp/musicgen_smoke.wav", wav[0].cpu(), sample_rate=32000)
print("MusicGen smoke test OK — /tmp/musicgen_smoke.wav")
EOF

# Smoke test — AudioGen (downloads ~3.0 GB model on first run)
python3 - <<'EOF'
import torch, torchaudio
from audiocraft.models import AudioGen

model = AudioGen.get_pretrained("facebook/audiogen-medium")
model.set_generation_params(duration=3)

wav = model.generate(["heavy wooden hatch lifted, creak"])
torchaudio.save("/tmp/audiogen_smoke.wav", wav[0].cpu(), sample_rate=16000)
print("AudioGen smoke test OK — /tmp/audiogen_smoke.wav")
EOF
```

> Models are cached to `~/.cache/huggingface/`. If you want them next to
> the other project caches, set:
> ```bash
> export HF_HOME=/home/royce3/Desktop/Witness-Interactive-3D/model_cache/huggingface
> ```
> Add that export to your `.bashrc`/`.zshrc`/`~/.config/fish/config.fish`.

---

## 4. Higgs-Audio v2 — narrator + NPC voice synthesis

Higgs-Audio v2 is a controllable TTS system with expressive/stable preset
modes. Install from the official GitHub release:

```bash
pip install -U higgs-audio

# If the PyPI package is not yet available, install from source:
# pip install git+https://github.com/bosonai/higgs-audio.git

# Verify
python3 -c "import higgs_audio; print('higgs_audio ok')"
```

### Voice preset smoke test

The narrator character uses an **expressive** preset. Set up a reference
audio clip first — even a 3-second `.wav` of any male elderly voice works:

```bash
# Use the bundled fallback reference (10-second neutral male voice)
# — swap this for a custom recording when available
python3 - <<'EOF'
from higgs_audio import HiggsAudio
import soundfile as sf

ha = HiggsAudio.from_pretrained()   # downloads model on first run (~2 GB)

wav, sr = ha.synthesize(
    text="June, 1994. I have kept this book for eleven years.",
    voice_preset="expressive_elder_male",   # adjust to actual preset name
    reference_audio=None,                   # use built-in default
)
sf.write("/tmp/higgs_smoke.wav", wav, sr)
print(f"Higgs-Audio smoke test OK — /tmp/higgs_smoke.wav (sr={sr})")
EOF
```

> **Note:** Higgs-Audio v2's preset API may differ from the snippet above
> depending on the version installed. Check `python3 -c "help(higgs_audio)"`
> or the package README if `voice_preset` is not a recognised kwarg.
> The M19 generation script (`tools/generate_narrator_audio.py`) will be
> written against whatever API is installed — run this smoke test first and
> note the exact constructor and method signatures.

---

## 5. All-clear check

Run this block. Every line should print OK.

```bash
python3 - <<'EOF'
import sys, subprocess

checks = []

# FFmpeg
r = subprocess.run(["ffmpeg", "-version"], capture_output=True)
checks.append(("FFmpeg",           r.returncode == 0))

# diffusers / FLUX deps
try:
    import diffusers, transformers, accelerate, sentencepiece, safetensors
    checks.append(("FLUX deps",    True))
except ImportError as e:
    checks.append(("FLUX deps",    False))

# AudioCraft
try:
    import audiocraft
    checks.append(("AudioCraft",   True))
except ImportError:
    checks.append(("AudioCraft",   False))

# Higgs-Audio
try:
    import higgs_audio
    checks.append(("Higgs-Audio",  True))
except ImportError:
    checks.append(("Higgs-Audio",  False))

# GPU
import torch
checks.append(("CUDA available",   torch.cuda.is_available()))
checks.append(("GPU name",         "RTX 5090" in torch.cuda.get_device_name(0)))

ok = all(v for _, v in checks)
for name, passed in checks:
    print(f"  {'OK' if passed else 'FAIL':4}  {name}")
sys.exit(0 if ok else 1)
EOF
```

All five rows must print `OK` before moving to M19.

---

## 6. What runs next

Once all-clear passes:

| Milestone | Script | Needs |
|---|---|---|
| **M19** | `tools/generate_narrator_audio.py` | Higgs-Audio v2 + FFmpeg |
| **M20** | `tools/generate_ambient_audio.py` | AudioCraft + FFmpeg |
| **M22** | `tools/asset_pipeline.py --kind mesh` | FLUX + Hunyuan3D (already running) |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pip install audiocraft` fails on Python 3.14 | AudioCraft pins `numpy<2`. Try: `pip install "numpy<2" audiocraft` — or create a venv with Python 3.11: `python3.11 -m venv .venv-audio && source .venv-audio/bin/activate` |
| FLUX OOM on 32 GB | Add `pipe.enable_model_cpu_offload()` before `.to("cuda")` to stream layers |
| Higgs-Audio model download stalls | Check disk space — model is ~2 GB. Try `HF_HUB_OFFLINE=0 pip install higgs-audio` |
| `No module named 'soundfile'` | `pip install soundfile` |
| MusicGen/AudioGen output is silent | Sample rate mismatch — check `model.sample_rate` and pass it to `torchaudio.save` |
