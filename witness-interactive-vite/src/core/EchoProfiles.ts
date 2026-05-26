/**
 * EchoProfiles
 *
 * Per-fragment cinematic parameters for the echo pre-roll and dwell phases.
 * Each profile gives a fragment a distinct spatial/emotional register so the
 * player feels a different quality of pull for each memory:
 *
 *   - Cellar echoes:   underground, compressed — FOV narrows, heavier pull.
 *   - Ravine echoes:   elevated, exposed — FOV slightly opens, light pull.
 *   - Lake echoes:     open water, outward urgency — slight narrowing.
 *   - Altar echoes:    intimate, reverent — moderate FOV and pull.
 *   - Path A (Hider):  weight and claustrophobia grow with each puzzle.
 *   - Path B (Escapist): expanding, the triage calculus of survival.
 *   - Path C (Observer): detached watch — widened FOV, gentlest pull.
 *
 * Values are intentionally non-disorienting (total camera motion ≤ 0.22 m,
 * |fovDelta| ≤ 0.08 rad) while remaining perceptibly distinct. See
 * CHRONOS_SWITCH.md §3.6 for the design intent behind the pre-roll beat.
 */

export interface EchoPrerollProfile {
  /**
   * FOV change in radians applied over the first half of the pre-roll, then
   * returned to baseline in the second half. Negative = narrows (underground,
   * intimate). Positive = opens (elevated, exposed).
   */
  fovDelta: number;
  /** Total pre-roll duration in seconds. Longer for heavier echoes. */
  durationSec: number;
  /**
   * Metres to pull the camera toward the anchor during pre-roll.
   * 0 = no pull. Clamped internally to keep ≥ 0.45 m from the anchor.
   */
  pullMag: number;
}

/** Per-fragment profiles, keyed by the fragment's `fragmentId`. */
export const ECHO_PROFILES: Readonly<Record<string, EchoPrerollProfile>> = {
  // ── Act 2: evidence anchors ──────────────────────────────────────────────
  // Cellar door latch — subterranean, weight of what's below
  cellar_door_latch:    { fovDelta: -0.06, durationSec: 0.65, pullMag: 0.18 },
  // Observer's journal — elevated, watching from a distance
  observer_notes:       { fovDelta: +0.02, durationSec: 0.50, pullMag: 0.10 },
  // Boat paddle — reaching toward the water, outward
  boat_paddle:          { fovDelta: -0.02, durationSec: 0.55, pullMag: 0.15 },
  // Family records / altar photo — intimate, looking down
  family_records:       { fovDelta: -0.05, durationSec: 0.60, pullMag: 0.12 },

  // ── Act 3A: Hider path — compression grows with each puzzle ──────────────
  // Cellar mats — the human scale of eight people, darkness below
  cellar_mats:          { fovDelta: -0.08, durationSec: 0.70, pullMag: 0.22 },
  // Water schedule — routine risk, each mark a day survived
  water_schedule:       { fovDelta: -0.06, durationSec: 0.65, pullMag: 0.16 },
  // Neighbor's letter — the cost of the choice, sealed gratitude
  neighbor_letter:      { fovDelta: -0.07, durationSec: 0.65, pullMag: 0.20 },

  // ── Act 3B: Escapist path — outward, expanding, the math of triage ───────
  // Passenger list — forty names, circled and crossed
  passenger_list:       { fovDelta: -0.03, durationSec: 0.55, pullMag: 0.14 },
  // Boat capacity board — arithmetic of survival, clinical
  boat_capacity_notes:  { fovDelta: -0.01, durationSec: 0.50, pullMag: 0.11 },
  // Escape route map — the journey outward, horizon-facing
  escape_route_map:     { fovDelta: +0.02, durationSec: 0.55, pullMag: 0.09 },
  // Survivor's letter — post-departure, gratitude across time
  survivor_letter:      { fovDelta: -0.04, durationSec: 0.60, pullMag: 0.13 },

  // ── Act 3C: Observer path — detached watch, widened perspective ───────────
  // Chalk patrol marks — reading the columns' routes, safe distance
  chalk_patrol_marks:   { fovDelta: +0.03, durationSec: 0.52, pullMag: 0.07 },
  // Checkpoint records — what he knew, what he kept
  checkpoint_records:   { fovDelta: +0.02, durationSec: 0.52, pullMag: 0.08 },
  // Reflection letters — writing by starlight, turned inward
  reflection_letters:   { fovDelta: +0.04, durationSec: 0.55, pullMag: 0.06 },
  // Visitor's account — post-1994, the consequence of silence
  visitor_account:      { fovDelta: -0.03, durationSec: 0.60, pullMag: 0.10 },
};

/** Fallback profile for any fragment not in `ECHO_PROFILES`. */
export const DEFAULT_ECHO_PROFILE: EchoPrerollProfile = {
  fovDelta:    -0.04,
  durationSec: 0.55,
  pullMag:     0,
};

/** Look up a profile by fragmentId, falling back to the default. */
export function getEchoProfile(fragmentId: string): EchoPrerollProfile {
  return ECHO_PROFILES[fragmentId] ?? DEFAULT_ECHO_PROFILE;
}
