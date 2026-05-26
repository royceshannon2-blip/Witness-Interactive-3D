/**
 * CinematicDirector
 *
 * Multi-beat, multi-track sequencer that builds on the primitives in
 * `AnimationDirector`. Runs ordered `Beat[]` sequences where each beat
 * maps to a specific camera, audio, overlay, or control action.
 *
 * A `parallel` beat runs all child beats simultaneously and resolves when
 * the longest child completes — allowing camera motion + audio + text to
 * happen in sync without nesting.
 *
 * Sequences are skippable via Escape. `prefers-reduced-motion` disables
 * camera movement beats (waits still run so audio isn't cut).
 *
 * Architecture note: CinematicDirector is a tool, not a singleton. The
 * caller (bootstrap/main.ts, bootstrap/BreatherSequences.ts) constructs
 * it once, holds it, and calls `play()` for each sequence.
 */

import { KeyboardEventTypes, Vector3 } from "@babylonjs/core";
import type { Observer, KeyboardInfo, Scene, UniversalCamera } from "@babylonjs/core";
import {
  cameraDolly,
  cameraApproach,
  fovTween,
  softEase,
  waitFrames,
} from "./AnimationDirector";
import type { DollyTarget } from "./AnimationDirector";
import { audioManager } from "../audio/AudioManager";

// ---------------------------------------------------------------------------
// Beat types

export interface CameraDollyBeat {
  type: "camera-dolly";
  to: DollyTarget;
  durationSec: number;
}

export interface CameraApproachBeat {
  type: "camera-approach";
  anchor: Vector3;
  pullMag: number;
  durationSec: number;
}

export interface FovBeat {
  type: "fov";
  targetFov: number;
  durationSec: number;
}

export interface AudioPlayBeat {
  type: "audio-play";
  /** Key passed to `audioManager.playNarratorEntry()`. */
  key: string;
}

export interface AudioEffectBeat {
  type: "audio-effect";
  key: string;
  position?: Vector3;
}

export interface WaitBeat {
  type: "wait";
  seconds: number;
}

export interface OverlayTextBeat {
  type: "overlay-text";
  text: string;
  /** Additional CSS class name applied to the overlay element. */
  styleClass?: string;
  /** Fade-in duration in seconds. Default 0.5. */
  fadeInSec?: number;
}

export interface OverlayHideBeat {
  type: "overlay-hide";
  /** Fade-out duration in seconds. Default 0.5. */
  fadeOutSec?: number;
}

export interface ControlLockBeat {
  type: "control-lock";
}

export interface ControlUnlockBeat {
  type: "control-unlock";
}

/** Runs all child beats in parallel; resolves when the longest one finishes. */
export interface ParallelBeat {
  type: "parallel";
  beats: Beat[];
}

export type Beat =
  | CameraDollyBeat
  | CameraApproachBeat
  | FovBeat
  | AudioPlayBeat
  | AudioEffectBeat
  | WaitBeat
  | OverlayTextBeat
  | OverlayHideBeat
  | ControlLockBeat
  | ControlUnlockBeat
  | ParallelBeat;

// ---------------------------------------------------------------------------

const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export class CinematicDirector {
  private readonly scene: Scene;
  private readonly camera: UniversalCamera;

  private skipRequested = false;
  private inputLocked = false;
  private kbObs: Observer<KeyboardInfo> | null = null;
  private overlayEl: HTMLElement | null = null;

  constructor(scene: Scene, camera: UniversalCamera) {
    this.scene = scene;
    this.camera = camera;
  }

  /**
   * Execute a sequence of beats. Resolves when all beats complete (or when
   * the player presses Escape to skip). Safe to `await` in a longer boot
   * chain — will not block the Babylon render loop.
   */
  async play(beats: Beat[]): Promise<void> {
    this.skipRequested = false;
    this._registerEscapeListener();
    try {
      await this._runSequence(beats);
    } finally {
      this._removeEscapeListener();
      // Always restore input if the sequence locked it.
      if (this.inputLocked) this._doUnlock();
      // Always hide any lingering overlay.
      this._hideOverlayImmediate();
    }
  }

  dispose(): void {
    this._removeEscapeListener();
    this._hideOverlayImmediate();
    if (this.inputLocked) this._doUnlock();
  }

  // ---------------------------------------------------------------------------

  private async _runSequence(beats: Beat[]): Promise<void> {
    for (const beat of beats) {
      if (this.skipRequested) break;
      await this._executeBeat(beat);
    }
  }

  private async _executeBeat(beat: Beat): Promise<void> {
    if (this.skipRequested) return;
    switch (beat.type) {
      case "camera-dolly":
        if (!REDUCED_MOTION) {
          await cameraDolly(this.scene, this.camera, beat.to, {
            durationSec: beat.durationSec,
          });
        } else {
          // Snap to end position without animation.
          this.camera.position.copyFrom(beat.to.position);
        }
        break;

      case "camera-approach":
        if (!REDUCED_MOTION) {
          await cameraApproach(
            this.scene,
            this.camera,
            beat.anchor,
            beat.pullMag,
            beat.durationSec,
          );
        }
        break;

      case "fov":
        if (!REDUCED_MOTION) {
          await fovTween(this.scene, this.camera, beat.targetFov, beat.durationSec, softEase());
        } else {
          this.camera.fov = beat.targetFov;
        }
        break;

      case "audio-play":
        audioManager.playNarratorEntry(beat.key);
        break;

      case "audio-effect":
        audioManager.playEffect(
          beat.key,
          beat.position ? { x: beat.position.x, y: beat.position.y, z: beat.position.z } : undefined,
        );
        break;

      case "wait":
        await waitFrames(this.scene, beat.seconds);
        break;

      case "overlay-text":
        this._showOverlayText(beat.text, beat.styleClass, beat.fadeInSec ?? 0.5);
        break;

      case "overlay-hide":
        await this._hideOverlay(beat.fadeOutSec ?? 0.5);
        break;

      case "control-lock":
        this._doLock();
        break;

      case "control-unlock":
        this._doUnlock();
        break;

      case "parallel":
        await Promise.all(beat.beats.map((b) => this._executeBeat(b)));
        break;
    }
  }

  // ---------------------------------------------------------------------------
  // Input control

  private _doLock(): void {
    if (this.inputLocked) return;
    this.inputLocked = true;
    const canvas = this.scene.getEngine().getRenderingCanvas();
    if (canvas) this.camera.detachControl();
  }

  private _doUnlock(): void {
    if (!this.inputLocked) return;
    this.inputLocked = false;
    const canvas = this.scene.getEngine().getRenderingCanvas();
    if (canvas) this.camera.attachControl(canvas, true);
  }

  // ---------------------------------------------------------------------------
  // Escape to skip

  private _registerEscapeListener(): void {
    this.kbObs = this.scene.onKeyboardObservable.add((info) => {
      if (
        info.type === KeyboardEventTypes.KEYDOWN &&
        info.event.code === "Escape"
      ) {
        this.skipRequested = true;
      }
    });
  }

  private _removeEscapeListener(): void {
    if (this.kbObs) {
      this.scene.onKeyboardObservable.remove(this.kbObs);
      this.kbObs = null;
    }
  }

  // ---------------------------------------------------------------------------
  // DOM overlay

  private _ensureOverlay(): HTMLElement {
    if (!this.overlayEl) {
      const el = document.createElement("div");
      el.className = "cinematic-overlay";
      el.style.cssText = [
        "position:fixed",
        "bottom:12%",
        "left:50%",
        "transform:translateX(-50%)",
        "max-width:640px",
        "text-align:center",
        "color:#e8e0d4",
        "font-family:Georgia,serif",
        "font-size:1.1rem",
        "line-height:1.65",
        "letter-spacing:0.03em",
        "opacity:0",
        "transition:opacity 0.5s ease",
        "pointer-events:none",
        "z-index:900",
      ].join(";");
      document.body.appendChild(el);
      this.overlayEl = el;
    }
    return this.overlayEl;
  }

  private _showOverlayText(text: string, styleClass?: string, fadeInSec = 0.5): void {
    const el = this._ensureOverlay();
    el.textContent = text;
    if (styleClass) el.classList.add(styleClass);
    el.style.transition = `opacity ${fadeInSec}s ease`;
    // Force reflow before setting opacity so the transition fires.
    void el.offsetHeight;
    el.style.opacity = "1";
  }

  private async _hideOverlay(fadeOutSec = 0.5): Promise<void> {
    const el = this.overlayEl;
    if (!el) return;
    el.style.transition = `opacity ${fadeOutSec}s ease`;
    el.style.opacity = "0";
    await waitFrames(this.scene, fadeOutSec + 0.05);
  }

  private _hideOverlayImmediate(): void {
    if (this.overlayEl) {
      this.overlayEl.style.opacity = "0";
    }
  }
}
