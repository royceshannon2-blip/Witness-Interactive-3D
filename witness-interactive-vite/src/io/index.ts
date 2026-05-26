/**
 * Barrel for `io/`. ARCHITECTURE.md §5.7.
 *
 * Three runtime asset owners, one per kind produced by `tools/asset_pipeline.py`:
 *   - `AssetLibrary`  → `.glb` containers (mesh + animated kinds)
 *   - `SplatLibrary`  → `.ply` / `.splat` / `.spz` / `.sog` (splat kind)
 *   - `TilesetMount`  → 3D Tilesets via 3DTilesRendererJS adapter (tileset kind)
 *
 * Per `.claude/rules/asset-pipeline.md`, runtime code never hardcodes URLs;
 * it always goes through one of these owners.
 */

export { AssetLibrary } from "./AssetLibrary";
export { SplatLibrary, SPLAT_EXTENSIONS } from "./SplatLibrary";
export type { LoadedSplat, SplatExtension, SplatLoadOptions } from "./SplatLibrary";
export { TilesetMount } from "./TilesetMount";
export type { MountedTileset, TilesetRendererAdapter } from "./TilesetMount";

export {
  save as saveGame,
  load as loadGame,
  applyState as applySavedState,
  list as listSaves,
  remove as removeSave,
} from "./SaveSystem";
export type { SaveBlob } from "./SaveSystem";
