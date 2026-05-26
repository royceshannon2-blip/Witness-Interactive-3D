/**
 * Barrel export for the `core/` subsystem.
 *
 * Prefer importing from `./core` rather than individual files so that
 * internal reshuffles don't break consumers.
 */

export {
  LAYER_PRESENT,
  LAYER_PAST,
  LAYER_SHARED,
  LAYER_ALL,
  CAMERA_MASK_PRESENT,
  CAMERA_MASK_PAST,
  ERA_SCOPE_MASK,
  tagNode,
  tagLight,
} from "./LayerMasks";
export type { EraScope } from "./LayerMasks";

export { TimeManager, timeManager, PAST_FLAG_PREFIX } from "./TimeManager";
export type { Era, TimeEvent, TimeListener } from "./TimeManager";

export {
  MemoryFragment,
  FRAGMENT_FLAG_PREFIX,
  fragmentActivatedFlag,
} from "./MemoryFragment";
export type { MemoryFragmentOpts } from "./MemoryFragment";

export {
  pastSceneController,
  DEFAULT_PAST_DWELL_SEC,
  DEFAULT_TRANSITION_SEC,
} from "./PastSceneController";
export type { PastSceneSpec, PastSceneCompletion } from "./PastSceneController";

export {
  cameraDolly,
  cameraApproach,
  fovTween,
  meshMove,
  meshRotate,
  softEase,
  startCameraBreath,
  waitFrames,
} from "./AnimationDirector";
export type { CameraDollyOpts, DollyTarget } from "./AnimationDirector";

export {
  ECHO_PROFILES,
  DEFAULT_ECHO_PROFILE,
  getEchoProfile,
} from "./EchoProfiles";
export type { EchoPrerollProfile } from "./EchoProfiles";

export { CinematicDirector } from "./CinematicDirector";
export type {
  Beat,
  CameraDollyBeat,
  CameraApproachBeat,
  FovBeat,
  AudioPlayBeat,
  AudioEffectBeat,
  WaitBeat,
  OverlayTextBeat,
  OverlayHideBeat,
  ControlLockBeat,
  ControlUnlockBeat,
  ParallelBeat,
} from "./CinematicDirector";

export { vistaSystem } from "./VistaSystem";
export type { VistaDef } from "./VistaSystem";
