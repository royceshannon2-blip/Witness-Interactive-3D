/**
 * _3dTilesAdapter
 *
 * Bridge between `TilesetMount` and the 3DTilesRendererJS npm package.
 * Kept in a separate file so missions that don't use 3D Tiles aren't forced
 * to install the dependency: `TilesetMount` does a `await import('./_3dTilesAdapter')`
 * inside a try/catch and only reaches this file's runtime code if a tileset
 * is actually requested.
 *
 * The adapter stays minimal: `attach(scene, rootUrl) → TransformNode` and
 * `detach(node)`. Versions of 3DTilesRendererJS that ship a Babylon backend
 * register themselves through this thin shim. If the package is missing,
 * the dynamic import in TilesetMount fails and the user gets the install
 * hint there.
 *
 * v1: this is a stub. Wiring the real `3d-tiles-renderer` requires:
 *   1. `npm install 3d-tiles-renderer`
 *   2. Replace the throw below with the actual adapter calls.
 */

import { TransformNode } from "@babylonjs/core";
import type { Scene } from "@babylonjs/core";
import type { TilesetRendererAdapter } from "./TilesetMount";

const adapter: TilesetRendererAdapter = {
  attach(_scene: Scene, _rootUrl: string): TransformNode {
    throw new Error(
      "_3dTilesAdapter: stub implementation. Install 3d-tiles-renderer and " +
        "wire its Babylon backend before mounting tilesets at runtime.",
    );
  },

  detach(node: TransformNode): void {
    node.dispose();
  },
};

export default adapter;
