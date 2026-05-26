"""
render_validation.py — Stage 3 Blender headless: 3-point + HDRI render gate.

Runs INSIDE Blender 4+/5+ via:

    blender --background --factory-startup \\
        --python tools/blender/render_validation.py -- \\
        --glb processed/glb/<id>.textured.glb \\
        --asset-id <id> \\
        --renders-dir processed/renders/<id> \\
        [--hdri processed/hdris/<name>.hdr] \\
        [--samples 256] [--resolution 1024]

What it does:

1. Imports the textured GLB (output of stage 2).
2. Sets up the world environment:
     * If `--hdri <path>` is provided → load it as an Environment Texture.
     * Else → use a procedural Sky Texture (Nishita) at noon, ~5500 K.
3. Adds a three-point key/fill/rim lighting rig sized to the asset's
   bounding box. Key is warm 5500 K from 45° upper-front-left; fill is
   cool 6500 K from 30° lower-front-right at one third intensity; rim
   is pure-white from upper-back at half intensity.
4. Renders four turntable views (0°, 90°, 180°, 270°) at `--resolution`
   to `processed/renders/<id>/turntable_<deg>.png`.
5. Renders one hero shot (3/4 angle, slightly elevated) at the same
   resolution to `processed/renders/<id>/hero.png`.
6. Writes a small `renders.json` index alongside the PNGs so the
   CHANGELOG entry can link directly to the images.

The bake step (stage 2) already lights the textures themselves. Stage 3
is purely an output-gate: a place for the author to eyeball "does this
asset look like Digital Diorama?" before it ships to Babylon.

Exit codes (via sys.exit, captured by the orchestrator):
  0  all 5 renders written
  2  glb load failed / render crashed
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import traceback
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError:  # pragma: no cover — only when running outside Blender
    bpy = None  # type: ignore[assignment]
    Vector = None  # type: ignore[assignment]

CANONICAL_RENDERS = ("turntable_0", "turntable_90", "turntable_180", "turntable_270", "hero")


# ---------------------------------------------------------------------------
# args
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse args from sys.argv after Blender's `--` separator."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    p = argparse.ArgumentParser(description="3-point + HDRI validation renders.")
    p.add_argument("--glb", required=True)
    p.add_argument("--asset-id", required=True)
    p.add_argument("--renders-dir", required=True)
    p.add_argument("--hdri", default=None, help="Optional HDRI/EXR path for the environment.")
    p.add_argument("--samples", type=int, default=256, help="Cycles samples per render.")
    p.add_argument("--resolution", type=int, default=1024)
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# scene setup
# ---------------------------------------------------------------------------


def reset_scene() -> None:
    """Empty the default scene so import is clean."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def enable_gpu_cycles(samples: int) -> None:
    """Switch to Cycles GPU with OPTIX/CUDA fallback."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    any_gpu = False
    for d in prefs.devices:
        d.use = d.type in {"OPTIX", "CUDA"}
        if d.use:
            any_gpu = True
    scene.cycles.device = "GPU" if any_gpu else "CPU"
    scene.cycles.samples = samples
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False


def import_glb(path: Path) -> list:
    """Import the GLB; return the mesh objects added."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    added = set(bpy.data.objects) - before
    return [o for o in added if o.type == "MESH"]


def bbox_centre_and_diag(meshes: list) -> tuple[Vector, float]:
    """Return (centre_world, diagonal_length) of the meshes' combined bbox."""
    corners: list[Vector] = []
    for obj in meshes:
        for c in obj.bound_box:
            corners.append(obj.matrix_world @ Vector(c))
    bb_min = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    bb_max = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return (bb_min + bb_max) * 0.5, max((bb_max - bb_min).length, 1.0)


# ---------------------------------------------------------------------------
# lighting
# ---------------------------------------------------------------------------


def setup_environment(hdri_path: Path | None) -> None:
    """
    Configure the world background.

    With ``--hdri``, an Environment Texture node loads the EXR/HDR. Without,
    a Sky Texture (Nishita atmosphere) approximates the Digital Diorama
    overcast 5500 K. Both keep the world strength at 1.0; we let the
    three lights drive contrast.
    """
    world = bpy.data.worlds.new("WitnessWorld") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    if hdri_path and hdri_path.exists():
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(str(hdri_path))
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    else:
        sky = nt.nodes.new("ShaderNodeTexSky")
        # Blender 5 dropped the NISHITA enum and split atmospheric scattering
        # across MULTIPLE_SCATTERING (replacement for NISHITA) plus
        # HOSEK_WILKIE / PREETHAM. Try in fidelity order; ignore failures so
        # we keep working on future Blender versions.
        for candidate in ("MULTIPLE_SCATTERING", "HOSEK_WILKIE", "PREETHAM"):
            try:
                sky.sky_type = candidate
                break
            except TypeError:
                continue
        for attr, value in (("sun_elevation", math.radians(58.0)), ("sun_rotation", math.radians(135.0))):
            if hasattr(sky, attr):
                setattr(sky, attr, value)
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])


def add_light(
    name: str,
    location: Vector,
    target: Vector,
    energy: float,
    colour: tuple[float, float, float],
    size: float,
) -> "bpy.types.Object":
    """Create an area light pointing at a target."""
    light_data = bpy.data.lights.new(name=name, type="AREA")
    light_data.energy = energy
    light_data.color = colour
    light_data.size = size
    obj = bpy.data.objects.new(name=name, object_data=light_data)
    bpy.context.collection.objects.link(obj)
    obj.location = location

    track_target = bpy.data.objects.new(name=f"{name}_target", object_data=None)
    bpy.context.collection.objects.link(track_target)
    track_target.location = target
    constraint = obj.constraints.new(type="TRACK_TO")
    constraint.target = track_target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    return obj


def setup_three_point(centre: Vector, diag: float) -> None:
    """
    Build the key/fill/rim rig sized to the asset's bbox diagonal.

    Distance scales with diag so we get the same visual framing whether
    we're rendering a ledger book (≈ 0.25 m) or a eucalyptus tree (≈ 8 m).
    """
    dist = diag * 1.4

    # Key: warm white, 45° upper-front-left
    add_light(
        name="key",
        location=centre + Vector((-dist * 0.7, -dist * 0.6, dist * 0.8)),
        target=centre,
        energy=max(800.0, diag * 1200.0),
        colour=(1.00, 0.95, 0.85),
        size=diag * 1.5,
    )
    # Fill: cool blue, 1/3 intensity, 30° lower-front-right
    add_light(
        name="fill",
        location=centre + Vector((dist * 0.9, -dist * 0.5, dist * 0.3)),
        target=centre,
        energy=max(260.0, diag * 400.0),
        colour=(0.80, 0.88, 1.00),
        size=diag * 2.2,
    )
    # Rim: pure white, 1/2 intensity, upper-back
    add_light(
        name="rim",
        location=centre + Vector((dist * 0.2, dist * 1.0, dist * 0.9)),
        target=centre,
        energy=max(420.0, diag * 600.0),
        colour=(1.0, 1.0, 1.0),
        size=diag * 1.0,
    )


# ---------------------------------------------------------------------------
# camera + renders
# ---------------------------------------------------------------------------


def place_turntable_camera(centre: Vector, diag: float, angle_deg: float) -> "bpy.types.Object":
    """Camera at `angle_deg` around the asset, lens 50 mm, framing on bbox."""
    radius = diag * 1.6
    height = diag * 0.55
    angle_rad = math.radians(angle_deg)
    location = centre + Vector(
        (radius * math.sin(angle_rad), -radius * math.cos(angle_rad), height)
    )
    cam_data = bpy.data.cameras.new(name=f"cam_turntable_{int(angle_deg)}")
    cam_data.lens = 50.0
    cam_obj = bpy.data.objects.new(name=cam_data.name, object_data=cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = location

    target = bpy.data.objects.new(name=f"{cam_obj.name}_target", object_data=None)
    bpy.context.collection.objects.link(target)
    target.location = centre
    c = cam_obj.constraints.new(type="TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return cam_obj


def place_hero_camera(centre: Vector, diag: float) -> "bpy.types.Object":
    """3/4 angle, slightly elevated, tighter framing for the hero shot."""
    radius = diag * 1.35
    height = diag * 0.75
    location = centre + Vector((radius * 0.7, -radius * 0.7, height))
    cam_data = bpy.data.cameras.new(name="cam_hero")
    cam_data.lens = 65.0
    cam_obj = bpy.data.objects.new(name=cam_data.name, object_data=cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = location

    target = bpy.data.objects.new(name="cam_hero_target", object_data=None)
    bpy.context.collection.objects.link(target)
    target.location = centre
    c = cam_obj.constraints.new(type="TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return cam_obj


def render_to(scene: "bpy.types.Scene", camera: "bpy.types.Object", out_path: Path) -> None:
    """Render through `camera` and save to `out_path` (PNG)."""
    scene.camera = camera
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    if bpy is None:
        sys.stderr.write("ERROR: render_validation.py must run inside Blender\n")
        return 2

    args = parse_args()
    glb_path = Path(args.glb).resolve()
    if not glb_path.exists():
        sys.stderr.write(f"ERROR: GLB not found: {glb_path}\n")
        return 2

    renders_dir = Path(args.renders_dir).resolve()
    renders_dir.mkdir(parents=True, exist_ok=True)
    hdri = Path(args.hdri).resolve() if args.hdri else None

    sys.stdout.write(f"[render_validation] asset_id={args.asset_id}  hdri={hdri or 'procedural sky'}\n")
    reset_scene()
    enable_gpu_cycles(args.samples)

    meshes = import_glb(glb_path)
    if not meshes:
        sys.stderr.write("ERROR: imported GLB contained no meshes\n")
        return 2
    centre, diag = bbox_centre_and_diag(meshes)
    setup_environment(hdri)
    setup_three_point(centre, diag)

    scene = bpy.context.scene
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100

    written: list[str] = []
    for angle in (0.0, 90.0, 180.0, 270.0):
        cam = place_turntable_camera(centre, diag, angle)
        out = renders_dir / f"turntable_{int(angle)}.png"
        render_to(scene, cam, out)
        written.append(out.name)
        sys.stdout.write(f"[render_validation] wrote {out.relative_to(Path.cwd())}\n")

    hero_cam = place_hero_camera(centre, diag)
    hero_out = renders_dir / "hero.png"
    render_to(scene, hero_cam, hero_out)
    written.append(hero_out.name)
    sys.stdout.write(f"[render_validation] wrote {hero_out.relative_to(Path.cwd())}\n")

    index = {
        "asset_id": args.asset_id,
        "source_glb": str(glb_path),
        "hdri": str(hdri) if hdri else None,
        "samples": args.samples,
        "resolution": args.resolution,
        "renders": written,
    }
    (renders_dir / "renders.json").write_text(json.dumps(index, indent=2) + "\n")
    sys.stdout.write("[render_validation] done\n")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except SystemExit:
        raise
    except BaseException as exc:
        traceback.print_exc()
        sys.stderr.write(f"ERROR: render_validation.py raised {type(exc).__name__}: {exc}\n")
        rc = 2
    raise SystemExit(rc)
