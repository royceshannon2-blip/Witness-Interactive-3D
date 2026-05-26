/**
 * Ravine
 *
 * The mid-to-high-level vantage location east of the family compound, where
 * the grandparent kept watch over the valley during 1994. Per WORLD.md §"The
 * Ravine" and MISSION_BLUEPRINT.md §2 (observer's journal anchor), this is
 * the location whose Memory Fragment puts the player in **Hidden** mode (a
 * child crouched among stones) — see CHRONOS_SWITCH.md §5.2.
 *
 * Layout (relative to the compound, which sits at world origin):
 *
 *   - Outcrop centre at (+22, ground, +4) so the player can walk over from
 *     the gate without leaving the 80 m terrain block.
 *   - Cairn rises ~1.4 m above the outcrop; the observer's journal sits on
 *     the topmost flat stone, facing back toward the compound.
 *   - Past-only stone fortifications + chalk-mark strips + distant valley
 *     smoke columns represent the "site of resistance" backdrop.
 *
 * Per CHRONOS_SWITCH.md §3.2 every mesh is era-tagged. The cairn itself is
 * `shared` (the rocks are the same in 1994 and 2026); only the journal,
 * fortifications, chalk marks, and smoke columns differ across eras.
 *
 * Primitives only — same swap-to-GLB path as FamilyCompound.ts.
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

export interface RavineHandle {
  /** The observer's-journal anchor — carries the `observer_notes` fragment trigger. */
  observerJournal: AbstractMesh;
  /** Outcrop base centre, in world coordinates. Useful for HUD prompts and audio zones. */
  vantageAnchor: AbstractMesh;

  // Act 3C (Observer path) anchors — only reachable after `path_silent_chosen`.
  /** Chalk-marked stone on the outcrop east face — carries the `chalk_patrol_marks` fragment trigger (act_3c_puzzle_1). */
  chalkPatrolMarks: AbstractMesh;
  /** Scratched stone slab with checkpoint dates — carries the `checkpoint_records` fragment trigger (act_3c_puzzle_2). */
  checkpointRecords: AbstractMesh;
  /** Oilcloth-wrapped unsent letters wedged in the cairn base — carries the `reflection_letters` fragment trigger (act_3c_puzzle_3). */
  reflectionLetters: AbstractMesh;

  pastMeshes: AbstractMesh[];
  presentMeshes: AbstractMesh[];
  sharedMeshes: AbstractMesh[];
}

/** World position of the ravine outcrop's centre — kept as a const so the
 * bootstrap proximity probe can lean on it without digging into mesh state. */
export const RAVINE_VANTAGE_POSITION = new Vector3(22, 0.6, 4);

export function buildRavine(scene: Scene, materials: MaterialLibrary): RavineHandle {
  const sharedMeshes: AbstractMesh[] = [];

  // ---------------------------------------------------------------------------
  // Shared layer: rocky outcrop + cairn. The natural geology persists across
  // eras; only what humans left on it differs.
  // ---------------------------------------------------------------------------
  const outcrop = mkCyl(
    scene,
    "ravine.outcrop",
    3.6,
    4.2,
    0.6,
    "shared",
    materials.get("mat_concrete_weathered"),
  );
  outcrop.position = RAVINE_VANTAGE_POSITION.clone();
  sharedMeshes.push(outcrop);

  const cairnStones: Array<{ x: number; z: number; r: number; h: number }> = [
    { x: 0.0, z: 0.0, r: 0.55, h: 0.45 },
    { x: 0.35, z: -0.2, r: 0.42, h: 0.38 },
    { x: -0.3, z: 0.25, r: 0.36, h: 0.32 },
    { x: 0.1, z: 0.15, r: 0.32, h: 0.28 }, // top stone — flat-ish; the journal rests here
  ];
  let stackY = RAVINE_VANTAGE_POSITION.y + 0.3;
  cairnStones.forEach((s, i) => {
    const stone = mkCyl(
      scene,
      `ravine.cairn.${i}`,
      s.r * 1.8,
      s.r * 2.0,
      s.h,
      "shared",
      materials.get("mat_concrete_weathered"),
    );
    stackY += s.h * 0.5;
    stone.position = new Vector3(
      RAVINE_VANTAGE_POSITION.x + s.x,
      stackY,
      RAVINE_VANTAGE_POSITION.z + s.z,
    );
    stone.rotationQuaternion = Quaternion.RotationAxis(
      new Vector3(0, 1, 0),
      i * 0.7,
    );
    stackY += s.h * 0.5;
    sharedMeshes.push(stone);
  });

  // Vantage anchor mesh — a tiny invisible marker the bootstrap uses for
  // distance probes; not added to renderable arrays.
  const vantageAnchor = mkBox(
    scene,
    "ravine.vantage.anchor",
    0.05,
    0.05,
    0.05,
    "shared",
    materials.get("mat_concrete_weathered"),
  );
  vantageAnchor.position = RAVINE_VANTAGE_POSITION.clone();
  vantageAnchor.isVisible = false;

  // ---------------------------------------------------------------------------
  // Present layer (2026): weathered, mossy. The observer's journal is half-
  // buried at the cairn's apex.
  // ---------------------------------------------------------------------------
  const presentMeshes: AbstractMesh[] = [];

  const journalPosY = stackY + 0.04;
  const observerJournal = mkBox(
    scene,
    "ravine.observer.journal.present",
    0.34,
    0.06,
    0.24,
    "present",
    deriveMat(materials, "mat_wood_weathered", "ravine_journal_present", (m) => {
      m.albedoColor = new Color3(0.28, 0.22, 0.16);
      m.roughness = 0.95;
    }),
  );
  observerJournal.position = new Vector3(
    RAVINE_VANTAGE_POSITION.x + 0.05,
    journalPosY,
    RAVINE_VANTAGE_POSITION.z + 0.1,
  );
  observerJournal.rotationQuaternion = Quaternion.RotationAxis(
    new Vector3(0, 1, 0),
    -0.4,
  );
  presentMeshes.push(observerJournal);

  // A weathered paper sliver poking out of the journal — visible from the
  // approach so the player can spot it against the cairn.
  const paperWeathered = mkBox(
    scene,
    "ravine.observer.paper.present",
    0.22,
    0.005,
    0.16,
    "present",
    deriveMat(materials, "mat_cloth_white", "ravine_paper_present", (m) => {
      m.albedoColor = new Color3(0.62, 0.58, 0.5);
      m.roughness = 0.95;
    }),
  );
  paperWeathered.position = new Vector3(
    observerJournal.position.x + 0.06,
    journalPosY + 0.035,
    observerJournal.position.z + 0.04,
  );
  presentMeshes.push(paperWeathered);

  // Sparse moss / lichen tufts on the cairn — primitive flat boxes.
  for (let i = 0; i < 5; i++) {
    const moss = mkBox(
      scene,
      `ravine.moss.present.${i}`,
      0.25 + (i % 3) * 0.05,
      0.04,
      0.25 + (i % 3) * 0.05,
      "present",
      deriveMat(materials, "mat_grass_tall", "ravine_moss_present", (m) => {
        m.albedoColor = new Color3(0.18, 0.26, 0.14);
        m.roughness = 0.95;
      }),
    );
    const ang = (i / 5) * Math.PI * 2 + 0.4;
    const r = 1.6 + (i % 2) * 0.4;
    moss.position = new Vector3(
      RAVINE_VANTAGE_POSITION.x + Math.cos(ang) * r,
      RAVINE_VANTAGE_POSITION.y + 0.62,
      RAVINE_VANTAGE_POSITION.z + Math.sin(ang) * r,
    );
    presentMeshes.push(moss);
  }

  // ---------------------------------------------------------------------------
  // Past layer (1994): cleaner stone, chalk marks visible, low fortifications,
  // distant smoke columns in the valley as silent witness to the militia.
  // ---------------------------------------------------------------------------
  const pastMeshes: AbstractMesh[] = [];

  const journalPast = mkBox(
    scene,
    "ravine.observer.journal.past",
    0.36,
    0.06,
    0.26,
    "past",
    deriveMat(materials, "mat_wood_weathered", "ravine_journal_past", (m) => {
      m.albedoColor = new Color3(0.46, 0.32, 0.2);
      m.roughness = 0.7;
    }),
  );
  journalPast.position = new Vector3(
    RAVINE_VANTAGE_POSITION.x + 0.05,
    journalPosY,
    RAVINE_VANTAGE_POSITION.z + 0.1,
  );
  journalPast.rotationQuaternion = Quaternion.RotationAxis(
    new Vector3(0, 1, 0),
    -0.4,
  );
  pastMeshes.push(journalPast);

  const paperPast = mkBox(
    scene,
    "ravine.observer.paper.past",
    0.24,
    0.006,
    0.18,
    "past",
    deriveMat(materials, "mat_cloth_white", "ravine_paper_past", (m) => {
      m.albedoColor = new Color3(0.94, 0.9, 0.82);
      m.roughness = 0.85;
    }),
  );
  paperPast.position = new Vector3(
    journalPast.position.x + 0.06,
    journalPosY + 0.035,
    journalPast.position.z + 0.04,
  );
  pastMeshes.push(paperPast);

  // Chalk-marked stones — five small white strips on the cairn faces. These
  // stand in for the militia patrol marks that the journal documents.
  const chalkPositions: Array<{ x: number; y: number; z: number; r: number }> = [
    { x: -0.42, y: 0.42, z: 0.05, r: 0.0 },
    { x: 0.36, y: 0.5, z: -0.18, r: 0.6 },
    { x: -0.18, y: 0.78, z: 0.32, r: -0.3 },
    { x: 0.22, y: 0.92, z: 0.22, r: 0.9 },
    { x: -0.05, y: 1.1, z: -0.28, r: -0.6 },
  ];
  chalkPositions.forEach((p, i) => {
    const mark = mkBox(
      scene,
      `ravine.chalk.past.${i}`,
      0.16,
      0.012,
      0.04,
      "past",
      deriveMat(materials, "mat_cloth_white", "ravine_chalk_past", (m) => {
        m.albedoColor = new Color3(0.92, 0.9, 0.86);
        m.roughness = 0.65;
      }),
    );
    mark.position = new Vector3(
      RAVINE_VANTAGE_POSITION.x + p.x,
      RAVINE_VANTAGE_POSITION.y + 0.3 + p.y,
      RAVINE_VANTAGE_POSITION.z + p.z,
    );
    mark.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), p.r);
    pastMeshes.push(mark);
  });

  // Low stone fortifications — angular blocks behind the cairn, evoking
  // WORLD.md "scattered stones used as weapons/barricades."
  const fortPositions: Array<{ x: number; z: number; w: number; h: number; r: number }> = [
    { x: -2.0, z: 1.2, w: 1.4, h: 0.55, r: 0.2 },
    { x: -1.0, z: 2.1, w: 1.0, h: 0.42, r: -0.4 },
    { x: 1.4, z: 1.6, w: 1.2, h: 0.5, r: 0.3 },
  ];
  fortPositions.forEach((f, i) => {
    const fort = mkBox(
      scene,
      `ravine.fortification.past.${i}`,
      f.w,
      f.h,
      0.5,
      "past",
      deriveMat(materials, "mat_concrete_weathered", "ravine_fort_past", (m) => {
        m.albedoColor = new Color3(0.62, 0.58, 0.52);
        m.roughness = 0.9;
      }),
    );
    fort.position = new Vector3(
      RAVINE_VANTAGE_POSITION.x + f.x,
      RAVINE_VANTAGE_POSITION.y + f.h * 0.5,
      RAVINE_VANTAGE_POSITION.z + f.z,
    );
    fort.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), f.r);
    pastMeshes.push(fort);
  });

  // Distant valley smoke columns — three thin tall pillars, alpha 0.28.
  // Placed beyond the terrain edge so they read as far away.
  const smokePositions: Array<{ x: number; z: number; h: number }> = [
    { x: 38, z: -8, h: 12 },
    { x: 32, z: 18, h: 9 },
    { x: 44, z: 6, h: 14 },
  ];
  smokePositions.forEach((s, i) => {
    const col = mkCyl(
      scene,
      `ravine.smoke.past.${i}`,
      0.7,
      0.4,
      s.h,
      "past",
      deriveMat(materials, "mat_cloth_white", "ravine_smoke_past", (m) => {
        m.albedoColor = new Color3(0.42, 0.38, 0.34);
        m.alpha = 0.28;
        m.unlit = true;
      }),
    );
    col.position = new Vector3(s.x, s.h * 0.5, s.z);
    pastMeshes.push(col);
  });

  // ---------------------------------------------------------------------------
  // Act 3C (Observer path) — Present-only anchor meshes. Gate enforced in
  // bootstrap's proximity probe via `requiredFlags: ["path_silent_chosen"]`.
  // ---------------------------------------------------------------------------

  // Chalk-patrol-marks stone — a flat stone east of the cairn with faint
  // chalk lines still visible 30 years on (sheltered by an overhang).
  const chalkPatrolMarks = mkBox(
    scene,
    "ravine.chalk_patrol_marks.present",
    0.44,
    0.06,
    0.28,
    "present",
    deriveMat(materials, "mat_concrete_weathered", "ravine_chalk_present", (m) => {
      m.albedoColor = new Color3(0.54, 0.52, 0.48);
      m.roughness = 0.9;
    }),
  );
  chalkPatrolMarks.position = new Vector3(
    RAVINE_VANTAGE_POSITION.x + 1.5,
    RAVINE_VANTAGE_POSITION.y + 0.38,
    RAVINE_VANTAGE_POSITION.z + 1.8,
  );
  chalkPatrolMarks.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), 0.7);
  presentMeshes.push(chalkPatrolMarks);

  // Checkpoint-records slab — a scratched stone with hand-carved dates and
  // grid references for militia checkpoints. Half-buried in lichen.
  const checkpointRecords = mkBox(
    scene,
    "ravine.checkpoint_records.present",
    0.38,
    0.08,
    0.24,
    "present",
    deriveMat(materials, "mat_concrete_weathered", "ravine_ckpt_present", (m) => {
      m.albedoColor = new Color3(0.48, 0.46, 0.42);
      m.roughness = 0.94;
    }),
  );
  checkpointRecords.position = new Vector3(
    RAVINE_VANTAGE_POSITION.x - 1.8,
    RAVINE_VANTAGE_POSITION.y + 0.32,
    RAVINE_VANTAGE_POSITION.z + 1.6,
  );
  checkpointRecords.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), -0.4);
  presentMeshes.push(checkpointRecords);

  // Reflection letters — an oilcloth cylinder wedged between two cairn stones
  // at the west face. The cloth is desiccated but intact; letters inside are
  // Grandfather's unsent correspondence to himself.
  const reflectionLetters = mkBox(
    scene,
    "ravine.reflection_letters.present",
    0.06,
    0.06,
    0.22,
    "present",
    deriveMat(materials, "mat_cloth_kitenge", "ravine_letters_present", (m) => {
      m.albedoColor = new Color3(0.32, 0.26, 0.18);
      m.roughness = 0.95;
    }),
  );
  reflectionLetters.position = new Vector3(
    RAVINE_VANTAGE_POSITION.x - 0.6,
    RAVINE_VANTAGE_POSITION.y + 0.82,
    RAVINE_VANTAGE_POSITION.z - 1.2,
  );
  reflectionLetters.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 0, 1), 0.3);
  presentMeshes.push(reflectionLetters);

  return {
    observerJournal,
    vantageAnchor,
    chalkPatrolMarks,
    checkpointRecords,
    reflectionLetters,
    pastMeshes,
    presentMeshes,
    sharedMeshes,
  };
}

// ---------------------------------------------------------------------------
// Local helpers — duplicated from FamilyCompound.ts deliberately. Three calls
// is below the abstraction threshold; if a fourth location lands and they
// still agree, lift them into `world/_primitives.ts`.
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
