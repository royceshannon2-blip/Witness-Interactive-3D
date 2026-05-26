/**
 * AmbienceEngine
 *
 * Bed-management layer that sits between {@link AudioManager} and the rest of
 * the runtime. Owns the per-location, per-era ambient loops and crossfades
 * between them when the player moves location or the Chronos Switch flips.
 *
 * Design constraints (AUDIO_ARCHITECTURE.md §4 + §6, triple-A plan M21):
 *   - Exactly one bed is "current" at any time; the previous bed fades out
 *     while the new one fades in. Concurrent calls are single-flight — a
 *     second `setLocation`/`setEra` while a swap is in progress waits for the
 *     in-flight swap to complete before scheduling its own.
 *   - Crossfade durations follow AUDIO_ARCHITECTURE.md §4: location swaps
 *     use {@link LOCATION_FADE_SEC} (2 s), era flips use {@link ERA_FADE_SEC}
 *     (1.3 s, the longer of the doc's 0.5 s fade-out / 1.3 s fade-in pair —
 *     a single symmetric crossfade is a deliberate v1 simplification).
 *   - Ducking attenuates the current bed to {@link DUCK_FACTOR} of its base
 *     volume — matches the `reduce_ambience_volume(0.5)` rule from §6.
 *   - Stub-safe: when an audio file is missing the engine logs a warning and
 *     treats the slot as silence. The narrative still runs end-to-end before
 *     M20 audio generation lands.
 *
 * Bed id convention (matches M20 AudioCraft generation script + the
 * `BANTER_LINES` keys in {@link BanterLibrary}):
 *
 *     bed_<location>_<era>     →   /audios/ambience/bed_<location>_<era>.ogg
 *
 * Locations come from {@link BanterLibrary.LocationKey}; eras come from
 * {@link core.Era}. Five locations × two eras = ten bed slots.
 *
 * Owned by {@link AudioManager} — callers should not import this module
 * directly; route through {@link audioManager.setLocation},
 * `transitionToEra`, and `duckAmbience` instead.
 */

import {
  AudioParameterRampShape,
  CreateSoundAsync,
} from "@babylonjs/core";
import type { AudioEngineV2, StaticSound } from "@babylonjs/core";
import type { Era } from "../core";
import type { LocationKey } from "../narrative/BanterLibrary";

// ---------------------------------------------------------------------------
// Constants

/** Base linear gain of a bed when un-ducked. Roughly -3 dB. */
const BASE_VOLUME = 0.7;

/** Multiplier applied while a narrator clip plays (AUDIO_ARCHITECTURE.md §6). */
const DUCK_FACTOR = 0.5;

/** Default crossfade time for location changes (AUDIO_ARCHITECTURE.md §4). */
const LOCATION_FADE_SEC = 2.0;

/** Default crossfade time for era flips (AUDIO_ARCHITECTURE.md §4). */
const ERA_FADE_SEC = 1.3;

/** Default fade time when ducking / un-ducking around narrator lines. */
const DUCK_FADE_SEC = 0.3;

/** Public-folder URL prefix. Bed files land at `/audios/ambience/<id>.ogg`. */
const BED_URL_PREFIX = "/audios/ambience/";

// ---------------------------------------------------------------------------
// Internal types

interface BedSlot {
  id: string;
  sound: StaticSound;
}

// ---------------------------------------------------------------------------

class AmbienceEngineImpl {
  private engine: AudioEngineV2 | null = null;
  private currentLocation: LocationKey | null = null;
  private currentEra: Era = "present";
  private current: BedSlot | null = null;
  private soundCache = new Map<string, StaticSound | null>();
  private ducked = false;
  /** Tail of the swap chain — used for single-flight serialisation. */
  private swapChain: Promise<void> = Promise.resolve();

  /**
   * Bind the engine. Idempotent. Should be called from
   * {@link AudioManager.init} once the engine has been constructed.
   */
  attach(engine: AudioEngineV2): void {
    if (this.engine) return;
    this.engine = engine;
  }

  /** True if {@link attach} has been called. */
  get isAttached(): boolean {
    return this.engine !== null;
  }

  /**
   * Switch the active location, crossfading to its bed in the current era.
   * Idempotent on the same location.
   *
   * @param location  Canonical location key (compound | cellar | lakeshore |
   *                  ravine | heights). See {@link BanterLibrary.LocationKey}.
   * @param fadeSec   Override crossfade duration. Defaults to
   *                  {@link LOCATION_FADE_SEC}.
   */
  setLocation(location: LocationKey, fadeSec: number = LOCATION_FADE_SEC): Promise<void> {
    if (this.currentLocation === location) return Promise.resolve();
    this.currentLocation = location;
    return this._scheduleSwap(fadeSec);
  }

  /**
   * Switch the active era, crossfading to the matching bed at the current
   * location. Idempotent on the same era.
   *
   * @param era       Target era.
   * @param fadeSec   Override crossfade duration. Defaults to
   *                  {@link ERA_FADE_SEC}.
   */
  setEra(era: Era, fadeSec: number = ERA_FADE_SEC): Promise<void> {
    if (this.currentEra === era) return Promise.resolve();
    this.currentEra = era;
    return this._scheduleSwap(fadeSec);
  }

  /**
   * Duck the current bed to {@link DUCK_FACTOR} × base volume, or restore.
   * Idempotent. Safe to call before any bed is loaded.
   */
  setDuck(duck: boolean, fadeSec: number = DUCK_FADE_SEC): void {
    if (this.ducked === duck) return;
    this.ducked = duck;
    if (this.current) {
      this._rampVolume(this.current.sound, this._targetVolume(), fadeSec);
    }
  }

  /** Tear down — stop everything and clear caches. */
  dispose(): void {
    if (this.current) {
      try {
        this.current.sound.stop();
      } catch {
        /* ignore */
      }
      this.current = null;
    }
    for (const sound of this.soundCache.values()) {
      if (!sound) continue;
      try {
        sound.dispose();
      } catch {
        /* ignore */
      }
    }
    this.soundCache.clear();
    this.engine = null;
    this.currentLocation = null;
    this.currentEra = "present";
    this.ducked = false;
  }

  // ---------------------------------------------------------------------------
  // Internals

  /** Chain a swap onto {@link swapChain} so successive calls serialise. */
  private _scheduleSwap(fadeSec: number): Promise<void> {
    const targetBedId = this._currentBedId();
    const next = this.swapChain.then(() => this._performSwap(targetBedId, fadeSec));
    // Swallow errors at the chain root so one bad swap doesn't break the next.
    this.swapChain = next.catch((err) => {
      console.warn("[ambience] swap failed:", err);
    });
    return next;
  }

  private _currentBedId(): string | null {
    if (!this.currentLocation) return null;
    return `bed_${this.currentLocation}_${this.currentEra}`;
  }

  private async _performSwap(targetBedId: string | null, fadeSec: number): Promise<void> {
    if (!this.engine) return;
    if (targetBedId === this.current?.id) return;

    const newSound = targetBedId ? await this._loadBed(targetBedId) : null;
    const oldSlot = this.current;
    const target = this._targetVolume();

    // Start the new bed at silence + fade in.
    if (newSound) {
      newSound.volume = 0;
      try {
        newSound.play({ loop: true });
      } catch (err) {
        console.warn(`[ambience] play failed for ${targetBedId}:`, err);
      }
      this._rampVolume(newSound, target, fadeSec);
      this.current = { id: targetBedId!, sound: newSound };
      console.info(`[ambience] → ${targetBedId} (fade ${fadeSec}s, target ${target.toFixed(2)})`);
    } else {
      this.current = null;
      console.info(`[ambience] → (silence) (fade ${fadeSec}s)`);
    }

    // Fade the old bed to zero, then stop it. We do not dispose — the cache
    // keeps the loaded buffer so revisiting a location is cheap.
    if (oldSlot) {
      this._rampVolume(oldSlot.sound, 0, fadeSec);
      // Wait the crossfade out before stopping so we don't audibly cut.
      await _sleep(fadeSec * 1000);
      try {
        oldSlot.sound.stop();
      } catch {
        /* ignore — sound may already be stopped */
      }
    }
  }

  /**
   * Lazy-load a bed by id. Returns `null` (and caches the null) when the
   * file is missing so we don't retry on every swap.
   */
  private async _loadBed(bedId: string): Promise<StaticSound | null> {
    if (this.soundCache.has(bedId)) return this.soundCache.get(bedId) ?? null;
    if (!this.engine) return null;

    const url = `${BED_URL_PREFIX}${bedId}.ogg`;
    try {
      const sound = await CreateSoundAsync(
        bedId,
        url,
        { loop: true, volume: 0 },
        this.engine,
      );
      this.soundCache.set(bedId, sound);
      return sound;
    } catch (err) {
      console.warn(`[ambience] bed missing or failed to load: ${url}`, err);
      this.soundCache.set(bedId, null);
      return null;
    }
  }

  private _targetVolume(): number {
    return BASE_VOLUME * (this.ducked ? DUCK_FACTOR : 1.0);
  }

  private _rampVolume(sound: StaticSound, target: number, durationSec: number): void {
    if (durationSec <= 0) {
      sound.volume = target;
      return;
    }
    try {
      sound.setVolume(target, {
        duration: durationSec,
        shape: AudioParameterRampShape.Linear,
      });
    } catch (err) {
      // Fall back to immediate set — happens if a ramp is already in flight.
      console.warn("[ambience] volume ramp failed, setting immediately:", err);
      sound.volume = target;
    }
  }
}

// ---------------------------------------------------------------------------

function _sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** App-wide singleton. Owned by {@link AudioManager}. */
export const ambienceEngine = new AmbienceEngineImpl();
