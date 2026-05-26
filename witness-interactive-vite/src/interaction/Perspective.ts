/**
 * Perspective
 *
 * Past-era gameplay modifier: the player inhabits either the grandparent
 * (Protector — adult, mobile, makes choices) or a child the grandparent is
 * hiding (Hidden — slow, low, can only watch).
 *
 * Per CHRONOS_SWITCH.md §7 (Path A — cellar reconstruction). The two modes
 * differ only in `MovementProfile` and (later) UI affordances (the Hidden
 * mode disables certain interaction prompts).
 *
 * The narrative system decides which mode is active. This module exposes a
 * setter; PlayerController applies the matching `MovementProfile`.
 */

import {
  playerController,
  PROFILE_HIDDEN,
  PROFILE_INVESTIGATOR,
  PROFILE_PROTECTOR,
} from "./PlayerController";

export type PerspectiveMode = "investigator" | "protector" | "hidden";

let active: PerspectiveMode = "investigator";

export function setMode(mode: PerspectiveMode): void {
  active = mode;
  switch (mode) {
    case "investigator":
      playerController.setMovementProfile(PROFILE_INVESTIGATOR);
      return;
    case "protector":
      playerController.setMovementProfile(PROFILE_PROTECTOR);
      return;
    case "hidden":
      playerController.setMovementProfile(PROFILE_HIDDEN);
      return;
  }
}

export function currentMode(): PerspectiveMode {
  return active;
}
