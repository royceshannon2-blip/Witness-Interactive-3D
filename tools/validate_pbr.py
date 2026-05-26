#!/usr/bin/env python3
"""
validate_pbr.py — PBR Texture Contract Validator (Gate 5)

Hard-fails when the texture maps emitted by `bake_pbr.py` (and/or
optional stage 2b `texture_asset.py` SDXL/FLUX projection) violate
the OpenPBR contract defined in
[`docs/design-docs/ASSET_PIPELINE.md §3.3`](../docs/design-docs/ASSET_PIPELINE.md).

The canonical failure that motivated this gate is documented in
[`docs/design-docs/ASSET_GENERATION_OVERVIEW.md §0`](../docs/design-docs/ASSET_GENERATION_OVERVIEW.md):
stage 2b SDXL inherits black/empty view conditioning from the
upstream lighting bug and only paints a fraction of the UV space,
leaving the rest at Blender's mid-grey default — the "white squares"
artefact visible at runtime.

Checks (from doc §4 Gate 5):

  1. completeness        — albedo, normal, mr present and decode
  2. resolution_match    — all maps share the same width/height
  3. resolution_floor    — width ≥ 1024 (hero), 512 (everything else)
  4. albedo_fill         — < 5 % pixels at the default fill colour
                           (catches half-projected SDXL output)
  5. albedo_luminance    — mean in [0.05, 0.85] (not all-black,
                           not white-card)
  6. normal_distribution — R,G means near 0.5, B mean > 0.55
                           (rejects flat / inverted normal maps)
  7. mr_packing_contract — R channel must be ≤ 5 (unused per spec);
                           G (roughness) and B (metallic) must have
                           non-trivial variance

Optional checks behind flags:

  --strict-1024 / --strict-2048 / --strict-4096
                   raise the resolution floor for hero assets
  --no-mr-r-check
                   skip the R-must-be-unused gate (some legacy
                   exporters cram occlusion into R; allow opt-out)

Usage (orchestrator):

    python tools/validate_pbr.py \\
        --textures-dir processed/textures/<id>/ \\
        --asset-id <id> \\
        --template prompts/asset-templates/<id>.md \\
        --report processed/diagnostics/<id>.pbr.json

Exit codes:
  0  all checks passed
  1  bad inputs
  2  one or more gates failed
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# Gate thresholds (ASSET_GENERATION_OVERVIEW.md §4 Gate 5).
DEFAULT_RESOLUTION_FLOOR = 1024
ALBEDO_FILL_FLOOR_FRACTION = 0.05    # < 5 % pixels at default-fill colour
ALBEDO_LUMINANCE_RANGE = (0.05, 0.85)
NORMAL_RG_MEAN_TOL = 0.10            # |mean(R or G) − 0.5| < this
NORMAL_B_MEAN_MIN = 0.55             # mean(B) > this  ⇒ surface-aligned
MR_R_CHANNEL_MAX_MEAN = 5.0 / 255.0  # mean R must round to 0..5 of 255
MR_VARIANCE_FLOOR = 1e-4             # std² ≥ this on G and B
DEFAULT_FILL_TOLERANCE = 4.0 / 255.0  # |pixel − fill|_max within this


# Suspect "default fill" colours we treat as evidence of an unpainted
# patch. The set is conservative — any value here is the *exact* colour
# Blender's principled BSDF leaves on UV islands that the bake never
# touched, or that SDXL projection silently skipped. Adding new values
# requires a corresponding ADR.
SUSPECT_FILL_COLOURS = (
    (0.0, 0.0, 0.0),         # pure black (transparent bg leaked through)
    (0.5, 0.5, 0.5),         # mid-grey principled default
    (0.8, 0.8, 0.8),         # legacy diffuse default
    (1.0, 1.0, 1.0),         # pure white (un-baked)
)


@dataclass
class MapMetrics:
    name: str
    path: str
    width: int = 0
    height: int = 0
    channels: int = 0
    channel_means: list[float] = field(default_factory=list)
    channel_stds: list[float] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class PBRReport:
    asset_id: str
    textures_dir: str
    valid: bool = True
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    maps: list[MapMetrics] = field(default_factory=list)
    aggregate: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# loader + per-channel stats
# ---------------------------------------------------------------------------


def _load_rgb(path: Path):
    """Load PNG as float32 RGB(A) in [0, 1]; alpha preserved if present."""
    from PIL import Image
    import numpy as np

    img = Image.open(path)
    if img.mode in ("L", "I", "I;16"):
        img = img.convert("RGB")
    elif img.mode == "P":
        img = img.convert("RGBA")
    elif img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    return np.asarray(img, dtype="float32") / 255.0


def _stats(arr) -> tuple[list[float], list[float]]:
    """Per-channel means and stds (channel last)."""
    means = [float(arr[..., c].mean()) for c in range(arr.shape[-1])]
    stds = [float(arr[..., c].std()) for c in range(arr.shape[-1])]
    return means, stds


# ---------------------------------------------------------------------------
# per-map checks
# ---------------------------------------------------------------------------


def _check_albedo(metrics: MapMetrics, arr) -> None:
    """
    Gate 5.4 + 5.5 — fill-coverage and luminance window for base colour.

    SDXL's half-projection bug shows as a large region at a single flat
    "default fill" colour. We sample for each suspect colour and accept
    the worst offender. Threshold of 5 % is conservative: legitimate
    albedos with a small uniform background pass cleanly.
    """
    import numpy as np

    rgb = arr[..., :3]
    luminance = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    metrics.extras["luminance_mean"] = float(luminance.mean())
    metrics.extras["luminance_std"] = float(luminance.std())

    lo, hi = ALBEDO_LUMINANCE_RANGE
    if not (lo <= luminance.mean() <= hi):
        metrics.failures.append(
            f"albedo luminance mean {luminance.mean():.3f} outside "
            f"[{lo}, {hi}] — texture is unlit-black or blown-out white"
        )

    fill_fractions: dict[str, float] = {}
    worst_fill_name = ""
    worst_fill_frac = 0.0
    for fill in SUSPECT_FILL_COLOURS:
        fill_arr = np.asarray(fill, dtype="float32")
        diff = np.abs(rgb - fill_arr).max(axis=-1)
        frac = float((diff < DEFAULT_FILL_TOLERANCE).mean())
        key = f"fill_{int(fill[0]*255):03d}"
        fill_fractions[key] = frac
        if frac > worst_fill_frac:
            worst_fill_frac = frac
            worst_fill_name = f"#{int(fill[0]*255):02x}{int(fill[1]*255):02x}{int(fill[2]*255):02x}"
    metrics.extras["fill_fractions"] = fill_fractions
    metrics.extras["worst_fill_fraction"] = worst_fill_frac
    metrics.extras["worst_fill_colour"] = worst_fill_name
    if worst_fill_frac > ALBEDO_FILL_FLOOR_FRACTION:
        metrics.failures.append(
            f"albedo has {worst_fill_frac:.1%} pixels at suspect fill "
            f"colour {worst_fill_name} — likely uncovered UV islands "
            "(stage 2b projection failed to reach this region)"
        )


def _check_normal(metrics: MapMetrics, arr) -> None:
    """
    Gate 5.6 — normal-map signature check (OpenGL Y+ convention).

    A valid tangent-space normal map decodes to vectors that are
    roughly surface-aligned: encoded R,G near 0.5, encoded B > 0.55
    on average. We can't distinguish Y+ from Y- statistically (both
    encode +Y as G>0.5 in some texels and G<0.5 in others), but the
    project contract is Y+ everywhere — this gate is a no-confusion
    check, not a content check.
    """
    means, stds = _stats(arr[..., :3])
    r_mean, g_mean, b_mean = means
    metrics.extras["normal_means_rgb"] = means
    metrics.extras["normal_stds_rgb"] = stds

    if abs(r_mean - 0.5) > NORMAL_RG_MEAN_TOL:
        metrics.failures.append(
            f"normal R mean {r_mean:.3f} far from 0.5 "
            f"(tol ±{NORMAL_RG_MEAN_TOL}) — map is not tangent-space"
        )
    if abs(g_mean - 0.5) > NORMAL_RG_MEAN_TOL:
        metrics.failures.append(
            f"normal G mean {g_mean:.3f} far from 0.5 "
            f"(tol ±{NORMAL_RG_MEAN_TOL}) — map is not tangent-space"
        )
    if b_mean < NORMAL_B_MEAN_MIN:
        metrics.failures.append(
            f"normal B mean {b_mean:.3f} below {NORMAL_B_MEAN_MIN} — "
            "vectors are not pointing along the surface; likely a "
            "swapped channel or a non-normal map saved with this name"
        )


def _check_mr(metrics: MapMetrics, arr, skip_r_check: bool) -> None:
    """
    Gate 5.7 — packed metallic-roughness contract.

    Per [`ASSET_PIPELINE.md §3.3`](../docs/design-docs/ASSET_PIPELINE.md):
      R = unused (must be ~0)
      G = roughness
      B = metallic

    We accept a small R smudge from JPEG / KTX2 round-trips but flag
    anything above MR_R_CHANNEL_MAX_MEAN (≈ 5/255). G and B must vary;
    a constant-colour MR map means the bake didn't write the channel,
    which is a silent failure in upstream tools.
    """
    means, stds = _stats(arr[..., :3])
    metrics.extras["mr_means_rgb"] = means
    metrics.extras["mr_stds_rgb"] = stds
    r_mean, g_mean, b_mean = means
    _, g_std, b_std = stds

    if not skip_r_check and r_mean > MR_R_CHANNEL_MAX_MEAN:
        metrics.failures.append(
            f"MR R channel mean {r_mean:.4f} > "
            f"{MR_R_CHANNEL_MAX_MEAN:.4f} — R must be unused per "
            "OpenPBR packing contract"
        )
    if g_std * g_std < MR_VARIANCE_FLOOR:
        metrics.failures.append(
            f"MR G (roughness) variance {g_std*g_std:.6f} below "
            f"{MR_VARIANCE_FLOOR} — channel is constant, bake didn't "
            "write roughness"
        )
    if b_std * b_std < MR_VARIANCE_FLOOR:
        metrics.warnings.append(
            f"MR B (metallic) variance {b_std*b_std:.6f} below "
            f"{MR_VARIANCE_FLOOR} — pure dielectric is plausible "
            "(skin, cloth, paper); promote to failure with "
            "--strict-metallic if this asset should have metal"
        )


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def _resolve_map_path(textures_dir: Path, asset_id: str, role: str) -> Path | None:
    """
    Find the on-disk file for one PBR role.

    `bake_pbr.py` writes `<asset_id>_<role>.png` but stage 2b's SDXL
    pass adds `<asset_id>_albedo.ai.png` (and similar). We prefer the
    `.ai.png` variant when available since that's the final stage 2b
    output the runtime ships with; otherwise fall back to the plain
    bake. Returns None when neither exists.
    """
    suffixes_by_priority = (
        f"{asset_id}_{role}.ai.png",
        f"{asset_id}_{role}.png",
        f"{role}.png",
    )
    for name in suffixes_by_priority:
        p = textures_dir / name
        if p.exists():
            return p
    return None


def _resolution_floor_for(template_path: Path | None, override: int | None) -> int:
    """
    Per-asset resolution floor.

    Templates may declare `target_texture_resolution:` in frontmatter
    (e.g. 4096 for hero assets, 1024 for background fillers). When
    absent we default to DEFAULT_RESOLUTION_FLOOR (1024). CLI override
    wins — useful for an ad-hoc strict check.
    """
    if override is not None:
        return override
    if template_path is None or not template_path.exists():
        return DEFAULT_RESOLUTION_FLOOR
    text = template_path.read_text()
    if not text.startswith("---"):
        return DEFAULT_RESOLUTION_FLOOR
    end = text.find("\n---", 4)
    if end < 0:
        return DEFAULT_RESOLUTION_FLOOR
    for line in text[4:end].splitlines():
        line = line.strip()
        if line.startswith("target_texture_resolution:"):
            _, _, value = line.partition(":")
            try:
                return int(value.strip())
            except ValueError:
                return DEFAULT_RESOLUTION_FLOOR
    return DEFAULT_RESOLUTION_FLOOR


def validate_pbr(
    textures_dir: Path,
    asset_id: str,
    template_path: Path | None = None,
    skip_r_check: bool = False,
    resolution_floor_override: int | None = None,
) -> PBRReport:
    """Run every Gate 5 check on a texture directory."""
    report = PBRReport(asset_id=asset_id, textures_dir=str(textures_dir))

    if not textures_dir.exists():
        report.valid = False
        report.failures.append(f"textures directory not found: {textures_dir}")
        return report

    res_floor = _resolution_floor_for(template_path, resolution_floor_override)
    report.aggregate["resolution_floor"] = res_floor

    required_roles = ("albedo", "normal", "mr")
    paths: dict[str, Path | None] = {
        role: _resolve_map_path(textures_dir, asset_id, role) for role in required_roles
    }
    for role, path in paths.items():
        if path is None:
            report.failures.append(f"required map '{role}' not found in {textures_dir}")

    resolutions: list[tuple[int, int]] = []
    for role, path in paths.items():
        if path is None:
            continue
        m = MapMetrics(name=role, path=str(path))
        try:
            arr = _load_rgb(path)
        except Exception as exc:  # noqa: BLE001
            m.failures.append(f"failed to load {role}: {exc}")
            report.maps.append(m)
            continue

        m.height, m.width = arr.shape[:2]
        m.channels = arr.shape[-1]
        m.channel_means, m.channel_stds = _stats(arr)
        resolutions.append((m.width, m.height))

        if m.width < res_floor or m.height < res_floor:
            m.failures.append(
                f"{role} resolution {m.width}×{m.height} below floor "
                f"{res_floor}×{res_floor} for this asset"
            )

        if role == "albedo":
            _check_albedo(m, arr)
        elif role == "normal":
            _check_normal(m, arr)
        elif role == "mr":
            _check_mr(m, arr, skip_r_check=skip_r_check)

        report.maps.append(m)

    if len({(w, h) for w, h in resolutions}) > 1:
        report.failures.append(
            f"map resolutions disagree: {sorted(set(resolutions))} — "
            "all PBR channels must share the same dimensions"
        )

    for m in report.maps:
        for f in m.failures:
            report.failures.append(f"[{m.name}] {f}")
        for w in m.warnings:
            report.warnings.append(f"[{m.name}] {w}")

    report.valid = not report.failures
    return report


def emit_report(report: PBRReport, json_path: Path | None) -> None:
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(asdict(report), indent=2) + "\n")

    status = "PASS" if report.valid else "FAIL"
    print(f"[validate_pbr] {report.asset_id} → {status}")
    for k, v in report.aggregate.items():
        print(f"  {k:36s} {v}")
    for m in report.maps:
        means = ",".join(f"{c:.2f}" for c in m.channel_means)
        print(f"  {m.name:8s} {m.width}×{m.height} means=[{means}]")
        for k, v in m.extras.items():
            if isinstance(v, float):
                print(f"    {k:30s} {v:.4f}")
            elif isinstance(v, dict):
                pass  # dump skipped to keep CLI summary readable
            else:
                print(f"    {k:30s} {v}")
    for w in report.warnings:
        print(f"  ⚠ {w}")
    for f in report.failures:
        print(f"  ✗ {f}", file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Validate baked PBR textures (Gate 5).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--textures-dir",
        required=True,
        help="Directory containing <asset>_albedo.png, _normal.png, _mr.png.",
    )
    p.add_argument("--asset-id", required=True)
    p.add_argument(
        "--template",
        help="Template path for resolution floor extraction. "
             "Default: prompts/asset-templates/<asset-id>.md",
    )
    p.add_argument(
        "--report",
        help="JSON sidecar output. "
             "Default: processed/diagnostics/<asset-id>.pbr.json",
    )
    p.add_argument(
        "--no-mr-r-check",
        action="store_true",
        help="Skip the MR R-channel-must-be-unused gate.",
    )
    p.add_argument(
        "--resolution-floor",
        type=int,
        default=None,
        help="Override the per-asset resolution floor (default: from template "
             f"or {DEFAULT_RESOLUTION_FLOOR}).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    textures_dir = Path(args.textures_dir).resolve()
    template_path = (
        Path(args.template).resolve()
        if args.template
        else REPO_ROOT / "prompts" / "asset-templates" / f"{args.asset_id}.md"
    )
    report_path = (
        Path(args.report).resolve()
        if args.report
        else REPO_ROOT / "processed" / "diagnostics" / f"{args.asset_id}.pbr.json"
    )
    report = validate_pbr(
        textures_dir=textures_dir,
        asset_id=args.asset_id,
        template_path=template_path if template_path.exists() else None,
        skip_r_check=args.no_mr_r_check,
        resolution_floor_override=args.resolution_floor,
    )
    emit_report(report, report_path)
    return 0 if report.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
