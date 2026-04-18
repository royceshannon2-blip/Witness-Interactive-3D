/**
 * LayerMasks
 *
 * Bit-flag constants used to tag every mesh and light in the scene with
 * the era(s) it belongs to. The TimeManager flips the active camera's
 * `layerMask` to show one era and hide the other without swapping scenes.
 *
 * See `docs/design-docs/TIMELINE_SYNC.md` and `ARCHITECTURE.md §4`.
 *
 * Contract:
 *   - Every mesh in the scene is tagged with exactly one era scope:
 *     Present, Past, or Shared.
 *   - Camera.layerMask at runtime is always (active_era | SHARED).
 *   - Shared geometry (terrain, sky, era-agnostic landmarks) is visible
 *     in both eras.
 */

import type { AbstractMesh, Light, TransformNode } from "@babylonjs/core";

/** Layer bit for 2026 Present-era meshes (ruins, overgrowth, weathered). */
export const LAYER_PRESENT = 0x10000000;

/** Layer bit for 1994 Past-era meshes (intact, populated, saturated). */
export const LAYER_PAST = 0x20000000;

/** Layer bit for era-agnostic meshes (terrain, sky, cross-era landmarks). */
export const LAYER_SHARED = 0x40000000;

/** Mask matching every Chronos layer. Useful for cameras that render all eras (e.g., editor preview). */
export const LAYER_ALL = LAYER_PRESENT | LAYER_PAST | LAYER_SHARED;

/**
 * Era scope a mesh or light belongs to.
 *
 * - `"present"` — visible only when the active era is Present.
 * - `"past"`    — visible only when the active era is Past.
 * - `"shared"`  — visible in both eras.
 */
export type EraScope = "present" | "past" | "shared";

/** Map from EraScope → the layer bit pattern a tagged node should carry. */
export const ERA_SCOPE_MASK: Record<EraScope, number> = {
  present: LAYER_PRESENT,
  past: LAYER_PAST,
  shared: LAYER_SHARED,
};

/**
 * Camera-side layer masks. Given an active era, the camera must render that
 * era's meshes plus everything tagged Shared.
 */
export const CAMERA_MASK_PRESENT = LAYER_PRESENT | LAYER_SHARED;
export const CAMERA_MASK_PAST = LAYER_PAST | LAYER_SHARED;

/**
 * Tag a mesh (or TransformNode root, which propagates to children) with the
 * bit pattern matching the given era scope. Overwrites any prior mask.
 *
 * @param node  Mesh or TransformNode to tag.
 * @param scope Era scope to apply.
 */
export function tagNode(node: AbstractMesh | TransformNode, scope: EraScope): void {
  const mask = ERA_SCOPE_MASK[scope];
  // AbstractMesh has layerMask directly; TransformNode needs it set on children.
  if ("layerMask" in node) {
    (node as AbstractMesh).layerMask = mask;
  }
  const children = node.getChildMeshes?.(false) ?? [];
  for (const child of children) {
    child.layerMask = mask;
  }
}

/**
 * Tag a light with the given era scope. Babylon lights use `includeOnlyWithLayerMask`
 * and `excludeWithLayerMask` to gate which meshes they affect — we use
 * `includeOnlyWithLayerMask` so the light only illuminates meshes of the matching era.
 *
 * For Shared lights, set to 0 (disabled gate → affects everything).
 */
export function tagLight(light: Light, scope: EraScope): void {
  if (scope === "shared") {
    light.includeOnlyWithLayerMask = 0;
  } else {
    light.includeOnlyWithLayerMask = ERA_SCOPE_MASK[scope];
  }
}
