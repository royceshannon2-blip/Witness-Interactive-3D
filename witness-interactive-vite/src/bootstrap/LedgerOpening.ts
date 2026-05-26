/**
 * LedgerOpening
 *
 * Phase 1's closing beat. The player walks to the altar, presses E on the
 * ledger book; this routine takes over the camera, lifts the book, holds a
 * single text fragment, and settles the player back to the spawn pose.
 *
 * Choreography per OPENING_SEQUENCE.md §6 "first interactive object" and
 * MISSION_BLUEPRINT.md §3 Phase 1:
 *
 *   t = 0.0 s   Player input frozen. HUD prompt fades out.
 *   t = 0.0 s   Camera dollies from spawn → reading pose (close, tilted down).
 *               Ledger lifts ~25 cm and rotates to face the camera.
 *   t = 1.2 s   DOM modal fades in: title + the cryptic line + attribution.
 *   t = 1.6 s   "Press Space to continue" prompt fades in below.
 *   t = ?      Player presses Space → exit phase begins.
 *   t = +0.0 s Modal fades out. Ledger returns to altar pose.
 *               Camera dollies back to spawn pose.
 *   t = +1.4 s Player input restored. `act_1_complete` flag set; HUD toast.
 *
 * Boundary discipline: this module owns the *bootstrap-level* sequence wiring
 * (DOM overlay + camera animation + flag mutation). It imports primitives
 * from `core/AnimationDirector` and reads state via `globalState` but does
 * NOT mutate the narrative graph directly — that responsibility stays with
 * `narrativeController` consumers (the calling fragment in main.ts triggers
 * the puzzle completion on its own).
 */

import { Quaternion, Vector3 } from "@babylonjs/core";
import type { AbstractMesh, Scene, UniversalCamera } from "@babylonjs/core";
import { cameraDolly, meshMove, meshRotate, fovTween, waitFrames } from "../core";

const APPROACH_SEC = 1.2;
const HOLD_MIN_SEC = 2.5; // Minimum hold; player can press space sooner once visible.
const SETTLE_SEC = 1.4;

export interface LedgerOpeningOpts {
  /** The active Babylon scene. */
  scene: Scene;
  /** The gameplay camera. */
  camera: UniversalCamera;
  /** Ledger book mesh on the altar slab. */
  ledger: AbstractMesh;
  /** Returns true if input should be disabled now (called once at entry). */
  freezeInput: () => void;
  /** Restores normal input + HUD state. */
  restoreInput: () => void;
}

/**
 * Run the ledger opening sequence. Resolves after the player has dismissed
 * the reading modal and the camera has settled. Idempotent only in the sense
 * that callers should not re-invoke it once the underlying narrative flag is
 * set; this routine itself does not gate.
 */
export async function runLedgerOpening(opts: LedgerOpeningOpts): Promise<void> {
  const { scene, camera, ledger, freezeInput, restoreInput } = opts;

  // Snapshot the camera + ledger state so we can return to them exactly.
  const savedCamPos = camera.position.clone();
  const savedCamRot = camera.rotation.clone();
  const savedCamFov = camera.fov;
  const savedLedgerPos = ledger.position.clone();
  const savedLedgerRot = ledger.rotationQuaternion?.clone() ?? null;

  freezeInput();

  // ---------------------------------------------------------------------------
  // Phase 1 — approach: camera + ledger move in parallel, eased.
  // ---------------------------------------------------------------------------

  // Reading pose: 1.4 m above the altar, ~0.9 m back from it, looking down at
  // the ledger's lifted position. Altar centre is (-1.85, ~0.34, 3.55) per
  // FamilyCompound.ts; we frame the lifted book.
  const readingEye = new Vector3(-1.6, 1.45, 3.0);
  const liftedPos = savedLedgerPos.add(new Vector3(0.06, 0.32, 0.0));
  const readingTarget = liftedPos.clone();

  // Ledger lifts + rotates to face the camera (yaw so its long axis aims at
  // the reading eye).
  const faceCamRot = Quaternion.RotationAxis(new Vector3(0, 1, 0), 1.05);

  await Promise.all([
    cameraDolly(scene, camera, { position: readingEye, target: readingTarget }, {
      durationSec: APPROACH_SEC,
    }),
    fovTween(scene, camera, 0.78, APPROACH_SEC),
    meshMove(scene, ledger, liftedPos, APPROACH_SEC),
    meshRotate(scene, ledger, faceCamRot, APPROACH_SEC),
  ]);

  // ---------------------------------------------------------------------------
  // Phase 2 — reading: DOM modal up, hold for player input.
  // ---------------------------------------------------------------------------

  const overlay = mountReadingOverlay();
  const dismissed = waitForDismissal(overlay);
  await waitFrames(scene, HOLD_MIN_SEC);
  // Show the continue prompt only after the minimum hold so the player has
  // time to read the line first.
  overlay.dataset.continueVisible = "1";
  const promptEl = overlay.querySelector<HTMLElement>(".continue-prompt");
  if (promptEl) promptEl.style.opacity = "0.7";
  await dismissed;

  // ---------------------------------------------------------------------------
  // Phase 3 — settle: modal out, camera back, ledger back, input restored.
  // ---------------------------------------------------------------------------

  unmountReadingOverlay(overlay);

  await Promise.all([
    cameraDolly(scene, camera, { position: savedCamPos, target: undefined }, {
      durationSec: SETTLE_SEC,
    }),
    fovTween(scene, camera, savedCamFov, SETTLE_SEC),
    meshMove(scene, ledger, savedLedgerPos, SETTLE_SEC),
    savedLedgerRot ? meshRotate(scene, ledger, savedLedgerRot, SETTLE_SEC) : Promise.resolve(),
  ]);

  // Snap rotation in case the cameraDolly target wasn't supplied (we held the
  // saved rotation via the dolly's position-only mode). Restore it exactly so
  // first-person aim doesn't drift.
  camera.rotation.copyFrom(savedCamRot);
  camera.fov = savedCamFov;

  restoreInput();
}

// ---------------------------------------------------------------------------
// DOM overlay — same documentary register as IntroSequence + RemembranceSequence.
// ---------------------------------------------------------------------------

const OVERLAY_ID = "witness-ledger-opening";

function mountReadingOverlay(): HTMLElement {
  const overlay = document.createElement("div");
  overlay.id = OVERLAY_ID;
  overlay.setAttribute(
    "style",
    [
      "position:fixed;inset:0;z-index:8500;",
      "background:linear-gradient(180deg, rgba(6,5,4,0.0) 0%, rgba(6,5,4,0.62) 55%, rgba(6,5,4,0.86) 100%);",
      "display:flex;flex-direction:column;align-items:center;justify-content:flex-end;",
      "padding:0 24px 18vh;",
      "font-family:ui-serif,Georgia,'Times New Roman',serif;",
      "color:#e9e3d6;",
      "opacity:0;transition:opacity 0.9s ease-in-out;",
      "pointer-events:auto;",
    ].join(""),
  );

  const title = document.createElement("p");
  title.textContent = "From the ledger";
  title.setAttribute(
    "style",
    [
      "font-size:13px;letter-spacing:0.24em;text-transform:uppercase;",
      "color:#b8a98c;margin:0 0 18px;opacity:0.85;",
    ].join(""),
  );
  overlay.appendChild(title);

  const body = document.createElement("p");
  body.textContent = "The ledger will tell you why he never came home.";
  body.setAttribute(
    "style",
    [
      "font-size:clamp(20px, 2.4vw, 26px);",
      "font-style:italic;line-height:1.55;",
      "max-width:38ch;text-align:center;margin:0 0 14px;",
    ].join(""),
  );
  overlay.appendChild(body);

  const attribution = document.createElement("p");
  attribution.textContent = "— Grandma, before she died.";
  attribution.setAttribute(
    "style",
    [
      "font-size:14px;color:#a39681;letter-spacing:0.06em;",
      "margin:0 0 56px;opacity:0.78;",
    ].join(""),
  );
  overlay.appendChild(attribution);

  const cont = document.createElement("p");
  cont.className = "continue-prompt";
  cont.textContent = "Press space to continue";
  cont.setAttribute(
    "style",
    [
      "font-size:13px;letter-spacing:0.12em;text-transform:uppercase;",
      "color:#b8a98c;margin:0;opacity:0;transition:opacity 0.8s ease-in-out;",
    ].join(""),
  );
  overlay.appendChild(cont);

  document.body.appendChild(overlay);
  // Trigger transition.
  requestAnimationFrame(() => {
    overlay.style.opacity = "1";
  });
  return overlay;
}

function unmountReadingOverlay(overlay: HTMLElement): void {
  overlay.style.opacity = "0";
  setTimeout(() => overlay.remove(), 950);
}

/**
 * Resolve when the player presses Space, Enter, or clicks. The handler is
 * scoped to a single dismissal — listeners are torn down on first event.
 */
function waitForDismissal(overlay: HTMLElement): Promise<void> {
  return new Promise((resolve) => {
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === " " || e.key === "Enter" || e.key === "Escape") {
        cleanup();
        resolve();
      }
    };
    const onClick = (): void => {
      cleanup();
      resolve();
    };
    function cleanup(): void {
      window.removeEventListener("keydown", onKey);
      overlay.removeEventListener("click", onClick);
    }
    window.addEventListener("keydown", onKey);
    overlay.addEventListener("click", onClick);
  });
}
