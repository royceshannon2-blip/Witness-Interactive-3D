#!/usr/bin/env python3
"""
generate_scene.py — Batch Asset Generation

Reads a manifest of assets and generates them all in sequence.
Useful for building entire location sets (e.g., all assets for FamilyCompound).

Usage:
    python generate_scene.py <manifest.json> [--server http://localhost:8081]

Manifest format:
    [
      { "image": "assets/source/generated/jerrycan.png", "name": "Jerrycan", "era": "present", "steps": 50 },
      { "image": "assets/source/generated/bicycle.png", "name": "Bicycle", "era": "past", "steps": 50 }
    ]
"""

import argparse
import sys
import json
import subprocess
from pathlib import Path


def validate_manifest(manifest_path):
    """Load and validate manifest JSON."""
    path = Path(manifest_path)
    if not path.exists():
        print(f"ERROR: Manifest not found: {path}")
        sys.exit(1)

    try:
        with open(path, 'r') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in manifest: {e}")
        sys.exit(1)

    if not isinstance(manifest, list):
        print(f"ERROR: Manifest must be a JSON array")
        sys.exit(1)

    for i, item in enumerate(manifest):
        if not all(k in item for k in ['image', 'name', 'era']):
            print(f"ERROR: Item {i} missing required fields: image, name, era")
            sys.exit(1)

    return manifest


def generate_asset(image_path, asset_name, steps=50, server="http://localhost:8081"):
    """Call generate_asset.py for a single asset."""
    cmd = [
        'python', 'tools/generate_asset.py',
        image_path,
        asset_name,
        '--steps', str(steps),
        '--server', server
    ]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"ERROR: Failed to run generate_asset.py: {e}")
        return False


def optimize_asset(glb_path):
    """Call optimize_asset.py for a single asset."""
    cmd = [
        'python', 'tools/optimize_asset.py',
        glb_path,
        '--in-place'
    ]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"ERROR: Failed to run optimize_asset.py: {e}")
        return False


def register_asset(asset_name, era):
    """Call register_asset.py for a single asset."""
    cmd = [
        'python', 'tools/register_asset.py',
        asset_name,
        era
    ]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"ERROR: Failed to run register_asset.py: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate multiple assets from a manifest"
    )
    parser.add_argument('manifest', help='Path to manifest JSON file')
    parser.add_argument('--server', default='http://localhost:8081',
                        help='Hunyuan3D server URL')
    parser.add_argument('--skip-registration', action='store_true',
                        help='Skip asset registry step')

    args = parser.parse_args()

    # Load and validate
    manifest = validate_manifest(args.manifest)

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Batch Asset Generation")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Manifest:   {args.manifest}")
    print(f"Items:      {len(manifest)}")
    print(f"Server:     {args.server}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    success_count = 0
    failed_items = []

    for idx, item in enumerate(manifest, 1):
        image_path = item['image']
        asset_name = item['name']
        era = item['era']
        steps = item.get('steps', 50)

        print(f"\n[{idx}/{len(manifest)}] Processing: {asset_name}")
        print(f"  Image: {image_path}")
        print(f"  Era:   {era}")
        print(f"  Steps: {steps}")

        # Generate
        if not generate_asset(image_path, asset_name, steps, args.server):
            print(f"  ✗ Generation failed")
            failed_items.append((asset_name, "generation"))
            continue

        # Optimize
        glb_path = f"processed/glb/{asset_name}.glb"
        if not optimize_asset(glb_path):
            print(f"  ✗ Optimization failed")
            failed_items.append((asset_name, "optimization"))
            continue

        # Register
        if not args.skip_registration:
            if not register_asset(asset_name, era):
                print(f"  ✗ Registration failed")
                failed_items.append((asset_name, "registration"))
                continue

        success_count += 1
        print(f"  ✓ Complete")

    # Summary
    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Batch Complete")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Success: {success_count}/{len(manifest)}")

    if failed_items:
        print(f"\nFailed items:")
        for name, step in failed_items:
            print(f"  • {name} ({step})")
        sys.exit(1)
    else:
        print(f"\n✓ All assets generated successfully")


if __name__ == '__main__':
    main()
