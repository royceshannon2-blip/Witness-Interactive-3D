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
