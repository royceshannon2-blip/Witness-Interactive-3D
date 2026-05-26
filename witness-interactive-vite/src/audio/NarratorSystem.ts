/**
 * NarratorSystem
 *
 * Serialises narrator playback and manages caption sync + ambience ducking.
 *
 * Design constraints (AUDIO_ARCHITECTURE.md §4, triple-A plan M16):
 *   - Narrator lines must never overlap: a second `enqueue()` call waits for
 *     the current clip to finish + POST_SILENCE_SEC before starting.
 *   - Ambience ducks to -24 dBFS while the narrator speaks; restored after.
 *   - E-key skip: available only when no interactable object is in proximity
 *     (checked via `interactableRegistry.hasNearby()`).
 *   - Caption cues loaded from `/audios/narrator/<key>.vtt`; degrades
 *     gracefully to a blank overlay when the file is absent (pre-M19).
 *
 * Stub-safe: during M16 (before M19 audio generation) all "playback" is a
 * timed wait derived from estimated clip duration. When real WAV files land
 * in M19, replace `_stubPlay()` with a real Babylon Sound loader.
 *
 * Part of M16 (ARCHITECTURE.md §5.11).
 */

import { KeyboardEventTypes } from "@babylonjs/core";
import type { KeyboardInfo, Observer, Scene } from "@babylonjs/core";
import { captionOverlay, fetchCues } from "../ui/CaptionOverlay";
import { audioManager } from "./AudioManager";
import { interactableRegistry } from "../interaction/InteractableRegistry";

/** Seconds of silence after a clip ends before the next one begins. */
const POST_SILENCE_SEC = 0.8;

/** Estimated words-per-minute for the narrator (used in stub mode). */
const NARRATOR_WPM = 130;

/** Minimum stub duration per entry (seconds). */
const MIN_DURATION_SEC = 2.0;

interface QueueEntry {
  key: string;
  /** Optional plain-text fallback caption if no .vtt is found. */
  text?: string;
}

class NarratorSystemImpl {
  private queue: QueueEntry[] = [];
  private playing = false;
  private skipRequested = false;
  private kbObs: Observer<KeyboardInfo> | null = null;
  private scene: Scene | null = null;

  /** Wire E-key skip to the scene keyboard observable. Call once at boot. */
  attach(scene: Scene): void {
    if (this.scene) return;
    this.scene = scene;
    this.kbObs = scene.onKeyboardObservable.add((info) => this._onKeyboard(info));
  }

  detach(): void {
    if (!this.scene) return;
    if (this.kbObs) this.scene.onKeyboardObservable.remove(this.kbObs);
    this.kbObs = null;
    this.scene = null;
  }

  /**
   * Add a narrator clip to the queue. Resolves when the clip (and the post-
   * silence gap) are complete — or sooner if the clip was skipped.
   *
   * `text` is used as a caption fallback when the .vtt file is absent and as
   * the stub-mode duration estimate.
   */
  async enqueue(key: string, text?: string): Promise<void> {
    return new Promise<void>((resolve) => {
      this.queue.push({ key, text });
      if (!this.playing) void this._drain(resolve);
    });
  }

  /** Skip the currently playing narrator clip immediately. */
  skip(): void {
    this.skipRequested = true;
  }

  // ---------------------------------------------------------------------------

  private async _drain(resolveFirst: () => void): Promise<void> {
    this.playing = true;

    while (this.queue.length > 0) {
      const entry = this.queue.shift()!;
      this.skipRequested = false;
      const isFirst = resolveFirst !== _noop;
      const localResolve = isFirst ? resolveFirst : _noop;
      resolveFirst = _noop;

      await this._playEntry(entry);
      localResolve();

      if (this.queue.length > 0) {
        await _sleep(POST_SILENCE_SEC * 1000);
      }
    }

    this.playing = false;
  }

  private async _playEntry(entry: QueueEntry): Promise<void> {
    // 1. Fetch captions (best-effort).
    const vttUrl = `/audios/narrator/${entry.key}.vtt`;
    const cues = await fetchCues(vttUrl);

    // 2. Estimate duration from cues or from text word count.
    const durationSec = _estimateDuration(cues, entry.text);

    // 3. Duck ambience.
    audioManager.duckAmbience(true);

    // 4. Start captions.
    let stopCues: () => void;
    if (cues.length > 0) {
      stopCues = captionOverlay.playCues(cues);
    } else if (entry.text) {
      captionOverlay.showText(entry.text, durationSec);
      stopCues = () => captionOverlay.hide();
    } else {
      stopCues = () => {};
    }
    // 5. Play audio (stub: logs only; real impl mounts Babylon Sound in M19).
    audioManager.playNarratorEntry(entry.key);

    // 6. Wait for natural end or skip.
    await _waitOrSkip(durationSec, () => this.skipRequested);

    // 7. Teardown.
    stopCues();
    captionOverlay.hide();
    audioManager.duckAmbience(false);
  }

  private _onKeyboard(info: KeyboardInfo): void {
    if (info.type !== KeyboardEventTypes.KEYDOWN) return;
    if (info.event.code !== "KeyE") return;
    // Only consume E when no interactable is nearby — otherwise the registry
    // owns the keypress.
    if (!this.playing) return;
    if (interactableRegistry.hasNearby()) return;
    this.skipRequested = true;
  }
}

// ---------------------------------------------------------------------------
// Helpers

const _noop = () => {};

function _sleep(ms: number): Promise<void> {
  return new Promise((res) => setTimeout(res, ms));
}

/**
 * Wait `durationSec` seconds, but poll `isSkipped()` every 100 ms so the
 * clip can be cancelled early.
 */
async function _waitOrSkip(durationSec: number, isSkipped: () => boolean): Promise<void> {
  const end = performance.now() + durationSec * 1000;
  while (performance.now() < end) {
    if (isSkipped()) break;
    await _sleep(Math.min(100, end - performance.now()));
  }
}

/**
 * Derive clip duration from VTT cues (last end time) or fall back to a
 * word-count estimate.
 */
function _estimateDuration(cues: { endSec: number }[], text?: string): number {
  if (cues.length > 0) {
    return Math.max(MIN_DURATION_SEC, cues[cues.length - 1].endSec);
  }
  if (text) {
    const words = text.trim().split(/\s+/).length;
    return Math.max(MIN_DURATION_SEC, (words / NARRATOR_WPM) * 60);
  }
  return MIN_DURATION_SEC;
}

/** App-wide singleton. */
export const narratorSystem = new NarratorSystemImpl();
