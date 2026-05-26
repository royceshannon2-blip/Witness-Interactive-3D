/**
 * RenderingPipeline
 *
 * Wraps `DefaultRenderingPipeline` with project-defaults: ACES tone-mapping,
 * FXAA, optional SSAO2, optional bloom + grain + sharpen + vignette per
 * profile.
 *
 * Per RENDERING.md §5 and CHRONOS_SWITCH.md §3.4: a single pipeline is
 * attached to the gameplay camera. Per-era differences are applied via
 * `setEraProfile(era)` — the same pipeline, retuned coefficients.
 *
 * The HUD ortho camera (see ARCHITECTURE.md §10) is NOT in this pipeline;
 * the HUD has no post-fx by design.
 *
 * Two animated transition methods drive era switches:
 *   - `fadeToEra(era, durationSec)` — smooth lerp of exposure / contrast /
 *     vignette. The "graded look" that lasts after the transition completes.
 *   - `memoryDissolve(durationSec)` — symmetric burst of chromatic aberration
 *     + grain that peaks at midpoint and falls back to baseline. Triggered in
 *     parallel with `fadeToEra` to give the era flip a perceptible "moment of
 *     dissociation" matching the Chronos transition register
 *     (CHRONOS_SWITCH.md §3.6).
 */

import {
  DefaultRenderingPipeline,
  ImageProcessingConfiguration,
  Observer,
  SSAO2RenderingPipeline,
} from "@babylonjs/core";
import type { Camera, Scene } from "@babylonjs/core";
import { engineConfig, type PerformanceProfile } from "./config";

export type EraProfile = "present" | "past";

/** Per-era post-fx coefficients per CHRONOS_SWITCH.md §3.4. */
const ERA_COEFF: Record<EraProfile, { exposure: number; contrast: number; vignetteWeight: number }> = {
  present: { exposure: 0.95, contrast: 1.0, vignetteWeight: 1.6 },
  past: { exposure: 1.08, contrast: 1.12, vignetteWeight: 0.8 },
};

/** Peak chromatic-aberration amount reached at transition midpoint. */
const DISSOLVE_PEAK_ABERRATION = 22;
/** Peak grain intensity reached at transition midpoint (only if grain is on). */
const DISSOLVE_PEAK_GRAIN = 14;
/** Baseline grain intensity restored after the dissolve completes. */
const BASELINE_GRAIN = 4;

/**
 * The pipeline owns its `DefaultRenderingPipeline` and (optionally) an
 * `SSAO2RenderingPipeline`. Both are disposed via `dispose()`.
 */
export class RenderingPipeline {
  readonly defaultPipeline: DefaultRenderingPipeline;
  readonly ssao: SSAO2RenderingPipeline | null;
  private readonly scene: Scene;
  private fadeObs: Observer<Scene> | null = null;
  private dissolveObs: Observer<Scene> | null = null;
  private currentEra: EraProfile = "present";

  private constructor(scene: Scene, default_: DefaultRenderingPipeline, ssao: SSAO2RenderingPipeline | null) {
    this.scene = scene;
    this.defaultPipeline = default_;
    this.ssao = ssao;
  }

  /**
   * Attach the pipeline to a scene + gameplay camera. Idempotent only at the
   * scope of one `RenderingPipeline` instance — calling twice on the same
   * scene leaks. Caller is responsible for `dispose()` on teardown.
   *
   * @param scene   Scene the pipeline observes.
   * @param camera  Gameplay (perspective) camera. Do NOT pass the HUD camera.
   * @param profile Hardware profile — toggles SSAO/bloom/finishing fx.
   */
  static attach(scene: Scene, camera: Camera, profile: PerformanceProfile): RenderingPipeline {
    const cfg = engineConfig[profile];
    const pipe = new DefaultRenderingPipeline("witness-default", true, scene, [camera]);

    pipe.fxaaEnabled = true;
    pipe.samples = 1;

    pipe.imageProcessing.toneMappingEnabled = true;
    pipe.imageProcessing.toneMappingType = ImageProcessingConfiguration.TONEMAPPING_ACES;
    pipe.imageProcessing.contrast = 1.05;
    pipe.imageProcessing.exposure = 1.0;

    pipe.bloomEnabled = cfg.enableBloom;
    if (cfg.enableBloom) {
      pipe.bloomThreshold = 0.92;
      pipe.bloomWeight = 0.18;
      pipe.bloomKernel = 64;
      pipe.bloomScale = 0.5;
    }

    pipe.grainEnabled = cfg.enableGrain;
    if (cfg.enableGrain) {
      pipe.grain.intensity = BASELINE_GRAIN;
      pipe.grain.animated = true;
    }

    // Chromatic aberration — disabled at rest, momentarily ramped up during
    // an era transition (memoryDissolve). Always armed so we can toggle the
    // amount without re-allocating the post-process every transition.
    pipe.chromaticAberrationEnabled = true;
    pipe.chromaticAberration.aberrationAmount = 0;
    pipe.chromaticAberration.radialIntensity = 0.5;

    if (cfg.enableFinishingFx) {
      pipe.sharpenEnabled = true;
      pipe.sharpen.edgeAmount = 0.18;
      pipe.imageProcessing.vignetteEnabled = true;
      pipe.imageProcessing.vignetteWeight = 1.4;
    }

    let ssao: SSAO2RenderingPipeline | null = null;
    if (cfg.enableSsao) {
      ssao = new SSAO2RenderingPipeline("witness-ssao", scene, 1.0, [camera]);
      ssao.radius = 1.4;
      ssao.totalStrength = 0.85;
      ssao.expensiveBlur = profile === "high";
      ssao.samples = profile === "high" ? 16 : 8;
      ssao.maxZ = 80;
    }

    const wrapper = new RenderingPipeline(scene, pipe, ssao);
    wrapper.setEraProfile("present");
    return wrapper;
  }

  /**
   * Snap the post-fx coefficients to the given era. Use for boot and for
   * zero-duration transitions; for animated era changes call `fadeToEra`.
   */
  setEraProfile(era: EraProfile): void {
    this.currentEra = era;
    const ip = this.defaultPipeline.imageProcessing;
    const coeff = ERA_COEFF[era];
    ip.colorCurvesEnabled = true;
    ip.exposure = coeff.exposure;
    ip.contrast = coeff.contrast;
    if (ip.vignetteEnabled) ip.vignetteWeight = coeff.vignetteWeight;
  }

  /**
   * Lerp from the current era's coefficients to `target` over `durationSec`.
   * Re-entrant: a second call cancels the first and re-anchors from the
   * current frame's interpolated values, so back-to-back fades stay smooth.
   *
   * Drives Babylon's frame observer rather than `setTimeout` so the fade
   * stays in sync with `engine.runRenderLoop` regardless of FPS jitter.
   */
  fadeToEra(target: EraProfile, durationSec: number): Promise<void> {
    if (durationSec <= 0 || target === this.currentEra) {
      this.setEraProfile(target);
      return Promise.resolve();
    }

    if (this.fadeObs) {
      this.scene.onBeforeRenderObservable.remove(this.fadeObs);
      this.fadeObs = null;
    }

    const ip = this.defaultPipeline.imageProcessing;
    const from = { exposure: ip.exposure, contrast: ip.contrast, vignetteWeight: ip.vignetteWeight };
    const to = ERA_COEFF[target];
    const start = performance.now();
    const durationMs = durationSec * 1000;

    return new Promise<void>((resolve) => {
      this.fadeObs = this.scene.onBeforeRenderObservable.add(() => {
        const t = Math.min(1, (performance.now() - start) / durationMs);
        const eased = t * t * (3 - 2 * t); // ease-in-out cubic — CHRONOS_SWITCH §3.6
        ip.exposure = from.exposure + (to.exposure - from.exposure) * eased;
        ip.contrast = from.contrast + (to.contrast - from.contrast) * eased;
        if (ip.vignetteEnabled) {
          ip.vignetteWeight = from.vignetteWeight + (to.vignetteWeight - from.vignetteWeight) * eased;
        }
        if (t >= 1 && this.fadeObs) {
          this.scene.onBeforeRenderObservable.remove(this.fadeObs);
          this.fadeObs = null;
          this.currentEra = target;
          resolve();
        }
      });
    });
  }

  /**
   * Burst chromatic aberration + grain symmetrically over `durationSec`.
   * Peaks at midpoint, returns to baseline at end. Independent of `fadeToEra`
   * — call both with the same duration to drive a "memory dissolve" feel.
   *
   * Re-entrant: a second call cancels the first. Grain stays clamped to the
   * profile's grain-enabled state (if grain is off on LOW profile, only the
   * chromatic-aberration arm of the dissolve fires).
   */
  memoryDissolve(durationSec: number): Promise<void> {
    if (durationSec <= 0) {
      this.defaultPipeline.chromaticAberration.aberrationAmount = 0;
      if (this.defaultPipeline.grainEnabled) {
        this.defaultPipeline.grain.intensity = BASELINE_GRAIN;
      }
      return Promise.resolve();
    }

    if (this.dissolveObs) {
      this.scene.onBeforeRenderObservable.remove(this.dissolveObs);
      this.dissolveObs = null;
    }

    const ca = this.defaultPipeline.chromaticAberration;
    const grain = this.defaultPipeline.grain;
    const grainOn = this.defaultPipeline.grainEnabled;
    const start = performance.now();
    const durationMs = durationSec * 1000;

    return new Promise<void>((resolve) => {
      this.dissolveObs = this.scene.onBeforeRenderObservable.add(() => {
        const t = Math.min(1, (performance.now() - start) / durationMs);
        // Symmetric envelope: 4t(1-t) peaks at t=0.5 with value 1.
        const env = 4 * t * (1 - t);
        // Ease the envelope so the peak holds a moment instead of spiking.
        const eased = env * env * (3 - 2 * env);
        ca.aberrationAmount = DISSOLVE_PEAK_ABERRATION * eased;
        if (grainOn) {
          grain.intensity = BASELINE_GRAIN + (DISSOLVE_PEAK_GRAIN - BASELINE_GRAIN) * eased;
        }
        if (t >= 1 && this.dissolveObs) {
          this.scene.onBeforeRenderObservable.remove(this.dissolveObs);
          this.dissolveObs = null;
          ca.aberrationAmount = 0;
          if (grainOn) grain.intensity = BASELINE_GRAIN;
          resolve();
        }
      });
    });
  }

  dispose(): void {
    if (this.fadeObs) {
      this.scene.onBeforeRenderObservable.remove(this.fadeObs);
      this.fadeObs = null;
    }
    if (this.dissolveObs) {
      this.scene.onBeforeRenderObservable.remove(this.dissolveObs);
      this.dissolveObs = null;
    }
    this.defaultPipeline.dispose();
    this.ssao?.dispose();
  }
}
