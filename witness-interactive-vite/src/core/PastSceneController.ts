/**
 * PastSceneController
 *
 * Owns the lifecycle of a Memory-Fragment-triggered Past scene per
 * CHRONOS_SWITCH.md §4.4:
 *
 *   1. A fragment fires `begin(spec)` from its `onActivate` hook.
 *   2. The controller waits for `TimeManager` to report `to: "past"`,
 *      then runs the spec's enter-Past hook (narrator cue, etc.) and arms
 *      a return timer.
 *   3. When the timer fires, the controller transitions back to Present.
 *   4. On `to: "present"` completion, the controller records the
 *      designated past-change flag, sets the narrative `unlocksFlag`, and
 *      runs the return hook (ledger toast, etc.).
 *
 * Dependency discipline: `core/` is forbidden from importing `audio/` /
 * `ui/` / `narrative/` controllers it doesn't already depend on. Audio &
 * UI side effects are passed in as callbacks (`onEnterPast`,
 * `onReturnToPresent`) so the controller stays seam-thin and independently
 * unit-testable. See ARCHITECTURE.md §2 for the import rules.
 */

import { type Era, type TimeEvent, timeManager } from "./TimeManager";
import { globalState } from "../narrative/StateManager";
import { createLog } from "../log";

const log = createLog("past-scene");

/** Default Past dwell when a spec omits durationSec. Echoes are short. */
export const DEFAULT_PAST_DWELL_SEC = 12;

/** Default Past↔Present crossfade — matches CHRONOS_SWITCH.md §3.6. */
export const DEFAULT_TRANSITION_SEC = 1.8;

export interface PastSceneCompletion {
  fragmentId: string;
  pastChangeKey: string;
  unlocksFlag: string;
}

export interface PastSceneSpec {
  /** Fragment id that started this scene. Used for logging + debug. */
  fragmentId: string;
  /** Past-era dwell time. Capped to 30–180 s in production but the demo uses 12 s. */
  durationSec?: number;
  /** Crossfade duration for the return-to-Present transition. */
  returnTransitionSec?: number;
  /** Flag key recorded as a `past_<key>` change when the scene resolves. */
  pastChangeKey: string;
  /** Narrative flag set on completion (e.g. `"found_cellar_evidence"`). */
  unlocksFlag: string;
  /**
   * Called after the to-Past transition completes. Wire to
   * `audioManager.playNarratorEntry(...)`, particle emit, etc.
   */
  onEnterPast?: () => void;
  /**
   * Called after the return-to-Present transition completes, with the
   * unlock metadata. Wire to ledger toast / HUD pulse.
   */
  onReturnToPresent?: (completion: PastSceneCompletion) => void;
  /**
   * When true, the automatic dwell timer is NOT armed after entering the Past.
   * The caller must call `pastSceneController.returnNow()` to trigger the
   * return transition. Useful for interaction-driven echo exits (e.g. player
   * presses E to leave the Past rather than waiting a fixed duration).
   */
  interactionDriven?: boolean;
}

class PastSceneControllerImpl {
  private active: Required<Pick<PastSceneSpec, "fragmentId" | "durationSec" | "returnTransitionSec" | "pastChangeKey" | "unlocksFlag" | "interactionDriven">> &
    Pick<PastSceneSpec, "onEnterPast" | "onReturnToPresent"> | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private subscribed = false;

  /**
   * Start a Past-scene session. Idempotent during a single fragment's
   * activation — overlapping `begin` calls log a warning and are ignored.
   */
  begin(spec: PastSceneSpec): void {
    if (this.active) {
      log.warn(`begin(${spec.fragmentId}) ignored — '${this.active.fragmentId}' still active`);
      return;
    }
    this.subscribeOnce();
    this.active = {
      fragmentId: spec.fragmentId,
      durationSec: spec.durationSec ?? DEFAULT_PAST_DWELL_SEC,
      returnTransitionSec: spec.returnTransitionSec ?? DEFAULT_TRANSITION_SEC,
      pastChangeKey: spec.pastChangeKey,
      unlocksFlag: spec.unlocksFlag,
      interactionDriven: spec.interactionDriven ?? false,
      onEnterPast: spec.onEnterPast,
      onReturnToPresent: spec.onReturnToPresent,
    };
    log.info(`begin ${spec.fragmentId} — dwell ${this.active.durationSec}s`);
  }

  /** Cancel the active session — used by tests + by mission unload. */
  cancel(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.active = null;
  }

  /**
   * Immediately trigger the return-to-Present transition for the active session.
   * Primary use case: `interactionDriven` fragments where the player presses E
   * to leave the Past instead of waiting for the dwell timer.
   */
  returnNow(): void {
    if (!this.active) {
      log.warn("returnNow() called with no active session");
      return;
    }
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    void timeManager.transition("present", this.active.returnTransitionSec);
  }

  private subscribeOnce(): void {
    if (this.subscribed) return;
    this.subscribed = true;
    timeManager.subscribe((evt) => this.onTime(evt));
  }

  private onTime(evt: TimeEvent): void {
    if (!this.active) return;
    if (evt.type !== "transitionCompleted") return;

    const era: Era = evt.to;
    if (era === "past") {
      this.active.onEnterPast?.();
      if (!this.active.interactionDriven) {
        this.armReturnTimer();
      }
    } else if (era === "present") {
      this.finalize();
    }
  }

  private armReturnTimer(): void {
    if (!this.active) return;
    const spec = this.active;
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      this.timer = null;
      void timeManager.transition("present", spec.returnTransitionSec);
    }, spec.durationSec * 1000);
  }

  private finalize(): void {
    if (!this.active) return;
    const spec = this.active;
    const completion: PastSceneCompletion = {
      fragmentId: spec.fragmentId,
      pastChangeKey: spec.pastChangeKey,
      unlocksFlag: spec.unlocksFlag,
    };
    timeManager.recordPastChange(spec.pastChangeKey);
    globalState.setFlag(spec.unlocksFlag, true);
    log.info(`finalize ${spec.fragmentId} → ${spec.unlocksFlag}`);
    this.active = null;
    spec.onReturnToPresent?.(completion);
  }
}

/** App-wide singleton — there is one Past at a time per CHRONOS_SWITCH §3.1. */
export const pastSceneController = new PastSceneControllerImpl();
