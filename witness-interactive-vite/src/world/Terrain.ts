/**
 * Terrain
 *
 * Builds the ground mesh for a location. Two modes:
 *
 *   - **flat**: a single subdivided plane. Useful for boot/staging scenes
 *     and for locations whose hill profile is intentionally minimal.
 *   - **heightfield**: per-vertex displacement from a sampler function.
 *     Pattern salvaged from the Kigali prototype (PROTOTYPE_AUDIT.md §3) —
 *     `getApproxHeight` / `getFootprintMinHeight` / `isFlat` helpers move
 *     here so every world module shares one truth about terrain heights.
 *
 * Per CHRONOS_SWITCH.md §3.2, terrain is the canonical `LAYER_SHARED`
 * geometry — visible in both eras. Caller must `tagNode(ground, "shared")`
 * after build (this module deliberately does NOT depend on `core/` to keep
 * the dependency graph clean).
 */

import {
  Mesh,
  MeshBuilder,
  VertexBuffer,
} from "@babylonjs/core";
import type { Scene } from "@babylonjs/core";

export type HeightSampler = (x: number, z: number) => number;

export interface TerrainConfig {
  /** Side length of the ground in metres. */
  size: number;
  /** Number of subdivisions across the plane. Higher = smoother, costlier. */
  subdivisions: number;
  /**
   * Optional height sampler. If omitted, the ground stays flat. The sampler
   * receives world-space x/z and returns world-space y. Keep it deterministic
   * and side-effect free.
   */
  heightSampler?: HeightSampler;
}

export interface Terrain {
  /** The ground mesh. Caller positions it and tags it with the era scope. */
  ground: Mesh;
  /** Sample height at any world (x, z). Returns 0 for the flat-plane fallback. */
  getHeight: (x: number, z: number) => number;
  /** Lowest y over a footprint of width × depth at (cx, cz). */
  getFootprintMinHeight: (cx: number, cz: number, w: number, d: number) => number;
  /**
   * Is the area within `radius` of (cx, cz) flat enough (max-min ≤ tolerance)
   * to place a structure? Returns true for the flat-plane fallback.
   */
  isFlat: (cx: number, cz: number, radius: number, tolerance: number) => boolean;
}

/**
 * Build the ground. Cheap for the flat case; the heightfield case displaces
 * vertices using `config.heightSampler`.
 */
export function buildTerrain(scene: Scene, config: TerrainConfig): Terrain {
  const ground = MeshBuilder.CreateGround(
    "terrain",
    { width: config.size, height: config.size, subdivisions: config.subdivisions },
    scene,
  );
  ground.checkCollisions = true;

  const sampler = config.heightSampler;
  if (sampler) {
    applyHeightfield(ground, sampler);
  }

  const getHeight: (x: number, z: number) => number = sampler ?? (() => 0);

  return {
    ground,
    getHeight,
    getFootprintMinHeight: (cx, cz, w, d) => footprintMin(cx, cz, w, d, getHeight),
    isFlat: (cx, cz, radius, tolerance) => spotIsFlat(cx, cz, radius, tolerance, getHeight),
  };
}

/**
 * Walk the mesh's vertex positions and apply the sampler. The mesh keeps a
 * fresh normal recomputation so PBR lighting reads correctly.
 */
function applyHeightfield(ground: Mesh, sampler: HeightSampler): void {
  const positions = ground.getVerticesData(VertexBuffer.PositionKind);
  if (!positions) {
    throw new Error("Terrain build: ground mesh has no position buffer");
  }
  const next = positions.slice();
  for (let i = 0; i < next.length; i += 3) {
    const x = next[i];
    const z = next[i + 2];
    next[i + 1] = sampler(x, z);
  }
  ground.updateVerticesData(VertexBuffer.PositionKind, next, true);
  ground.createNormals(true);
}

/**
 * 4-corner footprint min — same approach as the prototype, generalized so
 * structure builders never sample unevenly.
 */
function footprintMin(
  cx: number,
  cz: number,
  w: number,
  d: number,
  sampler: HeightSampler,
): number {
  const hw = w * 0.5;
  const hd = d * 0.5;
  return Math.min(
    sampler(cx - hw, cz - hd),
    sampler(cx + hw, cz - hd),
    sampler(cx - hw, cz + hd),
    sampler(cx + hw, cz + hd),
    sampler(cx, cz),
  );
}

/**
 * Reject placements that would tip a building. Samples at 8 points around
 * the radius and the centre; rejects if max - min > tolerance.
 */
function spotIsFlat(
  cx: number,
  cz: number,
  radius: number,
  tolerance: number,
  sampler: HeightSampler,
): boolean {
  let min = Infinity;
  let max = -Infinity;
  for (let i = 0; i < 8; i++) {
    const angle = (Math.PI * 2 * i) / 8;
    const x = cx + Math.cos(angle) * radius;
    const z = cz + Math.sin(angle) * radius;
    const y = sampler(x, z);
    if (y < min) min = y;
    if (y > max) max = y;
  }
  const centre = sampler(cx, cz);
  if (centre < min) min = centre;
  if (centre > max) max = centre;
  return max - min <= tolerance;
}
