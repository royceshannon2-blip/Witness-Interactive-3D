/**
 * PlayerController
 *
 * Wraps a `UniversalCamera` with first-person input: WASD movement,
 * pointerlock on canvas click, optional crouch, and pluggable movement
 * profiles for `Perspective` modes (Protector / Hidden).
 *
 * Per PROTOTYPE_AUDIT.md §5 + §7 issues 14, 17, 18: the prototype's inline
 * pointerlock + magic-number gravity factor + mid-scene height fixup all move
 * here. Pointerlock is opt-in (registers + tears down a single observable);
 * never overrides scene-level handlers globally.
 *
 * The controller does NOT mutate world geometry. It triggers narrative
 * events (via narrativeController) or fragment activations (via the
 * InteractableRegistry).
 */

import { KeyboardEventTypes, PointerEventTypes } from "@babylonjs/core";
import type {
  Observer,
  KeyboardInfo,
  PointerInfo,
  UniversalCamera,
  Scene,
} from "@babylonjs/core";
import { worldConstants } from "../engine/config";

export interface MovementProfile {
  walkSpeed: number;
  crouchSpeed: number;
  /** Camera height while standing, in metres. */
  standHeight: number;
  /** Camera height while crouching. */
  crouchHeight: number;
  /** Mouse angular sensibility — bigger = slower turn. Babylon's reference is ~2000. */
  angularSensibility: number;
}

/** Default profile — investigator in 2026, deliberate pace. */
export const PROFILE_INVESTIGATOR: MovementProfile = {
  walkSpeed: 0.28,
  crouchSpeed: 0.15,
  standHeight: worldConstants.playerEyeHeight,
  crouchHeight: 0.95,
  angularSensibility: 1800,
};

/** Past-era Protector — adult agility, full mobility. */
export const PROFILE_PROTECTOR: MovementProfile = {
  walkSpeed: 0.32,
  crouchSpeed: 0.18,
  standHeight: 1.7,
  crouchHeight: 1.0,
  angularSensibility: 1700,
};

/** Past-era Hidden — child, constrained mobility. */
export const PROFILE_HIDDEN: MovementProfile = {
  walkSpeed: 0.18,
  crouchSpeed: 0.1,
  standHeight: 1.15,
  crouchHeight: 0.7,
  angularSensibility: 2200,
};

class PlayerControllerImpl {
  private camera: UniversalCamera | null = null;
  private profile: MovementProfile = PROFILE_INVESTIGATOR;
  private crouching = false;
  private kbObs: Observer<KeyboardInfo> | null = null;
  private ptrObs: Observer<PointerInfo> | null = null;

  /**
   * Bind the controller to a scene + camera. Registers WASD keys via the
   * camera's own keys API (so Babylon's input manager handles modifier
   * dispatch correctly) and adds keyboard/pointer observables for crouch +
   * pointerlock.
   */
  attach(scene: Scene, camera: UniversalCamera): void {
    this.camera = camera;
    const canvas = scene.getEngine().getRenderingCanvas();
    if (!canvas) {
      throw new Error("PlayerController.attach: scene engine has no rendering canvas");
    }
    camera.attachControl(canvas, true);
    this.applyProfile();

    camera.keysUp = [87, 38];        // W, ↑
    camera.keysDown = [83, 40];      // S, ↓
    camera.keysLeft = [65, 37];      // A, ←
    camera.keysRight = [68, 39];     // D, →

    this.kbObs = scene.onKeyboardObservable.add((info) => this.onKeyboard(info));
    this.ptrObs = scene.onPointerObservable.add((info) => this.onPointer(info, canvas));
  }

  /** Tear down. Safe to call without a prior `attach`. */
  detach(scene: Scene): void {
    if (this.kbObs) {
      scene.onKeyboardObservable.remove(this.kbObs);
      this.kbObs = null;
    }
    if (this.ptrObs) {
      scene.onPointerObservable.remove(this.ptrObs);
      this.ptrObs = null;
    }
    this.camera = null;
  }

  /** Switch movement profile (e.g., on era transition + perspective change). */
  setMovementProfile(profile: MovementProfile): void {
    this.profile = profile;
    this.applyProfile();
  }

  // ---------------------------------------------------------------------------

  private applyProfile(): void {
    const c = this.camera;
    if (!c) return;
    c.speed = this.crouching ? this.profile.crouchSpeed : this.profile.walkSpeed;
    c.angularSensibility = this.profile.angularSensibility;
    const h = this.crouching ? this.profile.crouchHeight : this.profile.standHeight;
    c.position.y = c.position.y - (c.position.y - h);
  }

  private onKeyboard(info: KeyboardInfo): void {
    if (info.type !== KeyboardEventTypes.KEYDOWN) return;
    const key = info.event.code;
    if (key === "KeyC" || key === "ControlLeft") {
      this.crouching = !this.crouching;
      this.applyProfile();
    }
  }

  private onPointer(info: PointerInfo, canvas: HTMLCanvasElement): void {
    if (info.type !== PointerEventTypes.POINTERDOWN) return;
    if (document.pointerLockElement !== canvas) {
      // Promise unhandled — older browsers don't return one.
      void canvas.requestPointerLock?.();
    }
  }
}

/** App-wide singleton — there's only ever one player. */
export const playerController = new PlayerControllerImpl();
