/**
 * AssetLibrary
 *
 * The single owner of `LoadAssetContainerAsync`. All GLB/Draco/KTX2 loads go
 * through here so the loader pipeline (registration of loaders, decoder URLs)
 * is configured exactly once.
 *
 * Per ARCHITECTURE.md §5.7 + §8.2: bounded N=4 concurrency on `preload`,
 * Map-cache by id, never adds to the scene at preload time. Per
 * `instantiate`, meshes get added and tagged.
 *
 * v1 implementation: real preload with bounded concurrency. The instantiate
 * path is functional but minimal; placement metadata (era tag, transform) is
 * the caller's responsibility.
 */

import { LoadAssetContainerAsync } from "@babylonjs/core";
import type { AssetContainer, InstantiatedEntries, Scene } from "@babylonjs/core";
import "@babylonjs/loaders/glTF";

export class AssetLibrary {
  private readonly cache = new Map<string, AssetContainer>();
  private readonly scene: Scene;
  /** Resolves an asset id to a URL. Replace via `setResolver` when a manifest pins paths. */
  private resolver: (id: string) => string;

  constructor(scene: Scene) {
    this.scene = scene;
    this.resolver = (id) => `/assets/${id}.glb`;
  }

  /** Override the id→URL resolver. Mission loaders set this from the manifest. */
  setResolver(resolver: (id: string) => string): void {
    this.resolver = resolver;
  }

  /**
   * Preload N=4 in parallel. Returns when all containers are cached.
   * Containers are NOT added to the scene; call `instantiate` for that.
   */
  async preload(ids: string[]): Promise<void> {
    const remaining = ids.filter((id) => !this.cache.has(id));
    if (!remaining.length) return;

    const limit = 4;
    const queue = [...remaining];
    const inflight: Promise<void>[] = [];

    const startNext = (): boolean => {
      const id = queue.shift();
      if (!id) return false;
      const p = this.loadOne(id).finally(() => {
        const idx = inflight.indexOf(p);
        if (idx !== -1) inflight.splice(idx, 1);
      });
      inflight.push(p);
      return true;
    };

    while (inflight.length < limit && startNext()) {
      // saturate
    }
    while (inflight.length) {
      await Promise.race(inflight);
      while (inflight.length < limit && startNext()) {
        // keep saturating until queue empty
      }
    }
  }

  /**
   * Get a previously preloaded container. Throws if it was never loaded —
   * caller bug, since manifests preload everything they need at boot.
   */
  get(id: string): AssetContainer {
    const c = this.cache.get(id);
    if (!c) throw new Error(`Asset '${id}' not preloaded — call preload([...]) first`);
    return c;
  }

  /**
   * Instantiate a copy of `id` into the scene. The returned `InstantiatedEntries`
   * contains the root nodes; caller is expected to position + tag them with
   * `tagNode(node, eraScope)` from `core/`.
   */
  instantiate(id: string): InstantiatedEntries {
    return this.get(id).instantiateModelsToScene();
  }

  /**
   * Dispose containers by id. Called on mission unload; ARCHITECTURE.md §3.3.
   */
  dispose(ids: string[]): void {
    for (const id of ids) {
      const c = this.cache.get(id);
      if (!c) continue;
      c.removeAllFromScene();
      c.dispose();
      this.cache.delete(id);
    }
  }

  /** Drop everything. Used at mission teardown when re-resolving asset paths. */
  clear(): void {
    for (const [id] of this.cache) {
      this.dispose([id]);
    }
  }

  // ---------------------------------------------------------------------------

  private async loadOne(id: string): Promise<void> {
    if (this.cache.has(id)) return;
    const url = this.resolver(id);
    const container = await LoadAssetContainerAsync(url, this.scene);
    this.cache.set(id, container);
  }
}
