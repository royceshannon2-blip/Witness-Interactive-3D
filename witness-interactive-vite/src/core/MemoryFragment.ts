/**
 * MemoryFragment
 *
 * A Present-era trigger placed at a witness location. Per
 * `docs/design-docs/MISSION_BLUEPRINT.md` (anchor-echo system) and
 * ARCHITECTURE.md §5.1: when the player interacts with a fragment in the
 * 2026 ruin, the narrative records a puzzle completion and the world
 * transitions to the 1994 Past for the corresponding echo.
 *
 * Fragment lifecycle:
 *   1. Construct with a Present-era mesh + a stable fragmentId.
 *   2. Mesh is tagged `LAYER_PRESENT` and registered with
 *      `interactableRegistry`. Activation requires a click or E-press
 *      while looking at the mesh.
 *   3. On first activation:
 *        a. Set flag `fragment_<id>_activated` so re-runs are idempotent
 *           and save files capture state.
 *        b. `narrativeController.triggerPuzzleCompletion(fragmentId)`.
 *        c. Optional `onActivate` hook (lets callers play SFX/animations
 *           before the era flip — kept synchronous-friendly via Promise).
 *        d. `timeManager.transition(opts.transitionTo)` — defaults to
 *           `"past"`; pass `null` to skip and let a narrative action
 *           drive the transition instead.
 *
 * Re-activations are no-ops; this class never reverses state.
 *
 * Boundary discipline: MemoryFragment is allowed to call narrative APIs
 * because it lives in `core/`, which is the single seam where world
 * triggers and narrative meet (see ARCHITECTURE.md §5.1). World/scene
 * code should never import this — it should construct fragments via the
 * mission loader and let them dispatch.
 */

import type { AbstractMesh } from "@babylonjs/core";
import { tagNode } from "./LayerMasks";
import { type Era, timeManager } from "./TimeManager";
import { globalState } from "../narrative/StateManager";
import { narrativeController } from "../narrative/NarrativeController";
import { createLog } from "../log";

const log = createLog("fragment");

/** Flag prefix for fragment activation state. Lives in `globalState.flagsSet`. */
export const FRAGMENT_FLAG_PREFIX = "fragment_";

/** Per-fragment configuration. */
export interface MemoryFragmentOpts {
  /**
   * Era to transition to on activation. `null` disables the auto-transition
   * (e.g. when a narrative action will drive it instead). Default `"past"`.
   */
  transitionTo?: Era | null;

  /** Crossfade seconds passed to `timeManager.transition`. Default `0`. */
  transitionDurationSec?: number;

  /**
   * Optional async hook fired after puzzle completion and before the era
   * transition. Use it for fragment-local SFX, camera punch, etc. Resolved
   * value is awaited so the transition waits for the hook.
   */
  onActivate?: (fragmentId: string) => void | Promise<void>;
}

/** Build the activation flag key for a given fragment id. */
export function fragmentActivatedFlag(fragmentId: string): string {
  return FRAGMENT_FLAG_PREFIX + fragmentId + "_activated";
}

export class MemoryFragment {
  readonly id: string;
  readonly mesh: AbstractMesh;
  private readonly opts: Required<Omit<MemoryFragmentOpts, "onActivate">> & {
    onActivate?: MemoryFragmentOpts["onActivate"];
  };
  private firing = false;
  private disposed = false;

  /**
   * Build a fragment without registering interaction. Pair with
   * `bindInteraction(register)` to plug in `interactableRegistry.register`
   * — the indirection keeps `core/` independent of `interaction/`.
   *
   * @param mesh       Present-era mesh in the scene. Will be re-tagged
   *                   `LAYER_PRESENT` regardless of any prior tag.
   * @param fragmentId Stable id used as both narrative puzzle id and the
   *                   activation flag suffix. Must not change across saves.
   * @param opts       Activation behaviour overrides.
   */
  constructor(mesh: AbstractMesh, fragmentId: string, opts: MemoryFragmentOpts = {}) {
    this.id = fragmentId;
    this.mesh = mesh;
    this.opts = {
      transitionTo: opts.transitionTo === null ? null : (opts.transitionTo ?? "past"),
      transitionDurationSec: opts.transitionDurationSec ?? 0,
      onActivate: opts.onActivate,
    };

    tagNode(mesh, "present");
    mesh.metadata = { ...(mesh.metadata ?? {}), fragmentId, interactive: true };
  }

  /** True once the fragment has been activated (this run or a loaded save). */
  get activated(): boolean {
    return globalState.getFlag(fragmentActivatedFlag(this.id));
  }

  /**
   * Hand off the mesh-handler pair to the interaction layer. Caller passes
   * `interactableRegistry.register.bind(interactableRegistry)` (or any
   * compatible function) so this module avoids a hard dependency on
   * `interaction/`.
   */
  bindInteraction(register: (mesh: AbstractMesh, handler: (m: AbstractMesh) => void) => void): void {
    register(this.mesh, () => {
      void this.activate();
    });
  }

  /**
   * Force an activation, bypassing the picking pathway. Used by cutscenes
   * and tests. Idempotent: no-ops once already activated or in flight.
   */
  async activate(): Promise<void> {
    if (this.disposed) return;
    if (this.firing) return;
    if (this.activated) {
      log.debug(`re-pick on already-activated fragment ${this.id}`);
      return;
    }
    this.firing = true;
    try {
      globalState.setFlag(fragmentActivatedFlag(this.id), true);
      log.info(`activate ${this.id}`);
      await narrativeController.triggerPuzzleCompletion(this.id, {
        kind: "memoryFragment",
        meshName: this.mesh.name,
      });
      if (this.opts.onActivate) {
        await this.opts.onActivate(this.id);
      }
      if (this.opts.transitionTo) {
        await timeManager.transition(this.opts.transitionTo, this.opts.transitionDurationSec);
      }
    } finally {
      this.firing = false;
    }
  }

  /**
   * Drop registration with whatever interaction layer holds the mesh. Like
   * `bindInteraction`, the unregister fn is supplied by the caller to keep
   * the dependency direction clean.
   */
  dispose(unregister?: (mesh: AbstractMesh) => void): void {
    if (this.disposed) return;
    this.disposed = true;
    unregister?.(this.mesh);
  }
}
