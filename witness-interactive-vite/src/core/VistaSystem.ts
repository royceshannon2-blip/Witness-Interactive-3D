/**
 * VistaSystem
 *
 * Detects when the player stands still near a designated vista anchor and
 * plays a location-specific narrator reflection. Analogous to RDR2's vistas
 * where stopping at a high point triggers ambient character commentary.
 *
 * Stillness heuristic: camera position delta < STILL_THRESHOLD_M per frame
 * for DWELL_REQUIRED_SEC consecutive seconds.
 *
 * Per session: each vista fires narrator once per session regardless of how
 * many times the player returns to that spot. The narration is soft —
 * player is still in full control and can walk away mid-sentence.
 *
 * Architecture: subscribes one `onBeforeRenderObservable` observer while
 * attached; no game-state writes. Calls `audioManager.playNarratorEntry()`
 * which respects the narrator queue in NarratorSystem once that is wired.
 */

import type { Observer, Scene, UniversalCamera } from "@babylonjs/core";
import { Vector3 } from "@babylonjs/core";
import { audioManager } from "../audio/AudioManager";

const STILL_THRESHOLD_M = 0.08;   // metres of movement allowed per frame
const DWELL_REQUIRED_SEC = 5.0;   // seconds of stillness before trigger

export interface VistaDef {
  /** Unique ID — used to track session-fired state. */
  id: string;
  /** World-space position of this vista's trigger sphere centre. */
  position: Vector3;
  /** Trigger radius in metres. */
  radius: number;
  /** Narrator audio key played when the player dwells here. */
  narratorKey: string;
}

class VistaSystemImpl {
  private vistas: VistaDef[] = [];
  private scene: Scene | null = null;
  private camera: UniversalCamera | null = null;
  private obs: Observer<Scene> | null = null;

  private lastCamPos: Vector3 | null = null;
  private dwellingSince: number | null = null;
  private activeVista: VistaDef | null = null;
  private readonly fired = new Set<string>();

  /** Register one vista. Safe to call before `attach()`. */
  register(def: VistaDef): void {
    this.vistas.push(def);
  }

  /**
   * Start the per-frame probe. Call after the scene and camera are ready.
   * Idempotent — a second call replaces the previous observer.
   */
  attach(scene: Scene, camera: UniversalCamera): void {
    this.detach();
    this.scene = scene;
    this.camera = camera;
    this.lastCamPos = camera.position.clone();

    this.obs = scene.onBeforeRenderObservable.add(() => this._tick());
  }

  /** Stop probing. Safe to call without a prior `attach`. */
  detach(): void {
    if (this.obs && this.scene) {
      this.scene.onBeforeRenderObservable.remove(this.obs);
      this.obs = null;
    }
    this.scene = null;
    this.camera = null;
    this.lastCamPos = null;
    this.dwellingSince = null;
    this.activeVista = null;
  }

  // ---------------------------------------------------------------------------

  private _tick(): void {
    const cam = this.camera;
    if (!cam || this.vistas.length === 0) return;

    const pos = cam.position;
    const prev = this.lastCamPos ?? pos.clone();
    const delta = Vector3.Distance(pos, prev);
    this.lastCamPos = pos.clone();

    const isStill = delta < STILL_THRESHOLD_M;

    // Find closest eligible vista.
    const nearVista = this._nearestUnfiredVista(pos);

    if (!nearVista) {
      // Left all vista radii — reset dwell.
      this.dwellingSince = null;
      this.activeVista = null;
      return;
    }

    if (nearVista !== this.activeVista) {
      // Entered a new vista radius — start dwell clock fresh.
      this.activeVista = nearVista;
      this.dwellingSince = null;
    }

    if (!isStill) {
      // Player moved — reset dwell timer.
      this.dwellingSince = null;
      return;
    }

    const now = performance.now() / 1000;
    if (this.dwellingSince === null) {
      this.dwellingSince = now;
      return;
    }

    if (now - this.dwellingSince >= DWELL_REQUIRED_SEC) {
      // Dwell threshold reached — fire narrator once.
      this.fired.add(nearVista.id);
      audioManager.playNarratorEntry(nearVista.narratorKey);
      // Remove from active so it doesn't re-trigger this session.
      this.activeVista = null;
      this.dwellingSince = null;
    }
  }

  private _nearestUnfiredVista(pos: Vector3): VistaDef | null {
    let best: VistaDef | null = null;
    let bestDist = Infinity;
    for (const v of this.vistas) {
      if (this.fired.has(v.id)) continue;
      const d = Vector3.Distance(pos, v.position);
      if (d <= v.radius && d < bestDist) {
        best = v;
        bestDist = d;
      }
    }
    return best;
  }
}

/** App-wide singleton — one vista system for the whole session. */
export const vistaSystem = new VistaSystemImpl();
