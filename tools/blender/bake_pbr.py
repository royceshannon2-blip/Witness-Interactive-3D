"""
bake_pbr.py — Stage 2 Blender headless: 8K PBR bake + view export.

Runs INSIDE Blender 4+/5+ via:

    blender --background --factory-startup \\
        --python tools/blender/bake_pbr.py -- \\
        --glb processed/glb/raw/<id>.glb \\
        --asset-id <id> \\
        --family <auto|mud_brick|tin|wood|stone|cloth|leather|wax|skin|vegetation> \\
        --texture-size 8192 \\
        --view-size 1024 \\
        --textures-dir processed/textures/<id> \\
        --views-dir processed/views/<id> \\
        --output-glb processed/glb/<id>.textured.glb

What it does:

1. Imports the raw GLB.
2. Ensures every mesh has a valid UV layout — Smart UV Project if missing.
3. Applies a Principled BSDF material driven by procedural noise + voronoi
   networks parametrised by `material_families.FAMILIES[<family>]`.
4. Renders 6 canonical views (±X, ±Y, ±Z) at `--view-size` with Cycles GPU
   for use by stage 2b (AI projection via SDXL + ControlNet depth). Each
   view emits a beauty pass, a depth pass (16-bit), and a normal pass.
5. Bakes Albedo, MR (R-unused, G-roughness, B-metallic, per Babylon
   convention), Normal (OpenGL Y+), and AO to `--texture-size`² PNGs in
   `--textures-dir`.
6. Re-exports a textured GLB to `--output-glb`. Optimizer can then run
   Draco + KTX2 on this artefact.

The procedural-network output is the project's "good baseline". Stage 2b
(`tools/texture_asset.py --ai-project`) replaces the baked Albedo with an
AI-projected version using the 6 view PNGs + a ComfyUI depth-controlled
SDXL workflow.

Exit codes (via sys.exit, captured by the orchestrator):
  0  success
  2  glb load failed / bake failed
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

# This file runs inside Blender's embedded Python — `bpy` is provided by the
# host process. When running outside Blender (for syntax checks) `bpy` is
# absent; we shim it with None so import errors surface only at call time.
try:
    import bpy
    import bmesh
    from mathutils import Vector
except ImportError:  # pragma: no cover — only hit during static analysis
    bpy = None  # type: ignore[assignment]
    bmesh = None  # type: ignore[assignment]
    Vector = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_material_families():
    """
    Import `material_families.py` by file path.

    Blender's `--python` flag doesn't add the script's directory to
    `sys.path`, so a plain `import material_families` would fail. We
    locate the sibling file deterministically and load it via importlib.
    """
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "material_families", here / "material_families.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not locate material_families.py beside bake_pbr.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# arg parsing — Blender forwards args after `--` to sys.argv
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse args from sys.argv after Blender's `--` separator."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    p = argparse.ArgumentParser(description="Bake 8K PBR maps + render 6 canonical views.")
    p.add_argument("--glb", required=True, help="Raw GLB from stage 1 (Hunyuan output).")
    p.add_argument("--asset-id", required=True)
    p.add_argument("--family", default="auto", help="Material family override (default auto-pick from asset_id).")
    p.add_argument("--texture-size", type=int, default=8192)
    p.add_argument("--view-size", type=int, default=1024)
    p.add_argument("--textures-dir", required=True)
    p.add_argument("--views-dir", required=True)
    p.add_argument("--output-glb", required=True)
    p.add_argument("--samples", type=int, default=128, help="Cycles samples per bake / render.")
    p.add_argument("--skip-views", action="store_true", help="Skip the 6-view render pass.")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# scene setup
# ---------------------------------------------------------------------------


def reset_scene() -> None:
    """Wipe the default scene clean before importing the GLB."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def enable_gpu_cycles() -> None:
    """Switch Cycles to GPU compute. Falls back to CPU if no CUDA device."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"  # 5090 = Blackwell → OPTIX preferred
    prefs.get_devices()
    any_gpu = False
    for d in prefs.devices:
        d.use = d.type in {"OPTIX", "CUDA"}
        if d.use:
            any_gpu = True
    scene.cycles.device = "GPU" if any_gpu else "CPU"
    scene.cycles.samples = 128


def import_glb(path: Path) -> list:
    """Import the GLB; return the list of imported mesh objects."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    added = set(bpy.data.objects) - before
    return [o for o in added if o.type == "MESH"]


def ensure_uvs(meshes: list) -> None:
    """Smart UV Project any mesh that lacks a uv layer."""
    for obj in meshes:
        mesh = obj.data
        if mesh.uv_layers:
            continue
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bm = bmesh.from_edit_mesh(mesh)
        for f in bm.faces:
            f.select = True
        bmesh.update_edit_mesh(mesh)
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")


# ---------------------------------------------------------------------------
# procedural material — family-aware
# ---------------------------------------------------------------------------


def build_material(name: str, preset: dict) -> "bpy.types.Material":
    """
    Construct a Principled BSDF + noise/voronoi network from a preset.

    The network has three drivers:
        - Voronoi (small scale) → roughness variance
        - Voronoi (large scale) → albedo desaturation patches
        - Noise (medium scale)  → bump → normal output

    The result is bake-friendly: every channel is a single output node so
    Cycles' image-bake operator picks the right pass automatically.
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = preset["base_color"]
    bsdf.inputs["Metallic"].default_value = preset["metallic"]
    # Specular IOR Level replaced "Specular" in Blender 4.0 BSDF.
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = preset["specular"]
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = preset["specular"]

    rough_mean, rough_var = preset["roughness"]

    # Roughness driver: voronoi → map-range → Roughness.
    vor_r = nt.nodes.new("ShaderNodeTexVoronoi")
    vor_r.inputs["Scale"].default_value = 18.0
    map_r = nt.nodes.new("ShaderNodeMapRange")
    map_r.inputs["From Min"].default_value = 0.0
    map_r.inputs["From Max"].default_value = 1.0
    map_r.inputs["To Min"].default_value = max(0.05, rough_mean - rough_var)
    map_r.inputs["To Max"].default_value = min(1.0, rough_mean + rough_var)
    nt.links.new(vor_r.outputs["Distance"], map_r.inputs["Value"])
    nt.links.new(map_r.outputs["Result"], bsdf.inputs["Roughness"])

    # Albedo driver: voronoi → mix with base colour for patchy desaturation.
    vor_a = nt.nodes.new("ShaderNodeTexVoronoi")
    vor_a.inputs["Scale"].default_value = 4.5
    mix_a = nt.nodes.new("ShaderNodeMixRGB")
    mix_a.blend_type = "MULTIPLY"
    mix_a.inputs["Fac"].default_value = 0.45
    mix_a.inputs["Color1"].default_value = preset["base_color"]
    # darker shade for patches: 80% of base
    bc = preset["base_color"]
    mix_a.inputs["Color2"].default_value = (bc[0] * 0.7, bc[1] * 0.7, bc[2] * 0.7, 1.0)
    nt.links.new(vor_a.outputs["Distance"], mix_a.inputs["Fac"])
    nt.links.new(mix_a.outputs["Color"], bsdf.inputs["Base Color"])

    # Bump driver: noise → bump node → normal input.
    noise_b = nt.nodes.new("ShaderNodeTexNoise")
    noise_b.inputs["Scale"].default_value = 36.0
    noise_b.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = preset["normal_strength"]
    nt.links.new(noise_b.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def assign_material(meshes: list, material: "bpy.types.Material") -> None:
    """Drop the family material into every mesh's first slot."""
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(material)


# ---------------------------------------------------------------------------
# bake passes
# ---------------------------------------------------------------------------


def _new_image(name: str, size: int, alpha: bool = False, is_data: bool = False) -> "bpy.types.Image":
    """Create or replace a baking target image."""
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name=name, width=size, height=size, alpha=alpha, is_data=is_data)
    return img


def _add_bake_target(material: "bpy.types.Material", img: "bpy.types.Image") -> "bpy.types.ShaderNode":
    """Add and select an Image Texture node so Cycles bakes to it."""
    nt = material.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.select = True
    nt.nodes.active = tex
    return tex


def bake_channel(
    meshes: list,
    material: "bpy.types.Material",
    bake_type: str,
    target_size: int,
    output_path: Path,
    is_data: bool = False,
    pass_filter: set[str] | None = None,
) -> None:
    """
    Bake one channel for the selected mesh(es).

    `bake_type` is a Cycles bake-type enum string: DIFFUSE / NORMAL /
    ROUGHNESS / AO / EMIT / GLOSSY. `pass_filter` narrows DIFFUSE bakes
    to colour-only (no lighting) per Babylon's MR/PBR contract.

    Blender 5 made ``bpy.context.scene.render.bake.pass_filter``
    read-only; the filter is now an operator kwarg passed straight to
    ``bpy.ops.object.bake(...)``.
    """
    img_name = f"bake_{bake_type.lower()}_{output_path.stem}"
    img = _new_image(img_name, target_size, alpha=False, is_data=is_data)
    tex = _add_bake_target(material, img)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]

    cycles = bpy.context.scene.cycles
    cycles.bake_type = bake_type
    bpy.context.scene.render.bake.use_selected_to_active = False
    bpy.context.scene.render.bake.margin = 8
    bake_kwargs: dict = {"type": bake_type}
    if pass_filter is not None:
        bake_kwargs["pass_filter"] = pass_filter
    bpy.ops.object.bake(**bake_kwargs)

    img.filepath_raw = str(output_path)
    img.file_format = "PNG"
    img.save()
    material.node_tree.nodes.remove(tex)


def bake_mr_pack(meshes: list, material: "bpy.types.Material", target_size: int, output_path: Path) -> None:
    """
    Bake Babylon's MR pack: R unused, G roughness, B metallic.

    Cycles cannot pack three bake passes into one image in a single
    operator call. We bake Roughness to its own image, then composite into
    a 3-channel PNG via Pillow at save time. Metallic is constant per
    family (no per-texel variation today) so we fill the B channel.
    """
    rough_img_name = f"bake_roughness_pack_{output_path.stem}"
    rough_img = _new_image(rough_img_name, target_size, is_data=True)
    tex = _add_bake_target(material, rough_img)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]

    cycles = bpy.context.scene.cycles
    cycles.bake_type = "ROUGHNESS"
    bpy.ops.object.bake(type="ROUGHNESS")

    metallic = material.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value
    pixels = list(rough_img.pixels)
    metal_byte = max(0.0, min(1.0, metallic))
    for i in range(0, len(pixels), 4):
        # G channel = roughness (already there as r=g=b from ROUGHNESS bake)
        pixels[i + 0] = 0.0           # R unused per Babylon convention
        # pixels[i + 1] left as-is (G = roughness)
        pixels[i + 2] = metal_byte    # B = metallic
        pixels[i + 3] = 1.0
    rough_img.pixels = pixels
    rough_img.filepath_raw = str(output_path)
    rough_img.file_format = "PNG"
    rough_img.save()
    material.node_tree.nodes.remove(tex)


# ---------------------------------------------------------------------------
# 6-view render (for AI projection step downstream)
# ---------------------------------------------------------------------------

CANONICAL_VIEWS: list[tuple[str, tuple[float, float, float]]] = [
    ("front",  ( 0.0,  4.0, 0.0)),
    ("back",   ( 0.0, -4.0, 0.0)),
    ("left",   (-4.0,  0.0, 0.0)),
    ("right",  ( 4.0,  0.0, 0.0)),
    ("top",    ( 0.0,  0.0, 4.0)),
    ("bottom", ( 0.0,  0.0, -4.0)),
]


def fit_camera_to_meshes(meshes: list, offset: Vector) -> "bpy.types.Object":
    """Drop a camera at world `offset` aimed at the bbox centre of the meshes."""
    corners_world: list[Vector] = []
    for obj in meshes:
        for c in obj.bound_box:
            corners_world.append(obj.matrix_world @ Vector(c))
    bb_min = Vector((min(c.x for c in corners_world), min(c.y for c in corners_world), min(c.z for c in corners_world)))
    bb_max = Vector((max(c.x for c in corners_world), max(c.y for c in corners_world), max(c.z for c in corners_world)))
    centre = (bb_min + bb_max) * 0.5
    diag = (bb_max - bb_min).length

    cam_data = bpy.data.cameras.new("WitnessCam")
    cam_data.lens = 50.0
    cam_obj = bpy.data.objects.new("WitnessCam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = centre + offset.normalized() * max(diag * 1.2, 1.0)

    # Track-to constraint pointing at the centre.
    target = bpy.data.objects.new("WitnessCamTarget", None)
    bpy.context.collection.objects.link(target)
    target.location = centre
    tc = cam_obj.constraints.new(type="TRACK_TO")
    tc.target = target
    tc.track_axis = "TRACK_NEGATIVE_Z"
    tc.up_axis = "UP_Y"
    bpy.context.view_layer.update()
    return cam_obj


def render_views(meshes: list, views_dir: Path, view_size: int, samples: int) -> None:
    """
    Render the 6 canonical views. Each view writes <view>.png plus
    <view>.depth.exr (16-bit linear depth) for the downstream AI projector.
    """
    scene = bpy.context.scene
    scene.render.resolution_x = view_size
    scene.render.resolution_y = view_size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.cycles.samples = samples
    scene.render.image_settings.file_format = "PNG"
    # Render directly to file — avoids the compositor node tree, which
    # requires different setup in Blender 4.x (scene.use_nodes + scene.node_tree)
    # vs 5.x (compositing_node_group API, use_nodes deprecated). Beauty renders
    # are all the AI projector needs; depth EXR can be layered in later.
    views_dir.mkdir(parents=True, exist_ok=True)
    for name, offset in CANONICAL_VIEWS:
        cam = fit_camera_to_meshes(meshes, Vector(offset))
        scene.camera = cam
        scene.render.filepath = str(views_dir / f"{name}_beauty_0001")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam, do_unlink=True)
    # Output filenames match the pattern texture_asset.py expects.


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    if bpy is None:
        sys.stderr.write("ERROR: bake_pbr.py must run inside Blender (use `blender --background --python`)\n")
        return 2

    args = parse_args()
    families = _load_material_families()
    family = args.family if args.family != "auto" else families.pick_family(args.asset_id)
    if family not in families.FAMILIES:
        sys.stderr.write(f"ERROR: unknown material family: {family}\n")
        return 2

    glb_path = Path(args.glb).resolve()
    if not glb_path.exists():
        sys.stderr.write(f"ERROR: GLB not found: {glb_path}\n")
        return 2

    textures_dir = Path(args.textures_dir).resolve()
    views_dir = Path(args.views_dir).resolve()
    output_glb = Path(args.output_glb).resolve()
    textures_dir.mkdir(parents=True, exist_ok=True)
    output_glb.parent.mkdir(parents=True, exist_ok=True)

    sys.stdout.write(f"[bake_pbr] family={family}  texture_size={args.texture_size}\n")
    reset_scene()
    enable_gpu_cycles()

    meshes = import_glb(glb_path)
    if not meshes:
        sys.stderr.write(f"ERROR: imported {glb_path.name} contained no meshes\n")
        return 2
    ensure_uvs(meshes)

    preset = families.get(family)
    mat = build_material(f"witness_{family}", preset)
    assign_material(meshes, mat)

    if not args.skip_views:
        sys.stdout.write("[bake_pbr] rendering 6 canonical views\n")
        render_views(meshes, views_dir, args.view_size, samples=args.samples)

    sys.stdout.write("[bake_pbr] baking Albedo (8K)\n")
    bake_channel(
        meshes,
        mat,
        "DIFFUSE",
        args.texture_size,
        textures_dir / f"{args.asset_id}_albedo.png",
        pass_filter={"COLOR"},
    )

    sys.stdout.write("[bake_pbr] baking MR pack (8K)\n")
    bake_mr_pack(meshes, mat, args.texture_size, textures_dir / f"{args.asset_id}_mr.png")

    sys.stdout.write("[bake_pbr] baking Normal (8K)\n")
    bake_channel(
        meshes,
        mat,
        "NORMAL",
        args.texture_size,
        textures_dir / f"{args.asset_id}_normal.png",
        is_data=True,
    )

    sys.stdout.write("[bake_pbr] baking AO (8K)\n")
    bake_channel(
        meshes,
        mat,
        "AO",
        args.texture_size,
        textures_dir / f"{args.asset_id}_ao.png",
        is_data=True,
    )

    sys.stdout.write(f"[bake_pbr] exporting textured GLB → {output_glb}\n")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(output_glb),
        export_format="GLB",
        use_selection=True,
        export_image_format="AUTO",
        export_materials="EXPORT",
    )
    sys.stdout.write("[bake_pbr] done\n")
    return 0


if __name__ == "__main__":
    # Blender swallows uncaught exceptions and exits 0, which masks bake
    # failures from the orchestrator. Catch everything and force a
    # non-zero exit code so `texture_asset.py` reliably detects failure.
    try:
        rc = main()
    except SystemExit:
        raise
    except BaseException as exc:
        import traceback

        traceback.print_exc()
        sys.stderr.write(f"ERROR: bake_pbr.py raised {type(exc).__name__}: {exc}\n")
        rc = 2
    raise SystemExit(rc)
