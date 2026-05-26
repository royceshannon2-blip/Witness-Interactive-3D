/**
 * Lighting
 *
 * Builds the three-light rig used in both eras: sun (DirectionalLight),
 * sky/fill (HemisphericLight), and storm rim (DirectionalLight).
 *
 * Per RENDERING.md §4 and CHRONOS_SWITCH.md §3.5: lights are duplicated per
 * era, not animated. Each rig is tagged via `tagLight(light, scope)` and
 * culled with `includeOnlyWithLayerMask`.
 *
 * This module returns the rig — caller is responsible for tagging, shadow
 * generation, and per-era selection. Tagging is deliberately decoupled so
 * world/ can decide which mode (present/past/shared) each rig represents.
 */

import {
  Color3,
  DirectionalLight,
  HemisphericLight,
  ShadowGenerator,
  Vector3,
} from "@babylonjs/core";
import type { Scene } from "@babylonjs/core";
import { engineConfig, type PerformanceProfile } from "./config";

export interface LightingRig {
  sun: DirectionalLight;
  sky: HemisphericLight;
  stormRim: DirectionalLight;
  /** Shadow generator attached to the sun. Only present on MEDIUM/HIGH profiles. */
  shadowGenerator: ShadowGenerator | null;
}

/**
 * Build the Present-era rig: cool blue-grey overcast light. Values mirror
 * RENDERING.md §4.1 (Present sun) and §4.2 (sky fill).
 */
export function buildPresentRig(scene: Scene, profile: PerformanceProfile): LightingRig {
  const sun = new DirectionalLight("sunPresent", new Vector3(-0.4, -0.9, -0.15), scene);
  sun.diffuse = Color3.FromHSV(210, 0.08, 0.95);
  sun.specular = new Color3(0.2, 0.2, 0.22);
  sun.intensity = 0.6;
  sun.position = new Vector3(20, 60, -30);

  const sky = new HemisphericLight("skyPresent", new Vector3(0, 1, 0), scene);
  sky.intensity = 0.95;
  sky.diffuse = new Color3(0.78, 0.8, 0.82);
  sky.groundColor = new Color3(0.32, 0.24, 0.18);
  sky.specular = new Color3(0.05, 0.05, 0.05);

  const stormRim = new DirectionalLight("stormRimPresent", new Vector3(0.6, -0.3, -1), scene);
  stormRim.intensity = 0.16;
  stormRim.diffuse = new Color3(0.55, 0.58, 0.7);
  stormRim.specular = new Color3(0.04, 0.04, 0.06);

  return { sun, sky, stormRim, shadowGenerator: makeShadowGen(sun, profile) };
}

/**
 * Build the Past-era rig: warmer afternoon sun (1994 April).
 * Values mirror RENDERING.md §4.1 (Past sun).
 */
export function buildPastRig(scene: Scene, profile: PerformanceProfile): LightingRig {
  const sun = new DirectionalLight("sunPast", new Vector3(-0.18, -1, 0.3), scene);
  sun.diffuse = new Color3(0.98, 0.94, 0.84);
  sun.specular = new Color3(0.18, 0.16, 0.14);
  sun.intensity = 0.85;
  sun.position = new Vector3(20, 60, -30);

  const sky = new HemisphericLight("skyPast", new Vector3(0, 1, 0), scene);
  sky.intensity = 1.05;
  sky.diffuse = new Color3(0.86, 0.82, 0.74);
  sky.groundColor = new Color3(0.4, 0.22, 0.12);
  sky.specular = new Color3(0.06, 0.06, 0.06);

  const stormRim = new DirectionalLight("stormRimPast", new Vector3(0.5, -0.4, -0.9), scene);
  stormRim.intensity = 0.12;
  stormRim.diffuse = new Color3(0.7, 0.55, 0.45);
  stormRim.specular = new Color3(0.04, 0.03, 0.02);

  return { sun, sky, stormRim, shadowGenerator: makeShadowGen(sun, profile) };
}

/**
 * Construct a PCSS shadow generator on the sun. Per CLAUDE.md "PCSS only" —
 * no PCF. LOW profile skips shadows entirely (returns null).
 */
function makeShadowGen(sun: DirectionalLight, profile: PerformanceProfile): ShadowGenerator | null {
  if (profile === "low") return null;
  const cfg = engineConfig[profile];
  const gen = new ShadowGenerator(cfg.shadowMapSize, sun);
  gen.usePercentageCloserFiltering = true;
  gen.filteringQuality = ShadowGenerator.QUALITY_HIGH;
  gen.bias = 0.0008;
  gen.normalBias = 0.018;
  return gen;
}
