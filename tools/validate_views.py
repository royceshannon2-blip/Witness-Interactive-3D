#!/usr/bin/env python3
"""
validate_views.py — Multi-View Beauty Render Validator (Gate 3)

Hard-fails when the 6 canonical views emitted by `bake_pbr.py
render_views()` are unfit to condition stage 2b texture projection.

The canonical failure that motivated this gate is documented in
[`docs/design-docs/ASSET_GENERATION_OVERVIEW.md §0`](../docs/design-docs/ASSET_GENERATION_OVERVIEW.md):
`reset_scene()` wipes Blender's factory lights and `film_transparent=True`
leaves un-shaded pixels black, so back/bottom views render as pure
darkness. SDXL projection then sees black conditioning and produces a
half-filled albedo — the visible "white untextured squares" symptom.

Checks (from doc §4 Gate 3):

  1. all-views-present  — every expected view file exists and decodes
  2. luminance-floor     — mean luminance ≥ 0.05  (catches all-black)
  3. luminance-ceiling   — mean luminance ≤ 0.95  (catches all-white)
  4. contrast-floor      — std luminance ≥ 0.04   (catches flat colour)
  5. coverage-floor      — non-background pixel fraction ≥ 0.10
                                                  (catches edge-on flat
                                                  mesh views where the
                                                  object is a sliver.)
  6. cross-view-consistency — stdev across the per-view mean luminances
                              < 0.15. One radically darker view almost
                              always means a lighting / camera issue.
  7. cross-view-colour (WARNING) — each view's mean foreground colour stays
                              within FG_COLOR_DIVERGENCE_WARN (L1) of the
                              OTHER views' median (leave-one-out). Flags a view
                              that fused a different subject/background —
                              incoherent multi-view input smears Hunyuan's
                              texture fusion. Needs >= MIN_VIEWS_FOR_COLOUR
                              views; below that one outlier drags the median, so
                              the check is skipped (noted in aggregate).

All-view CLIP semantic gate (D2 in the doc):
  When torch + transformers are available we score EVERY view against the
  asset prompt AND a set of failure-mode prompts (untextured / featureless /
  corrupted), then softmax. A view fails when the probability mass on the
  real subject drops below CLIP_REAL_PROB_FLOOR — i.e. it reads more like a
  blank slab or a corrupted render than like the asset. This relative
  contrast test catches the documented "featureless triangular-prism slab"
  that an absolute cosine floor let through, and generalises across kinds.

Usage (orchestrator):

    python tools/validate_views.py processed/views/<id>/ \\
        --asset-id <id> \\
        --template prompts/asset-templates/<id>.md \\
        --report processed/diagnostics/<id>.views.json

Exit codes:
  0  all checks passed
  1  bad inputs
  2  one or more gates failed
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# Gate thresholds (ASSET_GENERATION_OVERVIEW.md §4 Gate 3).
EXPECTED_VIEW_DIRECTIONS = ("front", "back", "left", "right", "top", "bottom")
# Filename suffixes for the beauty (lit colour) render. `.beauty.png` is the
# current `bake_pbr.render_views()` convention; `view_<dir>.png` is the older
# layout still found in some test fixtures. We accept both so the validator
# survives a bake_pbr refactor without churn.
BEAUTY_SUFFIXES = (".beauty.png", ".beauty.exr", ".png", ".exr")
LUMINANCE_FLOOR = 0.05            # mean ≥ this
LUMINANCE_CEILING = 0.95          # mean ≤ this
CONTRAST_FLOOR = 0.04             # std  ≥ this
COVERAGE_FLOOR = 0.10             # fraction of non-bg pixels
CROSS_VIEW_LUMINANCE_STD_MAX = 0.15
# Cross-view structural consistency. A coherent multi-view set shows the SAME
# object — similar dominant foreground colour — from every angle; a view that
# fused a different subject/background or washed out diverges, and feeding that
# to Hunyuan smears the texture fusion. Surfaced as a WARNING (not a hard
# fail): a legitimately multi-coloured asset can vary by side, and the CLIP
# gate already hard-fails wrong-subject views. NOTE: there is deliberately no
# coverage-consistency *fail* — empirically coverage does not discriminate this
# failure (a good full-frame subject and a garbled one both fill the frame, so
# the bad grandfather views and the good hand views both ran 0.84–0.97).
FG_COLOR_DIVERGENCE_WARN = 0.22   # L1 distance (summed RGB, range 0..3) from the other views' consensus
MIN_VIEWS_FOR_COLOUR = 5          # below this one outlier drags the median and false-warns the inliers, so skip
# All-view CLIP semantic gate. Each view is scored against the asset prompt
# plus the failure-mode prompts below, then softmaxed; a view must keep at
# least CLIP_REAL_PROB_FLOOR of the probability mass on the real subject. A
# relative contrast test beats an absolute cosine floor because a Hunyuan slab
# scores higher on "untextured placeholder" than on the real subject even when
# its raw cosine to the prompt clears a fixed bar. Negatives target the QUALITY
# failure (blank / untextured / corrupted), not a shape, so a legitimately
# blocky but well-textured asset (stone slab, plank) is not false-flagged.
CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
CLIP_NEGATIVE_PROMPTS = (
    "a blank untextured grey 3D primitive",
    "a smooth featureless placeholder block with no surface detail",
    "an abstract shapeless blob",
    "a corrupted distorted 3D render with no recognizable subject",
)
CLIP_REAL_PROB_FLOOR = 0.40
BG_DETECT_BORDER_PX = 4           # sample border pixels for bg colour
BG_DETECT_TOLERANCE = 0.04        # |pixel - bg|_L1 below this = "background"


@dataclass
class ViewMetrics:
    """Per-view stats extracted before any cross-view aggregation."""
    name: str
    path: str
    width: int = 0
    height: int = 0
    luminance_mean: float = 0.0
    luminance_std: float = 0.0
    coverage: float = 0.0
    foreground_rgb: list[float] = field(default_factory=list)
    background_rgba: list[float] = field(default_factory=list)
    clip_score: float | None = None
    failures: list[str] = field(default_factory=list)


@dataclass
class ViewsReport:
    """
    Structured result aggregated across all 6 views.

    `per_view` retains the individual metrics so `diagnostic_report.py`
    can render a per-view failure matrix without re-loading PNGs.
    """
    asset_id: str
    views_dir: str
    valid: bool = True
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    per_view: list[ViewMetrics] = field(default_factory=list)
    aggregate: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# image stats
# ---------------------------------------------------------------------------


def _load_rgba(path: Path):
    """
    Load PNG as float32 RGBA in [0, 1].

    Uses PIL because it's already in the ComfyUI venv (SDXL needs it)
    and avoids dragging in OpenCV just for a sanity check.
    """
    from PIL import Image
    import numpy as np

    img = Image.open(path).convert("RGBA")
    arr = np.asarray(img, dtype="float32") / 255.0
    return arr


def _estimate_background(arr) -> tuple[float, float, float, float]:
    """
    Estimate the background colour from a border-pixel sample.

    `bake_pbr.render_views()` sets `film_transparent=True` so the
    background is usually (0,0,0,0) — but a future fix may swap that
    to mid-grey or HDRI-tinted neutrals. Sampling the actual border
    keeps the check correct under either regime.
    """
    import numpy as np

    h, w = arr.shape[:2]
    b = BG_DETECT_BORDER_PX
    border = np.concatenate(
        [
            arr[:b, :, :].reshape(-1, 4),
            arr[-b:, :, :].reshape(-1, 4),
            arr[:, :b, :].reshape(-1, 4),
            arr[:, -b:, :].reshape(-1, 4),
        ]
    )
    return tuple(float(c) for c in border.mean(axis=0))


def _compute_metrics(view_name: str, path: Path) -> ViewMetrics:
    """Populate luminance + coverage stats for one view."""
    import numpy as np

    m = ViewMetrics(name=view_name, path=str(path))
    if not path.exists():
        m.failures.append(f"view file missing: {path}")
        return m

    try:
        arr = _load_rgba(path)
    except Exception as exc:  # noqa: BLE001
        m.failures.append(f"failed to decode PNG: {exc}")
        return m

    m.height, m.width = arr.shape[:2]

    # ITU-R BT.709 luminance from un-premultiplied RGB; alpha is
    # ignored on purpose so a transparent black image still flags as
    # too-dark rather than passing because alpha=0.
    rgb = arr[..., :3]
    luminance = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    m.luminance_mean = float(luminance.mean())
    m.luminance_std = float(luminance.std())

    bg = _estimate_background(arr)
    m.background_rgba = list(bg)
    # Coverage: fraction of pixels whose RGB is meaningfully different
    # from the detected background colour. Cheap proxy for "the object
    # is actually in the frame".
    bg_rgb = np.asarray(bg[:3], dtype="float32")
    diff = np.abs(rgb - bg_rgb).sum(axis=-1)
    fg_mask = diff > BG_DETECT_TOLERANCE * 3
    m.coverage = float(fg_mask.mean())
    # Mean foreground (non-background) colour, for cross-view colour
    # consistency. Empty-foreground views keep the default [] so the
    # cross-view step skips them.
    if fg_mask.any():
        m.foreground_rgb = [float(c) for c in rgb[fg_mask].mean(axis=0)]

    if m.luminance_mean < LUMINANCE_FLOOR:
        m.failures.append(
            f"mean luminance {m.luminance_mean:.4f} below floor "
            f"{LUMINANCE_FLOOR} — render is black. Likely cause: "
            "bake_pbr.render_views() has no scene lights (factory "
            "reset wiped default light, world background empty)."
        )
    if m.luminance_mean > LUMINANCE_CEILING:
        m.failures.append(
            f"mean luminance {m.luminance_mean:.4f} above ceiling "
            f"{LUMINANCE_CEILING} — render is blown-out white"
        )
    if m.luminance_std < CONTRAST_FLOOR:
        m.failures.append(
            f"luminance std {m.luminance_std:.4f} below floor "
            f"{CONTRAST_FLOOR} — image is a flat colour"
        )
    if m.coverage < COVERAGE_FLOOR:
        m.failures.append(
            f"object coverage {m.coverage:.3f} below floor "
            f"{COVERAGE_FLOOR} — view shows a sliver of the mesh, "
            "likely an edge-on view of a flat depth-card"
        )
    return m


# ---------------------------------------------------------------------------
# optional CLIP gate (D2)
# ---------------------------------------------------------------------------


def _extract_clip_prompt(template_path: Path | None) -> str | None:
    """
    Pull a CLIP-friendly prompt from the asset template.

    Preference order:
      1. `clip_prompt:` in YAML frontmatter (curated, short).
      2. The first non-blank paragraph of the body after the
         frontmatter (long-form prompt — works but noisier).
      3. None — CLIP gate is skipped with a warning.
    """
    if template_path is None or not template_path.exists():
        return None
    text = template_path.read_text()
    if text.startswith("---"):
        end = text.find("\n---", 4)
        if end > 0:
            front = text[4:end]
            for line in front.splitlines():
                line = line.strip()
                if line.startswith("clip_prompt:"):
                    _, _, value = line.partition(":")
                    value = value.strip().strip('"').strip("'")
                    if value:
                        return value
            body = text[end + 4 :]
        else:
            body = text
    else:
        body = text
    for paragraph in body.split("\n\n"):
        paragraph = paragraph.strip()
        if paragraph and not paragraph.startswith("#"):
            return paragraph[:300]
    return None


def _shorten_for_clip(prompt: str) -> str:
    """
    Trim a long asset prompt to fit CLIP's 77-token text encoder.

    We keep the first sentence (capped at ~50 words) so the subject
    noun-phrase dominates the embedding rather than the trailing material,
    lighting, and rigging spec that the full template body carries.
    """
    first = re.split(r"(?<=[.!?])\s", prompt.strip(), maxsplit=1)[0]
    return " ".join(first.split()[:50])


def _maybe_run_clip_gate(report: ViewsReport, prompt: str | None) -> None:
    """
    All-view semantic gate. Skipped gracefully if transformers / torch are
    unavailable — a missing optional dep must never block the pipeline; this
    is defence-in-depth on top of the cheap pixel-stat gates.

    Scoring is a relative contrast test rather than an absolute cosine floor:
    every view is scored against the (shortened) asset prompt AND the
    CLIP_NEGATIVE_PROMPTS failure modes, then softmaxed. ``clip_score`` is the
    softmax probability mass landing on the real subject; a view fails when
    that drops below CLIP_REAL_PROB_FLOOR (i.e. it reads more like a blank
    slab / corrupted render than the asset). This is what catches a featureless
    Hunyuan slab that the old cosine floor — and the geometry gate — missed.
    """
    if prompt is None:
        report.warnings.append(
            "no clip_prompt available — skipping CLIP semantic gate"
        )
        return
    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor
    except ImportError as exc:
        report.warnings.append(
            f"transformers/torch not available ({exc}) — skipping CLIP semantic gate"
        )
        return

    try:
        from PIL import Image

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = CLIPModel.from_pretrained(CLIP_MODEL_ID).to(device).eval()
        processor = CLIPProcessor.from_pretrained(CLIP_MODEL_ID)

        real = _shorten_for_clip(prompt)
        texts = [real, *CLIP_NEGATIVE_PROMPTS]
        report.aggregate["clip_prompt"] = real
        report.aggregate["clip_real_prob_floor"] = CLIP_REAL_PROB_FLOOR

        with torch.no_grad():
            for m in report.per_view:
                p = Path(m.path)
                if not p.exists():
                    continue
                image = Image.open(p).convert("RGB")
                inputs = processor(
                    text=texts, images=image,
                    return_tensors="pt", padding=True, truncation=True,
                ).to(device)
                probs = model(**inputs).logits_per_image.softmax(dim=-1).squeeze(0)
                real_prob = float(probs[0].item())
                m.clip_score = real_prob
                if real_prob < CLIP_REAL_PROB_FLOOR:
                    worst = texts[int(probs.argmax().item())]
                    m.failures.append(
                        f"CLIP semantic gate: P(asset)={real_prob:.2f} < "
                        f"{CLIP_REAL_PROB_FLOOR} — view reads more like "
                        f'"{worst}" than the asset prompt'
                    )
    except Exception as exc:  # noqa: BLE001
        report.warnings.append(f"CLIP gate raised {exc!r} — skipping")


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def _resolve_view_paths(views_dir: Path, indexed: bool = False) -> list[tuple[str, Path]]:
    """
    Map each canonical view direction to a render on disk.

    Two layouts are supported:

      * direction layout (default) — `<dir>.beauty.png` from
        `bake_pbr.render_views()`, or legacy `view_<dir>.png` /
        `<dir>.png`. Used for post-bake validation.

      * indexed layout (`indexed=True`) — `view_0.png` … `view_5.png`
        from `generate_multi_views.py` (Zero123++ v1.2). Used for
        Phase B2 pre-Hunyuan validation so we can hard-fail before
        wasting GPU time on a bad synth. The Zero123++ pose set is
        fixed: 0=front, 1=front-right, 2=back-right, 3=back,
        4=back-left, 5=front-left (top/bottom are not produced by
        Zero123++ v1.2 — those are post-bake artefacts only).

    Returns a missing-file placeholder when none of the candidates
    exist so the report surfaces the gap as a failure rather than
    silently skipping.
    """
    found: list[tuple[str, Path]] = []
    if indexed:
        # Glob whatever view_*.png exist so the gate handles a variable
        # count: Zero123++ synth always writes exactly 6, but a real
        # multi-view capture may supply any number of angles. Sort by the
        # numeric index so view_10 follows view_9, not view_1.
        def _idx(p: Path) -> int:
            nums = re.findall(r"\d+", p.stem)
            return int(nums[0]) if nums else 0

        existing = sorted(views_dir.glob("view_*.png"), key=_idx)
        if existing:
            return [(p.stem, p) for p in existing]
        # None found — surface 6 missing rows so a failed synth still
        # reports a per-view gap rather than silently shrinking the set.
        for idx in range(6):
            found.append((f"view_{idx}", views_dir / f"view_{idx}.png"))
        return found
    for direction in EXPECTED_VIEW_DIRECTIONS:
        candidates = [views_dir / f"{direction}{sfx}" for sfx in BEAUTY_SUFFIXES]
        candidates.extend(views_dir / f"view_{direction}{sfx}" for sfx in BEAUTY_SUFFIXES)
        for c in candidates:
            if c.exists():
                found.append((direction, c))
                break
        else:
            found.append((direction, views_dir / f"{direction}.beauty.png"))
    return found


def validate_views(
    views_dir: Path,
    asset_id: str,
    template_path: Path | None = None,
    run_clip: bool = True,
    indexed: bool = False,
) -> ViewsReport:
    """Run every Gate 3 check on a directory of view renders.

    ``indexed`` selects the Zero123++ synth output layout (view_0..5.png)
    instead of the post-bake direction-named layout.
    """
    import statistics

    report = ViewsReport(asset_id=asset_id, views_dir=str(views_dir))

    if not views_dir.exists():
        report.valid = False
        report.failures.append(f"views directory not found: {views_dir}")
        return report

    view_paths = _resolve_view_paths(views_dir, indexed=indexed)
    for name, path in view_paths:
        m = _compute_metrics(name, path)
        report.per_view.append(m)

    luminances = [m.luminance_mean for m in report.per_view if not m.failures or "missing" not in m.failures[0]]
    if luminances:
        cross_std = statistics.pstdev(luminances) if len(luminances) > 1 else 0.0
        report.aggregate["luminance_mean_across_views"] = sum(luminances) / len(luminances)
        report.aggregate["luminance_std_across_views"] = cross_std
        report.aggregate["luminance_std_threshold"] = CROSS_VIEW_LUMINANCE_STD_MAX
        if cross_std > CROSS_VIEW_LUMINANCE_STD_MAX:
            report.failures.append(
                f"cross-view luminance std {cross_std:.4f} > "
                f"{CROSS_VIEW_LUMINANCE_STD_MAX} — one or more views "
                "diverge dramatically. Often signals an unlit camera "
                "(black view) or an overexposed angle."
            )

    # Cross-view foreground-colour consistency (WARNING). The same object
    # should present a similar dominant colour from every angle; a view whose
    # foreground colour diverges sharply often fused a different subject or let
    # the background leak in, which smears Hunyuan's texture fusion. Warning,
    # not fail — a legitimately multi-coloured asset can vary by side, and the
    # CLIP gate already hard-fails wrong-subject views.
    fg = [m for m in report.per_view if m.foreground_rgb]
    if len(fg) >= MIN_VIEWS_FOR_COLOUR:
        import numpy as np

        arr = np.asarray([m.foreground_rgb for m in fg], dtype="float32")
        # Leave-one-out: compare each view to the median of the OTHERS so a
        # view is never measured against a centre that includes itself, and a
        # lone outlier stands out crisply instead of dragging its own target.
        loo_dists = []
        for i in range(len(arr)):
            centre = np.median(np.delete(arr, i, axis=0), axis=0)
            loo_dists.append(float(np.abs(arr[i] - centre).sum()))
        report.aggregate["fg_colour_median"] = [float(c) for c in np.median(arr, axis=0)]
        report.aggregate["fg_colour_divergence_max"] = max(loo_dists)
        report.aggregate["fg_colour_divergence_threshold"] = FG_COLOR_DIVERGENCE_WARN
        for m, d in zip(fg, loo_dists):
            if d > FG_COLOR_DIVERGENCE_WARN:
                report.warnings.append(
                    f"[{m.name}] foreground colour diverges (L1 {d:.2f} from the "
                    "other views' consensus) — view may show a different "
                    "subject/background; check multi-view coherence"
                )
    elif len(fg) >= 2:
        report.aggregate["fg_colour_note"] = (
            f"cross-view colour check skipped: {len(fg)} foreground view(s) < "
            f"{MIN_VIEWS_FOR_COLOUR} needed for a stable consensus"
        )

    if run_clip:
        _maybe_run_clip_gate(report, _extract_clip_prompt(template_path))

    # Roll per-view failures up to the report level so the orchestrator
    # only has to check `report.valid`.
    for m in report.per_view:
        for f in m.failures:
            report.failures.append(f"[{m.name}] {f}")

    report.valid = not report.failures
    return report


def emit_report(report: ViewsReport, json_path: Path | None) -> None:
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        # asdict handles nested dataclasses cleanly.
        json_path.write_text(json.dumps(asdict(report), indent=2) + "\n")

    status = "PASS" if report.valid else "FAIL"
    print(f"[validate_views] {report.asset_id} → {status}")
    for m in report.per_view:
        clip = f" clip={m.clip_score:.3f}" if m.clip_score is not None else ""
        print(
            f"  {m.name:14s} lum={m.luminance_mean:.3f}±{m.luminance_std:.3f} "
            f"cov={m.coverage:.3f}{clip}"
        )
    for k, v in report.aggregate.items():
        print(f"  {k:36s} {v:.4f}" if isinstance(v, float) else f"  {k:36s} {v}")
    for w in report.warnings:
        print(f"  ⚠ {w}")
    for f in report.failures:
        print(f"  ✗ {f}", file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Validate 6-view beauty renders (Gate 3).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("views_dir", help="Directory containing view_front.png … view_bottom.png")
    p.add_argument("--asset-id", required=True)
    p.add_argument(
        "--template",
        help="Template path for clip_prompt extraction. "
             "Default: prompts/asset-templates/<asset-id>.md",
    )
    p.add_argument(
        "--report",
        help="Write a JSON metrics sidecar to this path. "
             "Default: processed/diagnostics/<asset-id>.views.json",
    )
    p.add_argument(
        "--no-clip",
        action="store_true",
        help="Skip the optional CLIP semantic gate even if available.",
    )
    p.add_argument(
        "--indexed",
        action="store_true",
        help=(
            "Use the Zero123++ indexed layout (view_0.png … view_5.png) "
            "instead of direction-named beauty renders. Pass when "
            "validating stage 0.5 synth output before Hunyuan."
        ),
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    views_dir = Path(args.views_dir).resolve()
    template_path = (
        Path(args.template).resolve()
        if args.template
        else REPO_ROOT / "prompts" / "asset-templates" / f"{args.asset_id}.md"
    )
    report_path = (
        Path(args.report).resolve()
        if args.report
        else REPO_ROOT / "processed" / "diagnostics" / f"{args.asset_id}.views.json"
    )
    report = validate_views(
        views_dir=views_dir,
        asset_id=args.asset_id,
        template_path=template_path if template_path.exists() else None,
        run_clip=not args.no_clip,
        indexed=args.indexed,
    )
    emit_report(report, report_path)
    return 0 if report.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
