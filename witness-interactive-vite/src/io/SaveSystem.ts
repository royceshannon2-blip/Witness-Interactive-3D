/**
 * SaveSystem
 *
 * Thin wrapper around `narrativeController.saveGame() / loadGame()` that
 * persists to `localStorage` with slot keys.
 *
 * Per ARCHITECTURE.md §3.4 + §5.7: the only payload persisted is the
 * narrative-state JSON plus the missionId. World, time, audio, UI, and
 * physics state are all derived from narrative state at scene-build time —
 * nothing else gets serialized.
 */

import { narrativeController } from "../narrative/NarrativeController";

const STORAGE_PREFIX = "witness:save:";

export interface SaveBlob {
  missionId: string;
  /** ISO timestamp when the save was created. */
  savedAt: string;
  /** narrative state, serialized via narrativeController.saveGame(). */
  narrative: string;
}

/**
 * Persist the active narrative state under `slot`. The mission id is
 * supplied by the caller — typically `missionLoader.currentManifest?.id`.
 */
export function save(slot: string, missionId: string): void {
  const blob: SaveBlob = {
    missionId,
    savedAt: new Date().toISOString(),
    narrative: narrativeController.saveGame(),
  };
  window.localStorage.setItem(STORAGE_PREFIX + slot, JSON.stringify(blob));
}

/**
 * Load a previously persisted slot. Returns the blob so the caller can
 * inspect `missionId` (and load the matching mission via `missionLoader`)
 * before applying the narrative state.
 */
export function load(slot: string): SaveBlob | null {
  const raw = window.localStorage.getItem(STORAGE_PREFIX + slot);
  if (!raw) return null;
  return JSON.parse(raw) as SaveBlob;
}

/** Apply the narrative payload from a previously loaded blob. */
export function applyState(blob: SaveBlob): void {
  narrativeController.loadGame(blob.narrative);
}

/** List populated slots. */
export function list(): string[] {
  const slots: string[] = [];
  for (let i = 0; i < window.localStorage.length; i++) {
    const key = window.localStorage.key(i);
    if (key?.startsWith(STORAGE_PREFIX)) {
      slots.push(key.slice(STORAGE_PREFIX.length));
    }
  }
  return slots;
}

/** Remove a slot. */
export function remove(slot: string): void {
  window.localStorage.removeItem(STORAGE_PREFIX + slot);
}
