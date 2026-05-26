/**
 * Physics
 *
 * Wraps `@babylonjs/havok` initialization and `PhysicsAggregate` registration.
 *
 * Per CLAUDE.md and ARCHITECTURE.md §5.3: Havok is the only permitted physics
 * backend. Cannon/Ammo are forbidden. Default gravity is real (-9.81), no
 * fudge factor (rejecting prototype audit §7 issue 1).
 *
 * Lifecycle:
 *   await Physics.init(scene)         // boot WASM module, enable scene physics
 *   const agg = Physics.aggregate(...) // register a body — respects profile cap
 *   Physics.dispose()                  // release plugin on mission teardown
 *
 * The aggregate budget per profile (ARCHITECTURE.md §6 + §7.5) is enforced:
 * the (cap+1)th dynamic body is rejected with a warning and falls back to
 * `PhysicsMotionType.STATIC`.
 */

import HavokPhysics from "@babylonjs/havok";
import {
  HavokPlugin,
  PhysicsAggregate,
  PhysicsMotionType,
  PhysicsShapeType,
  Vector3,
} from "@babylonjs/core";
import type { Scene, TransformNode } from "@babylonjs/core";
import { engineConfig, worldConstants, type PerformanceProfile } from "./config";

let plugin: HavokPlugin | null = null;
let dynamicCount = 0;
let activeProfile: PerformanceProfile = "medium";

export interface AggregateOptions {
  shape: PhysicsShapeType;
  mass: number;
  /** Restitution (bounciness). 0 = no bounce. */
  restitution?: number;
  /** Friction coefficient. */
  friction?: number;
}

/**
 * Boot the Havok WASM module and enable physics on `scene`.
 * Idempotent: a second call returns the existing plugin.
 *
 * @throws if the WASM fetch or instantiation fails. Caller decides whether to
 *         degrade gracefully (e.g., disable physics-dependent features) or
 *         abort mission load.
 */
export async function init(scene: Scene, profile: PerformanceProfile): Promise<HavokPlugin> {
  if (plugin) return plugin;
  activeProfile = profile;
  const havok = await HavokPhysics();
  plugin = new HavokPlugin(true, havok);
  scene.enablePhysics(new Vector3(0, worldConstants.gravityY, 0), plugin);
  return plugin;
}

/**
 * Register a `PhysicsAggregate` for `node`. Enforces the per-profile dynamic
 * body cap (ARCHITECTURE.md §6) — excess registrations fall back to STATIC.
 *
 * @returns the aggregate, or null if physics has not been initialized yet.
 *          Callers MUST treat null as a recoverable degraded state, not an
 *          error — fail-soft per ARCHITECTURE.md §10.3.
 */
export function aggregate(node: TransformNode, opts: AggregateOptions): PhysicsAggregate | null {
  if (!plugin) return null;

  const cap = engineConfig[activeProfile].dynamicPhysicsBodyCap;
  const wantsDynamic = opts.mass > 0;
  const allowDynamic = wantsDynamic && dynamicCount < cap;

  const agg = new PhysicsAggregate(node, opts.shape, {
    mass: allowDynamic ? opts.mass : 0,
    restitution: opts.restitution ?? 0,
    friction: opts.friction ?? 0.6,
  });

  if (wantsDynamic && !allowDynamic) {
    console.warn(
      `[physics] dynamic budget (${cap}) reached — '${node.name}' downgraded to static`,
    );
    agg.body.setMotionType(PhysicsMotionType.STATIC);
  } else if (allowDynamic) {
    dynamicCount++;
  }

  return agg;
}

/**
 * Mark an aggregate as inactive — used for the era variant the camera
 * cannot see, per CHRONOS_SWITCH.md and ARCHITECTURE.md §7.5.
 *
 * Cost: ~zero per Havok step (the body is excluded from the broadphase).
 */
export function freezeAggregate(agg: PhysicsAggregate): void {
  agg.body.disablePreStep = true;
  agg.body.setMotionType(PhysicsMotionType.STATIC);
}

/** Re-enable a previously frozen aggregate. */
export function thawAggregate(agg: PhysicsAggregate, motion: PhysicsMotionType): void {
  agg.body.disablePreStep = false;
  agg.body.setMotionType(motion);
}

/** Dispose the plugin and reset counters. Called on mission teardown. */
export function dispose(): void {
  plugin?.dispose();
  plugin = null;
  dynamicCount = 0;
}

/** Test/debug accessor — returns the active plugin or null. */
export function getPlugin(): HavokPlugin | null {
  return plugin;
}
