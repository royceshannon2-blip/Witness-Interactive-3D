#!/usr/bin/env python3
"""
diagnostic_report.py — Unified Gate Report (Gate 4)

Aggregates the JSON sidecars written by `validate_geometry.py`,
`validate_views.py`, and `validate_pbr.py` into a single
human-readable markdown report plus an aggregate JSON. This is the
artefact a human reaches for when "asset X failed at some stage" —
it shows which gate fired, what the metric was, and what to do
about it, without making the operator open three sidecar files.

The report file is the canonical record consulted by:

  * `asset_pipeline.py` retry harness (Phase F) — reads the
    aggregate to decide whether to re-roll seed or escalate.
  * The orchestrator's --diagnose-only mode (Phase A4) — runs all
    gates without re-generating, useful for re-running validation
    after a `bake_pbr.py` fix without paying the Hunyuan cost again.
  * Hand triage — `processed/diagnostics/<id>.report.md` is the
    first file a human opens when the canary asset regresses.

Usage:

    python tools/diagnostic_report.py <asset-id> \\
        [--diagnostics-dir processed/diagnostics] \\
        [--md-out  processed/diagnostics/<id>.report.md] \\
        [--json-out processed/diagnostics/<id>.aggregate.json]

Exit codes:
  0  every gate that ran reported pass
  1  bad inputs (no sidecars found at all)
  2  one or more gates reported fail
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DIAGNOSTICS = REPO_ROOT / "processed" / "diagnostics"

# Canonical gate metadata — keeping it in one table lets the report,
# the retry harness, and the doc cross-reference share a single source
# of truth. Sidecar names must match the ones the validators write.
GATE_TABLE = (
    # Order reflects pipeline ordering, not gate number — the report
    # reads top-to-bottom as a timeline. `synth_views` is Phase B2's
    # pre-Hunyuan check (sidecar key `synth_views`); `views` is the
    # post-bake beauty render check. Both reuse validate_views.py with
    # different `--indexed` settings, but they document distinct stages.
    ("synth_views", "Gate 1 — Pre-Hunyuan Synth Views (Zero123++)", "synth_views"),
    ("geometry",    "Gate 2 — Post-Hunyuan Geometry", "geometry"),
    ("views",       "Gate 3 — Multi-View Beauty Renders", "views"),
    ("pbr",         "Gate 5 — PBR Texture Contract", "pbr"),
)


@dataclass
class GateOutcome:
    """One sidecar's bottom-line state for the markdown table."""
    key: str
    title: str
    found: bool = False
    valid: bool | None = None
    failure_count: int = 0
    warning_count: int = 0
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# sidecar collection
# ---------------------------------------------------------------------------


def load_gate(diagnostics_dir: Path, asset_id: str, key: str) -> GateOutcome:
    """
    Load one `<id>.<key>.json` sidecar into a GateOutcome.

    Robust to a missing or corrupt sidecar — both states render as a
    "no run" row rather than crashing the aggregator. A missing sidecar
    is information: it means the validator never ran (e.g. pipeline
    halted before reaching that stage).
    """
    out = GateOutcome(key=key, title=next(t for k, t, _ in GATE_TABLE if k == key))
    path = diagnostics_dir / f"{asset_id}.{key}.json"
    if not path.exists():
        return out
    out.found = True
    try:
        data = json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        out.failures.append(f"failed to parse sidecar: {exc}")
        out.failure_count = 1
        out.valid = False
        return out
    out.raw = data
    out.valid = bool(data.get("valid"))
    out.failures = list(data.get("failures", []))
    out.warnings = list(data.get("warnings", []))
    out.failure_count = len(out.failures)
    out.warning_count = len(out.warnings)
    return out


# ---------------------------------------------------------------------------
# markdown rendering
# ---------------------------------------------------------------------------


_STATUS_GLYPH = {True: "PASS", False: "FAIL", None: "—"}


def render_markdown(asset_id: str, outcomes: list[GateOutcome]) -> str:
    """
    Render the aggregate as a markdown document.

    Structure:
      # title
      summary one-liner
      | table of gates |
      ## per-gate details (failures + key metrics)
      ## remediation hints (decisions D1-D6 from the doc)
    """
    overall_pass = all(o.valid for o in outcomes if o.found and o.valid is not None)
    any_ran = any(o.found for o in outcomes)
    if not any_ran:
        headline = "**NO GATES RAN** — sidecars missing in diagnostics dir."
    elif overall_pass:
        headline = "**ALL RAN GATES PASSED**"
    else:
        headline = "**ONE OR MORE GATES FAILED** — see per-gate details below."

    lines: list[str] = [
        f"# Diagnostic Report — `{asset_id}`",
        "",
        headline,
        "",
        "| Gate | Status | Failures | Warnings |",
        "| ---- | ------ | -------: | -------: |",
    ]
    for o in outcomes:
        status = _STATUS_GLYPH[o.valid] if o.found else "skipped"
        lines.append(
            f"| {o.title} | {status} | {o.failure_count} | {o.warning_count} |"
        )
    lines.append("")

    for o in outcomes:
        if not o.found:
            continue
        lines.append(f"## {o.title}")
        lines.append("")
        if o.failures:
            lines.append("**Failures**")
            lines.append("")
            for f in o.failures:
                lines.append(f"- {f}")
            lines.append("")
        if o.warnings:
            lines.append("**Warnings**")
            lines.append("")
            for w in o.warnings:
                lines.append(f"- {w}")
            lines.append("")
        metrics = o.raw.get("metrics") or o.raw.get("aggregate") or {}
        if metrics:
            lines.append("**Key metrics**")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(metrics, indent=2))
            lines.append("```")
            lines.append("")

    if not overall_pass and any_ran:
        lines.extend(_remediation_hints(outcomes))
    return "\n".join(lines) + "\n"


def _remediation_hints(outcomes: list[GateOutcome]) -> list[str]:
    """
    Translate gate failures into pipeline actions.

    These hints map 1:1 to the decisions in [`ASSET_GENERATION_OVERVIEW.md §4`](../docs/design-docs/ASSET_GENERATION_OVERVIEW.md).
    The retry harness (Phase F) reads the JSON aggregate's
    `recommended_action` field to decide whether a fresh seed will fix
    the failure or whether the operator must intervene.
    """
    hints: list[str] = [
        "## Remediation",
        "",
        "Mapped from [`ASSET_GENERATION_OVERVIEW.md §4`](../../docs/design-docs/ASSET_GENERATION_OVERVIEW.md):",
        "",
    ]
    for o in outcomes:
        if not o.found or o.valid:
            continue
        # Synth-view failures get their own hint because the post-bake
        # remediation pointers (Phase C lighting refactor, etc.) are
        # wrong for this gate — the views come from Zero123++, not Blender.
        if o.key == "synth_views":
            hints.append(
                "- **D1 / D5 (pre-Hunyuan)** — Zero123++ produced bad "
                "synth views. Re-roll `--multi-view-seed`, raise "
                "`--multi-view-steps` (75 → 100), or fix the ref.png "
                "(stage 0.25 might be over-denoising — try "
                "`--refine-ref-strength 0.40`). Do NOT proceed to "
                "Hunyuan with these views: it will collapse to a "
                "depth-card."
            )
        for f in o.failures:
            f_lower = f.lower()
            if "depth-card" in f_lower or "bbox depth" in f_lower:
                hints.append(
                    "- **D1 / D5** — Hunyuan produced a flat depth-card. "
                    "Re-run with `--multi-view` (now default) and N≥3 seed "
                    "ensemble; if it persists across seeds, raise "
                    "`octree_resolution` and increase `inference_steps`."
                )
            elif "luminance" in f_lower and "below floor" in f_lower:
                hints.append(
                    "- **D4** — beauty renders are unlit. `bake_pbr.render_views()` "
                    "needs the HDRI + 3-point fill restored; this is the "
                    "Phase C lighting refactor."
                )
            elif "coverage" in f_lower and "below floor" in f_lower:
                hints.append(
                    "- **D1 / D4** — view shows edge of flat mesh OR an unlit "
                    "scene. First confirm geometry passed Gate 2; if it did, "
                    "the camera framing / lighting in `render_views()` is wrong."
                )
            elif "fill colour" in f_lower or "uncovered uv" in f_lower:
                hints.append(
                    "- **D3** — stage 2b projection skipped UV islands. Switch "
                    "the projector to FLUX.2 [klein] (Phase D); legacy SDXL "
                    "drops coverage when conditioning views are dark."
                )
            elif "face count" in f_lower and "above" in f_lower:
                hints.append(
                    "- **B1** — Hunyuan overshoots the poly budget. Lower "
                    "`octree_resolution` or add a decimate pass before stage 2a."
                )
            elif "tangent-space" in f_lower or "normal" in f_lower:
                hints.append(
                    "- **D4** — normal map is malformed. Verify Blender's "
                    "compositor wires the normal pass to the OpenGL Y+ output "
                    "(stage 2a writes Y- by default)."
                )
            elif "mr g" in f_lower or "roughness" in f_lower:
                hints.append(
                    "- **D3 / D4** — roughness channel never got written. "
                    "Check `bake_pbr.py` BSDF wiring; the principled "
                    "shader's Roughness output must connect to the bake's "
                    "G channel before `image.save(...)`."
                )
    seen: set[str] = set()
    deduped: list[str] = []
    for h in hints:
        if h not in seen:
            deduped.append(h)
            seen.add(h)
    return deduped + [""]


# ---------------------------------------------------------------------------
# json aggregate (read by retry harness)
# ---------------------------------------------------------------------------


def render_json(asset_id: str, outcomes: list[GateOutcome]) -> dict[str, Any]:
    """Aggregate sidecars into one parseable record."""
    failed_keys = [o.key for o in outcomes if o.found and o.valid is False]
    return {
        "asset_id": asset_id,
        "overall_valid": all(
            o.valid for o in outcomes if o.found and o.valid is not None
        ),
        "gates_ran": [o.key for o in outcomes if o.found],
        "gates_failed": failed_keys,
        "recommended_action": _recommend_action(failed_keys, outcomes),
        "per_gate": {
            o.key: {
                "found": o.found,
                "valid": o.valid,
                "failure_count": o.failure_count,
                "warning_count": o.warning_count,
                "failures": o.failures,
                "warnings": o.warnings,
            }
            for o in outcomes
        },
    }


def _recommend_action(
    failed_keys: list[str], outcomes: list[GateOutcome]
) -> str:
    """
    Map the failure pattern to a single action label.

    Used by Phase F retry harness to decide whether to:
      * `retry_with_new_seed` — geometry / view failures plausibly
        fixed by a different Hunyuan or projector seed.
      * `halt_and_fix_pipeline` — a contract violation (wrong channel
        packing, wrong file layout) — re-rolling won't help, the
        operator must repair the pipeline first.
      * `pass` — no action needed.
    """
    if not failed_keys:
        return "pass"
    contract_violations = (
        "tangent-space", "OpenPBR", "resolution", "packing", "not found"
    )
    for o in outcomes:
        if o.valid is False:
            for f in o.failures:
                if any(token in f for token in contract_violations):
                    return "halt_and_fix_pipeline"
    return "retry_with_new_seed"


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def aggregate(
    asset_id: str, diagnostics_dir: Path
) -> tuple[str, dict[str, Any], list[GateOutcome]]:
    """Load all known gates and return (markdown, json, outcomes)."""
    outcomes = [
        load_gate(diagnostics_dir, asset_id, key) for key, _, _ in GATE_TABLE
    ]
    return render_markdown(asset_id, outcomes), render_json(asset_id, outcomes), outcomes


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Aggregate validator sidecars into a single report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("asset_id")
    p.add_argument(
        "--diagnostics-dir",
        default=str(DIAGNOSTICS),
        help=f"Directory containing <id>.{{geometry,views,pbr}}.json. Default: {DIAGNOSTICS}",
    )
    p.add_argument(
        "--md-out",
        help="Markdown report destination. "
             "Default: <diagnostics-dir>/<id>.report.md",
    )
    p.add_argument(
        "--json-out",
        help="Aggregate JSON destination. "
             "Default: <diagnostics-dir>/<id>.aggregate.json",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    diag_dir = Path(args.diagnostics_dir).resolve()
    md_path = (
        Path(args.md_out).resolve()
        if args.md_out
        else diag_dir / f"{args.asset_id}.report.md"
    )
    json_path = (
        Path(args.json_out).resolve()
        if args.json_out
        else diag_dir / f"{args.asset_id}.aggregate.json"
    )

    md, js, outcomes = aggregate(args.asset_id, diag_dir)
    if not any(o.found for o in outcomes):
        sys.stderr.write(
            f"ERROR: no sidecars found in {diag_dir} for asset '{args.asset_id}'.\n"
            "Run validate_geometry / validate_views / validate_pbr first.\n"
        )
        return 1

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md)
    json_path.write_text(json.dumps(js, indent=2) + "\n")

    print(f"[diagnostic_report] {args.asset_id}")
    print(f"  markdown → {md_path}")
    print(f"  json     → {json_path}")
    overall = js["overall_valid"]
    print(f"  overall  → {'PASS' if overall else 'FAIL'}  "
          f"(action: {js['recommended_action']})")
    return 0 if overall else 2


if __name__ == "__main__":
    raise SystemExit(main())
