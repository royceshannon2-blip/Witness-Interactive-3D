/**
 * SceneOptimizerFactory
 *
 * Builds a `SceneOptimizerOptions` chain whose phases match
 * ARCHITECTURE.md §7.4: shadows → lens flares → post-fx → particles →
 * texture cap → hardware scaling. Cosmetic effects drop first; pixel
 * reduction is the last resort.
 *
 * The optimizer is started in default (degrade-only) mode so quality never
 * climbs back up mid-play — that would be visually distracting.
 */

import {
  HardwareScalingOptimization,
  LensFlaresOptimization,
  ParticlesOptimization,
  PostProcessesOptimization,
  SceneOptimizerOptions,
  ShadowsOptimization,
  TextureOptimization,
} from "@babylonjs/core";
import { type PerformanceProfile } from "../engine/config";

/**
 * Returns a `SceneOptimizerOptions` configured for the given profile. The
 * target FPS is drawn from `engineConfig[profile].targetFps` indirectly —
 * we hardcode 30 for LOW, 60 otherwise to match ARCHITECTURE.md §7.4.
 */
export function buildOptimizerOptions(profile: PerformanceProfile): SceneOptimizerOptions {
  const targetFps = profile === "low" ? 30 : 60;
  const opts = new SceneOptimizerOptions(targetFps, 3000);

  // Phase 0: cosmetic — cheap visual loss for big perf wins.
  opts.optimizations.push(new ShadowsOptimization(0));
  opts.optimizations.push(new LensFlaresOptimization(0));

  // Phase 1: post-fx — disables grain, bloom, vignette.
  opts.optimizations.push(new PostProcessesOptimization(1));
  opts.optimizations.push(new ParticlesOptimization(1));

  // Phase 2: drop largest texture mips. 512 on LOW, 1024 elsewhere.
  opts.optimizations.push(new TextureOptimization(2, profile === "low" ? 512 : 1024));

  // Phase 3: last-resort pixel reduction.
  opts.optimizations.push(new HardwareScalingOptimization(3, profile === "low" ? 2 : 1.5));

  return opts;
}
