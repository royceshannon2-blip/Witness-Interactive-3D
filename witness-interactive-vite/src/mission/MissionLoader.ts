/**
 * MissionLoader
 *
 * Orchestrates the load/unload lifecycle of a mission, per
 * ARCHITECTURE.md §3.1, §3.3, §5.9.
 *
 * Lifecycle on load:
 *   1. fetch + validate manifest
 *   2. assetLibrary.preload(manifest.requiredAssets)
 *   3. world.build(scene, manifest, library) — places meshes, tags eras
 *   4. narrative.loadGraph(manifest.narrativeGraph)
 *   5. audio.init(manifest.audio)
 *   6. emit 'ready'
 *
 * Lifecycle on unload (also called when load() is invoked while another
 * mission is active):
 *   1. emit 'willUnload'
 *   2. scene.blockfreeActiveMeshesAndRenderingGroups = true
 *   3. world.tearDown(scene); assetLibrary.dispose(...)
 *   4. scene.blockfreeActiveMeshesAndRenderingGroups = false
 *   5. emit 'unloaded'
 *
 * v1 scope: this scaffold owns the validation + event surface. The actual
 * preload + build calls are TODOs flagged below — they hook up when a real
 * mission JSON exists at `public/missions/<id>/manifest.json`.
 */

import type { Manifest } from "./Manifest";

export type MissionEvent = "willLoad" | "ready" | "willUnload" | "unloaded";
export type MissionListener = (event: MissionEvent, manifest: Manifest | null) => void;

class MissionLoaderImpl {
  private current: Manifest | null = null;
  private readonly listeners = new Set<MissionListener>();

  /** Currently-loaded manifest, or null if none. */
  get currentManifest(): Manifest | null {
    return this.current;
  }

  /**
   * Load a mission. If another is active, unloads it first.
   *
   * @param source URL string (fetched + parsed) or pre-parsed Manifest object
   *               (test/dev). v1 scaffold accepts both; production missions
   *               always go through URL.
   */
  async load(source: string | Manifest): Promise<void> {
    if (this.current) await this.unload();

    const manifest = typeof source === "string" ? await this.fetchManifest(source) : source;
    this.validate(manifest);

    this.emit("willLoad", manifest);
    // TODO(vertical-slice): once io/AssetLibrary, world/, and audio/ are wired,
    // call them here in the order from ARCHITECTURE.md §3.1. For now we just
    // record the manifest and emit ready so the bootstrap can proceed.
    this.current = manifest;
    this.emit("ready", manifest);
  }

  async unload(): Promise<void> {
    if (!this.current) return;
    const m = this.current;
    this.emit("willUnload", m);
    // TODO(vertical-slice): teardown sequence per ARCHITECTURE.md §3.3.
    this.current = null;
    this.emit("unloaded", m);
  }

  /** Subscribe to lifecycle events. Returns an unsubscribe function. */
  subscribe(listener: MissionListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  // ---------------------------------------------------------------------------

  private async fetchManifest(url: string): Promise<Manifest> {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Manifest fetch failed: ${res.status} ${res.statusText} (${url})`);
    return (await res.json()) as Manifest;
  }

  /**
   * Surface-level validation. Deep validation (asset existence, graph
   * integrity) belongs in `tools/validate_manifest.py` at CI time.
   */
  private validate(m: Manifest): void {
    const required: (keyof Manifest)[] = [
      "id",
      "version",
      "title",
      "provenance",
      "requiredAssets",
      "locations",
      "anchors",
      "narrativeGraph",
      "audio",
    ];
    for (const k of required) {
      if (m[k] === undefined || m[k] === null) {
        throw new Error(`Manifest validation: missing field '${String(k)}' on '${m.id ?? "<unknown>"}'`);
      }
    }
    if (!m.locations.length) {
      throw new Error(`Manifest '${m.id}': must declare at least one location`);
    }
  }

  private emit(event: MissionEvent, manifest: Manifest | null): void {
    for (const listener of this.listeners) listener(event, manifest);
  }
}

/** App-wide singleton. */
export const missionLoader = new MissionLoaderImpl();
