/**
 * Engine configuration constants, keyed by performance profile.
 *
 * Per ARCHITECTURE.md §10.1, per-environment constants live here as a frozen
 * object. The runtime selects a profile via `performance.detectProfile()` and
 * reads from `engineConfig[profile]`. Dev-only tunables go behind
 * `import.meta.env.DEV`.
 *
 * Never mutate these at runtime. Clone-and-tweak if a one-off override is
 * needed in tests.
 */

/** The three target hardware tiers. See ARCHITECTURE.md §6. */
export type PerformanceProfile = "low" | "medium" | "high";

export interface EngineProfile {
  /** Hardware scaling factor passed to `engine.setHardwareScalingLevel`. */
  hardwareScalingLevel: number;
  /** Target frames per second for the SceneOptimizer. */
  targetFps: number;
  /** Shadow-map side resolution in pixels. */
  shadowMapSize: number;
  /** Maximum simultaneous active audio voices. */
  maxAudioVoices: number;
  /** Per-mission asset VRAM budget in megabytes. */
  assetVramBudgetMb: number;
  /** Maximum dynamic Havok aggregates. Excess registrations fall back to static. */
  dynamicPhysicsBodyCap: number;
  /** Whether to enable SSAO2 in the pipeline. */
  enableSsao: boolean;
  /** Whether to enable bloom in the pipeline. */
  enableBloom: boolean;
  /** Whether to enable film grain in the pipeline. */
  enableGrain: boolean;
  /** Whether to enable sharpen + vignette in the pipeline. */
  enableFinishingFx: boolean;
}

/**
 * Per-profile engine settings. Values follow ARCHITECTURE.md §6 exactly.
 * Frozen so accidental writes throw in dev.
 */
export const engineConfig: Readonly<Record<PerformanceProfile, Readonly<EngineProfile>>> =
  Object.freeze({
    low: Object.freeze({
      hardwareScalingLevel: 1.5,
      targetFps: 30,
      shadowMapSize: 1024,
      maxAudioVoices: 8,
      assetVramBudgetMb: 200,
      dynamicPhysicsBodyCap: 10,
      enableSsao: false,
      enableBloom: false,
      enableGrain: false,
      enableFinishingFx: false,
    }),
    medium: Object.freeze({
      hardwareScalingLevel: 1.0,
      targetFps: 60,
      shadowMapSize: 2048,
      maxAudioVoices: 12,
      assetVramBudgetMb: 500,
      dynamicPhysicsBodyCap: 20,
      enableSsao: true,
      enableBloom: true,
      enableGrain: true,
      enableFinishingFx: false,
    }),
    high: Object.freeze({
      hardwareScalingLevel: 1.0,
      targetFps: 60,
      shadowMapSize: 2048,
      maxAudioVoices: 16,
      assetVramBudgetMb: 800,
      dynamicPhysicsBodyCap: 30,
      enableSsao: true,
      enableBloom: true,
      enableGrain: true,
      enableFinishingFx: true,
    }),
  });

/**
 * World-space constants that don't change per profile. Frozen.
 *
 * Gravity is real — the prototype's `-9.81 * 0.06` magic factor is rejected
 * per audit §7. Camera-bob fixes belong in the PlayerController.
 */
export const worldConstants = Object.freeze({
  /** Real Earth gravity, m/s². */
  gravityY: -9.81,
  /** Default fog start density (exp2). Bisesero is humid; tune per location. */
  fogDensityDefault: 0.012,
  /** Bisesero April overcast — cool blue-grey, NOT the prototype's warm tan. */
  fogColorPresent: { r: 0.62, g: 0.66, b: 0.7 },
  /** 1994 April afternoon — warmer, slightly hazier. */
  fogColorPast: { r: 0.7, g: 0.66, b: 0.58 },
  /** Player eye height in metres. */
  playerEyeHeight: 1.65,
  /** Default camera near plane. */
  cameraMinZ: 0.08,
  /** Default camera far plane (overridable per location). */
  cameraMaxZ: 240,
});
