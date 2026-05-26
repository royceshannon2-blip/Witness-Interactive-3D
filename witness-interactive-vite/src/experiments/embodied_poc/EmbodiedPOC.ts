/**
 * Embodied First-Person POC — Phase 0 Spike A
 *
 * Proves the frame-weighted locomotion blend tree from EMBODIED_FIRST_PERSON.md §6.1
 * end-to-end against a real rigged glTF:
 *
 *   1. Load model + skeleton + per-bone Animation tracks.
 *   2. Load an `<id>.anim.json` sidecar that maps clip names → frame ranges.
 *   3. Start every locomotion clip via scene.beginWeightedAnimation at weight 0.
 *      All clips share the scene clock + speedRatio → phase-locked.
 *   4. Per-frame: map a directional input vector to per-clip weights.
 *   5. Diagnostic overlay shows live weights so footstep alignment can be eyeballed.
 *
 * Controls (no pointerlock, no body controller — this is the animation system only):
 *   W/A/S/D ........ directional input vector
 *   Shift .......... hold to run (raises moveSpeed)
 *   1 .............. cycle additive-breathing mode (off / procedural / clip-bone)
 *   ` (backtick) ... toggle inspector
 *
 * Asset requirements (none of these exist yet — see runWithPlaceholder):
 *   public/assets/poc_rigged.glb         — rigged character with concatenated NLA track
 *   public/assets/poc_rigged.anim.json   — sidecar clip manifest
 *
 * Run via a temporary route or by calling `mountEmbodiedPOC(canvas)` from main.
 */

import {
  ArcRotateCamera,
  Color3,
  Color4,
  DirectionalLight,
  Engine,
  HemisphericLight,
  LoadAssetContainerAsync,
  Scene,
  Vector3,
  type AnimationGroup,
} from "@babylonjs/core";
import "@babylonjs/loaders/glTF";
import "@babylonjs/inspector";

// ---------------------------------------------------------------------------
// Clip manifest types — match the sidecar produced by tools/blender_animate.py

interface ClipSpec {
  start: number;
  end: number;
  loop: boolean;
  type: "locomotion" | "action";
}
interface ClipManifest {
  skeleton: string;
  fps: number;
  clips: Record<string, ClipSpec>;
}

// ---------------------------------------------------------------------------
// Input — a simple WASD vector + Shift for run. No camera coupling.

interface InputState {
  /** Normalized direction in local body space; z=forward, x=right. */
  moveDirection: Vector3;
  /** 0 = idle, 0.5 = walk, 1.0 = run. */
  moveSpeed: number;
  isMoving: boolean;
}

class POCInput {
  private keys = new Set<string>();
  constructor() {
    window.addEventListener("keydown", (e) => this.keys.add(e.code));
    window.addEventListener("keyup", (e) => this.keys.delete(e.code));
  }
  read(): InputState {
    const f = this.keys.has("KeyW") ? 1 : 0;
    const b = this.keys.has("KeyS") ? 1 : 0;
    const l = this.keys.has("KeyA") ? 1 : 0;
    const r = this.keys.has("KeyD") ? 1 : 0;
    const dir = new Vector3(r - l, 0, f - b);
    const len = dir.length();
    if (len > 0) dir.normalize();
    const moving = len > 0;
    const run = this.keys.has("ShiftLeft") || this.keys.has("ShiftRight");
    const speed = moving ? (run ? 1.0 : 0.5) : 0.0;
    return { moveDirection: dir, moveSpeed: speed, isMoving: moving };
  }
}

// ---------------------------------------------------------------------------
// Locomotion blend tree — the core of the POC

const LOCOMOTION_CLIPS = [
  "idle",
  "walking",
  "walking_back",
  "strafe_left",
  "strafe_right",
  "running",
] as const;
type LocomotionClipName = (typeof LOCOMOTION_CLIPS)[number];

/**
 * Drives a set of glTF AnimationGroups (one per locomotion clip) by name,
 * using per-group weights. This is the correct mechanism when the GLB was
 * exported with NLA strips → separate animation tracks. We do NOT use
 * scene.beginWeightedAnimation on the skeleton because the bone-level
 * animations are sliced per-group and not a single continuous timeline.
 */
class LocomotionBlender {
  private active = new Map<LocomotionClipName, AnimationGroup>();

  constructor(animationGroups: AnimationGroup[]) {
    // Stop any auto-started groups so we control playback explicitly.
    for (const g of animationGroups) g.stop();

    // Match groups by name first (when the exporter preserves NLA strip names),
    // then fall back to positional binding (Blender's per-armature glTF export
    // produces names like "Armature.001|mixamo.com|Layer0" in import order).
    const findGroup = (clip: LocomotionClipName, idx: number): AnimationGroup | undefined => {
      const exact = animationGroups.find((g) => g.name === clip);
      if (exact) return exact;
      const ci = animationGroups.find((g) => g.name.toLowerCase().includes(clip));
      if (ci) return ci;
      return animationGroups[idx];
    };

    for (let i = 0; i < LOCOMOTION_CLIPS.length; i++) {
      const clip = LOCOMOTION_CLIPS[i];
      const g = findGroup(clip, i);
      if (!g) {
        console.warn(
          `[POC] AnimationGroup for "${clip}" not found. Available: ` +
            animationGroups.map((x) => x.name).join(", ")
        );
        continue;
      }
      g.name = clip; // normalize for inspector + diagnostics
      this.enableBlendingOnGroup(g);
      const initialWeight = clip === "idle" ? 1.0 : 0.0;
      g.play(true);
      g.setWeightForAllAnimatables(initialWeight);
      this.active.set(clip, g);
    }
  }

  private enableBlendingOnGroup(g: AnimationGroup): void {
    for (const ta of g.targetedAnimations) {
      ta.animation.enableBlending = true;
      ta.animation.blendingSpeed = 0.08;
    }
  }

  setWeight(name: LocomotionClipName, weight: number): void {
    const g = this.active.get(name);
    if (!g) return;
    g.setWeightForAllAnimatables(Math.max(0, Math.min(1, weight)));
  }

  /** Read input, write weights. Called once per frame. */
  apply(input: InputState): Record<LocomotionClipName, number> {
    const fwd = Math.max(0, input.moveDirection.z);
    const back = Math.max(0, -input.moveDirection.z);
    const lft = Math.max(0, -input.moveDirection.x);
    const rgt = Math.max(0, input.moveDirection.x);
    const total = fwd + back + lft + rgt;

    const moving = input.isMoving && total > 0.01;
    // Walk→run interp: speed 0.5 = pure walk, speed 1.0 = pure run
    const runK = Math.max(0, Math.min(1, (input.moveSpeed - 0.5) / 0.5));

    const idleW = moving ? 0 : 1;
    const walkScale = moving ? 1 - runK : 0;
    const runScale = moving ? runK : 0;

    const norm = (v: number) => (total > 0 ? v / total : 0);
    const weights: Record<LocomotionClipName, number> = {
      idle: idleW,
      walking: walkScale * norm(fwd),
      walking_back: walkScale * norm(back),
      strafe_left: walkScale * norm(lft),
      strafe_right: walkScale * norm(rgt),
      running: runScale * norm(fwd),
    };

    for (const name of LOCOMOTION_CLIPS) this.setWeight(name, weights[name]);
    return weights;
  }
}

// ---------------------------------------------------------------------------
// Diagnostic overlay — live weights + footstep phase indicator

function createDiagnosticOverlay(): {
  el: HTMLDivElement;
  update: (weights: Record<LocomotionClipName, number>, phase: number) => void;
} {
  const el = document.createElement("div");
  el.style.cssText = `
    position: fixed; top: 10px; left: 10px; padding: 12px;
    background: rgba(0,0,0,0.75); color: #0f0; font-family: monospace;
    font-size: 12px; line-height: 1.4; z-index: 9999; min-width: 240px;
    border: 1px solid #0f0; pointer-events: none;`;
  document.body.appendChild(el);

  const bar = (w: number) => {
    const n = Math.round(w * 20);
    return "█".repeat(n) + "·".repeat(20 - n);
  };

  return {
    el,
    update(weights, phase) {
      const phaseBar =
        " ".repeat(Math.round(phase * 20)) + "♦" + " ".repeat(20 - Math.round(phase * 20));
      el.innerHTML =
        `<b>Embodied POC — Frame-Weighted Blend</b><br>` +
        `<br>Controls: WASD move · Shift run · 1 cycle additive · \` inspector<br><br>` +
        LOCOMOTION_CLIPS.map(
          (n) => `${n.padEnd(15)} ${bar(weights[n])} ${weights[n].toFixed(2)}`
        ).join("<br>") +
        `<br><br>Phase (shared clock) [${phaseBar}]<br>` +
        `<i>If footsteps slip across directions, clips are NOT phase-aligned</i>`;
    },
  };
}

// ---------------------------------------------------------------------------
// Main mount

export async function mountEmbodiedPOC(
  canvas: HTMLCanvasElement,
  modelUrl = "/assets/poc_rigged.glb",
  manifestUrl = "/assets/poc_rigged.anim.json"
): Promise<{ dispose: () => void }> {
  const engine = new Engine(canvas, true, { preserveDrawingBuffer: true });
  const scene = new Scene(engine);
  scene.clearColor = new Color4(0.05, 0.05, 0.08, 1);

  // Camera — orbital, third-person, just to see the body. Not the embodied camera.
  const camera = new ArcRotateCamera(
    "poc_cam",
    -Math.PI / 2,
    Math.PI / 2.5,
    3.5,
    new Vector3(0, 1.1, 0),
    scene
  );
  camera.attachControl(canvas, true);
  camera.minZ = 0.01;

  // Basic lighting — POC isn't about PBR, just visible silhouettes
  new HemisphericLight("hemi", new Vector3(0, 1, 0), scene).intensity = 0.6;
  const dir = new DirectionalLight("sun", new Vector3(-0.5, -1, -0.3), scene);
  dir.intensity = 0.8;
  dir.diffuse = new Color3(1, 0.95, 0.85);

  // ---------------------------------------------------------------------------
  // Load model + manifest in parallel
  let manifest: ClipManifest | null = null;
  let blender: LocomotionBlender | null = null;

  try {
    const [container, manifestResp] = await Promise.all([
      LoadAssetContainerAsync(modelUrl, scene),
      fetch(manifestUrl),
    ]);
    if (!manifestResp.ok) throw new Error(`manifest fetch ${manifestResp.status}`);
    manifest = (await manifestResp.json()) as ClipManifest;
    container.addAllToScene();
    if (!container.skeletons.length) throw new Error("model has no skeleton");
    if (!container.animationGroups.length)
      throw new Error("model has no AnimationGroups — re-export with NLA strips");
    blender = new LocomotionBlender(container.animationGroups);
    console.info(
      `[POC] loaded skeleton "${container.skeletons[0].name}" ` +
        `(${container.skeletons[0].bones.length} bones), ` +
        `${container.animationGroups.length} animation groups: ` +
        container.animationGroups.map((g) => g.name).join(", ")
    );
  } catch (err) {
    console.error("[POC] asset load failed — POC needs a rigged model + manifest:", err);
    showLoadError(err);
  }

  // ---------------------------------------------------------------------------
  const input = new POCInput();
  const overlay = createDiagnosticOverlay();

  // Inspector toggle
  window.addEventListener("keydown", (e) => {
    if (e.code === "Backquote") {
      if (scene.debugLayer.isVisible()) scene.debugLayer.hide();
      else void scene.debugLayer.show({ overlay: true });
    }
  });

  // Per-frame loop
  scene.onBeforeRenderObservable.add(() => {
    if (!blender || !manifest) return;
    const state = input.read();
    const weights = blender.apply(state);

    // Compute shared phase 0..1 for footstep diagnostic — pick any locomotion clip
    // and read its current frame relative to its range
    const idleSpec = manifest.clips.idle;
    const idleFrames = idleSpec ? idleSpec.end - idleSpec.start : 1;
    const phase = ((scene.getEngine().getFps() > 0
      ? performance.now() / 1000
      : 0) *
      manifest.fps) %
      idleFrames /
      idleFrames;
    overlay.update(weights, phase);
  });

  engine.runRenderLoop(() => scene.render());
  const resize = () => engine.resize();
  window.addEventListener("resize", resize);

  return {
    dispose() {
      window.removeEventListener("resize", resize);
      overlay.el.remove();
      engine.dispose();
    },
  };
}

function showLoadError(err: unknown): void {
  const el = document.createElement("div");
  el.style.cssText = `
    position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
    padding: 20px 30px; background: #200; color: #fcc; font-family: monospace;
    border: 2px solid #f00; z-index: 10000; max-width: 600px;`;
  el.innerHTML =
    `<b>POC asset missing</b><br><br>` +
    `This POC requires a rigged glTF + clip manifest:<br>` +
    `<code>public/assets/poc_rigged.glb</code><br>` +
    `<code>public/assets/poc_rigged.anim.json</code><br><br>` +
    `Use any CC0 rigged character (Mixamo, Sketchfab) and produce the manifest manually for the spike.<br><br>` +
    `<i>${String(err)}</i>`;
  document.body.appendChild(el);
}
