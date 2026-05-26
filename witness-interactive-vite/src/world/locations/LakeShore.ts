/**
 * LakeShore
 *
 * The lake-edge location west of the family compound — the southern shore of
 * Lake Kivu where the grandparent helped neighbours stage night crossings in
 * 1994. Per WORLD.md §"The Lake Shore" and MISSION_BLUEPRINT.md §2 (boat-
 * paddle anchor), this is the location whose Memory Fragment puts the player
 * in **Protector** mode (full mobility, the act of helping others escape) —
 * see CHRONOS_SWITCH.md §5.1.
 *
 * Layout (relative to the compound, which sits at world origin):
 *
 *   - Dock centre at (-25, ground, +18) so the player walks west-north-west
 *     from the gate. Stays inside the 80 m terrain block.
 *   - The dock runs roughly along +Z; the water plane is on the dock's west
 *     side (-X). The boat paddle (the anchor) is propped against the bench at
 *     the dock's landward end.
 *   - Past-only crates + jerrycans + fishing net + a lashed boat hull stand
 *     in for the 1994 staging that the journal describes.
 *
 * Per CHRONOS_SWITCH.md §3.2 every mesh is era-tagged. The dock planks +
 * pilings + water are `shared` (the geology of the shore persists); only the
 * boat hull, paddle, jerrycans, crates, and fishing net differ across eras.
 *
 * Primitives only — same swap-to-GLB path as FamilyCompound.ts and Ravine.ts.
 *
 * NOTE on hoisting helpers: this is the third location module that duplicates
 * `mkBox` / `mkCyl` / `deriveMat`. The 2026-05-09 vertical-slice memo set the
 * hoist-into-`world/_primitives.ts` threshold at the fourth location, so we
 * stay inline for now. A fourth module's author should make the call.
 */

import {
  Color3,
  MeshBuilder,
  PBRMaterial,
  Quaternion,
  Vector3,
} from "@babylonjs/core";
import type { AbstractMesh, Mesh, Scene } from "@babylonjs/core";
import { tagNode, type EraScope } from "../../core";
import { MaterialLibrary } from "../../engine";

export interface LakeShoreHandle {
  /** The boat-paddle anchor — carries the `boat_paddle` fragment trigger. */
  boatPaddle: AbstractMesh;
  /** Dock landing centre — useful for HUD prompts and audio zones. */
  dockAnchor: AbstractMesh;

  // Act 3B (Escapist path) anchors — only reachable after `path_escapist_chosen`.
  /** Oilcloth-wrapped passenger list under the bench — carries the `passenger_list` fragment trigger (act_3b_puzzle_1). */
  passengerList: AbstractMesh;
  /** Plank board with boat-capacity calculations — carries the `boat_capacity_notes` fragment trigger (act_3b_puzzle_2). */
  boatCapacityBoard: AbstractMesh;
  /** Folded escape-route map pinned under a dock stone — carries the `escape_route_map` fragment trigger (act_3b_puzzle_3). */
  escapeRouteMap: AbstractMesh;

  pastMeshes: AbstractMesh[];
  presentMeshes: AbstractMesh[];
  sharedMeshes: AbstractMesh[];
}

/** World position of the dock's landward bench — the boat paddle leans here. */
export const LAKE_DOCK_POSITION = new Vector3(-25, 0.4, 18);

export function buildLakeShore(scene: Scene, materials: MaterialLibrary): LakeShoreHandle {
  const sharedMeshes: AbstractMesh[] = [];

  // ---------------------------------------------------------------------------
  // Shared layer: water plane + dock planks + pilings. The geology of the
  // shore persists across eras; only the boats, jerrycans, and nets change.
  // ---------------------------------------------------------------------------

  // Water plane — a flat slab on the dock's west side, alpha-blended so the
  // laterite ground reads through at the edges.
  const water = mkBox(
    scene,
    "lake.water.shared",
    24,
    0.05,
    32,
    "shared",
    deriveMat(materials, "mat_water_lake", "lake_surface", (m) => {
      m.alpha = 0.78;
      m.roughness = 0.18;
    }),
  );
  water.position = new Vector3(
    LAKE_DOCK_POSITION.x - 13,
    0.04,
    LAKE_DOCK_POSITION.z + 4,
  );
  sharedMeshes.push(water);

  // Dock planks — three long boards laid end-to-end, walking out over water.
  const plankPositions: Array<{ x: number; z: number; w: number; d: number }> = [
    { x: 0.0, z: 0.0, w: 1.4, d: 4.0 }, // landward
    { x: -1.6, z: 0.0, w: 1.4, d: 4.0 }, // mid
    { x: -3.2, z: 0.0, w: 1.4, d: 4.0 }, // seaward
  ];
  plankPositions.forEach((p, i) => {
    const plank = mkBox(
      scene,
      `lake.dock.plank.${i}`,
      p.w,
      0.1,
      p.d,
      "shared",
      materials.get("mat_wood_weathered"),
    );
    plank.position = new Vector3(
      LAKE_DOCK_POSITION.x + p.x,
      0.5,
      LAKE_DOCK_POSITION.z + p.z,
    );
    sharedMeshes.push(plank);
  });

  // Pilings — short concrete posts under each plank pair.
  const pilingOffsets: Array<{ x: number; z: number }> = [
    { x: -0.8, z: -1.6 },
    { x: -0.8, z: 1.6 },
    { x: -2.4, z: -1.6 },
    { x: -2.4, z: 1.6 },
    { x: -3.8, z: -1.6 },
    { x: -3.8, z: 1.6 },
  ];
  pilingOffsets.forEach((o, i) => {
    const piling = mkCyl(
      scene,
      `lake.dock.piling.${i}`,
      0.22,
      0.26,
      0.95,
      "shared",
      materials.get("mat_concrete_weathered"),
    );
    piling.position = new Vector3(
      LAKE_DOCK_POSITION.x + o.x,
      0.0,
      LAKE_DOCK_POSITION.z + o.z,
    );
    sharedMeshes.push(piling);
  });

  // Landward bench — a low concrete block at the foot of the dock; the paddle
  // leans against it in both eras.
  const bench = mkBox(
    scene,
    "lake.dock.bench.shared",
    1.4,
    0.45,
    0.4,
    "shared",
    materials.get("mat_concrete_weathered"),
  );
  bench.position = new Vector3(
    LAKE_DOCK_POSITION.x + 0.9,
    0.225,
    LAKE_DOCK_POSITION.z,
  );
  sharedMeshes.push(bench);

  // Anchor marker — invisible probe target the bootstrap measures distance to.
  const dockAnchor = mkBox(
    scene,
    "lake.dock.anchor",
    0.05,
    0.05,
    0.05,
    "shared",
    materials.get("mat_concrete_weathered"),
  );
  dockAnchor.position = LAKE_DOCK_POSITION.clone();
  dockAnchor.isVisible = false;

  // ---------------------------------------------------------------------------
  // Present layer (2026): weathered, the boat is gone, only the paddle remains
  // — propped against the bench, pale and split.
  // ---------------------------------------------------------------------------
  const presentMeshes: AbstractMesh[] = [];

  // Paddle — long thin box leaning from bench edge to dock plank, at an angle.
  const boatPaddle = mkBox(
    scene,
    "lake.boat.paddle.present",
    0.12,
    1.4,
    0.06,
    "present",
    deriveMat(materials, "mat_wood_weathered", "lake_paddle_present", (m) => {
      m.albedoColor = new Color3(0.42, 0.36, 0.28);
      m.roughness = 0.95;
    }),
  );
  // Lean it ~25° toward the dock, top of the paddle resting on the bench.
  boatPaddle.position = new Vector3(
    LAKE_DOCK_POSITION.x + 0.45,
    0.7,
    LAKE_DOCK_POSITION.z + 0.05,
  );
  boatPaddle.rotationQuaternion = Quaternion.RotationAxis(
    new Vector3(0, 0, 1),
    -0.45,
  );
  presentMeshes.push(boatPaddle);

  // Rotted boat hull fragment — a thin curved slab half-submerged at the
  // dock's seaward end.
  const hullPresent = mkBox(
    scene,
    "lake.boat.hull.present",
    1.6,
    0.2,
    3.4,
    "present",
    deriveMat(materials, "mat_wood_weathered", "lake_hull_present", (m) => {
      m.albedoColor = new Color3(0.22, 0.18, 0.14);
      m.roughness = 0.95;
    }),
  );
  hullPresent.position = new Vector3(
    LAKE_DOCK_POSITION.x - 5.0,
    0.05,
    LAKE_DOCK_POSITION.z + 0.2,
  );
  hullPresent.rotationQuaternion = Quaternion.RotationAxis(
    new Vector3(0, 1, 0),
    0.18,
  );
  presentMeshes.push(hullPresent);

  // Reed clumps along the dock pilings.
  for (let i = 0; i < 8; i++) {
    const reed = mkBox(
      scene,
      `lake.reed.present.${i}`,
      0.2,
      0.7 + (i % 3) * 0.2,
      0.2,
      "present",
      deriveMat(materials, "mat_grass_tall", "lake_reed_present", (m) => {
        m.albedoColor = new Color3(0.32, 0.4, 0.18);
        m.roughness = 0.9;
      }),
    );
    const ang = (i / 8) * Math.PI - Math.PI * 0.5;
    reed.position = new Vector3(
      LAKE_DOCK_POSITION.x - 1.2 + Math.cos(ang) * 1.6,
      reed.scaling.y * 0.4,
      LAKE_DOCK_POSITION.z + Math.sin(ang) * 2.4,
    );
    presentMeshes.push(reed);
  }

  // ---------------------------------------------------------------------------
  // Past layer (1994): the dock is alive — staged jerrycans, fishing net, a
  // lashed boat hull moored beside the dock, the same paddle but darker wood.
  // ---------------------------------------------------------------------------
  const pastMeshes: AbstractMesh[] = [];

  // Paddle — same lean, fresher wood.
  const paddlePast = mkBox(
    scene,
    "lake.boat.paddle.past",
    0.13,
    1.45,
    0.07,
    "past",
    deriveMat(materials, "mat_wood_weathered", "lake_paddle_past", (m) => {
      m.albedoColor = new Color3(0.5, 0.36, 0.22);
      m.roughness = 0.7;
    }),
  );
  paddlePast.position = new Vector3(
    LAKE_DOCK_POSITION.x + 0.45,
    0.72,
    LAKE_DOCK_POSITION.z + 0.05,
  );
  paddlePast.rotationQuaternion = Quaternion.RotationAxis(
    new Vector3(0, 0, 1),
    -0.45,
  );
  pastMeshes.push(paddlePast);

  // Lashed wooden boat hull — sits beside the dock, ready for night loading.
  const hullPast = mkBox(
    scene,
    "lake.boat.hull.past",
    1.7,
    0.55,
    3.6,
    "past",
    deriveMat(materials, "mat_wood_weathered", "lake_hull_past", (m) => {
      m.albedoColor = new Color3(0.46, 0.32, 0.2);
      m.roughness = 0.75;
    }),
  );
  hullPast.position = new Vector3(
    LAKE_DOCK_POSITION.x - 5.0,
    0.32,
    LAKE_DOCK_POSITION.z + 0.2,
  );
  hullPast.rotationQuaternion = Quaternion.RotationAxis(
    new Vector3(0, 1, 0),
    0.04,
  );
  pastMeshes.push(hullPast);

  // Inner thwart of the boat — a flat seat plank.
  const thwart = mkBox(
    scene,
    "lake.boat.thwart.past",
    1.5,
    0.05,
    0.32,
    "past",
    deriveMat(materials, "mat_wood_weathered", "lake_thwart_past", (m) => {
      m.albedoColor = new Color3(0.42, 0.3, 0.18);
    }),
  );
  thwart.position = new Vector3(
    hullPast.position.x,
    hullPast.position.y + 0.32,
    hullPast.position.z,
  );
  pastMeshes.push(thwart);

  // Jerrycans staged on the bench + dock — three yellow metal cans for the
  // crossing. Per WORLD.md these are the iconic 1994 motif.
  const jerrycanPositions: Array<{ x: number; y: number; z: number; r: number }> = [
    { x: 0.7, y: 0.55, z: -0.3, r: 0.0 }, // on the bench
    { x: 0.9, y: 0.55, z: 0.4, r: 0.4 }, // on the bench
    { x: -0.6, y: 0.6, z: 0.0, r: -0.2 }, // landward end of dock
  ];
  jerrycanPositions.forEach((p, i) => {
    const can = mkBox(
      scene,
      `lake.jerrycan.past.${i}`,
      0.32,
      0.46,
      0.22,
      "past",
      materials.get("mat_metal_jerrycan"),
    );
    can.position = new Vector3(
      LAKE_DOCK_POSITION.x + p.x,
      p.y,
      LAKE_DOCK_POSITION.z + p.z,
    );
    can.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), p.r);
    pastMeshes.push(can);
  });

  // Wooden crates stacked at the dock's landward end — supplies for the
  // crossing.
  const crateStack: Array<{ x: number; y: number; z: number; s: number; r: number }> = [
    { x: 1.5, y: 0.3, z: 0.6, s: 0.6, r: 0.1 },
    { x: 1.45, y: 0.9, z: 0.55, s: 0.55, r: -0.15 },
    { x: 2.1, y: 0.3, z: 0.7, s: 0.6, r: -0.05 },
  ];
  crateStack.forEach((c, i) => {
    const crate = mkBox(
      scene,
      `lake.crate.past.${i}`,
      c.s,
      c.s,
      c.s,
      "past",
      deriveMat(materials, "mat_wood_weathered", "lake_crate_past", (m) => {
        m.albedoColor = new Color3(0.5, 0.36, 0.22);
        m.roughness = 0.78;
      }),
    );
    crate.position = new Vector3(
      LAKE_DOCK_POSITION.x + c.x,
      c.y,
      LAKE_DOCK_POSITION.z + c.z,
    );
    crate.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), c.r);
    pastMeshes.push(crate);
  });

  // Fishing net — a flat draped slab in kitenge orange-red, the closest cloth
  // material, suggesting woven fibre. Placed half-on-dock, half-off.
  const net = mkBox(
    scene,
    "lake.net.past",
    1.8,
    0.04,
    1.4,
    "past",
    deriveMat(materials, "mat_cloth_kitenge", "lake_net_past", (m) => {
      m.albedoColor = new Color3(0.38, 0.3, 0.22);
      m.roughness = 0.95;
    }),
  );
  net.position = new Vector3(
    LAKE_DOCK_POSITION.x - 2.4,
    0.58,
    LAKE_DOCK_POSITION.z - 0.6,
  );
  net.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), 0.2);
  pastMeshes.push(net);

  // ---------------------------------------------------------------------------
  // Act 3B (Escapist path) — Present-only anchor meshes. Gate enforced in
  // bootstrap's proximity probe via `requiredFlags: ["path_escapist_chosen"]`.
  // ---------------------------------------------------------------------------

  // Passenger list — an oilcloth bundle wedged under the bench. In 2026 the
  // oilcloth is intact; the list inside is still legible.
  const passengerList = mkBox(
    scene,
    "lake.passenger_list.present",
    0.22,
    0.08,
    0.14,
    "present",
    deriveMat(materials, "mat_cloth_kitenge", "lake_pax_list_present", (m) => {
      m.albedoColor = new Color3(0.38, 0.3, 0.22);
      m.roughness = 0.92;
    }),
  );
  passengerList.position = new Vector3(
    LAKE_DOCK_POSITION.x + 1.4,
    0.24,
    LAKE_DOCK_POSITION.z + 0.45,
  );
  passengerList.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), 0.5);
  presentMeshes.push(passengerList);

  // Boat-capacity board — a flat plank leaning against the bench's east face,
  // with faded ink calculations for weight and passenger count.
  const boatCapacityBoard = mkBox(
    scene,
    "lake.boat_capacity_board.present",
    0.32,
    0.42,
    0.04,
    "present",
    deriveMat(materials, "mat_wood_weathered", "lake_cap_board_present", (m) => {
      m.albedoColor = new Color3(0.36, 0.28, 0.2);
      m.roughness = 0.94;
    }),
  );
  boatCapacityBoard.position = new Vector3(
    LAKE_DOCK_POSITION.x + 0.2,
    0.66,
    LAKE_DOCK_POSITION.z - 0.88,
  );
  boatCapacityBoard.rotationQuaternion = Quaternion.RotationAxis(
    new Vector3(1, 0, 0),
    -0.25,
  );
  presentMeshes.push(boatCapacityBoard);

  // Escape-route map — a folded oilcloth square pinned under a flat rock at
  // the dock's landward-west corner.
  const escapeRouteMap = mkBox(
    scene,
    "lake.escape_route_map.present",
    0.26,
    0.02,
    0.2,
    "present",
    deriveMat(materials, "mat_cloth_kitenge", "lake_map_present", (m) => {
      m.albedoColor = new Color3(0.42, 0.34, 0.26);
      m.roughness = 0.9;
    }),
  );
  escapeRouteMap.position = new Vector3(
    LAKE_DOCK_POSITION.x - 0.5,
    0.6,
    LAKE_DOCK_POSITION.z - 1.8,
  );
  escapeRouteMap.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), -0.35);
  presentMeshes.push(escapeRouteMap);

  return {
    boatPaddle,
    dockAnchor,
    passengerList,
    boatCapacityBoard,
    escapeRouteMap,
    pastMeshes,
    presentMeshes,
    sharedMeshes,
  };
}

// ---------------------------------------------------------------------------
// Local helpers — duplicated from FamilyCompound.ts and Ravine.ts deliberately.
// Three locations is the threshold; lift to `world/_primitives.ts` when a
// fourth lands.
// ---------------------------------------------------------------------------

function mkBox(
  scene: Scene,
  name: string,
  width: number,
  height: number,
  depth: number,
  era: EraScope,
  material: PBRMaterial,
): Mesh {
  const m = MeshBuilder.CreateBox(name, { width, height, depth }, scene);
  m.material = material;
  tagNode(m, era);
  return m;
}

function mkCyl(
  scene: Scene,
  name: string,
  diameterTop: number,
  diameterBottom: number,
  height: number,
  era: EraScope,
  material: PBRMaterial,
): Mesh {
  const m = MeshBuilder.CreateCylinder(
    name,
    { diameterTop, diameterBottom, height },
    scene,
  );
  m.material = material;
  tagNode(m, era);
  return m;
}

function deriveMat(
  lib: MaterialLibrary,
  baseId: Parameters<MaterialLibrary["get"]>[0],
  suffix: string,
  patch: (m: PBRMaterial) => void,
): PBRMaterial {
  const clone = lib.cloneForVariant(baseId, suffix);
  patch(clone);
  clone.freeze();
  return clone;
}
