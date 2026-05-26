/**
 * SceneFactory
 *
 * Constructs a `BABYLON.Scene` ready to receive world content. Owns the
 * decisions that are scene-wide (clear colour, fog, default camera) but does
 * NOT build any mesh content — that belongs in `world/`.
 *
 * Per ARCHITECTURE.md §5.3, this module is import-isolated: only Babylon and
 * sibling engine/ modules. No imports from `world/`, `narrative/`, `core/`,
 * etc.
 */

import {
  Color3,
  Color4,
  Scene,
  UniversalCamera,
  Vector3,
} from "@babylonjs/core";
import type { Engine } from "@babylonjs/core";
import { worldConstants } from "./config";

export interface SceneInit {
  /** Scene the factory just built. */
  scene: Scene;
  /** Default first-person camera. Replace via `world/`/`interaction/` when ready. */
  camera: UniversalCamera;
}

/**
 * Build a fresh Scene with project-default fog, gravity, collisions enabled.
 *
 * The returned camera is a placeholder — it has no input wiring, no
 * controller. `interaction/PlayerController` is responsible for input;
 * call `playerController.attach(scene, camera)` after this returns.
 *
 * @param engine The Babylon engine the scene attaches to.
 */
export function createBaseScene(engine: Engine): SceneInit {
  const scene = new Scene(engine);
  scene.clearColor = new Color4(0.62, 0.66, 0.7, 1);
  scene.ambientColor = new Color3(0.18, 0.2, 0.22);
  scene.gravity = new Vector3(0, worldConstants.gravityY, 0);
  scene.collisionsEnabled = true;
  scene.fogMode = Scene.FOGMODE_EXP2;
  scene.fogDensity = worldConstants.fogDensityDefault;
  const fp = worldConstants.fogColorPresent;
  scene.fogColor = new Color3(fp.r, fp.g, fp.b);

  const camera = new UniversalCamera(
    "playerCam",
    new Vector3(0, worldConstants.playerEyeHeight, -8),
    scene,
  );
  camera.minZ = worldConstants.cameraMinZ;
  camera.maxZ = worldConstants.cameraMaxZ;
  camera.fov = 1.05;
  camera.ellipsoid = new Vector3(0.4, 0.85, 0.4);
  camera.checkCollisions = true;
  camera.applyGravity = true;

  return { scene, camera };
}
