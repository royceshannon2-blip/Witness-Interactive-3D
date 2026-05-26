"""
material_families.py — PBR presets for the eight material families.

Each family is one row from `prompts/asset-templates/_STYLE_GUIDE.md`'s
"What 'tactile' looks like per material family" table. The values here are
intentionally conservative: Cycles-bakeable Principled BSDF parameters that
produce a plausible Digital Diorama look on geometry that has no authored
textures yet. Stage 2 (`tools/blender/bake_pbr.py`) bakes these presets
through procedural noise/voronoi nodes into 8K PBR maps.

The bake script imports this module via `--python tools/blender/bake_pbr.py`
running under Blender's embedded Python; `material_families.py` is a plain
data module with no Blender imports so it can also be used by
`tools/texture_asset.py` outside Blender.

Schema per family:
    base_color:        (R, G, B, A) linear-sRGB, alpha always 1.0.
    roughness:         (mean, variance) — variance drives procedural noise.
    metallic:          0..1 — only `tin` is nonzero by default.
    specular:          0..1 — Principled BSDF specular intensity.
    normal_strength:   strength of the procedural bump→normal output, 0..2.
    ao_strength:       baked AO multiplier, 0..2.
    displacement_mid:  procedural displacement amplitude in metres, ≥ 0.
    notes:             short string for log lines and validation renders.
"""

from __future__ import annotations

from typing import TypedDict


class FamilyPreset(TypedDict):
    base_color: tuple[float, float, float, float]
    roughness: tuple[float, float]
    metallic: float
    specular: float
    normal_strength: float
    ao_strength: float
    displacement_mid: float
    notes: str


FAMILIES: dict[str, FamilyPreset] = {
    "mud_brick": {
        "base_color": (0.42, 0.31, 0.22, 1.0),
        "roughness": (0.92, 0.05),
        "metallic": 0.0,
        "specular": 0.20,
        "normal_strength": 0.8,
        "ao_strength": 1.2,
        "displacement_mid": 0.004,
        "notes": "Hand-applied troweling, mineral efflorescence, edge chips.",
    },
    "tin": {
        "base_color": (0.55, 0.48, 0.40, 1.0),
        "roughness": (0.65, 0.12),
        "metallic": 0.85,
        "specular": 0.50,
        "normal_strength": 0.4,
        "ao_strength": 0.6,
        "displacement_mid": 0.002,
        "notes": "Rust streaks in troughs, mineral water-staining, matte not shiny.",
    },
    "wood": {
        "base_color": (0.38, 0.28, 0.20, 1.0),
        "roughness": (0.78, 0.08),
        "metallic": 0.0,
        "specular": 0.30,
        "normal_strength": 1.0,
        "ao_strength": 1.0,
        "displacement_mid": 0.003,
        "notes": "Axe marks, knot eyes, end-grain crack, grey-silvered weathering.",
    },
    "stone": {
        "base_color": (0.48, 0.45, 0.40, 1.0),
        "roughness": (0.88, 0.10),
        "metallic": 0.0,
        "specular": 0.30,
        "normal_strength": 1.2,
        "ao_strength": 1.5,
        "displacement_mid": 0.006,
        "notes": "Lichen patches, mortar wash, drip-stain runs, irregular field stones.",
    },
    "cloth": {
        "base_color": (0.62, 0.55, 0.45, 1.0),
        "roughness": (0.85, 0.05),
        "metallic": 0.0,
        "specular": 0.25,
        "normal_strength": 0.6,
        "ao_strength": 0.8,
        "displacement_mid": 0.001,
        "notes": "Frayed edges, micro-weave bump, dust-staining at cuffs.",
    },
    "leather": {
        "base_color": (0.30, 0.20, 0.13, 1.0),
        "roughness": (0.55, 0.10),
        "metallic": 0.0,
        "specular": 0.50,
        "normal_strength": 0.7,
        "ao_strength": 0.9,
        "displacement_mid": 0.001,
        "notes": "Pocket-rub patina, edge-cracking at corners, soft sheen on high-touch.",
    },
    "wax": {
        "base_color": (0.92, 0.88, 0.78, 1.0),
        "roughness": (0.35, 0.05),
        "metallic": 0.0,
        "specular": 0.50,
        "normal_strength": 0.3,
        "ao_strength": 0.5,
        "displacement_mid": 0.001,
        "notes": "Drip trails fused to base, soot-darkened wick crater.",
    },
    "skin": {
        "base_color": (0.65, 0.45, 0.36, 1.0),
        "roughness": (0.60, 0.06),
        "metallic": 0.0,
        "specular": 0.45,
        "normal_strength": 0.5,
        "ao_strength": 0.7,
        "displacement_mid": 0.0005,
        "notes": "Subtle subsurface scatter, broadened knuckles, fine micro-folds.",
    },
    # Used as the default when nothing else matches; also for vegetation bark
    # + leaf assets where Hunyuan output is the dominant material signal.
    "vegetation": {
        "base_color": (0.45, 0.42, 0.32, 1.0),
        "roughness": (0.85, 0.10),
        "metallic": 0.0,
        "specular": 0.20,
        "normal_strength": 0.7,
        "ao_strength": 1.0,
        "displacement_mid": 0.002,
        "notes": "Shedding bark, drooping foliage, alpha-cutout leaf cards.",
    },
}


# Pattern → family. Order matters — first match wins. These patterns are
# derived from `docs/design-docs/PHASE1_ASSET_LIST.md` and the prompt
# templates already in `prompts/asset-templates/`.
ID_PATTERNS: list[tuple[str, str]] = [
    ("tin", "tin"),
    ("rugo", "mud_brick"),
    ("compound_gate", "wood"),
    ("door", "wood"),
    ("well_cover_plank", "wood"),
    ("plank", "wood"),
    ("stone", "stone"),
    ("shrine_slab", "stone"),
    ("ledger", "leather"),
    ("photo_frame", "wood"),
    ("candle", "wax"),
    ("hands", "skin"),
    ("eucalyptus", "vegetation"),
    ("vegetation_", "vegetation"),
    ("grass", "vegetation"),
    ("cloth", "cloth"),
    ("fabric", "cloth"),
    ("structure_", "mud_brick"),  # broad fallback for compound structures
    ("prop_", "wood"),              # broad fallback for hand-made props
]


def pick_family(asset_id: str) -> str:
    """
    Pick the best-matching family for an asset id.

    Falls back to ``vegetation`` if nothing matches (it has neutral
    parameters that don't blow out anything).
    """
    for pattern, family in ID_PATTERNS:
        if pattern in asset_id:
            return family
    return "vegetation"


def get(family: str) -> FamilyPreset:
    """Return the preset dict for a family, raising KeyError if unknown."""
    return FAMILIES[family]
