/**
 * TilesetMount
 *
 * Runtime owner for 3D Tilesets (the OGC streamable LOD format used by
 * Cesium / Google PhotoRealistic 3D Tiles / etc.). Babylon does not ship a
 * native 3D Tiles renderer; the project mounts them via 3DTilesRendererJS
 * (https://github.com/NASA-AMMOS/3DTilesRendererJS), which can target
 * Babylon as a backend.
 *
 * The asset pipeline (`tools/asset_pipeline.py --kind tileset`) writes a
 * `<id>.tileset.json` record under `public/assets/`. The record names the
 * root URL of the actual tileset (`.tileset.json` per the OGC spec) — we
 * keep the indirection so missions can re-target a tileset without touching
 * code.
 *
 * v1 implementation: this module is a *scaffold*. It validates the record,
 * exposes a `mount(id)` API, and, when the 3DTilesRendererJS package is
 * present in `node_modules`, dynamically imports it and attaches the
 * tileset. Without the package installed, `mount` throws with a clear
 * install hint rather than silently producing an empty scene.
 *
 * Adding the dependency:
 *   cd witness-interactive-vite && npm install 3d-tiles-renderer
 *
 * Per `.claude/rules/asset-pipeline.md` §5, runtime code must not bypass
 * this module to fetch a tileset URL directly.
 */

import type { Scene, TransformNode } from "@babylonjs/core";

interface TilesetRecord {
  asset_id: string;
  kind: "tileset";
  era: string;
  root: string;
  registered: string;
}

export interface MountedTileset {
  /** The root transform node containing the streamed tileset content. */
  root: TransformNode;
  /** The pipeline record loaded from `<id>.tileset.json`. */
  record: TilesetRecord;
  /** Dispose the tileset: stops streaming, removes meshes, frees memory. */
  dispose(): void;
}

export class TilesetMount {
  private readonly mounted = new Map<string, MountedTileset>();
  private readonly scene: Scene;
  private resolver: (id: string) => string;

  constructor(scene: Scene) {
    this.scene = scene;
    this.resolver = (id) => `/assets/${id}.tileset.json`;
  }

  /** Override the id→record-URL resolver. */
  setResolver(resolver: (id: string) => string): void {
    this.resolver = resolver;
  }

  /**
   * Fetch the tileset record and mount the tileset under a fresh
   * `TransformNode`. Throws if the 3DTilesRendererJS package is missing.
   */
  async mount(id: string): Promise<MountedTileset> {
    const cached = this.mounted.get(id);
    if (cached) return cached;

    const recordUrl = this.resolver(id);
    const recordRes = await fetch(recordUrl);
    if (!recordRes.ok) {
      throw new Error(`TilesetMount: failed to fetch record at ${recordUrl} (${recordRes.status})`);
    }
    const record = (await recordRes.json()) as TilesetRecord;
    if (record.kind !== "tileset" || !record.root) {
      throw new Error(`TilesetMount: '${id}' is not a valid tileset record`);
    }

    const renderer = await this.tryLoadRendererPackage();
    if (!renderer) {
      throw new Error(
        "TilesetMount: 3DTilesRendererJS is not installed. " +
          "Run `cd witness-interactive-vite && npm install 3d-tiles-renderer` " +
          "and re-attempt the mission load.",
      );
    }

    const root = renderer.attach(this.scene, record.root);
    const handle: MountedTileset = {
      root,
      record,
      dispose: () => {
        renderer.detach(root);
        this.mounted.delete(id);
      },
    };
    this.mounted.set(id, handle);
    return handle;
  }

  /** Detach all tilesets. Called on mission unload per ARCHITECTURE.md §3.3. */
  detachAll(): void {
    for (const [, handle] of this.mounted) handle.dispose();
    this.mounted.clear();
  }

  // ---------------------------------------------------------------------------

  /**
   * Attempt to dynamically import the 3DTilesRendererJS Babylon adapter.
   * Returns `null` if the package isn't installed yet (so missions that
   * don't use 3D Tiles aren't blocked by a missing dependency).
   *
   * The shape returned here is intentionally minimal — we don't want to
   * hard-couple the project to a specific 3DTilesRenderer version. The real
   * adapter lives in a follow-up file (`io/_3dTilesAdapter.ts`) once we
   * commit to a version.
   */
  private async tryLoadRendererPackage(): Promise<TilesetRendererAdapter | null> {
    try {
      const adapter = await import(/* @vite-ignore */ "./_3dTilesAdapter");
      return adapter.default ?? null;
    } catch {
      return null;
    }
  }
}

/** Minimum surface required from the 3D Tiles renderer adapter. */
export interface TilesetRendererAdapter {
  attach(scene: Scene, rootUrl: string): TransformNode;
  detach(node: TransformNode): void;
}
