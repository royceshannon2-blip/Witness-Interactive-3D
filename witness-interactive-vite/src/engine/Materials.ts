/**
 * Materials
 *
 * Shared PBRMaterial library. Per RENDERING.md §3 and CLAUDE.md "no
 * StandardMaterial." Every world surface references a material by name; no
 * world module is permitted to instantiate a `PBRMaterial` ad-hoc.
 *
 * Variant policy (RENDERING.md §3.3): one base material, cloned per era.
 * Cloning happens at location load time — never per frame.
 *
 * Freeze policy (RENDERING.md §3.2): every base material is frozen at
 * registration. Cloning before freeze is fine; mutating after freeze is not.
 *
 * v1 implementation: this scaffold ships only solid-colour starting points
 * matching the prototype's PBR palette (audit §3 row "PBR material starting
 * values"). Texture loading lands when the asset pipeline ships KTX2 maps;
 * the IDs and signatures are fixed now so callers can refer by name today.
 */

import { Color3, PBRMaterial } from "@babylonjs/core";
import type { Scene } from "@babylonjs/core";

export type MaterialId =
  | "mat_laterite"
  | "mat_brick_mud"
  | "mat_brick_fired"
  | "mat_concrete_weathered"
  | "mat_tin_roof"
  | "mat_eucalyptus_bark"
  | "mat_eucalyptus_leaf"
  | "mat_matooke_leaf"
  | "mat_grass_tall"
  | "mat_cloth_white"
  | "mat_cloth_kitenge"
  | "mat_wood_weathered"
  | "mat_metal_jerrycan"
  | "mat_water_lake";

interface MaterialSeed {
  albedo: Color3;
  roughness: number;
  metallic: number;
  /** Anisotropic filter level — set to 16 for ground/façades per CLAUDE.md. */
  anisotropy: number;
}

const seeds: Record<MaterialId, MaterialSeed> = {
  mat_laterite: { albedo: new Color3(0.48, 0.16, 0.06), roughness: 0.85, metallic: 0.0, anisotropy: 16 },
  mat_brick_mud: { albedo: new Color3(0.5, 0.32, 0.22), roughness: 0.9, metallic: 0.0, anisotropy: 16 },
  mat_brick_fired: { albedo: new Color3(0.62, 0.32, 0.24), roughness: 0.75, metallic: 0.0, anisotropy: 16 },
  mat_concrete_weathered: { albedo: new Color3(0.7, 0.69, 0.66), roughness: 0.8, metallic: 0.0, anisotropy: 16 },
  mat_tin_roof: { albedo: new Color3(0.55, 0.25, 0.18), roughness: 0.6, metallic: 0.8, anisotropy: 16 },
  mat_eucalyptus_bark: { albedo: new Color3(0.58, 0.5, 0.42), roughness: 0.85, metallic: 0.0, anisotropy: 4 },
  mat_eucalyptus_leaf: { albedo: new Color3(0.32, 0.45, 0.22), roughness: 0.7, metallic: 0.0, anisotropy: 4 },
  mat_matooke_leaf: { albedo: new Color3(0.34, 0.5, 0.18), roughness: 0.7, metallic: 0.0, anisotropy: 4 },
  mat_grass_tall: { albedo: new Color3(0.38, 0.46, 0.22), roughness: 0.75, metallic: 0.0, anisotropy: 16 },
  mat_cloth_white: { albedo: new Color3(0.92, 0.9, 0.86), roughness: 0.9, metallic: 0.0, anisotropy: 4 },
  mat_cloth_kitenge: { albedo: new Color3(0.74, 0.36, 0.14), roughness: 0.85, metallic: 0.0, anisotropy: 4 },
  mat_wood_weathered: { albedo: new Color3(0.36, 0.28, 0.2), roughness: 0.85, metallic: 0.0, anisotropy: 4 },
  mat_metal_jerrycan: { albedo: new Color3(0.85, 0.7, 0.18), roughness: 0.4, metallic: 0.1, anisotropy: 4 },
  mat_water_lake: { albedo: new Color3(0.16, 0.22, 0.26), roughness: 0.18, metallic: 0.0, anisotropy: 4 },
};

/**
 * Library facade. Build once at scene init, then read by world modules.
 *
 * Use:
 *   const lib = MaterialLibrary.build(scene);
 *   ground.material = lib.get("mat_laterite");
 */
export class MaterialLibrary {
  private readonly cache = new Map<MaterialId, PBRMaterial>();
  private readonly scene: Scene;

  private constructor(scene: Scene) {
    this.scene = scene;
  }

  /**
   * Construct and freeze the full library against `scene`.
   * Frozen at registration time per RENDERING.md §3.2.
   */
  static build(scene: Scene): MaterialLibrary {
    const lib = new MaterialLibrary(scene);
    for (const id of Object.keys(seeds) as MaterialId[]) {
      lib.cache.set(id, lib.makeOne(id));
    }
    return lib;
  }

  /**
   * Look up a material by ID. Throws if the ID was never registered, since
   * world modules typing against `MaterialId` should never miss.
   */
  get(id: MaterialId): PBRMaterial {
    const mat = this.cache.get(id);
    if (!mat) throw new Error(`Material '${id}' not in library — was MaterialLibrary.build() called?`);
    return mat;
  }

  /**
   * Clone a base material for a per-era variant. The clone is mutable until
   * the caller freezes it. Per RENDERING.md §3.3, era variants are cloned at
   * location-load time, never per frame.
   */
  cloneForVariant(id: MaterialId, variantSuffix: string): PBRMaterial {
    const base = this.get(id);
    const clone = base.clone(`${id}__${variantSuffix}`);
    if (!clone) throw new Error(`Failed to clone material '${id}'`);
    return clone;
  }

  private makeOne(id: MaterialId): PBRMaterial {
    const seed = seeds[id];
    const mat = new PBRMaterial(id, this.scene);
    mat.albedoColor = seed.albedo;
    mat.metallic = seed.metallic;
    mat.roughness = seed.roughness;
    mat.ambientColor = new Color3(0.05, 0.05, 0.05);
    mat.useAmbientOcclusionFromMetallicTextureRed = true;
    mat.useRoughnessFromMetallicTextureGreen = true;
    mat.useMetallnessFromMetallicTextureBlue = true;
    mat.freeze();
    return mat;
  }
}
