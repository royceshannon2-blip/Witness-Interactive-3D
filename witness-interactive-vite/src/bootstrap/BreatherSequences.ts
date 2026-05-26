/**
 * BreatherSequences
 *
 * Three mandatory "quiet interlude" moments inserted at specific narrative
 * checkpoints. These are the RDR2-style pacing beats that let emotional
 * weight settle before the next act.
 *
 * Beat definitions reference narrator audio keys (played via AudioManager)
 * and camera targets — both defined here; the actual WAV files are
 * generated in M19 (Higgs-Audio v2 batch).
 *
 * Sequences are designed to be skippable via Escape and to degrade
 * gracefully under `prefers-reduced-motion` (camera beats are skipped;
 * audio and wait beats always run).
 */

import { Vector3 } from "@babylonjs/core";
import type { Scene, UniversalCamera } from "@babylonjs/core";
import { CinematicDirector } from "../core/CinematicDirector";
import type { Beat } from "../core/CinematicDirector";

// ---------------------------------------------------------------------------
// Sequence 1 — Return to Shrine
//
// Triggered immediately after `all_evidence_found`.
// Player is unlocked but has no pending task — this 45-second moment is a
// forced pause before the path choice overlay appears. No camera control
// taken away; the player can walk, look, but no interactable appears until
// the sequence ends (the shrine is registered after this resolves).
//
// Narrator key: `breather_return_to_shrine`
// Text: "He could have left. Many did. He stayed."

const RETURN_TO_SHRINE_BEATS: Beat[] = [
  // Brief ambient swell + narrator line, then wait for it to settle.
  { type: "audio-play", key: "breather_return_to_shrine" },
  {
    type: "overlay-text",
    text: "He could have left. Many did. He stayed.",
    fadeInSec: 1.2,
  },
  { type: "wait", seconds: 5.0 },
  { type: "overlay-hide", fadeOutSec: 1.5 },
  { type: "wait", seconds: 4.0 },
];

// ---------------------------------------------------------------------------
// Sequence 2 — Mid-Path Vista
//
// Triggered once per path, at the midpoint of Act 3 (after the second
// puzzle in each path). The player is at or near a high-ground anchor
// with a view of the hills. Camera locks for 20s; a single narrator
// reflection plays.
//
// Three variants — one per path. The correct one is selected by the caller
// based on which path flag is set.

const MID_PATH_HIDER_BEATS: Beat[] = [
  { type: "control-lock" },
  {
    type: "parallel",
    beats: [
      { type: "audio-play", key: "breather_vista_hider" },
      {
        type: "overlay-text",
        text: "The hills held them. Eleven people in a space meant for root vegetables.",
        fadeInSec: 1.5,
      },
    ],
  },
  { type: "wait", seconds: 10.0 },
  { type: "overlay-hide", fadeOutSec: 1.5 },
  { type: "wait", seconds: 4.0 },
  { type: "control-unlock" },
];

const MID_PATH_ESCAPIST_BEATS: Beat[] = [
  { type: "control-lock" },
  {
    type: "parallel",
    beats: [
      { type: "audio-play", key: "breather_vista_escapist" },
      {
        type: "overlay-text",
        text: "He chose who could make it across the water. The others he did not choose.",
        fadeInSec: 1.5,
      },
    ],
  },
  { type: "wait", seconds: 10.0 },
  { type: "overlay-hide", fadeOutSec: 1.5 },
  { type: "wait", seconds: 4.0 },
  { type: "control-unlock" },
];

const MID_PATH_OBSERVER_BEATS: Beat[] = [
  { type: "control-lock" },
  {
    type: "parallel",
    beats: [
      { type: "audio-play", key: "breather_vista_observer" },
      {
        type: "overlay-text",
        text: "From here, you could see everything. That is all he ever claimed — that he saw.",
        fadeInSec: 1.5,
      },
    ],
  },
  { type: "wait", seconds: 10.0 },
  { type: "overlay-hide", fadeOutSec: 1.5 },
  { type: "wait", seconds: 4.0 },
  { type: "control-unlock" },
];

// ---------------------------------------------------------------------------
// Sequence 3 — Pre-Remembrance
//
// Triggered when Act 3 is complete, before the shrine becomes interactable.
// 30-second CinematicDirector sequence: golden-hour lighting shift (handled
// by lighting rig, not by this sequence), music fade to near-silence, and a
// camera slow-orbit. The shrine interactable is registered after this resolves.
//
// Narrator key: `breather_pre_remembrance`
// Text: no overlay — sound and camera only.

function buildPreRemembranceBeats(
  shrinePosition: Vector3,
): Beat[] {
  return [
    { type: "control-lock" },
    // Pull camera gently toward shrine (0.3 m), narrow FOV slightly.
    {
      type: "parallel",
      beats: [
        {
          type: "camera-approach",
          anchor: shrinePosition,
          pullMag: 0.3,
          durationSec: 3.0,
        },
        {
          type: "fov",
          targetFov: 0.98,
          durationSec: 3.0,
        },
        { type: "audio-play", key: "breather_pre_remembrance" },
      ],
    },
    { type: "wait", seconds: 14.0 },
    // Ease FOV back out before control returns.
    { type: "fov", targetFov: 1.05, durationSec: 2.0 },
    { type: "control-unlock" },
    { type: "wait", seconds: 1.0 },
  ];
}

// ---------------------------------------------------------------------------
// Public helpers

export type PathKey = "hider" | "escapist" | "observer";

/**
 * Runs the Return-to-Shrine interlude immediately after `all_evidence_found`.
 * Resolves when complete (or when skipped). The choice overlay should be
 * shown after this resolves.
 */
export async function runReturnToShrineBreather(
  scene: Scene,
  camera: UniversalCamera,
): Promise<void> {
  const director = new CinematicDirector(scene, camera);
  await director.play(RETURN_TO_SHRINE_BEATS);
  director.dispose();
}

/**
 * Runs the mid-path vista interlude at the Act 3 path midpoint.
 * Called after the second puzzle in each path completes.
 */
export async function runMidPathVistaBreather(
  scene: Scene,
  camera: UniversalCamera,
  path: PathKey,
): Promise<void> {
  const beats: Beat[] =
    path === "hider"
      ? MID_PATH_HIDER_BEATS
      : path === "escapist"
        ? MID_PATH_ESCAPIST_BEATS
        : MID_PATH_OBSERVER_BEATS;

  const director = new CinematicDirector(scene, camera);
  await director.play(beats);
  director.dispose();
}

/**
 * Runs the pre-Remembrance interlude before the shrine becomes interactable.
 * `shrinePosition` is used for the gentle camera-approach beat.
 */
export async function runPreRemembranceBreather(
  scene: Scene,
  camera: UniversalCamera,
  shrinePosition: Vector3,
): Promise<void> {
  const director = new CinematicDirector(scene, camera);
  await director.play(buildPreRemembranceBeats(shrinePosition));
  director.dispose();
}
