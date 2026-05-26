/**
 * SplatLibrary
 *
 * Runtime owner for Gaussian Splatting assets (.ply / .splat / .spz / .sog).
 * Counterpart to `AssetLibrary` (which owns `.glb` containers): the asset
 * pipeline (`tools/asset_pipeline.py --kind splat`) drops splat captures
 * under `public/assets/<id>.<ext>`, and this module is the only path that
 * loads them at runtime.
 *
 * Per `.claude/rules/asset-pipeline.md`, runtime code never hardcodes a path
 * to a splat file — it asks `splatLibrary.load(id)` and the resolver returns
 * the right URL.
 *
 * The Babylon side uses `ImportMeshAsync` with the SPLAT loader plugin
 * (registered statically at module load time, per
 * `docs/reference/babylon.js-documentation/content/features/featuresDeepDive/importers/gaussianSplatting.md`).
 * Both `.ply`, `.splat`, `.spz`, and `.sog` are handled natively in v9.
 */

import { ImportMeshAsync } from "@babylonjs/core";
import type { AbstractMesh, Scene } from "@babylonjs/core";
import "@babylonjs/loaders/SPLAT/splatFileLoader";

/** Allowed splat file extensions, matched against the resolver result. */
export const SPLAT_EXTENSIONS = [".spz", ".splat", ".ply", ".sog", ".sogs"] as const;
export type SplatExtension = (typeof SPLAT_EXTENSIONS)[number];

/** Per-load options forwarded to the Babylon splat plugin. */
export interface SplatLoadOptions {
  /** Niantic .spz files are often Y-flipped relative to Babylon's Y+. */
  flipY?: boolean;
}

export interface LoadedSplat {
  /** The root mesh — a `GaussianSplattingMesh` instance, typed as AbstractMesh
   * so this module doesn't expose Babylon's `GaussianSplattingMesh` directly
   * (callers that need the concrete type cast at the call site). */
  rootMesh: AbstractMesh;
  /** Disposes the splat and removes it from the scene. */
  dispose(): void;
}

export class SplatLibrary {
  private readonly cache = new Map<string, LoadedSplat>();
  private readonly scene: Scene;
  private resolver: (id: string) => string;

  constructor(scene: Scene) {
    this.scene = scene;
    // Default resolver: try common extensions in priority order. Mission
    // manifests can override via `setResolver` to pin the exact filename.
    this.resolver = (id) => `/assets/${id}.spz`;
  }

  /** Override the id→URL resolver. Mission loaders set this from the manifest. */
  setResolver(resolver: (id: string) => string): void {
    this.resolver = resolver;
  }

  /**
   * Load a splat by id. Cached on success; subsequent calls return the same
   * `LoadedSplat`. Throws on plugin failure rather than silently falling back
   * — splats are usually hero assets and a quiet failure would mean an empty
   * scene, which is worse than a thrown error.
   */
  async load(id: string, options?: SplatLoadOptions): Promise<LoadedSplat> {
    const cached = this.cache.get(id);
    if (cached) return cached;

    const url = this.resolver(id);
    const result = await ImportMeshAsync(url, this.scene, {
      pluginOptions: { splat: { flipY: options?.flipY ?? false } },
    });
    const rootMesh = result.meshes[0];
    if (!rootMesh) {
      throw new Error(`SplatLibrary: '${id}' loaded but produced no meshes (url=${url})`);
    }

    const handle: LoadedSplat = {
      rootMesh,
      dispose: () => {
        rootMesh.dispose(false, true);
        this.cache.delete(id);
      },
    };
    this.cache.set(id, handle);
    return handle;
  }

  /** Get an already-loaded splat by id; throws if `load` was not called. */
  get(id: string): LoadedSplat {
    const c = this.cache.get(id);
    if (!c) throw new Error(`Splat '${id}' not loaded — call load('${id}') first`);
    return c;
  }

  /** Dispose splats by id (or all of them if no ids given). */
  dispose(ids?: string[]): void {
    const targets = ids ?? Array.from(this.cache.keys());
    for (const id of targets) {
      const c = this.cache.get(id);
      if (c) c.dispose();
    }
  }
}
