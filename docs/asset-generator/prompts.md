# Prompts & LLM Orchestration — Asset Templates

> Prompt system design, template authoring, dynamic variables, ComfyUI workflow management.
> See [@claude.md](claude.md), [@asset-kinds.md](asset-kinds.md), [@generation-stages.md](generation-stages.md).

---

## Prompt System Overview

```
prompts/
├── asset-templates/
│   ├── <id>.md                  ← Prompt template (YAML + description)
│   ├── <id>/
│   │   ├── ref.png / ref.jpg    ← Reference image
│   │   ├── ref.original.png     ← Archive copy
│   │   └── README.md            ← Per-asset notes
│   ├── _STYLE_GUIDE.md          ← Digital Diorama design system
│   └── figure_investigator_hands/  ← Example: hero asset
│       ├── figure_investigator_hands.md
│       ├── ref.png
│       ├── ref.original.png
│       └── README.md
├── _flux_workflows/
│   ├── default.json             ← Stage 0 FLUX.1 (standard assets)
│   ├── hero.json                ← Stage 0 FLUX.1 (hero assets, higher guidance)
│   └── refine.json              ← Stage 0.25 FLUX.2 [klein] img2img
└── _pbr_workflows/
    ├── sdxl_depth_pbr.json      ← Stage 2b SDXL + ControlNet (depth)
    └── flux2_klein_pbr.json     ← Alternative FLUX.2 projection
```

---

## Asset Template Format

Every prompt template at `prompts/asset-templates/<id>.md` consists of:
1. **YAML frontmatter** — metadata for orchestrator
2. **Prose description** — asset brief, visual language

### YAML Frontmatter

**Required fields:**

```yaml
---
asset_name: prop_ledger_book           # matches file stem
category: prop                          # {vegetation, structure, prop, figure, animated}
era_scope: shared                       # {present, past, shared}
reference_image: prop_ledger_book/ref.png  # path to ref image (relative to prompts/asset-templates/)
seed: 481112                            # Hunyuan3D seed for reproducibility
inference_steps: 60                     # Hunyuan3D steps (default 50)
target_poly_lod0: 8000                  # target face count for LOD0 (used by Gate 2)
materials_runtime:                      # (optional) PBR material slots
  - mat_leather_ledger
  - mat_paper_aged
collision: convex_hull                  # collision strategy: convex_hull | mesh | none
kind: mesh                              # (optional, default mesh) asset kind
notes: |                                # (optional) brief usage notes
  HERO PROP — first interactable object at spawn. Player picks up + examines
  in ledger UI. Must read cleanly at close camera distance.
---
```

**Field definitions:**

| Field | Purpose | Example |
|-------|---------|---------|
| `asset_name` | Matches file stem (must match <id>) | `prop_ledger_book` |
| `category` | Prefix pattern for refine strength lookup | `vegetation`, `structure`, `prop`, `figure` |
| `era_scope` | Temporal context for runtime era switching | `present`, `past`, `shared` |
| `reference_image` | Path to ref.png (relative to `prompts/asset-templates/`) | `prop_ledger_book/ref.png` |
| `seed` | Hunyuan3D seed for deterministic generation | any 32-bit int |
| `inference_steps` | Hunyuan3D steps (higher = slower, better quality) | 20–80 (default 50) |
| `target_poly_lod0` | Target face count for LOD0 (decimation target) | 8000 (hero), 20000 (medium), 40000 (large) |
| `materials_runtime` | Named PBR material slots (from MaterialLibrary) | list of strings |
| `collision` | Collision strategy for physics | `convex_hull`, `mesh`, `none` |
| `kind` | Asset kind (default `mesh`) | `mesh`, `splat`, `tileset`, `navmesh`, `nme`, `animated` |
| `notes` | Author notes (visible to onboarding) | free text |

### Prose Description

After frontmatter, **free-form markdown** describing the asset visually. This prose is used by the refine_ref_image.py stage as context for FLUX.2 img2img, and by stage 0 (FLUX.1) auto-generation.

**Structure (recommended):**

```markdown
# <asset name> — <subtitle>

<1–2 sentence elevator pitch>

<Detailed visual description: shape, materials, weathering, pose, intended use>

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). <asset-specific notes on look>

## Reference image

`prompts/asset-templates/<id>/ref.png` should depict:

<Detailed brief for reference image: subject, background, lighting, pose, style>
```

**Example: prop_ledger_book.md**

```markdown
# The shepherd's ledger — a leather-bound hand-written notebook

A worn leather-bound notebook, the size and weight of an A5 (~21 cm × 15 cm
× ~3 cm thick when closed). The cover is dark brown leather, hand-stitched
along the spine with coarse natural thread, no embossing, no title, no
ornamentation — a plain working book that has clearly been carried in a
pocket for years.

Closed pose: the book lies flat on its back cover, slightly skewed (~5°
rotation around its vertical axis), so the front cover faces upward but
is angled toward where the camera will rest at spawn. The leather shows
the patina of long handling: a soft sheen near the corners where fingers
have worn the surface, slight darkening along the spine where the binding
flexes when opened, no cracks or tears.

[... more detailed visual description ...]

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). This is the hero
prop the player picks up at first frame — the worn corners, soft pocket-rub
patina on the leather, and the slight fan of the page block must read at
close camera distance. Filmic warm-mid-tone palette.

## Reference image

`prompts/asset-templates/prop_ledger_book/ref.png` should depict:

A worn leather-bound A5-sized notebook (~21 cm × ~15 cm × ~3 cm thick), CLOSED,
lying flat on a neutral matte surface. Photographed from straight-on top OR
from a ¾ angle (a ¾ angle reads better — both the front cover and the page
edge are then visible). Cover: dark brown leather, hand-stitched along the
spine with coarse natural thread, **no embossing, no title, no writing
visible anywhere**. [... detailed photographic brief ...]
```

---

## Template Authoring Workflow

### 1. Create Template File

```bash
mkdir -p prompts/asset-templates/<id>/
touch prompts/asset-templates/<id>.md
touch prompts/asset-templates/<id>/README.md
```

### 2. Write YAML Frontmatter

Start with required fields. Guess reasonable defaults:
- `seed`: any number (e.g., 481116 is the Phase 1 default)
- `inference_steps`: 50 (upstream Hunyuan default)
- `target_poly_lod0`: 8000 (hero), 20000 (medium), 40000 (large env)

### 3. Write Prose Description

- **Elevator pitch:** 1–2 sentences, *what is it?*
- **Visual description:** detail that would appear in a film storyboard
- **Materials & weathering:** surface finish, patina, wear
- **Pose:** orientation for spawn or interaction
- **Style section:** link to `_STYLE_GUIDE.md`, note asset-specific aesthetic
- **Reference image section:** brief for photographer (or stock photo searcher)

### 4. Source Reference Image

**Option A: Hand-dropped photograph**
- Locate real-world object or stock photo matching brief
- Photograph or download at ≥ 1024² resolution
- Desaturate to ~50% of original (filmic palette)
- Save as `prompts/asset-templates/<id>/ref.png`

**Option B: Auto-generate with `--auto-ref`**
- Create template WITHOUT `reference_image` file
- Run: `python tools/witness.py generate <id> --auto-ref`
- Stage 0 uses FLUX.1 + prose description to generate ref.png
- Inspect output; if unsatisfactory, either:
  - Hand-edit the prose description (more specific language)
  - Drop a better real-world reference and re-run stage 0.25
  - Delete ref.png + ref.original.png, start over

### 5. Test Stage 0.25

Stage 0.25 (FLUX.2 [klein] img2img) refines the reference to match Digital Diorama style:

```bash
python tools/witness.py generate <id> --no-refine-ref  # Skip refinement
python tools/witness.py generate <id>                  # Default: run refinement
```

Inspect the refined ref.png:
- Colours desaturated? ✓
- Palette warm/filmic? ✓
- Geometry preserved? ✓
- Weathering emphasised? ✓

If unsatisfactory, adjust `--refine-ref-strength`:
- Lower strength (0.0–0.4): preserve geometry, mild palette nudge
- Higher strength (0.6–1.0): aggressive restyle, geometry changes

---

## ComfyUI Workflow Management

### Workflow Files

Stored as JSON in `prompts/` subdirectories:

```
prompts/
├── _flux_workflows/
│   ├── default.json       ← Stage 0: FLUX.1 (default guidance)
│   ├── hero.json          ← Stage 0: FLUX.1 (higher guidance_scale = 7.5 vs 7.0)
│   └── refine.json        ← Stage 0.25: FLUX.2 [klein] img2img
└── _pbr_workflows/
    ├── sdxl_depth_pbr.json      ← Stage 2b: SDXL + ControlNet
    └── flux2_klein_pbr.json     ← Alternative stage 2b: FLUX.2 projection
```

### Workflow Structure (Example: refine.json)

ComfyUI workflows are directed graphs of nodes:

```json
{
  "1": {
    "inputs": [""],
    "class_type": "CheckpointLoaderSimple",
    "outputs": ["MODEL", "CLIP", "VAE"]
  },
  "2": {
    "inputs": [
      ["1", 0],    # Link to output 0 of node 1
      "positive prompt"
    ],
    "class_type": "CLIPTextEncode",
    "outputs": ["CONDITIONING"]
  },
  "3": {
    "inputs": ["image.png"],
    "class_type": "LoadImage",
    "outputs": ["IMAGE", "MASK"]
  },
  "4": {
    "inputs": [
      ["1", 0],    # Model
      ["2", 0],    # Positive conditioning
      ["2", 0],    # Negative conditioning
      ["3", 0],    # Input image
      0.75         # Denoise strength
    ],
    "class_type": "KSamplerAdvanced",
    "outputs": ["LATENT"]
  }
}
```

### Modifying Workflows

To tweak a workflow (e.g., change guidance scale):

```bash
# 1. Load JSON
python -c "import json; w = json.load(open('prompts/_flux_workflows/default.json')); print(json.dumps(w, indent=2))"

# 2. Edit in-place (find node class, change input field)
# 3. Validate JSON syntax
# 4. Test with a known asset:
python tools/witness.py generate prop_ledger_book --auto-ref --workflow default
```

### Key Workflow Nodes (FLUX.1 stage 0)

- `CheckpointLoaderSimple` — load model (flux1-dev.safetensors)
- `CLIPTextEncode` — encode prompt to conditioning
- `KSamplerAdvanced` — denoising sampler (DPM++ or Euler)
- `VAEDecode` — latent → image
- `SaveImage` — write PNG

### Key Workflow Nodes (FLUX.2 [klein] stage 0.25)

Same as FLUX.1, but:
- Model: `flux-2-klein-base-9b-fp8.safetensors`
- Sampler: `KSamplerAdvanced` with img2img mode (requires image input)
- Denoise: 0.0–1.0 (0 = no change, 1 = full regeneration)

### Key Workflow Nodes (SDXL + ControlNet stage 2b)

- `ControlNetLoader` — load ControlNet (depth variant)
- `SDXL_Sampler` — SDXL with ControlNet conditioning
- Input: beauty render + depth map (ControlNet condition)
- Output: painted albedo map

---

## Stage 0: Reference Auto-Generation Prompt

Used by `generate_ref_image.py` to create ref.png from asset description.

**Input:** asset template description prose
**Output:** ref.png (for subsequent stage 0.25 refinement)

**Example prompt construction:**

```python
def build_stage0_prompt(template_description: str) -> str:
    return f"""{template_description}

    Photograph: overcast daylight, 5000K diffuse light, no harsh shadows.
    Neutral light gray or seamless background. Centered composition with
    10–15% headroom. Professional photography, sharp focus, studio quality."""
```

### Guidance Scale Notes

- **Standard (default.json):** guidance_scale = 7.0
  - Good balance between prompt adherence + quality
- **Hero (hero.json):** guidance_scale = 7.5
  - Stronger prompt adherence for complex subjects (hands, faces)
  - Higher VRAM usage

---

## Stage 0.25: Reference Refinement Prompt (Canonical)

**Single source of truth** for style refinement. Defined in:
- `tools/refine_ref_image.py` — `REFINE_PROMPT_SUFFIX` constant
- `prompts/asset-templates/_STYLE_GUIDE.md` — documentation

**Canonical suffix:**

```
Restyle this photograph to match the Digital Diorama look: filmic
desaturated palette, tactile weathered realism, hyper-realistic PBR
materials with micro-bump and roughness variation, 1994 Rwanda
documentary photography aesthetic. Preserve the subject's geometry,
pose, and composition exactly. Overcast 5000 K diffuse daylight,
neutral mid-grey background, no harsh shadows, no people other than any
already present, no watermarks, no captions.
```

**If you edit this, you MUST update BOTH locations** (refine_ref_image.py + _STYLE_GUIDE.md) to keep them in sync.

---

## Digital Diorama Style Guide

See [@claude.md](claude.md) reference link: `prompts/asset-templates/_STYLE_GUIDE.md`

**Core principles:**
1. **Tactile, weathered, lived-in** — surfaces show age
2. **Hyper-realistic PBR** — micro-bump + roughness > colour
3. **Filmic / desaturated palette** — muted historical tones (1994 documentary)
4. **Macro cinematography** — close-range detail matters (shallow DOF)

**Per-material visual cues:**

| Material | Favour | Avoid |
|----------|--------|-------|
| Mud brick / plaster | Hand troweling, mineral efflorescence, edge chips | Painted surfaces |
| Corrugated tin | Rust streaks, mild dents, water-staining | Clean factory-fresh |
| Hand-hewn wood | Axe marks, knot eyes, grey-silver weathering | Sanded uniform |
| Stone + mortar | Lichen patches, mortar wash, drip stains | Cut/dressed blocks |
| Cotton cloth | Frayed edges, dust-staining at cuffs | Crisp ironed |
| Leather (ledger) | Pocket-rub patina, edge-cracking, soft sheen | Polished |
| Wax (candle) | Drip trails, soot-darkened wick crater | Pristine geometry |
| Skin (hands) | Subsurface scatter, broadened knuckles, micro-folds | Render-clean |

---

## Dynamic Variables (TBD)

**Future enhancement:** template variables for re-use across asset families.

Proposed syntax:

```yaml
---
asset_name: {{family}}_{{variant}}
# Resolved at generation time based on CLI args
---

A {{material}} {{object_type}} in {{era}} {{context}}...
```

Not yet implemented; currently templates are per-asset, hand-authored.

---

## Template Naming Conventions

**File:** `prompts/asset-templates/<id>.md`
**ID pattern:** `<category>_<name>[_<variant>]`

```
vegetation_eucalyptus_mature      ← Mature tree variant
vegetation_eucalyptus_sapling     ← Sapling variant
structure_rugo_main_house         ← Main house structure
structure_rugo_door               ← Detail prop (door only)
prop_ledger_book                  ← Hero prop (no variant)
figure_investigator_hands         ← First-person hands
figure_grandfather_hands          ← Third-person spirit hands
prop_altar_candle                 ← Secondary prop
prop_altar_photo_frame            ← Secondary prop
```

---

## Phase 1 Asset Template Status

See `docs/design-docs/PHASE1_ASSET_LIST.md` for:
- Priority (must-have vs. nice-to-have)
- Template authoring status
- Generation status
- Reference image source

---

## Troubleshooting Prompt Issues

### Generated mesh doesn't match description

**Diagnosis:**
- Inspect ref.png: does it match the prose description?
- Check stage 0.25 refinement: did FLUX.2 over-transform?

**Recovery:**
1. Refine the prose description (more specific language)
2. Hand-drop a better reference image
3. Adjust `--refine-ref-strength` (lower = preserve geometry)
4. Re-run stage 0.25 or 1

### Generated reference too saturated / wrong colours

**Diagnosis:** Stage 0.25 didn't push enough toward Digital Diorama

**Recovery:**
```bash
# Increase denoise strength
python tools/witness.py generate <id> --refine-ref-strength 0.7

# Or re-run with new seed
python tools/witness.py generate <id> --refine-ref-strength 0.7 --seed 999999
```

### Stage 0 reference auto-generation not matching intent

**Diagnosis:** FLUX.1 prompt was too vague or conflicting

**Recovery:**
1. Hand-drop a better reference (stock photo or real-world photo)
2. Let stage 0.25 refine it
3. Or iterate on prose: be *more specific* about materials, weathering, pose

---

**Last updated:** 2026-05-25 | **See also:** [@asset-kinds.md](asset-kinds.md), [@generation-stages.md](generation-stages.md), [@blender-pipeline.md](blender-pipeline.md)
