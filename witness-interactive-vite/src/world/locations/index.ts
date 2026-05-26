/**
 * Barrel for `world/locations/`.
 *
 * Each Bisesero canonical location (Family Compound, Lake Shore, Cellar,
 * Ravine, Heights) gets its own module that exports `build(scene,
 * materials)`. Per CHRONOS_SWITCH.md §8 milestones, the vertical slice ships
 * with FamilyCompound (M3, cellar_door_latch fragment) and Ravine (M4,
 * observer_notes fragment in Hidden mode).
 *
 * Adding a new location:
 *   1. Create `<LocationName>.ts` exporting `build(...)` per WORLD.md.
 *   2. Re-export from this file.
 *   3. Reference its asset ids in the mission manifest.
 */

export { buildFamilyCompound } from "./FamilyCompound";
export type { FamilyCompoundHandle } from "./FamilyCompound";

export { buildRavine, RAVINE_VANTAGE_POSITION } from "./Ravine";
export type { RavineHandle } from "./Ravine";

export { buildLakeShore, LAKE_DOCK_POSITION } from "./LakeShore";
export type { LakeShoreHandle } from "./LakeShore";
