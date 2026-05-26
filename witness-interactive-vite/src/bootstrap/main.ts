/**
 * bootstrap/main.ts
 *
 * The single entry point referenced by `index.html`. Builds the canvas,
 * Babylon engine, and every subsystem in the order ARCHITECTURE.md §3.1
 * prescribes. Scope through CHRONOS_SWITCH.md §8 M7:
 *   - Act 2 evidence anchors M3 → M6 (cellar, observer, boat, altar).
 *   - Act 3 path choice overlay (M7): triggered when all_evidence_found.
 *   - Act 3A (Hider) fragments: cellar_mats, water_schedule, neighbor_letter.
 *   - Act 3B (Escapist) fragments: passenger_list, boat_capacity_notes,
 *       escape_route_map, survivor_letter.
 *   - Act 3C (Observer) fragments: chalk_patrol_marks, checkpoint_records,
 *       reflection_letters, visitor_account.
 *   - Past↔Present crossfade, batched proximity probe, opening sequence + HUD.
 *
 * Boot order:
 *   1. Run IntroSequence (DOM overlay) in parallel with engine boot.
 *   2. Canvas + Engine + perf profile.
 *   3. Base scene + camera + physics + Present/Past lighting rigs.
 *   4. Rendering pipeline (fades on era change).
 *   5. Player controller + interactable registry + HUD.
 *   6. TimeManager attaches to camera.
 *   7. Build FamilyCompound + Ravine + LakeShore — both era variants tagged.
 *   8. Register four Act 2 + eleven Act 3 Memory Fragments.
 *   9. Subscribe TimeManager → RenderingPipeline.fadeToEra + AudioManager.
 *  10. Batched proximity probe (one observer) with optional requiredFlags gate.
 *  11. Wait for IntroSequence to finish, then expose the canvas.
 */

import "../style.css";
import { Vector3 } from "@babylonjs/core";
import type { AbstractMesh, Scene, UniversalCamera } from "@babylonjs/core";
import {
  buildPastRig,
  buildPresentRig,
  createBaseScene,
  initPhysics,
  MaterialLibrary,
  RenderingPipeline,
} from "../engine";
import { applyProfile, detectProfile } from "../performance";
import {
  Engine,
} from "@babylonjs/core";
import {
  interactableHighlight,
  interactableRegistry,
  playerController,
  setPerspective,
} from "../interaction";
import {
  cameraApproach,
  cameraDolly,
  fovTween,
  getEchoProfile,
  MemoryFragment,
  pastSceneController,
  startCameraBreath,
  tagLight,
  timeManager,
  waitFrames,
} from "../core";
import type { PastSceneSpec } from "../core";
import { captionOverlay, hud, ledgerUI } from "../ui";
import { audioManager, narratorSystem } from "../audio";
import { buildFamilyCompound, buildLakeShore, buildRavine } from "../world";
import { globalState } from "../narrative/StateManager";
import { narrativeController } from "../narrative/NarrativeController";
import { ledgerStore } from "../narrative/LedgerStore";
import { save, load, applyState } from "../io/SaveSystem";
import { runIntroSequence } from "./IntroSequence";
import { runLedgerOpening } from "./LedgerOpening";
import { showChoiceOverlay } from "./ChoiceOverlay";
import {
  type RemembrancePath,
  showRemembranceSequence,
} from "./RemembranceSequence";
import {
  runReturnToShrineBreather,
  runPreRemembranceBreather,
  runMidPathVistaBreather,
} from "./BreatherSequences";
import { vistaSystem } from "../core";
import { createLog } from "../log";
import { mountEmbodiedPOC } from "../experiments/embodied_poc/EmbodiedPOC";

const log = createLog("boot");

const PROXIMITY_RADIUS_M = 3.5;
const ECHO_TRANSITION_SEC = 1.8;
const AUTOSAVE_SLOT = "autosave";
const MISSION_ID = "witness";
/** FOV breath delta when entering Past — subtle pull inward. */
const ECHO_FOV_BREATH_ENTRY = 0.06;
/** FOV breath delta when returning to Present — wider burst, "breaking free". */
const ECHO_FOV_BREATH_RETURN = 0.12;

/**
 * Canonical ledger content for each unlock flag. `toast` is the short
 * one-liner shown in the HUD banner (fits 460 px wide, ~60 chars).
 * `body` is the full journal entry shown in the LedgerUI overlay.
 * Single source of truth for both live echo collection and ?resume=1 rehydration.
 */
interface LedgerEntryDef { toast: string; body: string; }
const LEDGER_ENTRIES: Readonly<Record<string, LedgerEntryDef>> = {
  act_1_complete: {
    toast: "The ledger — June 1994. \"The ledger will tell you why he never came home.\"",
    body:  "June, 1994. I have kept this book for eleven years. I record prices, weights, the measure of the harvest. Tonight I begin recording something else. There is no price for what I am about to write.",
  },
  found_cellar_evidence: {
    toast: "Bisesero, April 1994 — the cellar held nine.",
    body:  "April 9, 1994. Nine people in the space below the well. I told them three nights at most. I said it because I needed it to be true. I knew on the third day that it was not.",
  },
  found_observer_evidence: {
    toast: "Bisesero, June 1994 — what he saw, he wrote down.",
    body:  "June 3, 1994. From the ravine at first light, I counted four columns. They moved north, then turned. They knew where the people were sheltering. I wrote the direction, the time, the number. I wrote it all down.",
  },
  found_boat_evidence: {
    toast: "Lake Kivu, May 1994 — boats by night, no light, no names.",
    body:  "May 17, 1994. We pushed off from the reeds before the moon rose. I asked people to leave behind everything heavy. One man would not leave his son’s shoes. I let him keep them. The lake does not care about the weight of grief.",
  },
  found_family_records: {
    toast: "Bisesero, March 1994 — the names he kept by candlelight.",
    body:  "March 29, 1994. I write their names here so they cannot be forgotten: Félicité. Jean-Pierre. Innocent. Angèle. Théophile. Twelve names on this page. I have committed them to memory as well. The page can burn. Memory is harder to destroy.",
  },
  puzzle_a1_complete: {
    toast: "April 1994 — eight people. Sleeping in shifts.",
    body:  "April 14, 1994. Eight people now, not nine. Thérèse left in the night — I do not know where she went. The others sleep in shifts: four lying, four sitting. I brought down the two spare mats from the upper room. I told my wife they were old and worn out. She did not ask again.",
  },
  puzzle_a2_complete: {
    toast: "May 1994 — every third day, water. Each time, risk.",
    body:  "May 2, 1994. Every third day, one of us walks to the well at dawn. We go alone, we go naturally. We do not carry more than one bucket at a time. If they stop you and ask, you say you are making ugali and your wife sent you. I have rehearsed this. So has my son. He is eleven years old.",
  },
  puzzle_a3_complete: {
    toast: "July 1994 — “You saved us. I never saw you again.”",
    body:  "This letter arrived in August, carried by a man I did not recognize. It is from Consolée, who was in the cellar from April until June. She says eight of the nine survived. She asks if I am alive. She does not know the answer. I am reading her letter, so yes — but she is in Goma and I cannot tell her yet.",
  },
  puzzle_b1_complete: {
    toast: "May 1994 — forty names circled. The rest, blank space.",
    body:  "May 16, 1994. Forty names on the first list. I circled the ones the boat could hold and then I stopped. The people whose names I had not circled gathered on the shore and watched me write. I did not look up. Cowardice is sometimes the only honest thing.",
  },
  puzzle_b2_complete: {
    toast: "May 1994 — forty fit safely. Who gets on?",
    body:  "May 15, 1994. I measured the boat this morning. Forty sit safely. Forty-two if they are calm. The crossing to Zaire is four hours in the dark. If the water is rough — thirty-eight. I told myself I was doing mathematics. But mathematics does not choose who lives.",
  },
  puzzle_b3_complete: {
    toast: "May 1994 — the route that saved eighty-seven.",
    body:  "May 21, 1994. Two crossings. Forty on the first night, forty-seven on the second. The third night, militia were at the lake. I counted: eighty-seven names. Later I found the passenger lists in an oilcloth sack I had forgotten I buried. I had counted correctly. I do not know why that matters to me now.",
  },
  puzzle_b4_complete: {
    toast: "“We reached Zaire safely. I never forgot your face.”",
    body:  "This letter is dated September 1994. It is signed by Jean-Baptiste, who was on the second crossing. He describes the arrival in Goma, the camp, the walk to find family. He says he has told his children about the man who chose them. He got my name wrong. He wrote “Bernard.” My name is Barnabé. I kept the letter anyway.",
  },
  puzzle_c1_complete: {
    toast: "June 1994 — he read their marks. He said nothing.",
    body:  "June 5, 1994. I can read the chalk marks they leave on the stones. I learned this in April. Three marks: a route. Two marks crossed: already searched. One mark circled: a shelter found. I have been keeping a record. I do not know who I am keeping it for.",
  },
  puzzle_c2_complete: {
    toast: "June 1994 — he knew where they were. He warned no one.",
    body:  "June 12, 1994. I knew about the families in the gully below the ravine. I had seen them arrive two weeks earlier. The checkpoint moved south on the morning of the fourteenth. I knew the direction. I did not walk down to warn them. I told myself it was too dangerous. That was true. It was also not the whole truth.",
  },
  puzzle_c3_complete: {
    toast: "June 1994 — “Staying invisible keeps my family alive.”",
    body:  "June 18, 1994. I write this at the edge of darkness, the lamp turned low. If I fight, I die. If I hide them, we are found and we all die. If I take the boats, the militia watch the lake now. Staying invisible is the only weapon I have left. Invisible people do not save anyone else, but they survive to bury the dead. Someone must bury the dead.",
  },
  puzzle_c4_complete: {
    toast: "“He saw us die. He said nothing. But he saw.”",
    body:  "This account was recorded in 2002 by a research team documenting witness testimony. A woman named Espérance describes a figure she saw on the ravine high ground throughout June 1994. She says he watched. She saw his lantern at night. He never came down. She says: “I am not angry. I am something worse than angry. I am certain he saw us.” She did not know his name. But she described this compound exactly.",
  },
};

/**
 * Record an echo completion: add to the ledger store (idempotent), show the
 * HUD toast, and autosave narrative state. Called from every `onReturnToPresent`
 * handler so persistence and ledger collection happen in one place.
 */
function recordEcho(flag: string | undefined): void {
  const def = flag ? LEDGER_ENTRIES[flag] : undefined;
  if (flag && def) ledgerStore.add(flag, def.toast, def.body);
  if (def) hud.showLedgerToast(`Ledger entry unlocked: ${def.toast}`);
  save(AUTOSAVE_SLOT, MISSION_ID);
}

/**
 * Profile-aware echo pre-roll. Fires when the player triggers a Memory
 * Fragment — before the Past↔Present era transition starts.
 *
 * Per-fragment `EchoPrerollProfile` (from `core/EchoProfiles.ts`) drives:
 *   - `fovDelta`: FOV change per the echo's spatial register (cellar = narrow,
 *     ravine = open, lake = neutral). Applied symmetrically so the FOV is back
 *     at baseline when the transition begins.
 *   - `pullMag`: how far the camera drifts toward the anchor world position
 *     ("being drawn in"). Implemented via `cameraApproach`, which detaches
 *     and re-attaches input so the dolly isn't fought by WASD.
 *
 * Both effects run in parallel and resolve together, so the caller can
 * immediately chain `pastSceneController.begin(...)`.
 */
async function echoPreroll(
  scene: Scene,
  camera: UniversalCamera,
  fragmentId: string,
  anchorPos: Vector3,
): Promise<void> {
  const profile = getEchoProfile(fragmentId);
  const baseFov = camera.fov;
  const half = profile.durationSec / 2;

  await Promise.all([
    // Camera pull toward anchor — "being drawn in."
    cameraApproach(scene, camera, anchorPos, profile.pullMag, profile.durationSec),
    // FOV breath: narrow/widen on first half, return on second.
    fovTween(scene, camera, baseFov + profile.fovDelta, half).then(() =>
      fovTween(scene, camera, baseFov, half),
    ),
  ]);
}

/**
 * Wrap `pastSceneController.begin()` to add ambient camera breathing during
 * the Past dwell. The breath starts on `onEnterPast` and stops on
 * `onReturnToPresent`, so the player feels "present" in the memory for the
 * full 12–20 s without any authored motion in the world geometry.
 *
 * Uses a module-level `stopBreath` so that if a transition fires before the
 * dwell timer completes (e.g. `pastSceneController.returnNow()`), the breath
 * is correctly cancelled.
 */
let stopBreath: (() => void) | null = null;

function beginWithBreath(
  spec: PastSceneSpec,
  scene: Scene,
  camera: UniversalCamera,
): void {
  const origEnter = spec.onEnterPast;
  const origReturn = spec.onReturnToPresent;

  pastSceneController.begin({
    ...spec,
    onEnterPast: () => {
      origEnter?.();
      stopBreath?.();
      stopBreath = startCameraBreath(scene, camera);
    },
    onReturnToPresent: (completion) => {
      stopBreath?.();
      stopBreath = null;
      origReturn?.(completion);
    },
  });
}

/** A single registered interactable + the data the proximity probe needs. */
interface ProximityTarget {
  /** Returns true when this target should no longer show a proximity prompt. */
  isActivated: () => boolean;
  anchor: AbstractMesh;
  prompt: string;
  /** All listed flags must be true for this target's prompt to appear. */
  requiredFlags?: string[];
}

/**
 * Check whether all four Act 2 evidence flags are set; if so and the
 * choice has not been shown yet, set `all_evidence_found`, run the
 * all-evidence cinematic, show the path-selection overlay, then set the
 * chosen path flag on resolution.
 *
 * `runCinematic` is a closure defined inside `boot()` that has access to
 * `scene`, `camera`, and `pipeline`; it runs the camera lift + memoryDissolve
 * + choice overlay and resolves with the chosen path flag string.
 *
 * Called from each Act 2 fragment's `onReturnToPresent`.
 */
function makeChoiceChecker(runCinematic: () => Promise<string>): () => void {
  let shown = false;
  return () => {
    if (shown || globalState.getFlag("all_evidence_found")) return;
    if (
      !globalState.getFlag("found_cellar_evidence") ||
      !globalState.getFlag("found_boat_evidence") ||
      !globalState.getFlag("found_observer_evidence") ||
      !globalState.getFlag("found_family_records")
    ) return;

    shown = true;
    globalState.setFlag("all_evidence_found", true);
    log.info("all_evidence_found — running all-evidence cinematic + path choice");

    void runCinematic().then((pathFlag) => {
      globalState.setFlag(pathFlag, true);
      if (pathFlag === "path_hider_chosen") {
        globalState.setFlag("path_a_started", true);
        hud.showLedgerToast(
          "The path becomes clear — he hid people. Find what they left behind.",
          7000,
        );
      } else if (pathFlag === "path_escapist_chosen") {
        globalState.setFlag("path_b_started", true);
        hud.showLedgerToast(
          "The path becomes clear — he helped them escape. Trace the route.",
          7000,
        );
      } else if (pathFlag === "path_silent_chosen") {
        globalState.setFlag("path_c_started", true);
        hud.showLedgerToast(
          "The path becomes clear — he watched and said nothing. Read what he wrote.",
          7000,
        );
      }
      log.info(`path chosen — ${pathFlag} set`);
    });
  };
}

/**
 * Returns a one-shot checker for a single path's puzzle chain. Fires only
 * when all `puzzleFlags` are set. Sets `path_*_complete`, registers the
 * family shrine as a cinematic interactable, and pushes a shrine proximity
 * entry so the HUD guides the player back.
 *
 * The shrine interaction runs a brief camera-dolly approach + memoryDissolve
 * before presenting the Act 4 Remembrance overlay.
 *
 * @param scene / camera / pipeline — needed for the shrine approach cinematic.
 */
function makePathChecker(
  path: RemembrancePath,
  puzzleFlags: string[],
  shrineAnchor: AbstractMesh,
  proximityTargets: ProximityTarget[],
  scene: Scene,
  camera: UniversalCamera,
  pipeline: import("../engine").RenderingPipeline,
): () => void {
  let fired = false;
  return () => {
    if (fired) return;
    if (!puzzleFlags.every((f) => globalState.getFlag(f))) return;
    fired = true;
    const completeFlag = `path_${path}_complete` as const;
    globalState.setFlag(completeFlag, true);
    log.info(`${completeFlag} set — awaiting shrine return`);
    hud.showLedgerToast(
      "The ledger reveals its final page. Return to the family shrine.",
      8000,
    );

    // Pre-Remembrance breather runs first, then registers the shrine.
    // Wrapped in a void async IIFE so the outer checker stays synchronous
    // while the shrine registration is deferred until the sequence ends.
    let shrineTriggered = false;

    // Push the proximity prompt immediately so the HUD guides the player
    // back to the shrine during the breather sequence. The shrine itself
    // only becomes interactable after the breather resolves.
    proximityTargets.push({
      isActivated: () => shrineTriggered,
      anchor: shrineAnchor,
      prompt: "Press E to remember him",
      requiredFlags: [completeFlag],
    });

    // Pre-Remembrance breather resolves first, then the shrine becomes
    // interactive. Wrapped in a void IIFE so the outer checker stays sync.
    void (async () => {
      await runPreRemembranceBreather(scene, camera, shrineAnchor.absolutePosition);

      interactableRegistry.register(shrineAnchor, () => {
        if (shrineTriggered) return;
        shrineTriggered = true;
        interactableRegistry.unregister(shrineAnchor);

        void (async () => {
          // ── Shrine approach cinematic ──────────────────────────────────
          // Pull the camera 0.65 m toward the shrine and narrow the FOV to an
          // intimate reading angle. The memoryDissolve builds the same
          // perceptual weight as an era transition, signalling that the player
          // is about to cross a threshold — but it's the threshold into memory,
          // not out of it. Input stays detached until the page reloads.
          const canvas = scene.getEngine().getRenderingCanvas();
          if (canvas) camera.detachControl();

          const toShrine = shrineAnchor.absolutePosition.subtract(camera.position).normalize();
          const approachPos = camera.position.clone().add(toShrine.scale(0.65));
          approachPos.y = camera.position.y; // keep eye height

          await Promise.all([
            cameraDolly(
              scene, camera,
              { position: approachPos, target: shrineAnchor.absolutePosition },
              { durationSec: 1.4 },
            ),
            fovTween(scene, camera, 0.82, 1.4),
            pipeline.memoryDissolve(1.4),
          ]);

          // Brief pause — the weight of arriving settles before the overlay.
          await waitFrames(scene, 0.35);

          const memorialization = await showRemembranceSequence(path);
          // The RemembranceSequence "Play again" button reloads the page, so
          // we don't need to restore camera state after this point.
          globalState.setFlag("game_complete", true);
          globalState.setFlag("memorialization_complete", true);
          narrativeController.onGameComplete(path, memorialization);
          log.info(`game_complete — path ${path}, memorialization: ${memorialization}`);
        })();
      });
    })();
  };
}

async function boot(): Promise<void> {
  const params = new URLSearchParams(window.location.search);

  // Dev: Embodied POC route — bypass the full narrative and test animation blending.
  if (params.get("poc") === "1") {
    const canvas = document.createElement("canvas");
    canvas.id = "renderCanvas";
    document.body.appendChild(canvas);
    await mountEmbodiedPOC(canvas);
    log.info("embodied POC mounted");
    return;
  }

  // Resume from autosave when the URL contains ?resume=1. Applied before the
  // scene is built so narrative flags are live during world construction.
  if (params.get("resume") === "1") {
    const blob = load(AUTOSAVE_SLOT);
    if (blob) {
      applyState(blob);
      // Restore ledger entries whose unlock flags survived the save.
      for (const [flag, def] of Object.entries(LEDGER_ENTRIES)) {
        if (globalState.getFlag(flag)) ledgerStore.add(flag, def.toast, def.body);
      }
      log.info("session resumed from autosave");
    } else {
      log.warn("?resume=1 but no autosave found — starting fresh");
    }
  }

  const canvas = document.createElement("canvas");
  canvas.id = "renderCanvas";
  canvas.tabIndex = 0;
  document.body.appendChild(canvas);

  const engine = new Engine(canvas, true, {
    stencil: true,
    preserveDrawingBuffer: false,
    powerPreference: "high-performance",
  });
  engine.resize();
  log.info(`canvas ${canvas.clientWidth}×${canvas.clientHeight}, gl=${engine.webGLVersion}`);

  const profile = detectProfile();
  applyProfile(engine, profile);

  const { scene, camera } = createBaseScene(engine);

  // First-frame pose is **elevated wide** per the OPENING_SEQUENCE §6
  // "satellite-descent" register — the player arrives mid-descent and the
  // cinematic camera settles into spawn pose just as the intro overlay
  // fades. The spawn pose ("just inside the gate, facing the house") is
  // captured below; the intro `onFadeStart` callback drives the dolly.
  const cinematicEye = new Vector3(0, 4.2, -7);
  const cinematicTarget = new Vector3(0, 1.0, 6);
  const spawnEye = new Vector3(0, 1.65, -2);
  const spawnTarget = new Vector3(0, 1.4, 6);
  const spawnFov = 1.05;
  const cinematicFov = 1.28;
  camera.position = cinematicEye.clone();
  camera.setTarget(cinematicTarget);
  camera.fov = cinematicFov;

  // Intro runs in parallel with engine init — assets stream behind the
  // text frame per OPENING_SEQUENCE §3 "load-state behavior". The
  // `onFadeStart` callback lets the cinematic descent land in sync with the
  // overlay clearing. On `prefers-reduced-motion`, we snap to spawn pose
  // instantly to respect vestibular-sensitive players (§9 accessibility).
  const HANDOFF_DOLLY_SEC = 2.4;
  const introPromise = runIntroSequence({
    onFadeStart: ({ reduceMotion }) => {
      if (reduceMotion) {
        camera.position.copyFrom(spawnEye);
        camera.setTarget(spawnTarget);
        camera.fov = spawnFov;
        return;
      }
      void cameraDolly(scene, camera, { position: spawnEye, target: spawnTarget }, {
        durationSec: HANDOFF_DOLLY_SEC,
      });
      void fovTween(scene, camera, spawnFov, HANDOFF_DOLLY_SEC);
    },
  });

  await initPhysics(scene, profile);

  // Both era lighting rigs live in the scene; layer-mask filtering on each
  // light decides which era's meshes they illuminate (CHRONOS_SWITCH §3.5).
  const presentRig = buildPresentRig(scene, profile);
  const pastRig = buildPastRig(scene, profile);
  tagLight(presentRig.sun, "present");
  tagLight(presentRig.sky, "present");
  tagLight(presentRig.stormRim, "present");
  tagLight(pastRig.sun, "past");
  tagLight(pastRig.sky, "past");
  tagLight(pastRig.stormRim, "past");

  const pipeline = RenderingPipeline.attach(scene, camera, profile);

  playerController.attach(scene, camera);
  interactableRegistry.attach(scene);
  interactableHighlight.attach(scene);
  timeManager.attach(camera);
  vistaSystem.attach(scene, camera);
  hud.attach(scene, camera);
  hud.setLocationLabel("Family Compound");
  await audioManager.init(scene, profile);
  audioManager.setLocation("family_compound");
  captionOverlay.attach();
  captionOverlay.restorePreference();
  narratorSystem.attach(scene);

  // World content — Act 2 + Act 3 evidence locations.
  const materials = MaterialLibrary.build(scene);
  const compound = buildFamilyCompound(scene, materials);
  const ravine = buildRavine(scene, materials);
  const lakeShore = buildLakeShore(scene, materials);

  // Vista anchor points — player must stand still for 5 s inside the radius
  // to trigger a narrator reflection. Positions are scaffold placeholders;
  // tune to match actual geometry once assets are in place.
  vistaSystem.register({
    id: "vista_compound_heights",
    position: new Vector3(2, 3.5, 8),
    radius: 8,
    narratorKey: "vista_compound_hills",
  });
  vistaSystem.register({
    id: "vista_lakeshore",
    position: new Vector3(12, 1.8, 18),
    radius: 7,
    narratorKey: "vista_lake_water",
  });
  vistaSystem.register({
    id: "vista_ravine_high",
    position: new Vector3(-8, 5.0, 20),
    radius: 7,
    narratorKey: "vista_ravine_valley",
  });
  vistaSystem.register({
    id: "vista_heights_overlook",
    position: new Vector3(-4, 7.0, 30),
    radius: 9,
    narratorKey: "vista_heights_silence",
  });

  // -------------------------------------------------------------------------
  // Phase 1 ledger pickup — the first interactable. Sets `act_1_complete`
  // which gates every Act 2 prompt in the proximity probe below.
  // -------------------------------------------------------------------------
  let ledgerOpening = false;
  if (!globalState.getFlag("act_1_complete")) {
    interactableRegistry.register(compound.ledgerBook, () => {
      if (ledgerOpening || globalState.getFlag("act_1_complete")) return;
      ledgerOpening = true;
      // Disable HUD prompt + freeze input via a one-shot "input frozen"
      // sentinel checked by the proximity probe below. The PlayerController
      // doesn't expose freeze/restore, so we detach the camera control for
      // the duration of the sequence.
      const canvas = engine.getRenderingCanvas()!;
      void runLedgerOpening({
        scene,
        camera,
        ledger: compound.ledgerBook,
        freezeInput: () => {
          camera.detachControl();
          hud.setProximity(false);
          interactableHighlight.setHovered(null);
        },
        restoreInput: () => {
          camera.attachControl(canvas, true);
          ledgerOpening = false;
          globalState.setFlag("act_1_complete", true);
          interactableRegistry.unregister(compound.ledgerBook);
          recordEcho("act_1_complete");
          log.info("act_1_complete — Phase 1 closed, Act 2 opened");
          // Quiet beat after the close before the world re-opens.
          setTimeout(() => {
            hud.showLedgerToast(
              "The compound is yours. Walk where the evidence leads.",
              6500,
            );
          }, 600);
        },
      });
    });
  }

  // Shared check function — each Act 2 echo calls this on return to see if
  // all four evidence flags are now set and the choice should appear.
  // Late-bound: `allEvidenceCinematic` is defined further down once `scene`,
  // `camera`, and `pipeline` are in scope; we reassign before any fragment
  // can call it so the no-op default is never reached in practice.
  let checkAllEvidence: () => void = () => {};

  // Per-path completion checkers — reassigned after proximityTargets is defined
  // below so the shrine anchor + targets array can be passed in. The no-op
  // defaults are safe because the fragments are not yet interactive at this point.
  let checkPathA: () => void = () => {};
  let checkPathB: () => void = () => {};
  let checkPathC: () => void = () => {};

  // -------------------------------------------------------------------------
  // Act 2 — four evidence-anchor Memory Fragments (M3 → M6).
  // -------------------------------------------------------------------------

  // M3: Cellar door latch — Protector dwell, 12 s.
  const cellarFragment = new MemoryFragment(compound.cellarLatch, "cellar_door_latch", {
    transitionTo: "past",
    transitionDurationSec: ECHO_TRANSITION_SEC,
    onActivate: async () => {
      await echoPreroll(scene, camera, "cellar_door_latch", compound.cellarLatch.absolutePosition.clone());
      beginWithBreath({
        fragmentId: "cellar_door_latch",
        durationSec: 12,
        returnTransitionSec: ECHO_TRANSITION_SEC,
        pastChangeKey: "cellar_evidence_witnessed",
        unlocksFlag: "found_cellar_evidence",
        onEnterPast: () => {
          audioManager.playNarratorEntry("cellar_echo_intro");
          hud.setProximity(false);
          hud.setDateLabel("1994, April. Bisesero Hills.");
        },
        onReturnToPresent: ({ unlocksFlag }) => {
          hud.setDateLabel("2026, April. Bisesero Hills.");
          recordEcho(unlocksFlag);
          log.info(`echo complete — ${unlocksFlag} set`);
          checkAllEvidence();
        },
      }, scene, camera);
    },
  });
  cellarFragment.bindInteraction((mesh, handler) => interactableRegistry.register(mesh, handler));

  // M4: Observer's journal — Hidden dwell, 14 s. Perspective flips.
  const observerFragment = new MemoryFragment(ravine.observerJournal, "observer_notes", {
    transitionTo: "past",
    transitionDurationSec: ECHO_TRANSITION_SEC,
    onActivate: async () => {
      await echoPreroll(scene, camera, "observer_notes", ravine.observerJournal.absolutePosition.clone());
      beginWithBreath({
        fragmentId: "observer_notes",
        durationSec: 14,
        returnTransitionSec: ECHO_TRANSITION_SEC,
        pastChangeKey: "observer_notes_witnessed",
        unlocksFlag: "found_observer_evidence",
        onEnterPast: () => {
          audioManager.playNarratorEntry("ravine_echo_intro");
          hud.setProximity(false);
          hud.setLocationLabel("Ravine — vantage point");
          hud.setDateLabel("1994, June. Bisesero Hills.");
          setPerspective("hidden");
        },
        onReturnToPresent: ({ unlocksFlag }) => {
          hud.setDateLabel("2026, April. Bisesero Hills.");
          hud.setLocationLabel("Family Compound");
          recordEcho(unlocksFlag);
          setPerspective("investigator");
          log.info(`echo complete — ${unlocksFlag} set`);
          checkAllEvidence();
        },
      }, scene, camera);
    },
  });
  observerFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // M6a: Boat paddle — Protector dwell, 14 s.
  const boatPaddleFragment = new MemoryFragment(lakeShore.boatPaddle, "boat_paddle", {
    transitionTo: "past",
    transitionDurationSec: ECHO_TRANSITION_SEC,
    onActivate: async () => {
      await echoPreroll(scene, camera, "boat_paddle", lakeShore.boatPaddle.absolutePosition.clone());
      beginWithBreath({
        fragmentId: "boat_paddle",
        durationSec: 14,
        returnTransitionSec: ECHO_TRANSITION_SEC,
        pastChangeKey: "boat_paddle_witnessed",
        unlocksFlag: "found_boat_evidence",
        onEnterPast: () => {
          audioManager.playNarratorEntry("lake_echo_intro");
          hud.setProximity(false);
          hud.setLocationLabel("Lake shore — dock");
          hud.setDateLabel("1994, May. Lake Kivu, southern bend.");
        },
        onReturnToPresent: ({ unlocksFlag }) => {
          hud.setDateLabel("2026, April. Bisesero Hills.");
          hud.setLocationLabel("Family Compound");
          recordEcho(unlocksFlag);
          log.info(`echo complete — ${unlocksFlag} set`);
          checkAllEvidence();
        },
      }, scene, camera);
    },
  });
  boatPaddleFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // M6b: Household altar photo frame — Protector dwell, 10 s.
  const familyRecordsFragment = new MemoryFragment(
    compound.familyRecords,
    "family_records",
    {
      transitionTo: "past",
      transitionDurationSec: ECHO_TRANSITION_SEC,
      onActivate: async () => {
        await echoPreroll(scene, camera, "family_records", compound.familyRecords.absolutePosition.clone());
        beginWithBreath({
          fragmentId: "family_records",
          durationSec: 10,
          returnTransitionSec: ECHO_TRANSITION_SEC,
          pastChangeKey: "family_records_witnessed",
          unlocksFlag: "found_family_records",
          onEnterPast: () => {
            audioManager.playNarratorEntry("altar_echo_intro");
            hud.setProximity(false);
            hud.setLocationLabel("Family compound — household altar");
            hud.setDateLabel("1994, March. Bisesero Hills.");
          },
          onReturnToPresent: ({ unlocksFlag }) => {
            hud.setDateLabel("2026, April. Bisesero Hills.");
            hud.setLocationLabel("Family Compound");
            recordEcho(unlocksFlag);
            log.info(`echo complete — ${unlocksFlag} set`);
            checkAllEvidence();
          },
        }, scene, camera);
      },
    },
  );
  familyRecordsFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // -------------------------------------------------------------------------
  // Act 3A — Hider path fragments (requiredFlags: path_hider_chosen + chain).
  // -------------------------------------------------------------------------

  // puzzle_1: Cellar reconstruction — sleeping mats near the well.
  const cellarMatsFragment = new MemoryFragment(compound.cellarMats, "cellar_mats", {
    transitionTo: "past",
    transitionDurationSec: ECHO_TRANSITION_SEC,
    onActivate: async () => {
      await echoPreroll(scene, camera, "cellar_mats", compound.cellarMats.absolutePosition.clone());
      beginWithBreath({
        fragmentId: "cellar_mats",
        durationSec: 16,
        returnTransitionSec: ECHO_TRANSITION_SEC,
        pastChangeKey: "cellar_mats_witnessed",
        unlocksFlag: "puzzle_a1_complete",
        onEnterPast: () => {
          audioManager.playNarratorEntry("cellar_mats_intro");
          hud.setProximity(false);
          hud.setLocationLabel("Family compound — cellar");
          hud.setDateLabel("1994, April. Underground.");
        },
        onReturnToPresent: ({ unlocksFlag }) => {
          hud.setDateLabel("2026, April. Bisesero Hills.");
          hud.setLocationLabel("Family Compound");
          recordEcho(unlocksFlag);
          log.info(`echo complete — ${unlocksFlag} set`);
        },
      }, scene, camera);
    },
  });
  cellarMatsFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // puzzle_2: Evidence of risk — water-schedule marks on the compound wall.
  const waterScheduleFragment = new MemoryFragment(compound.waterSchedule, "water_schedule", {
    transitionTo: "past",
    transitionDurationSec: ECHO_TRANSITION_SEC,
    onActivate: async () => {
      await echoPreroll(scene, camera, "water_schedule", compound.waterSchedule.absolutePosition.clone());
      beginWithBreath({
        fragmentId: "water_schedule",
        durationSec: 14,
        returnTransitionSec: ECHO_TRANSITION_SEC,
        pastChangeKey: "water_schedule_witnessed",
        unlocksFlag: "puzzle_a2_complete",
        onEnterPast: () => {
          audioManager.playNarratorEntry("water_schedule_intro");
          hud.setProximity(false);
          hud.setLocationLabel("Family compound — east wall");
          hud.setDateLabel("1994, May. Every third day.");
        },
        onReturnToPresent: ({ unlocksFlag }) => {
          hud.setDateLabel("2026, April. Bisesero Hills.");
          hud.setLocationLabel("Family Compound");
          recordEcho(unlocksFlag);
          log.info(`echo complete — ${unlocksFlag} set`);
          void runMidPathVistaBreather(scene, camera, "hider");
        },
      }, scene, camera);
    },
  });
  waterScheduleFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // puzzle_3: The cost — sealed letter from a hidden neighbor.
  const neighborLetterFragment = new MemoryFragment(compound.neighborLetter, "neighbor_letter", {
    transitionTo: "past",
    transitionDurationSec: ECHO_TRANSITION_SEC,
    onActivate: async () => {
      await echoPreroll(scene, camera, "neighbor_letter", compound.neighborLetter.absolutePosition.clone());
      beginWithBreath({
        fragmentId: "neighbor_letter",
        durationSec: 12,
        returnTransitionSec: ECHO_TRANSITION_SEC,
        pastChangeKey: "neighbor_letter_witnessed",
        unlocksFlag: "puzzle_a3_complete",
        onEnterPast: () => {
          audioManager.playNarratorEntry("neighbor_letter_intro");
          hud.setProximity(false);
          hud.setLocationLabel("Family compound — cellar stone");
          hud.setDateLabel("1994, July. A letter, sealed.");
        },
        onReturnToPresent: ({ unlocksFlag }) => {
          hud.setDateLabel("2026, April. Bisesero Hills.");
          hud.setLocationLabel("Family Compound");
          recordEcho(unlocksFlag);
          log.info(`echo complete — ${unlocksFlag} set`);
          checkPathA();
        },
      }, scene, camera);
    },
  });
  neighborLetterFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // -------------------------------------------------------------------------
  // Act 3B — Escapist path fragments (requiredFlags: path_escapist_chosen + chain).
  // -------------------------------------------------------------------------

  // puzzle_1: The lake route — passenger list at the dock.
  const passengerListFragment = new MemoryFragment(lakeShore.passengerList, "passenger_list", {
    transitionTo: "past",
    transitionDurationSec: ECHO_TRANSITION_SEC,
    onActivate: async () => {
      await echoPreroll(scene, camera, "passenger_list", lakeShore.passengerList.absolutePosition.clone());
      beginWithBreath({
        fragmentId: "passenger_list",
        durationSec: 16,
        returnTransitionSec: ECHO_TRANSITION_SEC,
        pastChangeKey: "passenger_list_witnessed",
        unlocksFlag: "puzzle_b1_complete",
        onEnterPast: () => {
          audioManager.playNarratorEntry("passenger_list_intro");
          hud.setProximity(false);
          hud.setLocationLabel("Lake shore — dock");
          hud.setDateLabel("1994, May. Names, circled and crossed.");
        },
        onReturnToPresent: ({ unlocksFlag }) => {
          hud.setDateLabel("2026, April. Bisesero Hills.");
          hud.setLocationLabel("Lake Shore");
          recordEcho(unlocksFlag);
          log.info(`echo complete — ${unlocksFlag} set`);
        },
      }, scene, camera);
    },
  });
  passengerListFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // puzzle_2: The selection — boat-capacity board.
  const boatCapacityFragment = new MemoryFragment(
    lakeShore.boatCapacityBoard,
    "boat_capacity_notes",
    {
      transitionTo: "past",
      transitionDurationSec: ECHO_TRANSITION_SEC,
      onActivate: async () => {
        await echoPreroll(scene, camera, "boat_capacity_notes", lakeShore.boatCapacityBoard.absolutePosition.clone());
        beginWithBreath({
          fragmentId: "boat_capacity_notes",
          durationSec: 14,
          returnTransitionSec: ECHO_TRANSITION_SEC,
          pastChangeKey: "boat_capacity_witnessed",
          unlocksFlag: "puzzle_b2_complete",
          onEnterPast: () => {
            audioManager.playNarratorEntry("boat_capacity_intro");
            hud.setProximity(false);
            hud.setLocationLabel("Lake shore — dock bench");
            hud.setDateLabel("1994, May. The arithmetic of survival.");
          },
          onReturnToPresent: ({ unlocksFlag }) => {
            hud.setDateLabel("2026, April. Bisesero Hills.");
            hud.setLocationLabel("Lake Shore");
            recordEcho(unlocksFlag);
            log.info(`echo complete — ${unlocksFlag} set`);
            void runMidPathVistaBreather(scene, camera, "escapist");
          },
        }, scene, camera);
      },
    },
  );
  boatCapacityFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // puzzle_3: The journey — escape route map near the dock.
  const escapeRouteFragment = new MemoryFragment(
    lakeShore.escapeRouteMap,
    "escape_route_map",
    {
      transitionTo: "past",
      transitionDurationSec: ECHO_TRANSITION_SEC,
      onActivate: async () => {
        await echoPreroll(scene, camera, "escape_route_map", lakeShore.escapeRouteMap.absolutePosition.clone());
        beginWithBreath({
          fragmentId: "escape_route_map",
          durationSec: 16,
          returnTransitionSec: ECHO_TRANSITION_SEC,
          pastChangeKey: "escape_route_witnessed",
          unlocksFlag: "puzzle_b3_complete",
          onEnterPast: () => {
            audioManager.playNarratorEntry("escape_route_intro");
            hud.setProximity(false);
            hud.setLocationLabel("Lake shore — route markers");
            hud.setDateLabel("1994, May. Three villages. One night.");
          },
          onReturnToPresent: ({ unlocksFlag }) => {
            hud.setDateLabel("2026, April. Bisesero Hills.");
            hud.setLocationLabel("Lake Shore");
            recordEcho(unlocksFlag);
            log.info(`echo complete — ${unlocksFlag} set`);
          },
        }, scene, camera);
      },
    },
  );
  escapeRouteFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // puzzle_4: The afterward — survivor's letter at the altar.
  const survivorLetterFragment = new MemoryFragment(
    compound.survivorLetter,
    "survivor_letter",
    {
      transitionTo: "past",
      transitionDurationSec: ECHO_TRANSITION_SEC,
      onActivate: async () => {
        await echoPreroll(scene, camera, "survivor_letter", compound.survivorLetter.absolutePosition.clone());
        beginWithBreath({
          fragmentId: "survivor_letter",
          durationSec: 10,
          returnTransitionSec: ECHO_TRANSITION_SEC,
          pastChangeKey: "survivor_letter_witnessed",
          unlocksFlag: "puzzle_b4_complete",
          onEnterPast: () => {
            audioManager.playNarratorEntry("survivor_letter_intro");
            hud.setProximity(false);
            hud.setLocationLabel("Family compound — altar");
            hud.setDateLabel("1994, May. Departure at dawn.");
          },
          onReturnToPresent: ({ unlocksFlag }) => {
            hud.setDateLabel("2026, April. Bisesero Hills.");
            hud.setLocationLabel("Family Compound");
            recordEcho(unlocksFlag);
            log.info(`echo complete — ${unlocksFlag} set`);
            checkPathB();
          },
        }, scene, camera);
      },
    },
  );
  survivorLetterFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // -------------------------------------------------------------------------
  // Act 3C — Observer path fragments (requiredFlags: path_silent_chosen + chain).
  // -------------------------------------------------------------------------

  // puzzle_1: The vantage point — chalk patrol marks on the outcrop stone.
  const chalkMarksFragment = new MemoryFragment(
    ravine.chalkPatrolMarks,
    "chalk_patrol_marks",
    {
      transitionTo: "past",
      transitionDurationSec: ECHO_TRANSITION_SEC,
      onActivate: async () => {
        await echoPreroll(scene, camera, "chalk_patrol_marks", ravine.chalkPatrolMarks.absolutePosition.clone());
        beginWithBreath({
          fragmentId: "chalk_patrol_marks",
          durationSec: 20,
          returnTransitionSec: ECHO_TRANSITION_SEC,
          pastChangeKey: "chalk_marks_witnessed",
          unlocksFlag: "puzzle_c1_complete",
          onEnterPast: () => {
            audioManager.playNarratorEntry("chalk_marks_intro");
            hud.setProximity(false);
            hud.setLocationLabel("Ravine — vantage point");
            hud.setDateLabel("1994, June. The valley below.");
            setPerspective("hidden");
          },
          onReturnToPresent: ({ unlocksFlag }) => {
            hud.setDateLabel("2026, April. Bisesero Hills.");
            hud.setLocationLabel("Family Compound");
            recordEcho(unlocksFlag);
            setPerspective("investigator");
            log.info(`echo complete — ${unlocksFlag} set`);
          },
        }, scene, camera);
      },
    },
  );
  chalkMarksFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // puzzle_2: The moral inventory — checkpoint-records slab.
  const checkpointRecordsFragment = new MemoryFragment(
    ravine.checkpointRecords,
    "checkpoint_records",
    {
      transitionTo: "past",
      transitionDurationSec: ECHO_TRANSITION_SEC,
      onActivate: async () => {
        await echoPreroll(scene, camera, "checkpoint_records", ravine.checkpointRecords.absolutePosition.clone());
        beginWithBreath({
          fragmentId: "checkpoint_records",
          durationSec: 18,
          returnTransitionSec: ECHO_TRANSITION_SEC,
          pastChangeKey: "checkpoint_records_witnessed",
          unlocksFlag: "puzzle_c2_complete",
          onEnterPast: () => {
            audioManager.playNarratorEntry("checkpoint_records_intro");
            hud.setProximity(false);
            hud.setLocationLabel("Ravine — stones");
            hud.setDateLabel("1994, June. What he knew. What he kept.");
            setPerspective("hidden");
          },
          onReturnToPresent: ({ unlocksFlag }) => {
            hud.setDateLabel("2026, April. Bisesero Hills.");
            hud.setLocationLabel("Family Compound");
            recordEcho(unlocksFlag);
            setPerspective("investigator");
            log.info(`echo complete — ${unlocksFlag} set`);
            void runMidPathVistaBreather(scene, camera, "observer");
          },
        }, scene, camera);
      },
    },
  );
  checkpointRecordsFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // puzzle_3: The rationalization — unsent reflection letters in the cairn.
  const reflectionLettersFragment = new MemoryFragment(
    ravine.reflectionLetters,
    "reflection_letters",
    {
      transitionTo: "past",
      transitionDurationSec: ECHO_TRANSITION_SEC,
      onActivate: async () => {
        await echoPreroll(scene, camera, "reflection_letters", ravine.reflectionLetters.absolutePosition.clone());
        beginWithBreath({
          fragmentId: "reflection_letters",
          durationSec: 20,
          returnTransitionSec: ECHO_TRANSITION_SEC,
          pastChangeKey: "reflection_letters_witnessed",
          unlocksFlag: "puzzle_c3_complete",
          onEnterPast: () => {
            audioManager.playNarratorEntry("reflection_letters_intro");
            hud.setProximity(false);
            hud.setLocationLabel("Ravine — starlight");
            hud.setDateLabel("1994, June. Writing by dark.");
            setPerspective("hidden");
          },
          onReturnToPresent: ({ unlocksFlag }) => {
            hud.setDateLabel("2026, April. Bisesero Hills.");
            hud.setLocationLabel("Family Compound");
            recordEcho(unlocksFlag);
            setPerspective("investigator");
            log.info(`echo complete — ${unlocksFlag} set`);
          },
        }, scene, camera);
      },
    },
  );
  reflectionLettersFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // puzzle_4: The aftermath — visitor's account near the house east wall.
  const visitorAccountFragment = new MemoryFragment(
    compound.visitorAccount,
    "visitor_account",
    {
      transitionTo: "past",
      transitionDurationSec: ECHO_TRANSITION_SEC,
      onActivate: async () => {
        await echoPreroll(scene, camera, "visitor_account", compound.visitorAccount.absolutePosition.clone());
        beginWithBreath({
          fragmentId: "visitor_account",
          durationSec: 12,
          returnTransitionSec: ECHO_TRANSITION_SEC,
          pastChangeKey: "visitor_account_witnessed",
          unlocksFlag: "puzzle_c4_complete",
          onEnterPast: () => {
            audioManager.playNarratorEntry("visitor_account_intro");
            hud.setProximity(false);
            hud.setLocationLabel("Family compound — east wall");
            hud.setDateLabel("Post-1994. A visitor comes.");
          },
          onReturnToPresent: ({ unlocksFlag }) => {
            hud.setDateLabel("2026, April. Bisesero Hills.");
            hud.setLocationLabel("Family Compound");
            recordEcho(unlocksFlag);
            log.info(`echo complete — ${unlocksFlag} set`);
            checkPathC();
          },
        }, scene, camera);
      },
    },
  );
  visitorAccountFragment.bindInteraction((mesh, handler) =>
    interactableRegistry.register(mesh, handler),
  );

  // ── All-evidence cinematic closure ────────────────────────────────────────
  // Fires when all four Act 2 evidence flags are set. Lifts the camera into
  // a surveying position (the world seen from just above it — all three
  // anchor sites visible if the player is near the compound centre), then
  // shows the path-choice overlay, then settles the camera back. The
  // memoryDissolve during the lift builds the same perceptual anticipation as
  // an era transition — the player knows something irrevocable is about to
  // happen. MISSION_BLUEPRINT.md §3 Phase 3.
  const allEvidenceCinematic = async (): Promise<string> => {
    // Quiet breather before the choice overlay — player retains control,
    // narrator plays, text fades in and out. Runs first while the player
    // is still free to walk; camera lock happens after it resolves.
    await runReturnToShrineBreather(scene, camera);

    const canvas = engine.getRenderingCanvas()!;
    camera.detachControl();
    const savedPos = camera.position.clone();
    const savedFov = camera.fov;

    // Lift 1.5 m + widen FOV to give a surveying perspective.
    const surveyPos = new Vector3(savedPos.x, savedPos.y + 1.5, savedPos.z);
    await Promise.all([
      cameraDolly(scene, camera, { position: surveyPos }, { durationSec: 2.2 }),
      fovTween(scene, camera, savedFov + 0.10, 2.2),
      pipeline.memoryDissolve(2.2),
    ]);

    // Brief pause at apex before the overlay — the weight of the moment.
    await waitFrames(scene, 0.45);

    const pathFlag = await showChoiceOverlay();

    // Settle back to spawn pose.
    await Promise.all([
      cameraDolly(scene, camera, { position: savedPos }, { durationSec: 1.0 }),
      fovTween(scene, camera, savedFov, 1.0),
    ]);
    camera.attachControl(canvas, true);
    return pathFlag;
  };

  // Now that the cinematic closure is defined, wire it into the checker.
  checkAllEvidence = makeChoiceChecker(allEvidenceCinematic);

  // Wire TimeManager events to the rendering pipeline + audio mixer.
  // Asymmetric FOV breath: entering Past = subtle pull inward (narrow),
  // returning to Present = wider burst ("breaking free").
  // CHRONOS_SWITCH.md §3.6 "moment of dissociation."
  timeManager.subscribe((evt) => {
    if (evt.type === "transitionStarted") {
      void pipeline.fadeToEra(evt.to, evt.durationSec);
      void pipeline.memoryDissolve(evt.durationSec);
      void audioManager.transitionToEra(evt.to, evt.durationSec * 1000);

      const isReturn = evt.to === "present";
      const breathDelta = isReturn ? ECHO_FOV_BREATH_RETURN : ECHO_FOV_BREATH_ENTRY;
      const baseFov = camera.fov;
      const half = evt.durationSec / 2;
      void fovTween(scene, camera, baseFov + breathDelta, half).then(() =>
        fovTween(scene, camera, baseFov, half),
      );
    }
  });

  // Single batched proximity probe — one observer scans all targets per frame.
  // `requiredFlags` lists flags that must all be true for a target's prompt to
  // appear; acts as the path-gate for Act 3 fragments.
  // The shrine entries for Act 4 are pushed by makePathChecker when a path
  // completes, so the array is mutable and kept alive for the session.
  const proximityTargets: ProximityTarget[] = [
    // Phase 1 — the ledger book on the altar, the first interactable.
    // Hidden once `act_1_complete` is set (the registry entry is also dropped).
    {
      isActivated: () => globalState.getFlag("act_1_complete") || ledgerOpening,
      anchor: compound.ledgerBook,
      prompt: "Press E to open the ledger",
    },

    // Act 2 — gated on `act_1_complete`; available only after the ledger opens.
    { isActivated: () => cellarFragment.activated,        anchor: compound.cellarLatch,    prompt: "Press E to remember", requiredFlags: ["act_1_complete"] },
    { isActivated: () => observerFragment.activated,      anchor: ravine.observerJournal,  prompt: "Press E to read",     requiredFlags: ["act_1_complete"] },
    { isActivated: () => boatPaddleFragment.activated,    anchor: lakeShore.boatPaddle,    prompt: "Press E to lift",     requiredFlags: ["act_1_complete"] },
    { isActivated: () => familyRecordsFragment.activated, anchor: compound.familyRecords,  prompt: "Press E to look",     requiredFlags: ["act_1_complete"] },

    // Act 3A — Hider path, gated + sequenced.
    { isActivated: () => cellarMatsFragment.activated,     anchor: compound.cellarMats,     prompt: "Press E to examine", requiredFlags: ["path_hider_chosen"] },
    { isActivated: () => waterScheduleFragment.activated,  anchor: compound.waterSchedule,  prompt: "Press E to study",   requiredFlags: ["path_hider_chosen", "puzzle_a1_complete"] },
    { isActivated: () => neighborLetterFragment.activated, anchor: compound.neighborLetter, prompt: "Press E to open",    requiredFlags: ["path_hider_chosen", "puzzle_a2_complete"] },

    // Act 3B — Escapist path, gated + sequenced.
    { isActivated: () => passengerListFragment.activated,  anchor: lakeShore.passengerList,     prompt: "Press E to unfold", requiredFlags: ["path_escapist_chosen"] },
    { isActivated: () => boatCapacityFragment.activated,   anchor: lakeShore.boatCapacityBoard, prompt: "Press E to read",   requiredFlags: ["path_escapist_chosen", "puzzle_b1_complete"] },
    { isActivated: () => escapeRouteFragment.activated,    anchor: lakeShore.escapeRouteMap,    prompt: "Press E to trace",  requiredFlags: ["path_escapist_chosen", "puzzle_b2_complete"] },
    { isActivated: () => survivorLetterFragment.activated, anchor: compound.survivorLetter,     prompt: "Press E to open",   requiredFlags: ["path_escapist_chosen", "puzzle_b3_complete"] },

    // Act 3C — Observer (Silent) path, gated + sequenced.
    { isActivated: () => chalkMarksFragment.activated,         anchor: ravine.chalkPatrolMarks,   prompt: "Press E to read",     requiredFlags: ["path_silent_chosen"] },
    { isActivated: () => checkpointRecordsFragment.activated,  anchor: ravine.checkpointRecords,  prompt: "Press E to decipher",  requiredFlags: ["path_silent_chosen", "puzzle_c1_complete"] },
    { isActivated: () => reflectionLettersFragment.activated,  anchor: ravine.reflectionLetters,  prompt: "Press E to unfold",   requiredFlags: ["path_silent_chosen", "puzzle_c2_complete"] },
    { isActivated: () => visitorAccountFragment.activated,     anchor: compound.visitorAccount,   prompt: "Press E to read",     requiredFlags: ["path_silent_chosen", "puzzle_c3_complete"] },
  ];

  // Wire path checkers now that proximityTargets + compound.shrineAnchor are ready.
  checkPathA = makePathChecker("a", ["puzzle_a1_complete", "puzzle_a2_complete", "puzzle_a3_complete"], compound.shrineAnchor, proximityTargets, scene, camera, pipeline);
  checkPathB = makePathChecker("b", ["puzzle_b1_complete", "puzzle_b2_complete", "puzzle_b3_complete", "puzzle_b4_complete"], compound.shrineAnchor, proximityTargets, scene, camera, pipeline);
  checkPathC = makePathChecker("c", ["puzzle_c1_complete", "puzzle_c2_complete", "puzzle_c3_complete", "puzzle_c4_complete"], compound.shrineAnchor, proximityTargets, scene, camera, pipeline);

  scene.onBeforeRenderObservable.add(() => {
    if (timeManager.isTransitioning || timeManager.currentEra !== "present") {
      hud.setProximity(false);
      interactableHighlight.setHovered(null);
      return;
    }
    let bestPrompt: string | null = null;
    let bestMesh: AbstractMesh | null = null;
    let bestDist = PROXIMITY_RADIUS_M;
    for (const t of proximityTargets) {
      if (t.isActivated()) continue;
      if (t.requiredFlags && !t.requiredFlags.every((f) => globalState.getFlag(f))) continue;
      const d = Vector3.Distance(camera.position, t.anchor.absolutePosition);
      if (d <= bestDist) {
        bestDist = d;
        bestPrompt = t.prompt;
        bestMesh = t.anchor;
      }
    }
    hud.setProximity(bestPrompt !== null, bestPrompt ?? undefined);
    interactableHighlight.setHovered(bestMesh);
    interactableRegistry.setNearestHint(bestMesh);
  });

  // Ledger indicator — updates the HUD badge whenever an entry is added.
  ledgerStore.onChanged(() => hud.setLedgerCount(ledgerStore.count()));
  // Initialise the indicator — reflects rehydrated count on ?resume=1.
  hud.setLedgerCount(ledgerStore.count());

  // Keyboard shortcuts: J = ledger toggle, F5 = manual save, F9 = manual load.
  window.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "j" || e.key === "J") {
      // Block ledger while in the Past or mid-transition — content belongs to Present.
      if (timeManager.isTransitioning || timeManager.currentEra !== "present") return;
      ledgerUI.toggle(ledgerStore.entries());
    } else if (e.key === "F5") {
      e.preventDefault();
      save(AUTOSAVE_SLOT, MISSION_ID);
      hud.showLedgerToast("Session saved.", 2000);
    } else if (e.key === "F9") {
      e.preventDefault();
      const blob = load(AUTOSAVE_SLOT);
      if (blob) {
        applyState(blob);
        hud.showLedgerToast("Session restored. Reload the page to apply.", 4000);
        log.info("manual restore from autosave");
      } else {
        hud.showLedgerToast("No saved session found.", 2500);
      }
    }
  });

  if (params.get("inspect") === "1") {
    const { Inspector } = await import("@babylonjs/inspector");
    Inspector.Show(scene, { embedMode: true });
  }

  window.addEventListener("resize", () => engine.resize());
  engine.runRenderLoop(() => scene.render());

  log.info(`scaffold ready — profile=${profile}, era=${timeManager.currentEra}`);

  // Hold the canvas opaque until the intro finishes so beats line up.
  await introPromise;
  log.info("intro handed off");
}

boot().catch((err: unknown) => {
  console.error("[boot] fatal", err);
  const msg = err instanceof Error ? err.message : String(err);
  const overlay = document.createElement("pre");
  overlay.textContent = `Boot failed: ${msg}`;
  overlay.setAttribute(
    "style",
    "position:fixed;inset:1rem;color:#f88;background:#000d;padding:1rem;font-family:ui-monospace,monospace;white-space:pre-wrap;z-index:9999;",
  );
  document.body.appendChild(overlay);
});
