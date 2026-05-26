/**
 * Barrel for `performance/`. Imports `engine/` only (ARCHITECTURE.md §5.10).
 */

export {
  detectProfile,
  applyProfile,
  runFreezePass,
  startSceneOptimizer,
  currentProfile,
} from "./PerformanceManager";

export { buildOptimizerOptions } from "./SceneOptimizerFactory";
