/**
 * TimeManager
 *
 * The Chronos Switch runtime. Owns the current era (`Present` | `Past`),
 * flips the active camera's layerMask to toggle visibility between them,
 * and records changes made while in the Past so the Present can read them
 * later — the intergenerational-consequence mechanic.
 *
 * See:
 *   - `docs/design-docs/TIMELINE_SYNC.md` — design and flag convention.
 *   - `docs/design-docs/CHRONOS_SWITCH.md` — overall mechanic.
 *   - `ARCHITECTURE.md §4` — layer-mask strategy.
 *
 * Contract:
 *   - Exactly one era is active at any time.
 *   - Transition is single-flight — overlapping calls are rejected.
 *   - Changes recorded via `recordPastChange(key)` set the flag
 *     `PAST_FLAG_PREFIX + key` in `globalState` and are readable
 *     from either era via `hasPastChange(key)`.
 *   - TimeManager never mutates world geometry directly; scenes
 *     subscribe to era-change events and react.
 */

import type { Camera } from "@babylonjs/core";
import { CAMERA_MASK_PAST, CAMERA_MASK_PRESENT } from "./LayerMasks";
import { globalState } from "../narrative/StateManager";

/** The two timelines the player can inhabit. */
export type Era = "present" | "past";

/** Prefix applied to every flag recorded by `recordPastChange`. */
export const PAST_FLAG_PREFIX = "past_";

/** Event emitted by TimeManager's subscribers. */
export type TimeEvent =
  | { type: "transitionStarted"; from: Era; to: Era }
  | { type: "transitionCompleted"; from: Era; to: Era }
  | { type: "pastChangeRecorded"; key: string; value: boolean };

export type TimeListener = (event: TimeEvent) => void;

/**
 * Lifecycle:
 *   1. Construct (starts in Present; no camera attached).
 *   2. `attach(camera)` — apply Present mask to the camera.
 *   3. `transition("past")` / `transition("present")` — switch eras.
 *   4. While in Past: `recordPastChange(key)` persists a boolean flag.
 *   5. From either era: `hasPastChange(key)` queries it.
 */
export class TimeManager {
  private era: Era = "present";
  private camera: Camera | null = null;
  private transitioning = false;
  private readonly listeners: Set<TimeListener> = new Set();

  /** Current active era. */
  get currentEra(): Era {
    return this.era;
  }

  /** True while a transition is in progress. Re-entry is rejected. */
  get isTransitioning(): boolean {
    return this.transitioning;
  }

  /**
   * Bind the camera whose `layerMask` will be driven by era changes.
   * Applies the current era's mask immediately.
   */
  attach(camera: Camera): void {
    this.camera = camera;
    this.applyMask(this.era);
  }

  /** Release the camera reference (for teardown/hot-reload). */
  detach(): void {
    this.camera = null;
  }

  /**
   * Switch to the given era. Resolves after the (optional) crossfade completes.
   * Rejects silently if already in the target era or already transitioning.
   *
   * @param target   Era to switch into.
   * @param duration Crossfade duration in seconds. Defaults to `0` (instant).
   *                 Non-zero values are reserved for a future post-fx blend;
   *                 for now the duration is awaited but the swap is instant.
   */
  async transition(target: Era, duration = 0): Promise<void> {
    if (this.transitioning) return;
    if (target === this.era) return;

    const from = this.era;
    this.transitioning = true;
    this.emit({ type: "transitionStarted", from, to: target });

    if (duration > 0) {
      await new Promise<void>((resolve) => setTimeout(resolve, duration * 1000));
    }

    this.era = target;
    this.applyMask(target);
    this.transitioning = false;
    this.emit({ type: "transitionCompleted", from, to: target });
  }

  /**
   * Record a change made by the player while in the Past. Persists as
   * `past_<key>` in the narrative StateManager so that Present-era scenes
   * can query it via `hasPastChange` (or `globalState.getFlag`).
   *
   * Intentionally callable from either era — the narrative does not always
   * drive recording from live gameplay (e.g., a cutscene may preset state).
   * If you want strict "must be in Past," gate at the call site.
   *
   * @param key   Short identifier, e.g. `"hid_child_in_cellar"`. The prefix
   *              is applied automatically.
   * @param value Boolean value to record. Defaults to `true`.
   */
  recordPastChange(key: string, value = true): void {
    const flagKey = PAST_FLAG_PREFIX + key;
    globalState.setFlag(flagKey, value);
    this.emit({ type: "pastChangeRecorded", key, value });
  }

  /**
   * Read a Past-era change. Returns `false` if never recorded.
   * Safe to call from any era — this is exactly the Present-era lookup path
   * for reading intergenerational consequences.
   */
  hasPastChange(key: string): boolean {
    return globalState.getFlag(PAST_FLAG_PREFIX + key);
  }

  /**
   * Snapshot of all Past-era changes currently recorded. Useful for debug
   * overlays and save-file inspection. Does not include non-Past flags.
   */
  getPastChanges(): Record<string, boolean> {
    const snapshot: Record<string, boolean> = {};
    const flags = globalState.getState().progress.flagsSet;
    for (const [key, value] of Object.entries(flags)) {
      if (key.startsWith(PAST_FLAG_PREFIX)) {
        snapshot[key.slice(PAST_FLAG_PREFIX.length)] = value;
      }
    }
    return snapshot;
  }

  /**
   * Subscribe to time events. Returns an unsubscribe function.
   */
  subscribe(listener: TimeListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private emit(event: TimeEvent): void {
    for (const listener of this.listeners) {
      listener(event);
    }
  }

  private applyMask(era: Era): void {
    if (!this.camera) return;
    this.camera.layerMask = era === "past" ? CAMERA_MASK_PAST : CAMERA_MASK_PRESENT;
  }
}

/** App-wide singleton. Scenes, world modules, and UI all share this instance. */
export const timeManager = new TimeManager();
