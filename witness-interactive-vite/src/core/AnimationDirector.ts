/**
 * AnimationDirector
 *
 * Cinematic-grade animation primitives over Babylon's `Animation` system.
 * Builds keyframed animations (60 fps target) with eased interpolation and
 * returns Promises that resolve when the animation completes. Designed for
 * studio-quality transitions: ledger pickup choreography, intro hand-off
 * camera lift, Past↔Present FOV breath.
 *
 * Why this exists separately from `RenderingPipeline.fadeToEra`:
 *   - `fadeToEra` drives **post-fx coefficients** (exposure, contrast,
 *     vignette) — global colour grade tweens.
 *   - `AnimationDirector` drives **scene-graph properties** (camera position,
 *     camera rotation, mesh transforms, FOV) — geometric animation.
 *
 * Both share the same Babylon render loop; both use `CubicEase` ease-in-out
 * by default so they look like one motion. Frame-rate independent — Babylon's
 * `beginDirectAnimation` is driven by the engine's clock, not setTimeout.
 *
 * Per .claude/rules/babylon-patterns.md: prefer Babylon's animation system
 * over manual lerp loops for any non-trivial tween — the engine already
 * handles frame jitter, pause-state, and disposal lifecycle.
 */

import {
  Animation,
  CubicEase,
  EasingFunction,
  SineEase,
  Vector3,
} from "@babylonjs/core";
import type {
  Camera,
  Quaternion,
  Scene,
  TransformNode,
  UniversalCamera,
} from "@babylonjs/core";

/** Default ease — cubic in-out matches the project's "weighted" register. */
function defaultEase(): EasingFunction {
  const ease = new CubicEase();
  ease.setEasingMode(EasingFunction.EASINGMODE_EASEINOUT);
  return ease;
}

/** Sine ease — softer than cubic, useful for FOV breaths and idle drift. */
export function softEase(): EasingFunction {
  const ease = new SineEase();
  ease.setEasingMode(EasingFunction.EASINGMODE_EASEINOUT);
  return ease;
}

const FPS = 60;

export interface DollyTarget {
  /** End position for the camera. */
  position: Vector3;
  /** Optional look-at target. If omitted, rotation is held. */
  target?: Vector3;
}

export interface CameraDollyOpts {
  durationSec: number;
  /** Optional easing override. Defaults to cubic ease-in-out. */
  easing?: EasingFunction;
}

/**
 * Animate a `UniversalCamera` from its current pose to a new pose. If
 * `target` is supplied, the camera's `rotation` is also keyframed so the
 * camera ends up looking at that point.
 *
 * Idempotent w.r.t. concurrent calls: Babylon's `beginDirectAnimation`
 * cancels any prior animation on the same target+property automatically.
 *
 * @returns Promise that resolves when the dolly completes.
 */
export function cameraDolly(
  scene: Scene,
  camera: UniversalCamera,
  to: DollyTarget,
  opts: CameraDollyOpts,
): Promise<void> {
  const totalFrames = Math.max(1, Math.round(opts.durationSec * FPS));
  const ease = opts.easing ?? defaultEase();
  const animations: Animation[] = [];

  const posAnim = new Animation(
    "camDolly.position",
    "position",
    FPS,
    Animation.ANIMATIONTYPE_VECTOR3,
    Animation.ANIMATIONLOOPMODE_CONSTANT,
  );
  posAnim.setKeys([
    { frame: 0, value: camera.position.clone() },
    { frame: totalFrames, value: to.position.clone() },
  ]);
  posAnim.setEasingFunction(ease);
  animations.push(posAnim);

  if (to.target) {
    const endYawPitch = yawPitchTowards(to.position, to.target);
    const startRot = camera.rotation.clone();
    const endRot = new Vector3(endYawPitch.pitch, endYawPitch.yaw, 0);

    const rotAnim = new Animation(
      "camDolly.rotation",
      "rotation",
      FPS,
      Animation.ANIMATIONTYPE_VECTOR3,
      Animation.ANIMATIONLOOPMODE_CONSTANT,
    );
    rotAnim.setKeys([
      { frame: 0, value: startRot },
      { frame: totalFrames, value: endRot },
    ]);
    rotAnim.setEasingFunction(ease);
    animations.push(rotAnim);
  }

  return new Promise((resolve) => {
    scene.beginDirectAnimation(camera, animations, 0, totalFrames, false, 1, () =>
      resolve(),
    );
  });
}

/**
 * Animate `camera.fov` from current to `targetFov` over `durationSec`. Use
 * for "breath" beats (subtle zoom-in/out during memory dissolves) and for
 * the intro hand-off settling.
 */
export function fovTween(
  scene: Scene,
  camera: Camera,
  targetFov: number,
  durationSec: number,
  easing: EasingFunction = softEase(),
): Promise<void> {
  const totalFrames = Math.max(1, Math.round(durationSec * FPS));
  const anim = new Animation(
    "cam.fov",
    "fov",
    FPS,
    Animation.ANIMATIONTYPE_FLOAT,
    Animation.ANIMATIONLOOPMODE_CONSTANT,
  );
  anim.setKeys([
    { frame: 0, value: camera.fov },
    { frame: totalFrames, value: targetFov },
  ]);
  anim.setEasingFunction(easing);
  return new Promise((resolve) => {
    scene.beginDirectAnimation(camera, [anim], 0, totalFrames, false, 1, () =>
      resolve(),
    );
  });
}

/**
 * Move a mesh from its current world position to `targetWorldPos` over
 * `durationSec`. The mesh's `position` is animated directly — parent
 * transforms are honoured because Babylon's animation operates on the local
 * `position` field. Caller is responsible for ensuring the mesh isn't frozen.
 */
export function meshMove(
  scene: Scene,
  mesh: TransformNode,
  targetWorldPos: Vector3,
  durationSec: number,
  easing: EasingFunction = defaultEase(),
): Promise<void> {
  const totalFrames = Math.max(1, Math.round(durationSec * FPS));
  const anim = new Animation(
    `mesh.move.${mesh.name}`,
    "position",
    FPS,
    Animation.ANIMATIONTYPE_VECTOR3,
    Animation.ANIMATIONLOOPMODE_CONSTANT,
  );
  anim.setKeys([
    { frame: 0, value: mesh.position.clone() },
    { frame: totalFrames, value: targetWorldPos.clone() },
  ]);
  anim.setEasingFunction(easing);
  return new Promise((resolve) => {
    scene.beginDirectAnimation(mesh, [anim], 0, totalFrames, false, 1, () => resolve());
  });
}

/**
 * Rotate a mesh from its current quaternion to a new quaternion over
 * `durationSec`. Use for lifting/rotating a prop to face the camera.
 */
export function meshRotate(
  scene: Scene,
  mesh: TransformNode,
  targetRotation: Quaternion,
  durationSec: number,
  easing: EasingFunction = defaultEase(),
): Promise<void> {
  if (!mesh.rotationQuaternion) {
    // Fall back to no-op if the mesh uses Euler rotations — caller should
    // ensure the mesh was constructed with a quaternion (FamilyCompound does).
    return Promise.resolve();
  }
  const totalFrames = Math.max(1, Math.round(durationSec * FPS));
  const anim = new Animation(
    `mesh.rotate.${mesh.name}`,
    "rotationQuaternion",
    FPS,
    Animation.ANIMATIONTYPE_QUATERNION,
    Animation.ANIMATIONLOOPMODE_CONSTANT,
  );
  anim.setKeys([
    { frame: 0, value: mesh.rotationQuaternion.clone() },
    { frame: totalFrames, value: targetRotation.clone() },
  ]);
  anim.setEasingFunction(easing);
  return new Promise((resolve) => {
    scene.beginDirectAnimation(mesh, [anim], 0, totalFrames, false, 1, () => resolve());
  });
}

/**
 * Wait `durationSec` driven by the Babylon render loop. Unlike `setTimeout`,
 * this pauses when the engine pauses (e.g. on tab blur if the host page
 * suspends animation frames). Useful inside choreographed sequences.
 */
export function waitFrames(scene: Scene, durationSec: number): Promise<void> {
  const start = performance.now();
  const ms = durationSec * 1000;
  return new Promise((resolve) => {
    const obs = scene.onBeforeRenderObservable.add(() => {
      if (performance.now() - start >= ms) {
        scene.onBeforeRenderObservable.remove(obs);
        resolve();
      }
    });
  });
}

/**
 * Continuous sinusoidal Y-axis oscillation — simulates embodied breathing.
 * Returns a `stop()` function; call it to cancel and snap the camera back.
 *
 * Amplitude (0.007 m default) is sub-perceptual at normal monitor distance;
 * its effect is felt as presence rather than seen as movement. Use during
 * Past echo dwells (12–20 s static camera) to sell "inhabiting a memory."
 *
 * Safe to run while `attachControl` is active: the offset is strictly
 * additive to `camera.position.y` and the amplitude is too small to
 * interfere with WASD or mouse-look (which drives rotation, not position.y).
 */
export function startCameraBreath(
  scene: Scene,
  camera: UniversalCamera,
  opts: {
    /** Peak-to-trough displacement in metres. Default 0.007. */
    amplitudeM?: number;
    /** Oscillation frequency in Hz. Default 0.28. */
    freqHz?: number;
  } = {},
): () => void {
  const amp = opts.amplitudeM ?? 0.007;
  const freq = opts.freqHz ?? 0.28;
  const t0 = performance.now();
  let prevOffset = 0;

  const obs = scene.onBeforeRenderObservable.add(() => {
    const t = (performance.now() - t0) / 1000;
    const offset = amp * Math.sin(t * Math.PI * 2 * freq);
    camera.position.y += offset - prevOffset;
    prevOffset = offset;
  });

  return () => {
    scene.onBeforeRenderObservable.remove(obs);
    camera.position.y -= prevOffset;
  };
}

/**
 * Brief camera pull toward an anchor world position — the "being drawn in"
 * moment before an era transition. Detaches input, dollies `pullMag` metres
 * toward `anchorPos`, re-attaches. Runs the Babylon animation system, not a
 * manual lerp, so it obeys engine pause.
 *
 * Minimum-distance guard: the camera will not move closer than 0.45 m to
 * the anchor so the player is never inside a mesh.
 *
 * Safe to run in parallel with `fovTween` (they target different properties:
 * `position` vs `fov`).
 */
export async function cameraApproach(
  scene: Scene,
  camera: UniversalCamera,
  anchorPos: Vector3,
  pullMag: number,
  durationSec: number,
): Promise<void> {
  if (pullMag <= 0) return;
  const canvas = scene.getEngine().getRenderingCanvas();
  if (canvas) camera.detachControl();

  const toAnchor = anchorPos.subtract(camera.position);
  const dist = toAnchor.length();
  const safePull = Math.min(pullMag, Math.max(0, dist - 0.45));
  if (safePull > 0.001) {
    const target = camera.position.add(toAnchor.normalize().scale(safePull));
    target.y = Math.max(target.y, 0.3); // never underground
    await cameraDolly(scene, camera, { position: target }, { durationSec });
  }

  if (canvas) camera.attachControl(canvas, true);
}

// ---------------------------------------------------------------------------

/**
 * Compute yaw + pitch (radians) so a camera at `eye` looks at `target`.
 * Matches Babylon's `UniversalCamera.rotation` convention: x=pitch, y=yaw.
 */
function yawPitchTowards(eye: Vector3, target: Vector3): { yaw: number; pitch: number } {
  const dx = target.x - eye.x;
  const dy = target.y - eye.y;
  const dz = target.z - eye.z;
  const yaw = Math.atan2(dx, dz);
  const pitch = -Math.atan2(dy, Math.sqrt(dx * dx + dz * dz));
  return { yaw, pitch };
}
