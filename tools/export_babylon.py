#!/usr/bin/env python3
"""
export_babylon.py — Babylon.js Asset Exporter

Validates optimized GLB files and exports them to the public assets folder
in the correct naming convention for Babylon.js loading.

Usage:
    python export_babylon.py <glb_path> <asset_name>

Example:
    python export_babylon.py processed/glb/Jerrycan.optimized.glb Jerrycan
    → copies to: witness-interactive-vite/public/assets/Jerrycan.glb
"""

import argparse
import sys
import shutil
import re
from pathlib import Path


PUBLIC_ASSETS_DIR = Path("witness-interactive-vite/public/assets")


def validate_naming(asset_name):
    """Ensure asset name is PascalCase."""
    # PascalCase: starts with uppercase, no underscores/hyphens
    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', asset_name):
        print(f"ERROR: Asset name must be PascalCase (e.g. Jerrycan, RedClay)")
        print(f"  Got: {asset_name}")
        return False
    return True


def validate_glb(glb_path):
    """Basic validation of GLB file."""
    path = Path(glb_path)
    if not path.exists():
        print(f"ERROR: GLB file not found: {path}")
        return False

    if path.suffix.lower() != '.glb':
        print(f"ERROR: File must be .glb, got: {path.suffix}")
        return False

    size = path.stat().st_size
    if size < 1024:  # Less than 1KB
        print(f"ERROR: GLB file suspiciously small: {size} bytes")
        return False

    print(f"  ✓ File exists: {size:,} bytes")
    return True


def export_asset(glb_path, asset_name):
    """Copy GLB to public assets folder."""
    glb_path = Path(glb_path)
    PUBLIC_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = PUBLIC_ASSETS_DIR / f"{asset_name}.glb"

    try:
        shutil.copy2(glb_path, output_path)
        print(f"  ✓ Exported to: {output_path}")
        return True
    except IOError as e:
        print(f"ERROR: Failed to copy file: {e}")
        return False


def generate_loader_code(asset_name):
    """Print example loader code."""
    code = f"""
// In src/io/AssetLoader.ts:
const glb = await AssetLoader.loadGlb('assets/{asset_name}.glb');
const mesh = glb.instantiateModelsToScene();

// Or with direct BABYLON API:
const container = await BABYLON.SceneLoader.LoadAssetContainerAsync(
  'assets/',
  '{asset_name}.glb',
  scene
);
container.addAllToScene();
"""
    return code


def main():
    parser = argparse.ArgumentParser(
        description="Export optimized GLB to Babylon.js public assets folder"
    )
    parser.add_argument('glb_path', help='Path to optimized GLB file')
    parser.add_argument('asset_name', help='Asset name (PascalCase, e.g. Jerrycan)')

    args = parser.parse_args()

    # Validate
    if not validate_naming(args.asset_name):
        sys.exit(1)

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Babylon.js Asset Export")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Asset:    {args.asset_name}")
    print(f"Source:   {args.glb_path}")
    print(f"Dest:     {PUBLIC_ASSETS_DIR / f'{args.asset_name}.glb'}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    print(f"\n[1/2] Validating GLB...")
    if not validate_glb(args.glb_path):
        sys.exit(1)

    print(f"\n[2/2] Exporting to public assets...")
    if not export_asset(args.glb_path, args.asset_name):
        sys.exit(1)

    print(f"\n✓ Export successful")
    print(f"\nExample loader code:")
    print(generate_loader_code(args.asset_name))

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == '__main__':
    main()
