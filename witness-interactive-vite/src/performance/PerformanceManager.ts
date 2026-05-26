/**
 * PerformanceManager
 *
 * Detects hardware tier at boot, applies engine-level settings, runs the
 * one-shot freeze pass on static content, and starts the SceneOptimizer.
 *
 * Per ARCHITECTURE.md §5.10 + §6 + §7. The order of operations is fixed:
 *   1. detectProfile (boot)
 *   2. applyProfile (engine + scene tweaks before the first build)
 *   3. runFreezePass (after world content is in scene; once per mission)
 *   4. startSceneOptimizer (after freeze pass)
 *
 * Profile detection follows ARCHITECTURE.md §6.1 priority:
 *   1. ?perf=low|medium|high query param.
 *   2. localStorage 'witness:perfProfile'.
 *   3. navigator.deviceMemory / hardwareConcurrency / WebGL 1 heuristics.
 *
 * The §6.1 step 4 ("FPS probe on a throwaway scene") is intentionally
 * deferred — it's a 200 ms boot delay, and the heuristics are good enough
 * for the first scaffolding pass. Add it before shipping.
 */

import { AbstractMesh, SceneOptimizer } from "@babylonjs/core";
import type { Engine, Scene } from "@babylonjs/core";
import { engineConfig, type PerformanceProfile } from "../engine/config";
import { buildOptimizerOptions } from "./SceneOptimizerFactory";

const STORAGE_KEY = "witness:perfProfile";

let activeProfile: PerformanceProfile = "medium";

/**
 * Decide the hardware tier. Pure read of environment + navigator. Idempotent.
 * Logs the decision to `console.info` so users can tell why their settings
 * came out the way they did.
 */
export function detectProfile(): PerformanceProfile {
  const fromQuery = readQueryParam();
  if (fromQuery) {
    activeProfile = fromQuery;
    console.info(`[perf] profile from ?perf=: ${fromQuery}`);
    return fromQuery;
  }
  const fromStorage = readLocalStorage();
  if (fromStorage) {
    activeProfile = fromStorage;
    console.info(`[perf] profile from localStorage: ${fromStorage}`);
    return fromStorage;
  }
  const fromHeuristics = heuristicProfile();
  activeProfile = fromHeuristics;
  console.info(`[perf] profile from heuristics: ${fromHeuristics}`);
  return fromHeuristics;
}

/**
 * Apply the profile's engine settings. Call once after `engine` is created
 * and before the first scene is built.
 */
export function applyProfile(engine: Engine, profile: PerformanceProfile): void {
  activeProfile = profile;
  const cfg = engineConfig[profile];
  engine.setHardwareScalingLevel(cfg.hardwareScalingLevel);
  engine.disableManifestCheck = true;
}

/**
 * One-shot freeze pass per ARCHITECTURE.md §7.1. Walks every mesh, freezing
 * world matrices, marking always-active, locking material uniforms, and
 * flipping scene-level guards (skipPointerMovePicking, blockMaterialDirty).
 *
 * Skips meshes flagged `metadata.interactive = true` (fragments, dynamic
 * physics bodies). Skips materials flagged `metadata.dynamic = true`
 * (water, animated shaders).
 *
 * Idempotent within a mission: re-running is harmless. Call once per
 * `missionReady`.
 */
export function runFreezePass(scene: Scene): void {
  for (const mesh of scene.meshes) {
    if (mesh.metadata?.interactive) continue;
    mesh.freezeWorldMatrix();
    mesh.alwaysSelectAsActiveMesh = true;
    mesh.doNotSyncBoundingInfo = true;
    mesh.cullingStrategy = AbstractMesh.CULLINGSTRATEGY_BOUNDINGSPHERE_ONLY;
    const mat = mesh.material;
    if (mat && !mat.metadata?.dynamic && !mat.isFrozen) {
      mat.freeze();
    }
  }
  scene.freezeActiveMeshes();
  scene.skipPointerMovePicking = true;
  scene.blockMaterialDirtyMechanism = true;
}

/**
 * Start the SceneOptimizer with the profile's degradation chain. Returns the
 * optimizer so the caller can stop it manually if needed.
 */
export function startSceneOptimizer(scene: Scene, profile: PerformanceProfile): SceneOptimizer {
  const options = buildOptimizerOptions(profile);
  const optimizer = new SceneOptimizer(scene, options, true /* autoGeneratePriorities */);
  optimizer.start();
  return optimizer;
}

/** Current tier. */
export function currentProfile(): PerformanceProfile {
  return activeProfile;
}

// ---------------------------------------------------------------------------

function readQueryParam(): PerformanceProfile | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  const v = params.get("perf");
  if (v === "low" || v === "medium" || v === "high") return v;
  return null;
}

function readLocalStorage(): PerformanceProfile | null {
  if (typeof window === "undefined") return null;
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    if (v === "low" || v === "medium" || v === "high") return v;
  } catch {
    // Storage may be disabled (incognito, classroom kiosk lockdown).
  }
  return null;
}

function heuristicProfile(): PerformanceProfile {
  if (typeof navigator === "undefined") return "medium";
  const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory;
  const cores = navigator.hardwareConcurrency ?? 0;
  if (memory !== undefined && memory < 4) return "low";
  if (cores > 0 && cores <= 4) return "low";
  if (memory !== undefined && memory < 8) return "medium";
  if (cores <= 8) return "medium";
  return "high";
}
