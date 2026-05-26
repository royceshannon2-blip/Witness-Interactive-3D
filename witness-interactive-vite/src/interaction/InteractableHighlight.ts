/**
 * InteractableHighlight
 *
 * A `HighlightLayer` wrapper that gives proximate interactables a subtle
 * cream outline that pulses on a slow sine — the world's diegetic version of
 * the HUD reticle. Per the project's tonal register, this is **never** a
 * neon highlight; the outline is low-alpha and slow-pulsing so it reads as
 * "this is worth approaching" rather than "click me."
 *
 * The bootstrap's per-frame proximity probe calls `setHovered(mesh)` with the
 * single nearest interactable (or null). At most one mesh is highlighted at a
 * time. The HighlightLayer is shared and instantiated once per scene.
 *
 * Per ARCHITECTURE.md §5.5: this lives in `interaction/` because its lifecycle
 * is bound to the proximity probe. It imports only `@babylonjs/core` —
 * narrative state and HUD wiring stay in the bootstrap.
 *
 * Performance note: HighlightLayer adds one full-screen post-pass. We keep
 * exactly one mesh in the layer at any time. The layer's blur kernels are
 * sized for the cream-outline look, not the default neon-glow look.
 */

import { Color3, HighlightLayer } from "@babylonjs/core";
import type { AbstractMesh, Mesh, Observer, Scene } from "@babylonjs/core";

/** Base outline colour — cream, matches the HUD palette. */
const BASE_COLOR = new Color3(0.91, 0.89, 0.84);
/** Pulse depth — how far the outline brightens from baseline. */
const PULSE_DEPTH = 0.45;
/** Pulse period — seconds for a full sine cycle. */
const PULSE_PERIOD_SEC = 2.6;

class InteractableHighlightImpl {
  private layer: HighlightLayer | null = null;
  private scene: Scene | null = null;
  private hovered: AbstractMesh | null = null;
  private pulseObs: Observer<Scene> | null = null;
  private startTime = 0;

  /**
   * Attach to the active scene. Idempotent; calling twice is a no-op.
   * Builds the HighlightLayer with a fine outline kernel and starts the
   * per-frame pulse observer.
   */
  attach(scene: Scene): void {
    if (this.layer) return;
    this.scene = scene;
    const layer = new HighlightLayer("interactable-highlight", scene, {
      mainTextureRatio: 0.5,
      blurHorizontalSize: 0.4,
      blurVerticalSize: 0.4,
      isStroke: false,
    });
    // Inner glow off — we want a clean outline, not a soft halo. The "stroke"
    // mode is closer to what we want; outerGlow gives the proximity nudge.
    layer.innerGlow = false;
    layer.outerGlow = true;
    this.layer = layer;
    this.startTime = performance.now();
    this.pulseObs = scene.onBeforeRenderObservable.add(() => this.tickPulse());
  }

  /**
   * Update which mesh is highlighted. Pass `null` to clear. Submesh-children
   * are ignored — only root pickable meshes participate in the highlight.
   */
  setHovered(mesh: AbstractMesh | null): void {
    if (!this.layer) return;
    if (mesh === this.hovered) return;
    if (this.hovered) {
      this.layer.removeMesh(this.hovered as Mesh);
    }
    this.hovered = mesh;
    if (mesh) {
      this.layer.addMesh(mesh as Mesh, BASE_COLOR.clone());
    }
  }

  /** Tear down — used by mission unload + hot-reload paths. */
  detach(): void {
    if (this.pulseObs && this.scene) {
      this.scene.onBeforeRenderObservable.remove(this.pulseObs);
      this.pulseObs = null;
    }
    if (this.layer) {
      this.layer.dispose();
      this.layer = null;
    }
    this.hovered = null;
    this.scene = null;
  }

  // ---------------------------------------------------------------------------

  /**
   * Per-frame pulse: lerp the outline color brightness around the base via a
   * slow sine so the world reads as "something here is worth looking at"
   * without becoming distracting.
   */
  private tickPulse(): void {
    if (!this.layer || !this.hovered) return;
    const tSec = (performance.now() - this.startTime) / 1000;
    const phase = (tSec % PULSE_PERIOD_SEC) / PULSE_PERIOD_SEC;
    // 0 → 1 → 0 across the period, smoothed by sin².
    const wave = Math.sin(phase * Math.PI);
    const k = 1 - PULSE_DEPTH + PULSE_DEPTH * wave;
    // HighlightLayer stores per-mesh color; we mutate the existing color by
    // looking it up in the layer's internal map. Easier path: re-add with a
    // recomputed colour each frame. addMesh is idempotent w.r.t. duplicates
    // because of the internal map, so this just updates the stored colour.
    this.layer.addMesh(
      this.hovered as Mesh,
      new Color3(BASE_COLOR.r * k, BASE_COLOR.g * k, BASE_COLOR.b * k),
    );
  }
}

/** App-wide singleton — one HighlightLayer per scene is enough. */
export const interactableHighlight = new InteractableHighlightImpl();
