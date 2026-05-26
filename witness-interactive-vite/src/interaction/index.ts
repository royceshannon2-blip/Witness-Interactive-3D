/**
 * Barrel for `interaction/`. ARCHITECTURE.md §5.5.
 */

export {
  playerController,
  PROFILE_INVESTIGATOR,
  PROFILE_PROTECTOR,
  PROFILE_HIDDEN,
} from "./PlayerController";
export type { MovementProfile } from "./PlayerController";

export { interactableRegistry } from "./InteractableRegistry";
export type { InteractableHandler } from "./InteractableRegistry";

export { interactableHighlight } from "./InteractableHighlight";

export { setMode as setPerspective, currentMode as currentPerspective } from "./Perspective";
export type { PerspectiveMode } from "./Perspective";
