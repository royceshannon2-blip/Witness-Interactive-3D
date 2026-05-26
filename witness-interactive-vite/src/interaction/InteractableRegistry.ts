/**
 * InteractableRegistry
 *
 * Maps clickable/E-keyable meshes to handler callbacks. Per
 * ARCHITECTURE.md §5.5 + §7.2: pointer-move picking is OFF on LOW/MEDIUM
 * profiles; picks happen only on click or E-press, and only against
 * registered meshes.
 *
 * Handlers are responsible for triggering narrative events. The registry
 * itself never mutates world or narrative state — it just dispatches.
 */

import { KeyboardEventTypes, PointerEventTypes } from "@babylonjs/core";
import type {
  AbstractMesh,
  KeyboardInfo,
  Observer,
  PointerInfo,
  Scene,
} from "@babylonjs/core";

export type InteractableHandler = (mesh: AbstractMesh) => void;

class InteractableRegistryImpl {
  private readonly handlers = new Map<AbstractMesh, InteractableHandler>();
  private kbObs: Observer<KeyboardInfo> | null = null;
  private ptrObs: Observer<PointerInfo> | null = null;
  private scene: Scene | null = null;
  /** Nearest in-range mesh set by the proximity probe each frame. */
  private nearestHint: AbstractMesh | null = null;

  /** Wire the registry to scene-level click + E-key observables. */
  attach(scene: Scene): void {
    if (this.scene) return;
    this.scene = scene;
    scene.skipPointerMovePicking = true; // ARCHITECTURE.md §7.2
    this.ptrObs = scene.onPointerObservable.add((info) => this.onPointer(info));
    this.kbObs = scene.onKeyboardObservable.add((info) => this.onKeyboard(info));
  }

  detach(): void {
    if (!this.scene) return;
    if (this.ptrObs) this.scene.onPointerObservable.remove(this.ptrObs);
    if (this.kbObs) this.scene.onKeyboardObservable.remove(this.kbObs);
    this.ptrObs = null;
    this.kbObs = null;
    this.scene = null;
    this.handlers.clear();
  }

  /**
   * Register a mesh. Marks the mesh `metadata.interactive = true` so the
   * freeze pass (performance/) skips it.
   */
  register(mesh: AbstractMesh, handler: InteractableHandler): void {
    mesh.isPickable = true;
    mesh.metadata = { ...(mesh.metadata ?? {}), interactive: true };
    this.handlers.set(mesh, handler);
  }

  unregister(mesh: AbstractMesh): void {
    this.handlers.delete(mesh);
    if (this.nearestHint === mesh) this.nearestHint = null;
  }

  /**
   * Called by the proximity probe each frame with the closest in-range mesh
   * (or null when nothing is near). The E-key handler uses this so the player
   * doesn't need to aim the mouse at the mesh — standing close is enough.
   */
  setNearestHint(mesh: AbstractMesh | null): void {
    this.nearestHint = mesh;
  }

  /** Returns true when a mesh is close enough that E-key will trigger it. */
  hasNearby(): boolean {
    return this.nearestHint !== null;
  }

  // ---------------------------------------------------------------------------

  private onPointer(info: PointerInfo): void {
    if (info.type !== PointerEventTypes.POINTERDOWN) return;
    if (info.event.button !== 0) return; // left click only
    this.dispatchPick();
  }

  private onKeyboard(info: KeyboardInfo): void {
    if (info.type !== KeyboardEventTypes.KEYDOWN) return;
    if (info.event.code !== "KeyE") return;
    // Prefer the proximity-probe hint (player standing near the mesh) over a
    // pointer pick, so E works without the mouse hovering directly on the mesh.
    if (this.nearestHint) {
      const handler = this.handlers.get(this.nearestHint);
      if (handler) { handler(this.nearestHint); return; }
    }
    this.dispatchPick();
  }

  private dispatchPick(): void {
    if (!this.scene) return;
    const result = this.scene.pick(
      this.scene.pointerX,
      this.scene.pointerY,
      (m) => this.handlers.has(m),
    );
    if (!result?.hit || !result.pickedMesh) return;
    const handler = this.handlers.get(result.pickedMesh);
    handler?.(result.pickedMesh);
  }
}

/** App-wide singleton. */
export const interactableRegistry = new InteractableRegistryImpl();
