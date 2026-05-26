/**
 * Barrel export for `engine/`.
 *
 * The engine subsystem owns Babylon scene lifecycle, rendering pipeline,
 * materials, and physics. It imports nothing from elsewhere in the app
 * (ARCHITECTURE.md §5.3).
 */

export { createBaseScene } from "./SceneFactory";
export type { SceneInit } from "./SceneFactory";

export { buildPresentRig, buildPastRig } from "./Lighting";
export type { LightingRig } from "./Lighting";

export { RenderingPipeline } from "./RenderingPipeline";
export type { EraProfile } from "./RenderingPipeline";

export { MaterialLibrary } from "./Materials";
export type { MaterialId } from "./Materials";

export {
  init as initPhysics,
  aggregate as makeAggregate,
  freezeAggregate,
  thawAggregate,
  dispose as disposePhysics,
  getPlugin as getPhysicsPlugin,
} from "./Physics";
export type { AggregateOptions } from "./Physics";

export { engineConfig, worldConstants } from "./config";
export type { PerformanceProfile, EngineProfile } from "./config";
