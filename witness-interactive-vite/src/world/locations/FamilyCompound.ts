/**
 * FamilyCompound
 *
 * The vertical-slice location: the Bisesero family compound that the
 * grandchild returns to in 2026 and that the grandparent inhabited in 1994.
 * Layout follows OPENING_SEQUENCE.md §6 (first-frame composition):
 *
 *   - Player spawn: just inside the gate, ~5 m from the main house.
 *   - Eucalyptus grove on the player's LEFT.
 *   - Well + hidden cellar entrance on the RIGHT.
 *   - Main house ahead (centre, +Z).
 *
 * Per CHRONOS_SWITCH.md §3.2: every mesh is tagged `present` / `past` /
 * `shared`. The terrain is shared. Buildings have era variants — same
 * footprint, different condition (Present is overgrown ruin, Past is intact
 * with hearth smoke and a populated household).
 *
 * Primitives only — this is the architectural payoff demo, not the asset
 * pass. When the Hunyuan3D pipeline ships, callers swap the primitive build
 * helpers for `assetLibrary.instantiate(...)` while keeping the era tags
 * and anchor positions identical.
 *
 * Returns a `FamilyCompoundHandle` that names the anchor meshes the
 * caller (mission/bootstrap) needs — most importantly the cellar latch on
 * the well, which the cellar_door_latch fragment binds to.
 *
 * --- Phase-1 Asset Pipeline Swap Manifest ---------------------------------
 * Each primitive cluster below is annotated with a `TODO(asset-pipeline)`
 * naming the canonical asset_id (see prompts/asset-templates/<id>.md) that
 * will replace it once the Hunyuan3D pass produces a GLB. The swap is
 * mechanical: replace the cluster's `mk*` calls with one of
 *
 *   assetLibrary.instantiate("<id>")   // mesh containers
 *   // → returns InstantiatedEntries; position the root + call tagNode
 *
 * preserving the position, era tag, and the handle field the bootstrap
 * binds against. Reference: .claude/rules/asset-pipeline.md §4–§5 and
 * docs/design-docs/PHASE1_ASSET_LIST.md.
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
import { buildTerrain, type Terrain } from "../Terrain";

export interface FamilyCompoundHandle {
  /** Shared terrain — visible in both eras. */
  terrain: Terrain;
  /** Well-cover plank that carries the cellar_door_latch fragment trigger. */
  cellarLatch: AbstractMesh;
  /** Photo-frame on the household altar — carries the `family_records` fragment trigger (M6). */
  familyRecords: AbstractMesh;
  /** Gate post the player walks past at t = 45 s — used by the IntroSequence to compose the first frame. */
  gateAnchor: AbstractMesh;
  /** The shepherd's ledger, resting on the altar slab — Phase 1 first interactable (OPENING_SEQUENCE §6). */
  ledgerBook: AbstractMesh;

  // Act 3A (Hider path) anchors — only reachable after `path_hider_chosen`.
  /** Rolled sleeping mats north of the well — carries the `cellar_mats` fragment trigger (act_3a_puzzle_1). */
  cellarMats: AbstractMesh;
  /** Carved water-schedule marks on the east compound wall — carries the `water_schedule` fragment trigger (act_3a_puzzle_2). */
  waterSchedule: AbstractMesh;
  /** Sealed letter tucked under a stone near the cellar — carries the `neighbor_letter` fragment trigger (act_3a_puzzle_3). */
  neighborLetter: AbstractMesh;

  // Act 3B (Escapist path) anchor — only reachable after `path_escapist_chosen`.
  /** Rolled oilcloth by the altar; a post-genocide survivor's letter — carries the `survivor_letter` fragment trigger (act_3b_puzzle_4). */
  survivorLetter: AbstractMesh;

  // Act 3C (Observer path) anchor — only reachable after `path_silent_chosen`.
  /** Inscribed flat stone beside the house east wall — carries the `visitor_account` fragment trigger (act_3c_puzzle_4). */
  visitorAccount: AbstractMesh;

  /** Altar slab (present era) — Act 4 shrine-return proximity trigger. */
  shrineAnchor: AbstractMesh;

  /** Grouped Past meshes — disposed on mission unload. */
  pastMeshes: AbstractMesh[];
  /** Grouped Present meshes — disposed on mission unload. */
  presentMeshes: AbstractMesh[];
}

/**
 * Build the compound. Caller is responsible for `tagLight` on the
 * lighting rigs and for kicking the freeze pass after this returns.
 */
export function buildFamilyCompound(
  scene: Scene,
  materials: MaterialLibrary,
): FamilyCompoundHandle {
  // ---------------------------------------------------------------------------
  // Shared layer: terrain + gate posts (cross-era landmarks).
  // ---------------------------------------------------------------------------
  const terrain = buildTerrain(scene, { size: 80, subdivisions: 32 });
  terrain.ground.material = materials.get("mat_laterite");
  tagNode(terrain.ground, "shared");

  // TODO(asset-pipeline): replace with structure_compound_gate
  //   The three primitives below (two posts + beam) compose one gate model.
  //   Swap to: assetLibrary.instantiate("structure_compound_gate") at
  //   position (0, 0, -6), facing +Z. Keep gateAnchor pointing at the
  //   left-post root for IntroSequence first-frame composition.
  const gateAnchor = mkBox(scene, "compound.gate.left", 0.25, 1.6, 0.25, "shared", materials.get("mat_wood_weathered"));
  gateAnchor.position = new Vector3(-1.4, 0.8, -6);

  const gateRight = mkBox(scene, "compound.gate.right", 0.25, 1.6, 0.25, "shared", materials.get("mat_wood_weathered"));
  gateRight.position = new Vector3(1.4, 0.8, -6);

  const gateBeam = mkBox(scene, "compound.gate.beam", 3.0, 0.18, 0.18, "shared", materials.get("mat_wood_weathered"));
  gateBeam.position = new Vector3(0, 1.7, -6);

  // ---------------------------------------------------------------------------
  // Present layer (2026): overgrown ruin. Cool, damp, weathered.
  // ---------------------------------------------------------------------------
  const presentMeshes: AbstractMesh[] = [];

  // TODO(asset-pipeline): replace with structure_rugo_main_house
  //   Same mesh used for both eras; runtime swaps material variant.
  //   Tilted/collapsed look in 2026 comes from the cloned material, not
  //   geometry. Keep position + slight Z-axis rotation for ruin reading.
  const housePresent = mkBox(scene, "compound.house.present", 5.5, 2.6, 4.5, "present", materials.get("mat_concrete_weathered"));
  housePresent.position = new Vector3(0, 1.3, 6);
  housePresent.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 0, 1), 0.025);
  presentMeshes.push(housePresent);

  // TODO(asset-pipeline): replace with structure_rugo_tin_roof
  //   Era-derived material handles rust/cleanliness; geometry shared.
  const roofPresent = mkBox(scene, "compound.roof.present", 6.2, 0.12, 5.0, "present", deriveMat(materials, "mat_tin_roof", "weathered_present", (m) => {
    m.albedoColor = new Color3(0.35, 0.18, 0.12);
    m.roughness = 0.92;
  }));
  roofPresent.position = new Vector3(0, 2.7, 6);
  roofPresent.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 0, 1), -0.05);
  presentMeshes.push(roofPresent);

  // TODO(asset-pipeline): replace with structure_well_stone_ring
  //   Single mesh; era-derived material gives the lichen/mortar deltas.
  const wellRing = mkCyl(scene, "compound.well.present", 0.6, 0.6, 0.7, "present", materials.get("mat_concrete_weathered"));
  wellRing.position = new Vector3(3.2, 0.35, 0.5);
  presentMeshes.push(wellRing);

  // TODO(asset-pipeline): replace with structure_well_cover_plank
  //   Carries the `cellar_door_latch` Memory Fragment trigger — interactable
  //   raycast hits this mesh's top face. Asset pivot is centre of the top
  //   face per the prompt template.
  const cellarLatch = mkBox(scene, "compound.well.cover.present", 1.3, 0.08, 1.3, "present", materials.get("mat_wood_weathered"));
  cellarLatch.position = new Vector3(3.2, 0.74, 0.5);
  cellarLatch.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), 0.18);
  presentMeshes.push(cellarLatch);

  // TODO(asset-pipeline): replace with vegetation_eucalyptus_mature (ThinInstance)
  //   Swap the loop body for one `assetLibrary.instantiate(...)` + thin-instance
  //   matrix-builder call per ARCHITECTURE.md §5.7 (preload N=4, then
  //   ThinInstance.setBuffer for 6 placements). Same pivot convention.
  for (let i = 0; i < 6; i++) {
    const trunk = mkCyl(
      scene,
      `compound.eucalyptus.present.${i}`,
      0.18 + (i % 3) * 0.05,
      0.12,
      4.8 + (i % 4) * 0.6,
      "present",
      materials.get("mat_eucalyptus_bark"),
    );
    trunk.position = new Vector3(-3.5 - (i % 3) * 0.9, trunk.scaling.y * 2.4, -2 + i * 1.4);
    presentMeshes.push(trunk);
  }

  // TODO(asset-pipeline): replace with structure_family_shrine_slab
  //   Single shared mesh; era handled by material clones. Acts as the
  //   Phase-1 ledger pedestal AND the Act-4 shrineAnchor proximity trigger.
  // Household altar — a low concrete slab to the left of the front door. The
  // photo frame on top carries the M6 `family_records` fragment trigger. In
  // 2026 the slab is cracked and overgrown; the frame has fallen flat into
  // the laterite, glass long gone.
  const altarSlabPresent = mkBox(
    scene,
    "compound.altar.slab.present",
    0.95,
    0.32,
    0.55,
    "present",
    deriveMat(materials, "mat_concrete_weathered", "altar_present", (m) => {
      m.albedoColor = new Color3(0.58, 0.55, 0.5);
      m.roughness = 0.92;
    }),
  );
  altarSlabPresent.position = new Vector3(-1.85, 0.16, 3.5);
  presentMeshes.push(altarSlabPresent);

  // TODO(asset-pipeline): replace with prop_altar_photo_frame
  //   The asset is authored standing; the runtime rotates it onto its
  //   face for the 2026 fallen pose (see Past block below for upright).
  //   Carries the `family_records` Act-2 Memory Fragment trigger.
  const familyRecords = mkBox(
    scene,
    "compound.altar.frame.present",
    0.42,
    0.04,
    0.32,
    "present",
    deriveMat(materials, "mat_wood_weathered", "altar_frame_present", (m) => {
      m.albedoColor = new Color3(0.32, 0.24, 0.16);
      m.roughness = 0.95;
    }),
  );
  // Lying flat on the slab — fallen at some point in the years between.
  familyRecords.position = new Vector3(-1.85, 0.34, 3.5);
  familyRecords.rotationQuaternion = Quaternion.RotationAxis(
    new Vector3(0, 1, 0),
    0.35,
  );
  presentMeshes.push(familyRecords);

  // The faded photograph behind the frame — a thin slab in pale cloth.
  const photoPresent = mkBox(
    scene,
    "compound.altar.photo.present",
    0.32,
    0.005,
    0.22,
    "present",
    deriveMat(materials, "mat_cloth_white", "altar_photo_present", (m) => {
      m.albedoColor = new Color3(0.5, 0.46, 0.38);
      m.roughness = 0.95;
    }),
  );
  photoPresent.position = new Vector3(-1.85, 0.345, 3.5);
  photoPresent.rotationQuaternion = familyRecords.rotationQuaternion?.clone() ?? null;
  presentMeshes.push(photoPresent);

  // The shepherd's ledger — Phase 1 hero prop. Rests on the altar slab,
  // visible at first frame composition (OPENING_SEQUENCE §6). Shared mesh
  // tagged "present" because the player encounters it in 2026; the same
  // asset's geometry appears in any 1994 echo that shows the ledger.
  // TODO(asset-pipeline): replace with prop_ledger_book
  //   Pivot is the centre of the book's bottom face; sits flat on slab top.
  const ledgerBook = mkBox(
    scene,
    "compound.altar.ledger.present",
    0.21,
    0.03,
    0.15,
    "present",
    deriveMat(materials, "mat_wood_weathered", "ledger_present", (m) => {
      m.albedoColor = new Color3(0.22, 0.14, 0.08);
      m.roughness = 0.82;
    }),
  );
  // Sits flat on the altar slab top, slightly skewed so the front cover
  // angles toward the spawn camera.
  ledgerBook.position = new Vector3(-1.85, 0.345, 3.55);
  ledgerBook.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), 0.45);
  presentMeshes.push(ledgerBook);

  // TODO(asset-pipeline): replace with vegetation_elephant_grass (ThinInstance)
  //   Swap the loop body for one `assetLibrary.instantiate(...)` + thin-instance
  //   matrix-builder call for the 14 placements below.
  // Tall grass clumps — scattered, dark green.
  for (let i = 0; i < 14; i++) {
    const grass = mkBox(
      scene,
      `compound.grass.present.${i}`,
      0.6,
      0.55 + (i % 3) * 0.15,
      0.6,
      "present",
      deriveMat(materials, "mat_grass_tall", "present", (m) => {
        m.albedoColor = new Color3(0.22, 0.3, 0.14);
      }),
    );
    const ang = (i / 14) * Math.PI * 2;
    const r = 2.2 + (i % 5) * 0.5;
    grass.position = new Vector3(Math.cos(ang) * r, grass.scaling.y * 0.27, 1 + Math.sin(ang) * r);
    presentMeshes.push(grass);
  }

  // ---------------------------------------------------------------------------
  // Past layer (1994): intact compound, populated, warm light.
  // ---------------------------------------------------------------------------
  const pastMeshes: AbstractMesh[] = [];

  // TODO(asset-pipeline): replace with structure_rugo_main_house (past variant material)
  //   Same source mesh as the Present house above; instantiated again under
  //   the "past" era tag with the 1994 material clone.
  const housePast = mkBox(scene, "compound.house.past", 5.5, 2.6, 4.5, "past", deriveMat(materials, "mat_brick_mud", "past_intact", (m) => {
    m.albedoColor = new Color3(0.62, 0.42, 0.28);
  }));
  housePast.position = new Vector3(0, 1.3, 6);
  pastMeshes.push(housePast);

  // TODO(asset-pipeline): replace with structure_rugo_tin_roof (past variant material)
  const roofPast = mkBox(scene, "compound.roof.past", 6.2, 0.12, 5.0, "past", deriveMat(materials, "mat_tin_roof", "past_clean", (m) => {
    m.albedoColor = new Color3(0.78, 0.4, 0.24);
    m.roughness = 0.55;
  }));
  roofPast.position = new Vector3(0, 2.7, 6);
  pastMeshes.push(roofPast);

  // TODO(asset-pipeline): replace with structure_rugo_door
  //   Authored in a 30°-open pose; pivot at bottom-left corner. Past-era only.
  // Door — open, slightly angled (welcoming).
  const doorPast = mkBox(scene, "compound.door.past", 0.95, 1.95, 0.08, "past", deriveMat(materials, "mat_wood_weathered", "past_door", (m) => {
    m.albedoColor = new Color3(0.5, 0.34, 0.22);
  }));
  doorPast.position = new Vector3(-0.6, 1.0, 3.6);
  doorPast.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), -0.55);
  pastMeshes.push(doorPast);

  // Hearth smoke — a thin emissive column. Stand-in for particles until the
  // real audio + VFX pass lands.
  const smoke = mkCyl(scene, "compound.hearth.smoke.past", 0.4, 0.05, 4.0, "past", deriveMat(materials, "mat_cloth_white", "past_smoke", (m) => {
    m.albedoColor = new Color3(0.78, 0.74, 0.7);
    m.alpha = 0.32;
    m.unlit = true;
  }));
  smoke.position = new Vector3(1.2, 4.0, 6);
  pastMeshes.push(smoke);

  // TODO(asset-pipeline): replace with structure_well_stone_ring (past variant material)
  // Well — clean cover, bucket nearby. The cellar latch in 1994 is intact.
  const wellRingPast = mkCyl(scene, "compound.well.past", 0.6, 0.6, 0.7, "past", deriveMat(materials, "mat_concrete_weathered", "past_well", (m) => {
    m.albedoColor = new Color3(0.84, 0.8, 0.74);
  }));
  wellRingPast.position = new Vector3(3.2, 0.35, 0.5);
  pastMeshes.push(wellRingPast);

  // TODO(asset-pipeline): replace with structure_well_cover_plank (past variant material)
  const wellCoverPast = mkBox(scene, "compound.well.cover.past", 1.3, 0.08, 1.3, "past", deriveMat(materials, "mat_wood_weathered", "past_cover", (m) => {
    m.albedoColor = new Color3(0.62, 0.45, 0.3);
  }));
  wellCoverPast.position = new Vector3(3.2, 0.74, 0.5);
  pastMeshes.push(wellCoverPast);

  // TODO(asset-pipeline): replace with vegetation_eucalyptus_sapling (ThinInstance)
  //   Younger trees in 1994; same swap pattern as the Present grove loop.
  // Eucalyptus grove — younger, less dense.
  for (let i = 0; i < 5; i++) {
    const trunk = mkCyl(
      scene,
      `compound.eucalyptus.past.${i}`,
      0.15 + (i % 3) * 0.04,
      0.1,
      3.6 + (i % 3) * 0.5,
      "past",
      deriveMat(materials, "mat_eucalyptus_bark", "past_bark", (m) => {
        m.albedoColor = new Color3(0.66, 0.58, 0.5);
      }),
    );
    trunk.position = new Vector3(-3.5 - (i % 3) * 0.9, trunk.scaling.y * 1.8, -1 + i * 1.5);
    pastMeshes.push(trunk);
  }

  // TODO(asset-pipeline): replace with structure_family_shrine_slab (past variant material)
  // Household altar — Past variant: intact slab, upright frame, photograph
  // visible, a low candle stub beside it. The frame here is the same anchor
  // identity as the fallen one in 2026 — the player sees both.
  const altarSlabPast = mkBox(
    scene,
    "compound.altar.slab.past",
    0.95,
    0.34,
    0.55,
    "past",
    deriveMat(materials, "mat_concrete_weathered", "altar_past", (m) => {
      m.albedoColor = new Color3(0.86, 0.82, 0.74);
      m.roughness = 0.78;
    }),
  );
  altarSlabPast.position = new Vector3(-1.85, 0.17, 3.5);
  pastMeshes.push(altarSlabPast);

  // TODO(asset-pipeline): replace with prop_altar_photo_frame (upright pose)
  //   Same source asset as the Present-era fallen frame; runtime rotates.
  const framePast = mkBox(
    scene,
    "compound.altar.frame.past",
    0.42,
    0.32,
    0.04,
    "past",
    deriveMat(materials, "mat_wood_weathered", "altar_frame_past", (m) => {
      m.albedoColor = new Color3(0.5, 0.34, 0.2);
      m.roughness = 0.55;
    }),
  );
  // Standing upright on the slab, slight angle so the player sees its face.
  framePast.position = new Vector3(-1.85, 0.5, 3.45);
  framePast.rotationQuaternion = Quaternion.RotationAxis(
    new Vector3(0, 1, 0),
    -0.25,
  );
  pastMeshes.push(framePast);

  const photoPast = mkBox(
    scene,
    "compound.altar.photo.past",
    0.34,
    0.24,
    0.005,
    "past",
    deriveMat(materials, "mat_cloth_white", "altar_photo_past", (m) => {
      m.albedoColor = new Color3(0.84, 0.78, 0.7);
      m.roughness = 0.85;
    }),
  );
  photoPast.position = new Vector3(-1.85, 0.5, 3.43);
  photoPast.rotationQuaternion = framePast.rotationQuaternion?.clone() ?? null;
  pastMeshes.push(photoPast);

  // TODO(asset-pipeline): replace with prop_altar_candle (past-only)
  // Candle stub beside the frame — small cylinder.
  const candle = mkCyl(
    scene,
    "compound.altar.candle.past",
    0.05,
    0.06,
    0.12,
    "past",
    deriveMat(materials, "mat_cloth_white", "altar_candle_past", (m) => {
      m.albedoColor = new Color3(0.92, 0.88, 0.78);
      m.roughness = 0.6;
    }),
  );
  candle.position = new Vector3(-1.55, 0.4, 3.45);
  pastMeshes.push(candle);

  // TODO(asset-pipeline): replace with vegetation_elephant_grass (ThinInstance, past variant)
  // Cleared ground — short grass tufts only.
  for (let i = 0; i < 6; i++) {
    const tuft = mkBox(
      scene,
      `compound.grass.past.${i}`,
      0.4,
      0.25,
      0.4,
      "past",
      deriveMat(materials, "mat_grass_tall", "past", (m) => {
        m.albedoColor = new Color3(0.46, 0.5, 0.24);
      }),
    );
    const ang = (i / 6) * Math.PI * 2;
    const r = 3.4;
    tuft.position = new Vector3(Math.cos(ang) * r, 0.12, 1.5 + Math.sin(ang) * r);
    pastMeshes.push(tuft);
  }

  // ---------------------------------------------------------------------------
  // Act 3A (Hider path) — Present-only anchor meshes. Visible in 2026 only;
  // the Past echo always shows the 1994 moment regardless of which object
  // carries the trigger. Gate enforced in bootstrap's proximity probe.
  // ---------------------------------------------------------------------------

  // Sleeping mats — a flat rolled bundle north of the well. The player sees
  // weathered cloth sticking out of the soil, a sign something was once
  // stored underground here.
  const cellarMats = mkBox(
    scene, "compound.cellar_mats.present", 0.55, 0.14, 0.22, "present",
    deriveMat(materials, "mat_cloth_kitenge", "cellar_mats_present", (m) => {
      m.albedoColor = new Color3(0.28, 0.22, 0.16);
      m.roughness = 0.97;
    }),
  );
  cellarMats.position = new Vector3(3.4, 0.12, 1.5);
  cellarMats.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), 0.6);
  presentMeshes.push(cellarMats);

  // Water-schedule marks — a low stone slab propped against the east wall of
  // the compound, carved with tallies and dates for water-run schedules.
  const waterSchedule = mkBox(
    scene, "compound.water_schedule.present", 0.48, 0.58, 0.06, "present",
    deriveMat(materials, "mat_concrete_weathered", "water_sched_present", (m) => {
      m.albedoColor = new Color3(0.56, 0.52, 0.46);
      m.roughness = 0.88;
    }),
  );
  waterSchedule.position = new Vector3(3.0, 0.96, 5.2);
  waterSchedule.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), -0.18);
  presentMeshes.push(waterSchedule);

  // Neighbor's letter — a folded paper tucked under a flat stone south of the
  // well; the stone has shifted since 1994, exposing one corner.
  const neighborLetter = mkBox(
    scene, "compound.neighbor_letter.present", 0.18, 0.02, 0.14, "present",
    deriveMat(materials, "mat_cloth_white", "neighbor_letter_present", (m) => {
      m.albedoColor = new Color3(0.68, 0.62, 0.52);
      m.roughness = 0.95;
    }),
  );
  neighborLetter.position = new Vector3(2.4, 0.1, -0.4);
  neighborLetter.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), 1.1);
  presentMeshes.push(neighborLetter);

  // ---------------------------------------------------------------------------
  // Act 3B (Escapist path) — survivor's letter at the altar slab.
  // A rolled oilcloth tube; a survivor mailed it to the compound years later.
  // ---------------------------------------------------------------------------

  const survivorLetter = mkBox(
    scene, "compound.survivor_letter.present", 0.06, 0.06, 0.18, "present",
    deriveMat(materials, "mat_cloth_kitenge", "survivor_letter_present", (m) => {
      m.albedoColor = new Color3(0.52, 0.42, 0.3);
      m.roughness = 0.88;
    }),
  );
  survivorLetter.position = new Vector3(-1.4, 0.38, 3.85);
  survivorLetter.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 0, 1), 0.3);
  presentMeshes.push(survivorLetter);

  // ---------------------------------------------------------------------------
  // Act 3C (Observer path) — visitor's account, an inscribed flat stone near
  // the house east wall. A post-genocide visitor engraved what they knew.
  // ---------------------------------------------------------------------------

  const visitorAccount = mkBox(
    scene, "compound.visitor_account.present", 0.42, 0.06, 0.28, "present",
    deriveMat(materials, "mat_concrete_weathered", "visitor_acct_present", (m) => {
      m.albedoColor = new Color3(0.5, 0.48, 0.44);
      m.roughness = 0.92;
    }),
  );
  visitorAccount.position = new Vector3(2.8, 0.12, 5.0);
  visitorAccount.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 1, 0), 0.22);
  presentMeshes.push(visitorAccount);

  return {
    terrain,
    cellarLatch,
    familyRecords,
    gateAnchor,
    ledgerBook,
    cellarMats,
    waterSchedule,
    neighborLetter,
    survivorLetter,
    visitorAccount,
    shrineAnchor: altarSlabPresent,
    pastMeshes,
    presentMeshes,
  };
}

// ---------------------------------------------------------------------------
// Local helpers — primitive factories with era tagging baked in. They look
// chatty here on purpose; the parameter list is exactly the data the asset
// pipeline will produce, so the swap to `assetLibrary.instantiate(id, era,
// transform)` is mechanical when GLBs ship.
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
  m.scaling = new Vector3(1, 1, 1);
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
  const m = MeshBuilder.CreateCylinder(name, { diameterTop, diameterBottom, height }, scene);
  m.material = material;
  tagNode(m, era);
  return m;
}

/**
 * Pull a base material from the library, clone it for an era-specific tweak,
 * apply the patch, and freeze the clone. Per RENDERING.md §3.3 + Materials.ts
 * "cloneForVariant": the base stays frozen; the clone is mutable until we
 * freeze it ourselves.
 */
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
