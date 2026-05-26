#!/usr/bin/env python3
"""
register_asset.py — Asset Registry Manager

Appends a generated asset row to `docs/asset-index.md`.
Called by `asset_pipeline.py` after stage 2 + optimize for mesh/animated assets.
Non-mesh kinds (splat, tileset, navmesh, nme) write their rows via
`asset_pipeline.py`'s `PipelineContext.row()` directly.

Row format (8 columns, matches asset-index.md header):
  | Asset ID | Kind | Path | Era | Source | Registered | Faces | Gates |

`Faces` is pulled from processed/diagnostics/<id>.geometry.json if present.
`Gates` is pulled from processed/diagnostics/<id>.aggregate.json if present.
Both fall back to "n/a" when diagnostics are absent (first run or --no-texture).

Usage:
    python tools/register_asset.py <asset_id> <era>
        --glb-path <path>
        [--kind mesh]
        [--source <filename>]
        [--diagnostics-dir processed/diagnostics]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSET_INDEX = REPO_ROOT / "docs" / "asset-index.md"
DIAGNOSTICS_DIR = REPO_ROOT / "processed" / "diagnostics"

INDEX_HEADER = """\
# Asset Index

Auto-managed by `tools/asset_pipeline.py`. Do not hand-edit rows
— re-run the pipeline to refresh metadata.

| Asset ID | Kind | Path | Era | Source | Registered | Faces | Gates |
|---|---|---|---|---|---|---|---|
"""


def _era_label(era: str) -> str:
    return {
        "present": "2026 (investigator era)",
        "past": "1994 (grandparent era)",
        "shared": "both eras",
    }.get(era, era)


def _read_faces(asset_id: str, diag_dir: Path) -> str:
    sidecar = diag_dir / f"{asset_id}.geometry.json"
    if not sidecar.exists():
        return "n/a"
    try:
        data = json.loads(sidecar.read_text())
        faces = data.get("metrics", {}).get("face_count")
        if faces is not None:
            return f"{int(faces):,}"
    except Exception:
        pass
    return "n/a"


def _read_gates(asset_id: str, diag_dir: Path) -> str:
    sidecar = diag_dir / f"{asset_id}.aggregate.json"
    if not sidecar.exists():
        return "n/a"
    try:
        data = json.loads(sidecar.read_text())
        action = data.get("recommended_action", "")
        ran = data.get("gates_ran", [])
        failed = data.get("gates_failed", [])
        if not ran:
            return "n/a"
        if action == "pass":
            return f"✅ {len(ran)}/{len(ran)}"
        return f"❌ {len(ran) - len(failed)}/{len(ran)} ({', '.join(failed)})"
    except Exception:
        pass
    return "n/a"


def ensure_index() -> None:
    if not ASSET_INDEX.exists():
        ASSET_INDEX.parent.mkdir(parents=True, exist_ok=True)
        ASSET_INDEX.write_text(INDEX_HEADER)
        print(f"Created: {ASSET_INDEX.relative_to(REPO_ROOT)}")


def register_asset(
    asset_id: str,
    era: str,
    kind: str,
    glb_path: str,
    source: str,
    diag_dir: Path,
) -> bool:
    faces = _read_faces(asset_id, diag_dir)
    gates = _read_gates(asset_id, diag_dir)

    rel_path = glb_path
    try:
        rel_path = str(Path(glb_path).relative_to(REPO_ROOT))
    except ValueError:
        pass

    date_str = datetime.now().strftime("%Y-%m-%d")
    row = (
        f"| {asset_id} | {kind} | {rel_path} | {_era_label(era)} | "
        f"{source} | {date_str} | {faces} | {gates} |"
    )
    try:
        with ASSET_INDEX.open("a") as fh:
            fh.write(row + "\n")
        print(f"✓ Registered: {asset_id} ({kind}, {era})", flush=True)
        return True
    except IOError as exc:
        print(f"ERROR: failed to write to {ASSET_INDEX}: {exc}", flush=True)
        return False


def main() -> int:
    p = argparse.ArgumentParser(
        description="Register a generated asset in docs/asset-index.md"
    )
    p.add_argument("asset_id", help="Snake_case asset ID")
    p.add_argument("era", choices=["present", "past", "shared"])
    p.add_argument(
        "--glb-path",
        default=None,
        help="Path to the final GLB (default: processed/glb/<asset_id>.glb)",
    )
    p.add_argument("--kind", default="mesh", help="Asset kind (default: mesh)")
    p.add_argument(
        "--source",
        default="",
        help="Human-readable provenance string (filename or URL)",
    )
    p.add_argument(
        "--diagnostics-dir",
        default=str(DIAGNOSTICS_DIR),
        help="Directory containing <id>.geometry.json and <id>.aggregate.json sidecars.",
    )
    args = p.parse_args()

    glb_path = args.glb_path or f"processed/glb/{args.asset_id}.glb"
    diag_dir = Path(args.diagnostics_dir)

    print("━" * 56, flush=True)
    print("Asset Registry", flush=True)
    print("━" * 56, flush=True)
    print(f"  Asset:  {args.asset_id}", flush=True)
    print(f"  Kind:   {args.kind}", flush=True)
    print(f"  Era:    {args.era}", flush=True)
    print(f"  Index:  {ASSET_INDEX.relative_to(REPO_ROOT)}", flush=True)
    print("━" * 56, flush=True)

    ensure_index()
    ok = register_asset(
        asset_id=args.asset_id,
        era=args.era,
        kind=args.kind,
        glb_path=glb_path,
        source=args.source or Path(glb_path).name,
        diag_dir=diag_dir,
    )
    if not ok:
        return 1

    print(f"\n  View registry: cat {ASSET_INDEX.relative_to(REPO_ROOT)}", flush=True)
    print("━" * 56, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
