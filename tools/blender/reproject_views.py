"""
reproject_views.py — Stage 2c: UV-reproject AI view maps onto mesh UV.

Runs INSIDE Blender via:
    blender --background --factory-startup \\
        --python tools/blender/reproject_views.py -- \\
        --glb processed/glb/<id>.textured.glb \\
        --asset-id <id> \\
        --views-dir processed/views/<id> \\
        --textures-dir processed/textures/<id> \\
        --output-glb processed/glb/<id>.textured.glb \\
        --texture-size 4096 \\
        --samples 32

Algorithm:
  For each canonical view that has a .pbr.png file:
    1. Compute perspective-projected UVs for the view's camera position.
    2. Bake a facing-weight mask: dot(world_normal, view_direction), clamped 0-1.
    3. Bake the .pbr.png colour using the projected UV into the primary UV space.
  Blend all view bakes weighted by their facing masks (numpy).
  Save result as <asset_id>_albedo.ai.png, wire into a Principled BSDF material, re-export GLB.

Exit codes:
  0  success
  2  failure (GLB missing, no .pbr.png files, bake error)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
    import numpy as np
except ImportError:
    bpy = None  # type: ignore[assignment]
    Vector = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CANONICAL_VIEWS = [
    ("front",  ( 0, -1,  0)),
    ("back",   ( 0,  1,  0)),
    ("left",   (-1,  0,  0)),
    ("right",  ( 1,  0,  0)),
    ("top",    ( 0,  0,  1)),
    ("bottom", ( 0,  0, -1)),
]


# ---------------------------------------------------------------------------
# arg parsing
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True)
    p.add_argument("--asset-id", required=True)
    p.add_argument("--views-dir", required=True)
    p.add_argument("--textures-dir", required=True)
    p.add_argument("--output-glb", required=True)
    p.add_argument("--texture-size", type=int, default=4096)
    p.add_argument("--samples", type=int, default=32)
    p.add_argument(
        "--detail-view",
        default="",
        help="Canonical view name (front/back/left/right/top/bottom) whose "
             "<view>.detail.pbr.png is re-projected at higher blend priority.",
    )
    p.add_argument(
        "--detail-weight",
        type=float,
        default=2.5,
        help="Blend-weight multiplier for the detail view (wins its region).",
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# scene / render helpers
# ---------------------------------------------------------------------------


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for block in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras,
                  bpy.data.materials, bpy.data.images, bpy.data.objects):
        for item in list(block):
            try:
                block.remove(item)
            except Exception:
                pass


def enable_gpu_cycles(samples: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = samples
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
    except Exception:
        pass


def import_glb(path: Path) -> list:
    before = set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o.name not in before and o.type == "MESH"]


def _new_image(name: str, size: int, alpha: bool = False, is_data: bool = False) -> "bpy.types.Image":
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    return bpy.data.images.new(name=name, width=size, height=size, alpha=alpha, is_data=is_data)


# ---------------------------------------------------------------------------
# camera helpers (mirrored from bake_pbr.py for self-containment)
# ---------------------------------------------------------------------------


def _mesh_bounds(meshes: list) -> tuple[Vector, float]:
    """Return (center, radius) of the bounding sphere enclosing all meshes."""
    lo = Vector((float("inf"),) * 3)
    hi = Vector((float("-inf"),) * 3)
    for obj in meshes:
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    center = (lo + hi) / 2
    radius = max(((obj.matrix_world @ Vector(c)) - center).length
                 for obj in meshes for c in obj.bound_box)
    return center, max(radius, 0.01)


def make_camera(meshes: list, offset: tuple) -> "bpy.types.Object":
    """Create a perspective camera aimed at the mesh center from offset direction."""
    center, radius = _mesh_bounds(meshes)
    offset_v = Vector(offset).normalized()
    cam_pos = center + offset_v * (radius * 2.5)

    bpy.ops.object.camera_add(location=cam_pos)
    cam_obj = bpy.context.active_object
    cam_obj.data.type = "PERSP"
    cam_obj.data.lens = 35

    direction = (center - cam_pos).normalized()
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    return cam_obj


# ---------------------------------------------------------------------------
# UV projection
# ---------------------------------------------------------------------------


def project_uvs(obj: "bpy.types.Object", cam_obj: "bpy.types.Object",
                uv_layer_name: str, render_size: int) -> None:
    """
    Add a UV layer to obj where each loop UV = perspective projection under cam_obj.

    The projection uses cam_obj.calc_matrix_camera so it exactly matches what
    Blender rendered when bake_pbr.py produced the view images.
    """
    me = obj.data
    if uv_layer_name in me.uv_layers:
        me.uv_layers.remove(me.uv_layers[uv_layer_name])
    uv_layer = me.uv_layers.new(name=uv_layer_name)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    proj_mat = cam_obj.calc_matrix_camera(
        depsgraph,
        x=render_size,
        y=render_size,
        scale_x=scene.render.pixel_aspect_x,
        scale_y=scene.render.pixel_aspect_y,
    )
    full_mat = proj_mat @ cam_obj.matrix_world.inverted()

    for loop in me.loops:
        v_co = me.vertices[loop.vertex_index].co
        v_clip = full_mat @ (obj.matrix_world @ v_co.to_4d())
        w = v_clip.w
        if abs(w) > 1e-8:
            u = v_clip.x / w * 0.5 + 0.5
            v = v_clip.y / w * 0.5 + 0.5
        else:
            u, v = 0.5, 0.5
        uv_layer.data[loop.index].uv = (u, v)


# ---------------------------------------------------------------------------
# material builders
# ---------------------------------------------------------------------------


def _clear_mat(mat: "bpy.types.Material") -> "bpy.types.NodeTree":
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return nt


def build_facing_mask_mat(view_dir: tuple) -> "bpy.types.Material":
    """
    Emit material whose per-pixel brightness = dot(world_normal, view_dir) clamped 0-1.
    Baking this gives a grayscale mask: bright = facing camera, black = backface.
    """
    mat = bpy.data.materials.new(name="_facing_mask")
    nt = _clear_mat(mat)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (1, 1, 1, 1)

    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"

    clamp = nt.nodes.new("ShaderNodeClamp")
    clamp.inputs["Min"].default_value = 0.0
    clamp.inputs["Max"].default_value = 1.0

    geo = nt.nodes.new("ShaderNodeNewGeometry")

    vdir = nt.nodes.new("ShaderNodeCombineXYZ")
    vdir.inputs["X"].default_value = float(view_dir[0])
    vdir.inputs["Y"].default_value = float(view_dir[1])
    vdir.inputs["Z"].default_value = float(view_dir[2])

    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    nt.links.new(vdir.outputs["Vector"], dot.inputs[1])
    nt.links.new(dot.outputs["Value"], clamp.inputs["Value"])
    nt.links.new(clamp.outputs["Result"], emit.inputs["Strength"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def build_proj_emit_mat(pbr_img: "bpy.types.Image", proj_uv_name: str) -> "bpy.types.Material":
    """Emit material that samples pbr_img via the projected UV layer."""
    mat = bpy.data.materials.new(name="_proj_emit")
    nt = _clear_mat(mat)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = pbr_img
    uv_map = nt.nodes.new("ShaderNodeUVMap")
    uv_map.uv_map = proj_uv_name

    nt.links.new(uv_map.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def wire_final_material(mat: "bpy.types.Material",
                        albedo_path: Path, mr_path: Path, normal_path: Path) -> None:
    """Wire baked maps into a Principled BSDF for GLB export."""
    nt = _clear_mat(mat)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    def _tex(path: Path, is_data: bool = False) -> "bpy.types.ShaderNode":
        img = bpy.data.images.load(str(path))
        img.colorspace_settings.name = "Non-Color" if is_data else "sRGB"
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        return node

    alb = _tex(albedo_path)
    nt.links.new(alb.outputs["Color"], bsdf.inputs["Base Color"])

    mr = _tex(mr_path, is_data=True)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(mr.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])

    nrm = _tex(normal_path, is_data=True)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nrm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])


# ---------------------------------------------------------------------------
# baking
# ---------------------------------------------------------------------------


def _set_bake_target(mat: "bpy.types.Material", img: "bpy.types.Image") -> "bpy.types.ShaderNode":
    nt = mat.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.select = True
    nt.nodes.active = tex
    return tex


def bake_emit(meshes: list, mat: "bpy.types.Material",
              target_img: "bpy.types.Image") -> None:
    """Bake EMIT from mat → target_img using the active UV layer for output coords."""
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(mat)

    bake_node = _set_bake_target(mat, target_img)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]

    bpy.ops.object.bake(type="EMIT")
    mat.node_tree.nodes.remove(bake_node)


def bake_view_projection(
    meshes: list,
    scene: "bpy.types.Scene",
    view_dir: tuple,
    pbr_path: Path,
    size: int,
    uv_tag: str,
) -> "tuple[np.ndarray, np.ndarray]":
    """
    Project one stage-2b ``.pbr.png`` onto the mesh from ``view_dir`` and bake
    both its colour and a facing-weight mask into primary-UV space.

    Returns ``(color_rgba, mask_rgba)`` as (size,size,4) float32 arrays for the
    caller to blend. Shared by the six canonical views and the optional hero
    detail view so the projection maths stays in one place.
    """
    cam = make_camera(meshes, view_dir)
    scene.camera = cam
    bpy.context.view_layer.update()

    proj_uv = f"_proj_{uv_tag}"
    for obj in meshes:
        project_uvs(obj, cam, proj_uv, size)
        if obj.data.uv_layers:
            obj.data.uv_layers.active_index = 0

    # --- facing-weight mask ---
    mask_img = _new_image(f"_mask_{uv_tag}", size, is_data=True)
    mask_mat = build_facing_mask_mat(view_dir)
    bake_emit(meshes, mask_mat, mask_img)
    mask_np = img_to_np(mask_img, size)
    bpy.data.materials.remove(mask_mat)
    bpy.data.images.remove(mask_img)

    # --- colour bake from .pbr.png via projected UV ---
    pbr_img = bpy.data.images.load(str(pbr_path))
    pbr_img.colorspace_settings.name = "sRGB"
    color_img = _new_image(f"_color_{uv_tag}", size)
    color_mat = build_proj_emit_mat(pbr_img, proj_uv)
    bake_emit(meshes, color_mat, color_img)
    color_np = img_to_np(color_img, size)
    bpy.data.materials.remove(color_mat)
    bpy.data.images.remove(color_img)
    bpy.data.images.remove(pbr_img)

    for obj in meshes:
        if proj_uv in obj.data.uv_layers:
            obj.data.uv_layers.remove(obj.data.uv_layers[proj_uv])
    bpy.data.objects.remove(cam, do_unlink=True)
    return color_np, mask_np


def _save_gray_mask(mask: "np.ndarray", size: int, dest: Path) -> None:
    """Write a (size,size) float/bool coverage mask out as a grayscale PNG."""
    g = np.clip(mask.astype(np.float32), 0.0, 1.0)
    img = _new_image(f"{dest.stem}_cov", size, is_data=True)
    rgba = np.ones((size, size, 4), dtype=np.float32)
    rgba[:, :, 0] = g
    rgba[:, :, 1] = g
    rgba[:, :, 2] = g
    img.pixels[:] = rgba.ravel().tolist()
    img.filepath_raw = str(dest)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


# ---------------------------------------------------------------------------
# numpy blend
# ---------------------------------------------------------------------------


def img_to_np(img: "bpy.types.Image", size: int) -> "np.ndarray":
    """Return (size, size, 4) float32 RGBA array from a Blender image."""
    return np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4)


def _pull_push_fill(color: "np.ndarray", known: "np.ndarray", eps: float = 1e-6) -> "np.ndarray":
    """
    Fill unknown texels by pyramid pull-push interpolation from known texels.

    This is the "fill missing areas" step: the six orthographic views cannot
    see concavities, undersides, or deep folds, so some texels are covered by
    no view. Rather than leave a hard seam (flat procedural albedo where the
    AI-projected material stops), we smoothly interpolate the AI-projected
    colour of the nearest covered neighbours into the holes.

    `color` is (H, W, 3) float32; `known` is (H, W) bool (True = covered).
    Returns a fully-filled (H, W, 3). Pure numpy, O(N) via a Gaussian/box
    pyramid (Gortler pull-push). Assumes power-of-two texture sizes (8192 /
    4096); odd rows/cols at a level are cropped on pull and edge-padded on
    push so non-power-of-two inputs still complete without error.
    """
    col = color.astype(np.float32).copy()
    conf = known.astype(np.float32)
    col[conf <= 0.0] = 0.0

    cols = [col]
    confs = [conf]

    # PULL — build the pyramid by confidence-weighted 2x2 averaging.
    while min(cols[-1].shape[0], cols[-1].shape[1]) > 1:
        c = cols[-1]
        k = confs[-1]
        h, w = k.shape
        h2, w2 = h - (h % 2), w - (w % 2)
        c, k = c[:h2, :w2], k[:h2, :w2]
        k00, k10 = k[0::2, 0::2], k[1::2, 0::2]
        k01, k11 = k[0::2, 1::2], k[1::2, 1::2]
        wsum = k00 + k10 + k01 + k11
        csum = (
            c[0::2, 0::2] * k00[..., None] + c[1::2, 0::2] * k10[..., None]
            + c[0::2, 1::2] * k01[..., None] + c[1::2, 1::2] * k11[..., None]
        )
        cols.append(csum / np.maximum(wsum, eps)[..., None])
        confs.append(np.clip(wsum * 0.25, 0.0, 1.0))

    # PUSH — upsample coarse levels into the holes of finer levels.
    for lvl in range(len(cols) - 1, 0, -1):
        coarse = cols[lvl]
        fine_c, fine_k = cols[lvl - 1], confs[lvl - 1]
        fh, fw = fine_c.shape[:2]
        up = np.repeat(np.repeat(coarse, 2, axis=0), 2, axis=1)[:fh, :fw]
        if up.shape[0] < fh or up.shape[1] < fw:
            up = np.pad(up, ((0, fh - up.shape[0]), (0, fw - up.shape[1]), (0, 0)), mode="edge")
        a = fine_k[..., None]
        cols[lvl - 1] = a * fine_c + (1.0 - a) * up
        confs[lvl - 1] = np.ones_like(fine_k)

    return cols[0]


def blend_views(
    color_bakes: list,   # [(size,size,4)] RGBA per view
    mask_bakes: list,    # [(size,size,4)] grayscale (R channel = weight)
    size: int,
    fallback_np: "np.ndarray | None" = None,
    weights: "list[float] | None" = None,
) -> "tuple[np.ndarray, np.ndarray]":
    """
    Facing-weighted average of colour bakes, with the hero detail view (if
    any) carrying a >1 weight so it wins inside the region it covers.

    Texels covered by at least one view are the weighted mean. Texels covered
    by none are filled by pull-push interpolation from the covered ones
    (`_pull_push_fill`) so there is no style seam. Only when *nothing* is
    covered do we fall back to the procedural albedo.

    Returns ``(rgb (size,size,3) float32, coverage (size,size) bool)``.
    """
    if weights is None:
        weights = [1.0] * len(color_bakes)

    accum = np.zeros((size, size, 3), dtype=np.float32)
    weight = np.zeros((size, size), dtype=np.float32)
    for color, mask, wmul in zip(color_bakes, mask_bakes, weights):
        w = np.clip(mask[:, :, 0], 0.0, 1.0) * float(wmul)
        accum += color[:, :, :3] * w[:, :, np.newaxis]
        weight += w

    valid = weight > 1e-6
    result = np.zeros((size, size, 3), dtype=np.float32)
    result[valid] = accum[valid] / weight[valid, np.newaxis]

    if not valid.all():
        if valid.any():
            result = _pull_push_fill(result, valid)
        elif fallback_np is not None:
            result = fallback_np[:, :, :3].astype(np.float32).copy()

    return result, valid


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    if bpy is None:
        sys.stderr.write("ERROR: reproject_views.py must run inside Blender\n")
        return 2

    args = parse_args()
    glb_path = Path(args.glb).resolve()
    views_dir = Path(args.views_dir).resolve()
    textures_dir = Path(args.textures_dir).resolve()
    output_glb = Path(args.output_glb).resolve()
    size = args.texture_size

    if not glb_path.exists():
        sys.stderr.write(f"ERROR: GLB not found: {glb_path}\n")
        return 2

    # Only process views that have .pbr.png output from stage 2b
    available = {
        name: views_dir / f"{name}.pbr.png"
        for name, _ in CANONICAL_VIEWS
        if (views_dir / f"{name}.pbr.png").exists()
    }
    if not available:
        sys.stderr.write(f"ERROR: no .pbr.png files found in {views_dir}\n")
        return 2
    sys.stdout.write(f"[reproject] {len(available)}/6 AI view maps: {list(available)}\n")

    reset_scene()
    enable_gpu_cycles(args.samples)

    scene = bpy.context.scene
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100

    meshes = import_glb(glb_path)
    if not meshes:
        sys.stderr.write(f"ERROR: no meshes in {glb_path}\n")
        return 2

    # Ensure primary UV (index 0) is active — this is the output UV space for baking
    for obj in meshes:
        if obj.data.uv_layers:
            obj.data.uv_layers.active_index = 0

    # Load procedural albedo as fallback for uncovered pixels
    fallback_path = textures_dir / f"{args.asset_id}_albedo.png"
    fallback_np = None
    if fallback_path.exists():
        fb = bpy.data.images.load(str(fallback_path))
        fallback_np = img_to_np(fb, size)
        bpy.data.images.remove(fb)

    color_bakes: list = []
    mask_bakes: list = []
    blend_weights: list = []

    for view_name, view_dir in CANONICAL_VIEWS:
        pbr_path = available.get(view_name)
        if not pbr_path:
            sys.stdout.write(f"[reproject] skip {view_name} (no .pbr.png)\n")
            continue
        sys.stdout.write(f"[reproject] view: {view_name}\n")
        color_np, mask_np = bake_view_projection(
            meshes, scene, view_dir, pbr_path, size, view_name
        )
        color_bakes.append(color_np)
        mask_bakes.append(mask_np)
        blend_weights.append(1.0)

    # Hero detail pass (stage 2b-detail): re-project one canonical view at a
    # higher blend weight so a face / hands keep their fidelity instead of
    # being averaged down by the adjacent low-detail views.
    if args.detail_view:
        view_map = dict(CANONICAL_VIEWS)
        detail_pbr = views_dir / f"{args.detail_view}.detail.pbr.png"
        if args.detail_view not in view_map:
            sys.stdout.write(
                f"[reproject] detail-view '{args.detail_view}' is not canonical — skipping\n"
            )
        elif not detail_pbr.exists():
            sys.stdout.write(
                f"[reproject] detail pass skipped — {detail_pbr.name} not found\n"
            )
        else:
            sys.stdout.write(
                f"[reproject] detail view '{args.detail_view}' (weight x{args.detail_weight})\n"
            )
            color_np, mask_np = bake_view_projection(
                meshes, scene, view_map[args.detail_view], detail_pbr, size,
                f"detail_{args.detail_view}",
            )
            color_bakes.append(color_np)
            mask_bakes.append(mask_np)
            blend_weights.append(float(args.detail_weight))

    if not color_bakes:
        sys.stderr.write("ERROR: all views failed to bake — nothing to blend\n")
        return 2

    sys.stdout.write(f"[reproject] blending {len(color_bakes)} view(s)…\n")
    blended, coverage = blend_views(
        color_bakes, mask_bakes, size, fallback_np, weights=blend_weights
    )

    # Diagnostic + future generative-inpaint hook: white = ≥1 view covered the
    # texel, black = filled by pull-push interpolation.
    cov_path = textures_dir / f"{args.asset_id}_coverage.png"
    _save_gray_mask(coverage, size, cov_path)
    sys.stdout.write(
        f"[reproject] coverage {100.0 * float(coverage.mean()):.1f}% "
        f"(pull-push filled the rest) → {cov_path.name}\n"
    )

    # Save AI albedo PNG
    ai_albedo_path = textures_dir / f"{args.asset_id}_albedo.ai.png"
    ai_img = _new_image(f"{args.asset_id}_ai_albedo", size)
    rgba = np.ones((size, size, 4), dtype=np.float32)
    rgba[:, :, :3] = blended
    ai_img.pixels[:] = rgba.ravel().tolist()
    ai_img.filepath_raw = str(ai_albedo_path)
    ai_img.file_format = "PNG"
    ai_img.save()
    sys.stdout.write(f"[reproject] saved AI albedo → {ai_albedo_path.name}\n")

    # Wire AI albedo + existing MR + normal maps into a fresh material
    mat = bpy.data.materials.new(name=f"witness_{args.asset_id}_ai")
    mat.use_nodes = True
    wire_final_material(
        mat,
        albedo_path=ai_albedo_path,
        mr_path=textures_dir / f"{args.asset_id}_mr.png",
        normal_path=textures_dir / f"{args.asset_id}_normal.png",
    )
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(mat)

    # Export GLB with AI-projected albedo
    output_glb.parent.mkdir(parents=True, exist_ok=True)
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
    sys.stdout.write(f"[reproject] exported → {output_glb.name}\n")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except SystemExit:
        raise
    except BaseException:
        import traceback
        traceback.print_exc()
        sys.exit(2)
    sys.exit(rc)
