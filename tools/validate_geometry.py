#!/usr/bin/env python3
"""
validate_geometry.py — Post-Hunyuan Geometric Validator (Gate 2)

Hard-fails when a raw Hunyuan GLB is geometrically unfit for downstream
baking. The canonical failure mode that motivated this gate is the
"white untextured 2 flat squares" output documented in
[`docs/design-docs/ASSET_GENERATION_OVERVIEW.md §0`](../docs/design-docs/ASSET_GENERATION_OVERVIEW.md):
a single-photo Hunyuan run produces a near-2D depth card with Z thickness
under 2% of width/height, then stage 2a wastes hours baking a useless mesh.

Checks (from doc §4 Gate 2):

  1. bbox_depth_ratio  ≥  0.10   (min extent / max extent)
                                  catches flat depth-cards.
  2. manifold          == True   (warning unless --strict-manifold; hero
                                  meshes legitimately have holes/cuts.)
  3. poly_budget       ∈ [0.5×, 2.0×]  of template target_poly_lod0
                                  (warning if template lacks the field.)
  4. centroid_offset   ≤  0.3 × max(extents)
                                  catches off-origin / upside-down output.
  5. vertex_count      ∈ [1000, 2_000_000]
                                  sanity bound on degenerate output.

Usage (orchestrator):

    python tools/validate_geometry.py processed/glb/raw/<id>.glb \\
        --asset-id <id> \\
        --template prompts/asset-templates/<id>.md \\
        --report processed/diagnostics/<id>.geometry.json

Usage (ad hoc):

    python tools/validate_geometry.py processed/glb/raw/figure_grandfather_hands.glb \\
        --asset-id figure_grandfather_hands

Exit codes:
  0  all checks passed (warnings still printed)
  1  bad inputs (file missing, can't parse, etc.)
  2  one or more gate metrics failed — pipeline must halt or retry
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# Gate thresholds (from ASSET_GENERATION_OVERVIEW.md §4). Surfaced as module
# constants so future tuning is visible in one place.
MIN_BBOX_DEPTH_RATIO = 0.10        # min(extents) / max(extents)
POLY_BUDGET_MIN_MULT = 0.5         # actual_faces >= 0.5 × target  (too-few / degenerate check)
# NOTE: The upper bound is RAW_POLY_CAP, not POLY_BUDGET_MAX_MULT × target.
# Hunyuan raw output at octree_resolution 512–768 is always 200K–900K faces;
# the face_count API field controls texture-remesh, not mesh generation.
# optimize_asset.py applies Blender decimation in Stage 3 (after Gate 2),
# bringing the mesh to target_poly_lod0. The target-relative upper-bound
# check therefore belongs post-Stage-3, not here.
RAW_POLY_CAP = 2_000_000          # hard upper bound on raw Hunyuan mesh output
MAX_CENTROID_OFFSET_RATIO = 0.3    # |centroid_axis| / max(extents)
VERT_COUNT_FLOOR = 1_000
VERT_COUNT_CEIL = 2_000_000


@dataclass
class GeometryReport:
    """
    Structured result emitted by the validator.

    Designed to round-trip cleanly to JSON so `diagnostic_report.py` (Gate
    4 of Phase A) can pull a single artefact and render the full failure
    table without re-parsing the GLB.
    """
    asset_id: str
    glb_path: str
    valid: bool = True
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# template parsing — read target_poly_lod0 from the asset template frontmatter
# ---------------------------------------------------------------------------


def parse_template_target_poly(template_path: Path | None) -> int | None:
    """
    Extract `target_poly_lod0` from the template's YAML frontmatter.

    Returns None when the template is absent or the field is missing, so
    callers can decide whether to skip the poly-budget check or treat it
    as a warning. We hand-parse rather than depend on PyYAML to keep the
    validator's footprint minimal (it can run inside ComfyUI's venv or any
    Python without project-specific deps beyond trimesh + numpy).
    """
    if template_path is None or not template_path.exists():
        return None
    text = template_path.read_text()
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    front = text[4:end]
    for line in front.splitlines():
        line = line.strip()
        if line.startswith("target_poly_lod0:"):
            _, _, value = line.partition(":")
            try:
                return int(value.strip())
            except ValueError:
                return None
    return None


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------


def _load_mesh(glb_path: Path):
    """Load with trimesh, concatenating Scene primitives into one mesh."""
    import trimesh

    obj = trimesh.load(str(glb_path), process=False)
    if isinstance(obj, trimesh.Scene):
        if not obj.geometry:
            raise RuntimeError(f"GLB scene contains no geometry: {glb_path}")
        # Concatenate all mesh primitives; transforms come from the scene graph.
        mesh = trimesh.util.concatenate(
            [g.copy().apply_transform(obj.graph.get(name)[0])
             for name, g in obj.geometry.items()]
        )
        return mesh
    return obj


def check_bbox_depth(report: GeometryReport, extents: tuple[float, float, float]) -> None:
    """
    Gate 2.1 — the canonical "white flat squares" detector.

    Hunyuan from a single front-facing photo extrudes a 2D depth card
    with Z thickness ≈ 0.02 against X,Y ≈ 2.0 (i.e. ratio ≈ 0.01).
    Triple-A geometry has min/max extent ratio ≥ 0.10 even for thin
    objects (paper, cloth) at the canonical 2-unit Hunyuan scale.
    """
    mx = max(extents)
    mn = min(extents)
    ratio = mn / mx if mx > 0 else 0.0
    report.metrics["bbox_extents"] = list(extents)
    report.metrics["bbox_depth_ratio"] = ratio
    report.metrics["bbox_depth_threshold"] = MIN_BBOX_DEPTH_RATIO
    if ratio < MIN_BBOX_DEPTH_RATIO:
        report.failures.append(
            f"bbox depth ratio {ratio:.4f} < {MIN_BBOX_DEPTH_RATIO} "
            f"(extents X={extents[0]:.3f} Y={extents[1]:.3f} Z={extents[2]:.3f}) "
            "— Hunyuan produced a depth-card. Likely cause: single-image "
            "input without multi-view (Zero123++) augmentation. "
            "Re-run with --multi-view."
        )


def check_manifold(
    report: GeometryReport,
    mesh,  # trimesh.Trimesh
    strict: bool,
) -> None:
    """
    Gate 2.2 — manifold sanity.

    A non-watertight mesh isn't automatically wrong: hero assets like
    grandfather hands legitimately have cut edges at the wrist. We
    default to warning, escalating to a failure only when --strict-manifold
    is requested (e.g. for closed props like the ledger book).
    """
    is_manifold = bool(mesh.is_watertight)
    report.metrics["manifold"] = is_manifold
    if not is_manifold:
        msg = "mesh is non-watertight (open edges present)"
        if strict:
            report.failures.append(msg + " — --strict-manifold gate")
        else:
            report.warnings.append(msg + " — acceptable for open-form assets")


def check_poly_budget(
    report: GeometryReport,
    face_count: int,
    target: int | None,
) -> None:
    """
    Gate 2.3 — poly count sanity checks on raw Hunyuan output.

    Two independent checks:

    Lower bound (degenerate check):
        actual_faces >= POLY_BUDGET_MIN_MULT × target_poly_lod0
        Catches depth-cards and collapsed meshes with near-zero faces.
        Skipped when the template has no target_poly_lod0.

    Upper bound (runaway check):
        actual_faces <= RAW_POLY_CAP (2,000,000 absolute)
        Catches genuinely broken Hunyuan output (e.g. duplicated geometry,
        exploded marching-cubes artefact). Does NOT use target × multiplier
        because raw Hunyuan meshes at octree_resolution 512–768 are always
        200K–900K faces; optimize_asset.py (Stage 3) decimates to
        target_poly_lod0 *after* this gate runs.
    """
    report.metrics["face_count"] = face_count
    report.metrics["face_target"] = target
    report.metrics["raw_poly_cap"] = RAW_POLY_CAP

    # Lower bound — degenerate / missing geometry
    if target is not None:
        low = int(target * POLY_BUDGET_MIN_MULT)
        report.metrics["face_budget_low"] = low
        if face_count < low:
            report.failures.append(
                f"face count {face_count:,} below {POLY_BUDGET_MIN_MULT}× target "
                f"({low:,}) — mesh likely degenerate or missing geometry"
            )
    else:
        report.warnings.append(
            "template has no target_poly_lod0 — skipping lower poly-budget check"
        )

    # Upper bound — absolute raw cap
    if face_count > RAW_POLY_CAP:
        report.failures.append(
            f"face count {face_count:,} exceeds raw output cap ({RAW_POLY_CAP:,}) "
            f"— Hunyuan output is pathologically dense; check marching-cubes artefacts"
        )


def check_centroid(
    report: GeometryReport,
    centroid: tuple[float, float, float],
    extents: tuple[float, float, float],
) -> None:
    """
    Gate 2.4 — geometry centred on origin.

    Hunyuan sometimes produces output whose centroid is offset along the
    primary axis (often Z, for figures); this manifests as
    upside-down-relative-to-camera meshes downstream. The bound is a
    fraction of max extent so the check stays scale-invariant.
    """
    mx = max(extents)
    if mx <= 0:
        report.failures.append("max extent is zero — degenerate mesh")
        return
    offsets = [abs(c) / mx for c in centroid]
    report.metrics["centroid"] = list(centroid)
    report.metrics["centroid_offset_ratios"] = offsets
    report.metrics["centroid_offset_threshold"] = MAX_CENTROID_OFFSET_RATIO
    worst_axis = ["x", "y", "z"][offsets.index(max(offsets))]
    if max(offsets) > MAX_CENTROID_OFFSET_RATIO:
        report.failures.append(
            f"centroid offset along {worst_axis} "
            f"({max(offsets):.3f}) > {MAX_CENTROID_OFFSET_RATIO} "
            f"of max extent ({mx:.3f}) — mesh is off-origin"
        )


def check_vertex_count(report: GeometryReport, vert_count: int) -> None:
    """Gate 2.5 — sanity bound on degenerate / runaway output."""
    report.metrics["vertex_count"] = vert_count
    if vert_count < VERT_COUNT_FLOOR:
        report.failures.append(
            f"vertex count {vert_count:,} below floor {VERT_COUNT_FLOOR:,} "
            "— Hunyuan output is degenerate"
        )
    elif vert_count > VERT_COUNT_CEIL:
        report.failures.append(
            f"vertex count {vert_count:,} above ceiling {VERT_COUNT_CEIL:,} "
            "— mesh will not survive Draco compression in reasonable time"
        )


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def validate_geometry(
    glb_path: Path,
    asset_id: str,
    template_path: Path | None = None,
    strict_manifold: bool = False,
) -> GeometryReport:
    """
    Run every Gate 2 check on a single GLB and return a structured report.

    Callable from Python (`asset_pipeline.py` will import this) or from
    the command-line `main()`. Never raises on gate failures — instead
    populates `report.failures` so the caller can decide whether to
    retry, escalate to diagnostic, or surface to the user.
    """
    report = GeometryReport(asset_id=asset_id, glb_path=str(glb_path))

    if not glb_path.exists():
        report.valid = False
        report.failures.append(f"GLB not found at {glb_path}")
        return report

    try:
        mesh = _load_mesh(glb_path)
    except Exception as exc:  # noqa: BLE001 — surface any loader failure
        report.valid = False
        report.failures.append(f"trimesh failed to load GLB: {exc}")
        return report

    extents = tuple(float(e) for e in mesh.extents)
    centroid = tuple(float(c) for c in mesh.centroid)
    target_poly = parse_template_target_poly(template_path)

    check_bbox_depth(report, extents)
    check_vertex_count(report, len(mesh.vertices))
    check_poly_budget(report, len(mesh.faces), target_poly)
    check_centroid(report, centroid, extents)
    check_manifold(report, mesh, strict=strict_manifold)

    report.valid = not report.failures
    return report


def emit_report(report: GeometryReport, json_path: Path | None) -> None:
    """Write the JSON sidecar if requested, then print human summary."""
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(asdict(report), indent=2) + "\n")

    status = "PASS" if report.valid else "FAIL"
    print(f"[validate_geometry] {report.asset_id} → {status}")
    for key, val in report.metrics.items():
        if isinstance(val, float):
            print(f"  {key:30s} {val:.4f}")
        else:
            print(f"  {key:30s} {val}")
    for w in report.warnings:
        print(f"  ⚠ {w}")
    for f in report.failures:
        print(f"  ✗ {f}", file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Validate post-Hunyuan GLB geometry (Gate 2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("glb", help="Path to raw GLB from stage 1 (Hunyuan output).")
    p.add_argument(
        "--asset-id",
        required=True,
        help="Snake_case asset id (used to resolve template + report names).",
    )
    p.add_argument(
        "--template",
        help=(
            "Template markdown with `target_poly_lod0:` frontmatter. "
            "Default: prompts/asset-templates/<asset-id>.md"
        ),
    )
    p.add_argument(
        "--report",
        help=(
            "Write a JSON metrics sidecar to this path. "
            "Default: processed/diagnostics/<asset-id>.geometry.json"
        ),
    )
    p.add_argument(
        "--strict-manifold",
        action="store_true",
        help="Escalate non-watertight mesh from warning to hard failure.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    glb_path = Path(args.glb).resolve()
    template_path = (
        Path(args.template).resolve()
        if args.template
        else REPO_ROOT / "prompts" / "asset-templates" / f"{args.asset_id}.md"
    )
    report_path = (
        Path(args.report).resolve()
        if args.report
        else REPO_ROOT / "processed" / "diagnostics" / f"{args.asset_id}.geometry.json"
    )

    report = validate_geometry(
        glb_path=glb_path,
        asset_id=args.asset_id,
        template_path=template_path if template_path.exists() else None,
        strict_manifold=args.strict_manifold,
    )
    emit_report(report, report_path)
    return 0 if report.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
