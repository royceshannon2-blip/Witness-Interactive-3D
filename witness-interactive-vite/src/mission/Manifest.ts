/**
 * Mission Manifest schema.
 *
 * Per SCALABILITY_PLAN.md, every mission lives at
 * `public/missions/<mission-id>/manifest.json` and conforms to this shape.
 * The engine reads only data; everything else (code paths, asset bindings,
 * narrative graph) is data-driven.
 *
 * This file defines the TypeScript surface. The full JSON Schema lives in
 * `tools/validate_manifest.py` (to be authored) so the same schema is
 * authoritative for runtime + CI.
 */

/** Top-level manifest. */
export interface Manifest {
  /** Stable id, kebab-case. Becomes the directory name. */
  id: string;
  /** Schema version. Bumped when breaking changes land in this file. */
  version: string;
  /** Display name shown in UI. */
  title: string;
  /** Short tagline shown in mission picker. */
  summary: string;
  /** Historical provenance — required so missions can't ship without context. */
  provenance: ProvenanceBlock;
  /** Required assets, by id. Resolved against the asset registry. */
  requiredAssets: string[];
  /** Locations the player can visit. */
  locations: LocationDecl[];
  /** Memory Fragment anchors — the Present-era objects that trigger era switches. */
  anchors: AnchorDecl[];
  /** Path to the narrative graph JSON (relative to mission root). */
  narrativeGraph: string;
  /** Audio bundle config. */
  audio: AudioConfig;
  /** Optional starting era. Defaults to 'present'. */
  startEra?: "present" | "past";
  /** Optional starting location id. Defaults to first declared location. */
  startLocation?: string;
  /** Optional minimum performance profile. Mission refuses to load below this tier. */
  minProfile?: "low" | "medium" | "high";
}

export interface ProvenanceBlock {
  /** Year(s) the mission depicts. e.g., "1994" or "1994-2026". */
  era: string;
  /** Region or country. e.g., "Bisesero, Rwanda". */
  region: string;
  /** Primary historical sources cited. URLs or freeform refs. */
  sources: string[];
  /** Sensitivity notes. Ledger-tone language only — no military vocabulary. */
  sensitivityNotes?: string;
}

export interface LocationDecl {
  id: string;
  /** Display name (HUD, ledger). */
  name: string;
  /** World-space coordinates the location is built around. */
  origin: { x: number; y: number; z: number };
  /** Asset ids placed within this location's bounds. */
  assets: string[];
  /** Audio zones declared at this location. */
  audioZones: AudioZoneDecl[];
}

export interface AnchorDecl {
  id: string;
  /** Location id this anchor belongs to. */
  location: string;
  /** Narrative graph node this anchor advances. */
  graphNode: string;
  /** World-space position of the proximity trigger. */
  position: { x: number; y: number; z: number };
  /** Trigger radius in metres. */
  radius: number;
  /** Optional: ledger entry key to play on activation. */
  narratorEntry?: string;
}

export interface AudioZoneDecl {
  id: string;
  /** Centre of the zone. */
  position: { x: number; y: number; z: number };
  /** Audible radius in metres. */
  radius: number;
  /** Source file path, relative to mission root. */
  source: string;
  /** Era the zone is active in. */
  era: "present" | "past" | "shared";
}

export interface AudioConfig {
  /** Directory containing pre-baked narrator lines (relative to mission root). */
  narratorDir: string;
  /** Default narrator volume in linear gain. */
  narratorGain: number;
}
