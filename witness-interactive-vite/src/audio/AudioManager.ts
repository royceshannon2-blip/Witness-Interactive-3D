/**
 * AudioManager
 *
 * Owns the audio engine, spatial zones, narrator track, and era transitions.
 * Per AUDIO_ARCHITECTURE.md and ARCHITECTURE.md §5.11.
 *
 * Sub-systems owned by AudioManager:
 *   - {@link AmbienceEngine}: per-location, per-era ambient beds + ducking
 *   - {@link NarratorSystem}: serialised narrator playback + caption sync
 *     (lives in its own module; attached at boot but uses AudioManager via
 *     {@link duckAmbience} + {@link playNarratorEntry}).
 *
 * v1 scope (M21):
 *   - real init() boots Babylon AudioEngineV2 with the profile's voice cap
 *   - setLocation / transitionToEra delegate to AmbienceEngine (M21)
 *   - playNarratorEntry / playEffect remain stubs until M19/M20 wav files land
 *   - duckAmbience delegates to AmbienceEngine.setDuck
 *
 * No runtime synthesis: all audio is pre-baked per the 2026-04-19 changelog.
 * `playNarratorEntry(key)` will fetch `/audios/narrator/<key>.ogg` once the
 * M19 generation pipeline produces files.
 */

import { CreateAudioEngineAsync } from "@babylonjs/core";
import type { AudioEngineV2, Scene } from "@babylonjs/core";
import { engineConfig, type PerformanceProfile } from "../engine/config";
import type { Era } from "../core";
import type { LocationKey } from "../narrative/BanterLibrary";
import { ambienceEngine } from "./AmbienceEngine";

/** Legacy long-form location ids accepted by {@link AudioManagerImpl.setLocation}. */
const LOCATION_ALIASES: Record<string, LocationKey> = {
  family_compound: "compound",
  lake_shore: "lakeshore",
  lake: "lakeshore",
};

class AudioManagerImpl {
  private engine: AudioEngineV2 | null = null;
  private profile: PerformanceProfile = "medium";
  private currentLocation: LocationKey | null = null;
  private currentEra: Era = "present";

  /** Boot the audio engine with the profile's voice cap. Idempotent. */
  async init(_scene: Scene, profile: PerformanceProfile): Promise<void> {
    if (this.engine) return;
    this.profile = profile;
    this.engine = await CreateAudioEngineAsync();
    const cap = engineConfig[profile].maxAudioVoices;
    console.info(`[audio] engine ready, voice cap=${cap}`);
    ambienceEngine.attach(this.engine);
  }

  /**
   * Switch the active zone. Accepts both canonical {@link LocationKey}s and
   * a few legacy long-form aliases (e.g. `"family_compound"`); see
   * {@link LOCATION_ALIASES}. Delegates to {@link AmbienceEngine} for the
   * actual crossfade.
   */
  setLocation(locationId: LocationKey | string): void {
    const canonical = _normalizeLocation(locationId);
    if (!canonical) {
      console.warn(`[audio] unknown location id: ${locationId}`);
      return;
    }
    this.currentLocation = canonical;
    console.info(`[audio] location → ${canonical}`);
    void ambienceEngine.setLocation(canonical);
  }

  /**
   * Crossfade ambient mix between eras. Delegates to {@link AmbienceEngine}
   * for the bed crossfade; resolves after the fade completes (or `durationMs`
   * if no swap is needed).
   */
  async transitionToEra(era: Era, durationMs: number): Promise<void> {
    const from = this.currentEra;
    this.currentEra = era;
    console.info(`[audio] era ${from} → ${era} over ${durationMs}ms`);
    const durationSec = Math.max(0, durationMs / 1000);
    await ambienceEngine.setEra(era, durationSec);
  }

  /** Pre-baked narrator entry. Stub: logs only until M19 wires Babylon Sound. */
  playNarratorEntry(entryKey: string): void {
    console.info(`[audio] narrator: ${entryKey}`);
  }

  /** Spatial SFX. Stub: logs only until M20 SFX clips land. */
  playEffect(effectKey: string, position?: { x: number; y: number; z: number }): void {
    console.info(`[audio] effect ${effectKey}${position ? ` @${position.x},${position.y},${position.z}` : ""}`);
  }

  /**
   * Duck or restore the ambient bed around narrator playback. When `duck` is
   * true the ambient mix is attenuated to 50% of its base volume; when false
   * it restores. Delegates to {@link AmbienceEngine}.
   */
  duckAmbience(duck: boolean): void {
    console.info(`[audio] ambience ${duck ? "ducked" : "restored"}`);
    ambienceEngine.setDuck(duck);
  }

  /** Profile getter — UI can show "8 voices on LOW" debug overlays. */
  get currentProfile(): PerformanceProfile {
    return this.profile;
  }

  /** Convenience for tests + dev overlays. */
  get currentLocationId(): LocationKey | null {
    return this.currentLocation;
  }
}

function _normalizeLocation(id: string): LocationKey | null {
  if (id in LOCATION_ALIASES) return LOCATION_ALIASES[id];
  if (id === "compound" || id === "cellar" || id === "lakeshore" || id === "ravine" || id === "heights") {
    return id;
  }
  return null;
}

export const audioManager = new AudioManagerImpl();
