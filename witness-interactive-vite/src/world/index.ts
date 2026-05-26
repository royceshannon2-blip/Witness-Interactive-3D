/**
 * Barrel for `world/`. Per ARCHITECTURE.md §5.4: imports `engine/` and
 * `core/` only — never `narrative/`.
 */

export { buildTerrain } from "./Terrain";
export type { Terrain, TerrainConfig, HeightSampler } from "./Terrain";

export {
  buildFamilyCompound,
  buildRavine,
  buildLakeShore,
  RAVINE_VANTAGE_POSITION,
  LAKE_DOCK_POSITION,
} from "./locations";
export type {
  FamilyCompoundHandle,
  RavineHandle,
  LakeShoreHandle,
} from "./locations";
