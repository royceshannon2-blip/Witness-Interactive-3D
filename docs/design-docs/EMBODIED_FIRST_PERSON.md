# Embodied First-Person Animation System — PRD

**Status:** Planning (audited)
**Version:** 1.1
**Last Updated:** 2026-05-22  
**Owner:** @royceshannon2  
**Tech Stack:** Babylon.js 9 / UniversalCamera / Skeleton animations / AnimationBlending

---

## 1. Vision

Witness Interactive will shift from a disembodied floating viewpoint to a **first-person embodied experience** inspired by modded Skyrim. The player will see their own torso, arms, and legs in their peripheral and lower vision, with full-body movement animations that make actions feel continuous rather than interrupted by camera cuts.

### Core Principle
**The camera belongs to a body, not a floating eye.** Every animation transition, every step, every reach conveys physical presence. The embodied player is the narrative anchor—they don't teleport or pop between states; they move, breathe, and act.

### Success Criteria
- ✓ Visible torso, arms, and legs from first-person view without screen domination
- ✓ Seamless walk/idle/crouch transitions with full-body animation blending
- ✓ Subtle head bob and breathing motion during idle states
- ✓ Camera follows body motion with gentle lag instead of rigid lock
- ✓ Full interaction animations (picking up ledger, opening doors, sitting) stay in first-person
- ✓ All three era perspectives (Investigator, Protector, Hidden) have distinct body proportions and movement feel
- ✓ 60 FPS minimum on mid-range hardware; HIGH/MEDIUM/LOW quality profiles available

---

## 2. Visual Design Language — "First-Person Embodiment"

### Inspiration: Modded Skyrim
The modded Skyrim first-person look achieves embodied presence through:

1. **Body visibility**: Camera positioned so arms, chest, and upper legs appear naturally in frame. No grotesque warping; the body is part of the scene, not a heads-up display.
2. **Continuous transitions**: What would be a third-person animation (sitting, interacting, crafting) plays in first-person with a camera positioned inside the character's torso/head space.
3. **Subtle motion**: Idle breathing, shoulder sway, and head micro-adjustments make the view feel alive without inducing motion sickness.
4. **Weight and physics**: Camera lag and micro-movements reflect body mass and gravity.

### Witness-Specific Aesthetic

Combine embodied first-person with the **Digital Diorama** visual language (tactile, hyper-realistic PBR, filmic desaturation, macro cinematography):

- **Camera height**: Eye-level, positioned naturally for the character's era and perspective:
  - **Investigator (2026)**: 1.65m eye height, adult investigator
  - **Protector (1994)**: 1.70m eye height, adult protector
  - **Hidden (1994)**: 1.15m eye height, child (forced perspective reveals smaller world)
- **Body appearance**: Visible arms (with gloved/bare hands as era-appropriate) and upper torso, legs visible when looking down or sitting
- **Lighting context**: PBR arms and hands receive same lighting as the environment (no fake "screen-space" hands)
- **Color palette**: Desaturated, period-appropriate clothing (witness orange, Protector camouflage, child's weathered attire)

---

## 3. Technical Architecture

### 3.1 Character Rig Requirements

Each character (Investigator, Protector, Hidden) requires:

```
Body Rig (Blender source)
├── Armature
│   ├── Pelvis (root)
│   ├── Spine (lower, mid, upper)
│   ├── Chest / Ribcage
│   ├── Head
│   ├── Neck
│   ├── Shoulder.L / Shoulder.R
│   ├── Arm.L (upper, forearm, hand)
│   ├── Arm.R (upper, forearm, hand)
│   ├── Hip.L / Hip.R
│   ├── Leg.L (upper, lower, foot, toes)
│   └── Leg.R (upper, lower, foot, toes)
├── Mesh
│   ├── Torso (visible in FP view)
│   ├── Arms.L / Arms.R (forearm + hand visible)
│   ├── Hands.L / Hands.R (with glove/bare variants)
│   └── Legs (optional — only visible when sitting or looking down)
└── LOD0 / LOD1 (always in first-person, so high detail)
```

**Key constraint:** No head mesh in the rig (camera will be placed inside the head). The neck and shoulder silhouettes must read well without a visible skull.

**Material variance:**
- Arms/hands: Responsive to lighting. Gloved (Protector) or bare (Investigator child contact). Scars/detail per era.
- Clothing: Period-accurate fabric (witness orange vest, Protector gear, worn child's clothing).
- Skin tone: Consistent with Rwanda's Hutu/Tutsi demographics (Witness cast is Hutu).

### 3.2 Camera Placement & Behavior

**Authoritative motion source — WASD drives the BODY ROOT, not the camera.**
The current `PlayerController` (src/interaction/PlayerController.ts) attaches WASD to `UniversalCamera`. For embodied first-person we invert: WASD/crouch input mutates a `bodyRoot: TransformNode`, the body mesh + skeleton are parented to it, and the camera follows the head bone with lag (see §3.2.2). This avoids double-motion (camera and body both translating) and matches Skyrim-style mods. The current `UniversalCamera` keyboard input must be disabled (`camera.inputs.removeByType("FreeCameraKeyboardMoveInput")`); pointerlock mouse-look remains on the camera.

**Body collision:** the body root carries a Havok capsule (radius ~0.30m, height = profile.standHeight). Crouch swaps to a shorter capsule. This is the only collider the player has — the camera itself never collides. Adds `@babylonjs/havok` to the **required** runtime dependency list (was previously "pending, not blocking" — it now blocks M28).

**Camera position:** Babylon `UniversalCamera` positioned inside the character's head space, not locked to a bone but constrained to follow smoothly.

```typescript
// Conceptual placement
cameraOffset = {
  x: 0.02,      // Slight nose offset
  y: 0.08,      // Eye height relative to head joint (8cm)
  z: 0.01,      // Slight forward offset (eye is not at skull center)
  rotationLag: 0.15,  // Camera rotation follows body rotation with 150ms lag
}

// World position each frame:
camera.position = head_bone.position + offset
// But camera.rotation lags behind the player's input by 150ms (feels heavy)
```

**Subtle motion during idle:**

- **Head bob**: Small sinusoidal oscillation (amplitude 1cm, period 4 seconds)
- **Breathing**: Chest rises/falls (amplitude 0.5cm, period 5 seconds)
- **Postural sway**: Body leans slightly (angle 0.5°, random) to feel organic
- **Blink animation**: Eyes close/open (if visible in peripheral, future phase)

All idle motions are **additive** on top of player input, not competing with it.

### 3.3 Animation System: Blending & Layering

Use Babylon's **weighted animation** system to blend skeletal states:

```
Layer 1: Base Locomotion (weight: 1.0)
├── Idle (loop)
├── Walk Forward (loop)
├── Walk Backward (loop)
├── Walk Strafe Left (loop)
├── Walk Strafe Right (loop)
└── Crouch Idle (loop)

Layer 2: Upper-Body Additive (weight: 0.3–1.0)
├── Breathing (loop, blends with idle/walk)
├── Head Sway (loop, blends with idle/walk)
├── Arm Swing (synced to walk speed, fades in crouch)
└── Lean (additive rotation on spine)

Layer 3: Actions (weight: 0–1.0, exclusive)
├── Interact Ledger (sitting, reading)
├── Interact Door (reaching, pushing)
├── Reach / Pick Up (small props)
├── Sit Down / Stand Up (transition, then loops in seated animation)
└── Climb (future: ladder/rock sequences)

Transition Layer (weight: 0–1.0)
├── Walk → Run (accelerated arm swing, stride length)
├── Stand → Crouch (blend spine compression over 0.4s)
├── Walk → Idle (leg freeze, breath-only motion)
└── Action transitions (blend-out walk, blend-in action)
```

**Blending rules:**
- Locomotion layer is always playing (never fully off, 0.1 minimum weight even in actions)
- Upper-body layer can play additively over locomotion (arm swing during walk, breathing during sit)
- Actions exclusive (only one plays; cross-fade over 0.3s on transition)
- **Enabling blending** via `scene.beginWeightedAnimation(..., weight, loop)` ensures smooth current-state interpolation

### 3.4 Animation Inputs & State Machine

**Input state** (updated by `PlayerController`):

```typescript
interface PlayerMovementState {
  isMoving: boolean;
  moveDirection: Vector3;  // Normalized, from WASD input
  moveSpeed: number;        // 0.0–1.0 (actual speed / max walk speed)
  isCrouching: boolean;
  interactionTarget?: string;  // "ledger" | "door" | null
  targetAnimation?: string;   // When interaction starts
}
```

**Animation state machine** (lives in new `engine/PlayerAnimator.ts`):

```
Idle
├─ [start moving] → Walk
├─ [crouch pressed] → Crouch Idle
└─ [interaction] → Interact*

Walk (blended by direction)
├─ [stop moving] → Idle
├─ [crouch pressed] → Crouch Walk
├─ [interaction] → Interact*
└─ [speed up] → Run (future)

Crouch Idle
├─ [start moving] → Crouch Walk
├─ [crouch pressed] → Idle
└─ [interaction] → Interact*

Crouch Walk
├─ [stop] → Crouch Idle
├─ [crouch pressed] → Walk
└─ [interaction] → Interact*

Interact*
└─ [interaction ends] → Idle / Walk (resume previous)
```

---

## 4. Implementation Phases

### Phase 1: Character Rig & Asset Pipeline (M26–M27)

**Milestone M26:** Asset generation pipeline support for skeletal rigs

- [ ] Extend `witness.py generate` with `--kind animated` for full-body characters
- [ ] Add Blender export for:
  - Skeleton with named bones (standardized rig template)
  - Three LOD meshes (Investigator, Protector, Hidden proportions)
  - PBR materials (arms, hands, torso)
  - UV-packed for KTX2 compression
- [ ] Validate exported GLB:
  - Skeleton bone names match expected rig
  - No head mesh (verify mesh exclusion in pipeline)
  - Animations present (validate AnimationGroup count)

**Milestone M27:** Character asset generation

- [ ] Generate three base characters:
  - `figure_investigator_2026` — adult torso, hands (gloved)
  - `figure_protector_1994` — adult, weathered gear
  - `figure_hidden_1994` — child, smaller proportions
- [ ] Each includes:
  - Idle, Walk (4 directions), Crouch Idle, Crouch Walk animations
  - Breathing animation (additive)
  - Head Sway animation (additive)
  - Sit Down / Sit Idle / Stand Up animations
- [ ] Register in `docs/asset-index.md`
- [ ] Export to `witness-interactive-vite/public/assets/`

### Phase 2: Camera System & Player Body Display (M28–M29)

**Milestone M28:** Player body visibility in first-person

- [ ] Modify `PlayerController` to load + instantiate character rig at runtime
- [ ] Implement `PlayerBodyManager`:
  - Loads character GLB via `AssetLibrary`
  - Positions character mesh at camera position
  - **Layers/visibility:** Body mesh renders in all layers (era-agnostic visibility)
  - **Depth:** Ensures body does not clip through near geometry (adjust near plane or mesh depth offset)
  - **Switching characters:** On era/perspective change, unload old rig + load new one
- [ ] Set camera offset (0.02, 0.08, 0.01) relative to head bone
- [ ] Test visibility: body should appear naturally without dominating screen (60–70% of lower-left quadrant visible)

**Milestone M29:** Camera motion & idle breathing

- [ ] Implement `CameraBreathSystem`:
  - Sinusoidal head bob (1cm amplitude, 4s period)
  - Chest/spine breathing (0.5cm spine lift, 5s period)
  - Postural micro-sway (0.5° random sway, 3–8s cycles)
  - All additive on top of player input (no competing motion)
- [ ] Implement `CameraLagSystem`:
  - Camera rotation follows player input with 150ms lag
  - Position interpolation for smooth body follow-cam
  - Test on 60 FPS (ensure lag feels physical, not sluggish)

### Phase 3: Animation Blending & Locomotion (M30–M31)

**Milestone M30:** State machine & animation blending architecture

- [ ] Create `engine/PlayerAnimator.ts`:
  - State machine (Idle ↔ Walk ↔ Crouch states)
  - Weighted animation manager using `scene.beginWeightedAnimation`
  - Direction-aware locomotion: blend between idle/walk-forward/walk-backward/strafe-left/strafe-right based on input vector
  - Smooth transitions (0.3s cross-fade)
- [ ] Connect `PlayerController` movement state → `PlayerAnimator` input
- [ ] Implement additive layers:
  - Base locomotion (weight 1.0)
  - Breathing + sway (weight 0.3–0.5 in idle, 0.1–0.2 in walk)
  - Arm swing sync (amplitude scales with walk speed)

**Milestone M31:** Test & balance locomotion

- [ ] Playtest walk speeds:
  - Investigator: 0.28 m/s feels deliberate, present
  - Protector: 0.32 m/s feels confident, agile
  - Hidden: 0.18 m/s feels cautious, constrained
- [ ] Tune animation blend timing (0.2–0.4s transitions)
- [ ] Verify no clipping: body mesh vs. environment collision (update near plane if needed)
- [ ] Profile on LOW / MEDIUM / HIGH hardware (ensure M profile hits 60 FPS)

### Phase 4: Interaction Animations (M32–M33)

**Milestone M32:** Sitting & ledger interactions

- [ ] Add animations to character rigs:
  - Sit Down (0.6s transition)
  - Sit Idle (loop, breathing still active)
  - Stand Up (0.6s transition)
  - Lean Forward (reading ledger)
- [ ] Implement `InteractionAnimator`:
  - `onInteractionStart(type: "ledger" | "door" | ...)` → blend out walk, blend in action
  - During interaction: camera adjusts to reading distance (slight zoom, slight head tilt)
  - `onInteractionEnd()` → blend out action, resume walk/idle
- [ ] Connect to `InteractableRegistry` (existing system, trigger on registry event)

**Milestone M33:** Reach & door interactions

- [ ] Add animations:
  - Reach Idle (holding position, hand toward object)
  - Open Door (push/pull motion, body sway)
  - Close Door (reverse motion)
- [ ] Implement camera follow during door interaction (camera lags body, stays inside head space)
- [ ] Test interaction feel: body movement should feel **continuous**, not cut away

### Phase 5: Era-Specific Customization (M34)

**Milestone M34:** Protector & Hidden perspective animation variants

- [ ] Generate era-specific idle + walk animations:
  - **Protector (1994):** Alert, military-trained stance. Faster arm swing, tighter posture.
  - **Hidden (1994):** Cautious, child-like locomotion. Smaller stride, hesitant idle (looking around).
  - **Investigator (2026):** Investigative, observant. Slower, deliberate movements (taking notes mentally).
- [ ] Blend era-specific breathing patterns:
  - Protector: tense, shallow breathing (higher frequency)
  - Hidden: anxious, irregular breathing (random skip patterns)
  - Investigator: calm, measured breathing
- [ ] Update `PlayerAnimator` to load era-specific animation sets on perspective change

### Phase 6: Polish & Optimization (M35–M36)

**Milestone M35:** Hand gestures & detailed interactions

- [ ] Add subtle hand animations during walk (fingers curling, thumb movement)
- [ ] Implement arm-reach variations:
  - Left-hand reach (ledger writing, taking notes)
  - Right-hand reach (opening doors, touching walls)
- [ ] Add micro-expressions if visible (eye movement during breathing, tension during stress moments)

**Milestone M36:** Performance & hardware support

- [ ] Profile on target devices:
  - HIGH: Workstation (full detail, 4x SSAO, complex shadows)
  - MEDIUM: Mid-range laptop (simpler breathing, fewer additive layers)
  - LOW: Chromebook (idle breathing only, simple transitions)
- [ ] Implement LOD system:
  - LOD0: Full detail (used in close-up moments, cinematics)
  - LOD1: Reduced bone count (distant moments, if ever visible)
- [ ] Verify 60 FPS lock on MEDIUM profile (target performance bar)
- [ ] Add toggle: "Hide body" (accessibility option for motion-sensitive players)

---

## 5. Animation Content Checklist

### Character: Investigator (2026)

```
Animations (30 FPS, ~60 frames per clip):
- idle_loop (60 frames)
- walk_forward_loop (40 frames)
- walk_backward_loop (40 frames)
- walk_strafe_left_loop (40 frames)
- walk_strafe_right_loop (40 frames)
- crouch_idle_loop (60 frames)
- crouch_walk_forward_loop (40 frames)
- crouch_walk_backward_loop (40 frames)
- crouch_walk_strafe_left_loop (40 frames)
- crouch_walk_strafe_right_loop (40 frames)
- sit_down_transition (20 frames)
- sit_idle_loop (60 frames)
- sit_lean_forward_loop (40 frames, additive)
- stand_up_transition (20 frames)
- breathing_additive_loop (150 frames, 5s)
- head_sway_additive_loop (120 frames, 4s)
- reach_left (20 frames)
- reach_right (20 frames)
- open_door_push (30 frames)
- close_door_pull (30 frames)

Total: ~1200 frames (40s of unique motion at 30 FPS)
```

**Process:**
1. Hand-author in Blender using motion capture reference (YouTube modded Skyrim playthroughs)
2. Refine with IK constraints (feet planted, hand reach targets)
3. Export as glTF AnimationGroup per animation name
4. Bake into GLB via asset pipeline
5. Validate frame counts + looping in inspector before shipping

### Characters: Protector & Hidden

Same animation set, but with:
- Different bone proportions (scale Blender rig)
- Era-specific stance adjustments
- Slightly different timing (Protector faster, Hidden slower)

---

## 6. Babylon.js API Usage Reference

### 6.1 Skeleton & Frame-Weighted Animation (v1.2 — canonical for locomotion/actions)

**Decision (v1.2):** locomotion (walk, run, strafe, jump) and use-actions are driven by **`scene.beginWeightedAnimation`** on per-bone `Animation` objects with explicit frame ranges, NOT by `AnimationGroup.weight`. This gives:

- **Phase-locked blending** — all locomotion clips share one master clock (a single `speedRatio` and aligned frame offsets), so footsteps don't slip when blending fwd/back/strafe/run.
- **Per-bone control** — additive upper-body layers (breathing, sway, arm-swing) target specific bones without competing with locomotion clips.
- **Smooth weight transitions** — `Animation.enableBlending = true` with a tuned `blendingSpeed` produces the cleanest possible crossfades (sub-frame interpolation).

`AnimationGroup` is still used for **one-shot scripted sequences** (sit-down transition, door-open, narrative interactions where phase-sync doesn't matter and we want simple `.play().then(...)` ergonomics). But the locomotion blend tree is frame-weighted.

#### Asset pipeline implication

The Blender exporter (`tools/blender_animate.py`) must emit:

1. **One consolidated NLA track per skeleton**, with all locomotion + action clips concatenated end-to-end at known frame ranges.
2. **A sidecar `<id>.anim.json`** (or glTF `extras` block on the root node) that maps clip names → `{ start, end, loop, type }`. Loaded at runtime alongside the GLB.

Example sidecar:

```json
{
  "skeleton": "investigator_rig",
  "fps": 30,
  "clips": {
    "idle":          { "start": 0,   "end": 60,  "loop": true,  "type": "locomotion" },
    "walk_forward":  { "start": 60,  "end": 100, "loop": true,  "type": "locomotion" },
    "walk_backward": { "start": 100, "end": 140, "loop": true,  "type": "locomotion" },
    "strafe_left":   { "start": 140, "end": 180, "loop": true,  "type": "locomotion" },
    "strafe_right":  { "start": 180, "end": 220, "loop": true,  "type": "locomotion" },
    "run_forward":   { "start": 220, "end": 260, "loop": true,  "type": "locomotion" },
    "jump_start":    { "start": 260, "end": 280, "loop": false, "type": "action" },
    "jump_loop":     { "start": 280, "end": 300, "loop": true,  "type": "action" },
    "jump_land":     { "start": 300, "end": 320, "loop": false, "type": "action" },
    "use_reach":     { "start": 320, "end": 340, "loop": false, "type": "action" }
  }
}
```

**Phase alignment requirement:** all locomotion clips (`type: "locomotion"`) MUST be authored so that the same gait phase lands at the same frame offset within the clip. E.g., for 40-frame clips at 30fps: left-foot-plant at frame 0, right-foot-plant at frame 20, in every directional variant. This is non-negotiable; it's what makes phase-locked blending work.

#### Runtime pattern

```typescript
import {
  LoadAssetContainerAsync,
  Animatable,
  Animation,
  Bone,
  Scene,
  Skeleton,
} from "@babylonjs/core";
import "@babylonjs/loaders/glTF";

interface ClipSpec { start: number; end: number; loop: boolean; type: "locomotion" | "action"; }
type ClipManifest = Record<string, ClipSpec>;

// 1) Load mesh + skeleton + per-bone Animation tracks
const container = await LoadAssetContainerAsync(
  "/assets/figure_investigator_2026.glb",
  scene
);
container.addAllToScene();
const skeleton: Skeleton = container.skeletons[0];

// 2) Load the sidecar that names the frame ranges
const clips: ClipManifest = await fetch(
  "/assets/figure_investigator_2026.anim.json"
).then((r) => r.json()).then((m) => m.clips);

// 3) Enable blending on every bone's Animation so weight changes are smooth.
//    The skeleton's animations live on its bones; iterate to set blending flags.
for (const bone of skeleton.bones) {
  for (const anim of bone.animations) {
    anim.enableBlending = true;
    anim.blendingSpeed = 0.08; // ~80ms transition feel
  }
}

// 4) Start every locomotion clip as a single weighted Animatable on the skeleton.
//    Babylon walks the skeleton's bones internally — one call per clip, not per bone.
//    All clips share the scene clock and the same speedRatio (1.0) → phase-locked.
const activeBlend = new Map<string, Animatable>();

function startWeighted(clipName: string, initialWeight: number) {
  const spec = clips[clipName];
  const animatable = scene.beginWeightedAnimation(
    skeleton,          // target: the skeleton itself
    spec.start,
    spec.end,
    initialWeight,
    spec.loop
  );
  activeBlend.set(clipName, animatable);
}

// Start the full locomotion blend tree (all at 0 except idle)
startWeighted("idle",          1.0);
startWeighted("walk_forward",  0.0);
startWeighted("walk_backward", 0.0);
startWeighted("strafe_left",   0.0);
startWeighted("strafe_right",  0.0);
startWeighted("run_forward",   0.0);

// 5) Per-frame: map PlayerMovementState → clip weights.
//    Weights are normalized so the sum across locomotion clips is 1.0;
//    Animation.enableBlending smooths the transition automatically.
function setClipWeight(clipName: string, weight: number) {
  const a = activeBlend.get(clipName);
  if (a) a.weight = weight;
}

scene.onBeforeRenderObservable.add(() => {
  const state = playerController.getMovementState();
  // 4-way directional fwd/back/L/R + run blending
  const fwd  = Math.max(0,  state.moveDirection.z);
  const back = Math.max(0, -state.moveDirection.z);
  const lft  = Math.max(0, -state.moveDirection.x);
  const rgt  = Math.max(0,  state.moveDirection.x);
  const total = fwd + back + lft + rgt;
  const moving = total > 0.01;

  // 0-1 walk→run interp based on speed
  const runK = Math.max(0, (state.moveSpeed - 0.5) / 0.5);

  const idleW = moving ? 0 : 1;
  const walkScale = moving ? (1 - runK) : 0;
  const runScale  = moving ? runK : 0;

  setClipWeight("idle",          idleW);
  setClipWeight("walk_forward",  walkScale * (fwd  / Math.max(total, 1)));
  setClipWeight("walk_backward", walkScale * (back / Math.max(total, 1)));
  setClipWeight("strafe_left",   walkScale * (lft  / Math.max(total, 1)));
  setClipWeight("strafe_right",  walkScale * (rgt  / Math.max(total, 1)));
  setClipWeight("run_forward",   runScale  * (fwd  / Math.max(total, 1)));
});
```

**Key methods (v9 verified):**
- `scene.beginWeightedAnimation(target, from, to, weight, loop, speedRatio?, onEnd?, animation?)` — start one Animation track with a frame range and a weight; returns `Animatable`
- `Animatable.weight` — mutate per frame to drive the blend tree
- `Animation.enableBlending = true` + `blendingSpeed` — smooth weight changes
- `Animatable.masterFrame` / `goToFrame()` — phase alignment between clips when needed
- `skeleton.bones[i]` — every bone is a target; iterating gives you per-bone weight control

**Additive layering (upper-body breathing, sway, arm-swing):**
Two approaches; recommendation is to combine them:
1. **Procedural in code (breathing, sway):** drive chest_lift and head_sway bones directly in `onBeforeRenderObservable` with sine waves. No asset coupling, free CPU.
2. **Per-bone weighted clip (arm-swing-sync):** author an `arm_swing` clip that ONLY keys shoulder/elbow bones, and run `beginWeightedAnimation` on those bones with weight scaled by `state.moveSpeed`. Because the clip targets bones not keyed by locomotion clips, it stacks cleanly.

### 6.2 Camera Lag & Motion

```typescript
// Camera laggy follow (from advanced_animations.md)
const cameraOffset = new BABYLON.Vector3(0.02, 0.08, 0.01);
const lagFactor = 0.15; // 150ms at 60 FPS

scene.registerBeforeRender(() => {
  if (headBone && camera) {
    const targetPos = headBone.position.add(cameraOffset);
    camera.position = BABYLON.Vector3.Lerp(
      camera.position,
      targetPos,
      lagFactor
    );

    // Additive breathing (applied on top of position)
    const breathAmount = Math.sin(Date.now() / 5000) * 0.005;
    camera.position.y += breathAmount;
  }
});
```

### 6.3 Animation Blending & Promises

**v1.1 correction:** the v1.0 example used `setInterval`. This is wrong for a Babylon runtime — `setInterval` doesn't pause when the engine pauses, doesn't respect deltaTime on framerate dips, and runs even when the tab is backgrounded. Use `scene.onBeforeRenderObservable` with the engine's deltaTime instead.

```typescript
import { AnimationGroup, Scene } from "@babylonjs/core";

/**
 * Crossfade between two AnimationGroups. Both must already be `.play()`-ing.
 * Resolves when the fade is complete.
 */
function crossfade(
  scene: Scene,
  from: AnimationGroup,
  to: AnimationGroup,
  durationSec = 0.3
): Promise<void> {
  return new Promise((resolve) => {
    const startFrom = from.weight;
    const startTo = to.weight;
    let elapsed = 0;
    const obs = scene.onBeforeRenderObservable.add(() => {
      const dt = scene.getEngine().getDeltaTime() / 1000;
      elapsed = Math.min(durationSec, elapsed + dt);
      const k = elapsed / durationSec;
      from.weight = startFrom * (1 - k);
      to.weight = startTo + (1 - startTo) * k;
      if (elapsed >= durationSec) {
        scene.onBeforeRenderObservable.remove(obs);
        resolve();
      }
    });
  });
}

// Usage
await crossfade(scene, idle, walk, 0.3);
```

For non-trivial transitions (idle → walk → run with parameter-driven blends) prefer a single per-frame "evaluator" that reads the current `PlayerMovementState` and writes weights to all locomotion groups — one observable, no race conditions between competing crossfades.

---

## 7. Dependencies & Prerequisites

### Asset Pipeline
- ✓ Hunyuan3D 2.1 (stage 1: mesh generation from reference + prompt)
- ✓ Blender 5.1+ (stage 1.5: skeletal rigging)
- ✓ Blender Cycles (stage 2: PBR bake)
- ✓ ComfyUI (stage 2b: AI projection of PBR maps)
- ✓ `witness.py generate --kind animated` (orchestrator support)

### Runtime Libraries
- ✓ `@babylonjs/core` v9.x (UniversalCamera, Skeleton, AnimationGroup, weighted animation)
- ✓ `@babylonjs/loaders` v9.x (glTF import with animations)
- ✓ `@babylonjs/havok` v1.3.x **(now required for M28)** — body collision capsule prevents the camera from penetrating walls when WASD drives the body root. Was previously "pending, not blocking"; the v1.1 architecture change in §3.2 makes this blocking.

### Code Modules
- ✓ `src/interaction/PlayerController.ts` (exists; will extend for animation input)
- [ ] `src/engine/PlayerAnimator.ts` (new; state machine + animation blending)
- [ ] `src/engine/PlayerBodyManager.ts` (new; character mesh instantiation + layering)
- [ ] `src/engine/CameraBreathSystem.ts` (new; subtle idle motion)
- [ ] `src/engine/InteractionAnimator.ts` (new; action state handling)

### Existing Systems That Must Integrate
- **TimeManager** (`src/core/TimeManager.ts`): On era/perspective change, switch character model + animation set. Trigger reload via observable.
- **NarrativeController** (`src/narrative/NarrativeController.ts`): Trigger interaction animations via action bus (e.g., `actionBus.onStateChange("interactionStart")`).
- **InteractableRegistry** (`src/interaction/InteractableRegistry.ts`): Call `InteractionAnimator` on registry event.

---

## 8. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Body mesh clips through environment near camera | Medium | High | Test with collision meshes; adjust near plane or mesh offset if needed |
| Animation blending creates jittery transitions | Low | Medium | Test weighted animation cross-fade duration (0.2–0.5s); profile at 60 FPS |
| Breathing motion induces motion sickness | Low | Medium | Keep amplitude small (< 1cm); add accessibility toggle "hide body" |
| Asset pipeline delays character generation | Medium | High | Start asset generation in parallel; use placeholder animations if needed |
| Performance regression on LOW profile | Low | High | Profile early and often; implement LOD system; simplify breathing on low-end |
| Hand gestures break during fast input changes | Medium | Low | Use additive layer with dampening; fall back to simple arm swing if needed |

---

## 9. Success Metrics

### Playtest Evaluation
- [ ] Players report feeling "in" a body, not floating
- [ ] No motion sickness reports (breathing amplitude acceptable)
- [ ] Camera lag feels physical, not sluggish
- [ ] Transitions between idle/walk/sit feel smooth and continuous
- [ ] 60 FPS on MEDIUM hardware (target machine: 2023 mid-range laptop)

### Technical
- [ ] All three perspectives (Investigator, Protector, Hidden) have distinct animation feels
- [ ] Animation blending has 0 visual pops or frame skips on transition
- [ ] Body mesh depth-sorted correctly (no z-fighting with environment)
- [ ] All interaction animations play uninterrupted in first-person

### Content
- [ ] 100+ frames of unique skeletal animation per character
- [ ] All animations loop smoothly or transition cleanly
- [ ] Breathing and sway animations are procedurally smooth (no keyframe popping)

---

## 10. Era Visibility & Layer Masking (v1.1 addition)

The body mesh's relationship to `CHRONOS_SWITCH` era layers is explicit:

- **The body is era-OWNED, not era-agnostic.** Each era + perspective has its own character GLB (Investigator-2026, Protector-1994, Hidden-1994). When `TimeManager.setEra(...)` fires, `PlayerBodyManager` swaps the active character:
  1. Stops + disposes the outgoing character's `AnimationGroup` instances.
  2. Removes its meshes from the scene (keeps the `AssetContainer` cached).
  3. `addAllToScene()` for the incoming container, re-tags meshes via `tagNode` with the new era scope.
  4. Re-binds the camera follow to the new head bone.
- **Layer mask:** body meshes are tagged with the era they belong to (same convention as world props). The active body always renders; inactive ones are removed from the scene, not just layer-masked.
- **Cross-era continuity:** the breathing/sway procedural system in `CameraBreathSystem` is era-agnostic and survives the swap (no animation state to reload).

This contradicts the v1.0 §3.2 line "Body mesh renders in all layers (era-agnostic visibility)" — that line is superseded by this section.

---

## 11. Phase 0 — De-risk spikes (v1.1 addition, runs BEFORE M26)

Before committing to the M26 schedule, two spikes must complete:

### Spike A — Babylon v9 skeletal blending POC
- **Goal:** confirm `AnimationGroup.weight` crossfade behaves as expected with a glTF-imported skeleton; measure transition smoothness; identify whether additive layering needs bone-masking or procedural overlay.
- **Asset:** any CC0 rigged character with at least 2 looping animations (idle + walk). Avoid Hunyuan dependency.
- **Output:** ≤ 200-line standalone scene under `witness-interactive-vite/src/experiments/embodied_poc/`. Loads model, plays both animations, crossfades on keypress. Verifies: weights sum, no visual pops, runs at 60 FPS.
- **Decision point:** procedural-additive vs. bone-mask-additive for breathing.

**Status (2026-05-24): partial.** Spike runs at `/?poc=1`. Mixamo `Ch24_nonPBR` character + six locomotion FBXs (idle, walking, walking_back, strafe_left, strafe_right, running) assembled in Blender into one armature with one NLA track per clip, exported via `export_nla_strips=True`. Six named `AnimationGroup`s round-trip into Babylon v9. `LocomotionBlender` (in `src/experiments/embodied_poc/EmbodiedPOC.ts`) calls `g.play(true)` + `setWeightForAllAnimatables(w)` per frame and sets `animation.enableBlending = true` so per-bone weights crossfade cleanly.

What works today:
- All six clips bind by name and blend visibly with no T-pose / no name-shift.
- WASD picks the right clip per direction; Shift+W transitions idle→walk→run on the same forward axis.
- Phase-locked playback (shared scene clock + speedRatio = 1) — footsteps don't slip.

Known gaps (more implementation needed before this becomes the production locomotion layer):
- **Single speed.** Strafe/back share `speed=0.5`; only Shift+W reaches `speed=1.0`. Walk→run blending for the lateral and backward clips is not wired.
- **No translation.** The character plays the animation in place; the body controller (CharacterController / Havok capsule) is not attached, so "moving forward" is purely visual.
- **No additive layer.** Idle breathing / weapon sway / head look-at are stubs.
- **No camera mount.** Spike uses an `ArcRotateCamera` for inspection; first-person eye-bone mount is deferred.
- **No era / rig variant handling.** Single Mixamo proportions; Investigator / Protector / Hidden splits are deferred to M26+.

Lessons captured (worth re-using in Spike B + production rigger):
- Babylon's `scene.beginWeightedAnimation(skeleton, …)` does **not** work on glTFs exported with NLA strips — per-clip bone tracks are sliced into separate `AnimationGroup`s, not one continuous skeleton timeline. Drive `container.animationGroups` directly.
- Each Mixamo animation FBX drags in its own duplicate armature + skinned mesh. To assemble onto one rig, import each anim FBX, harvest only the `Action` datablock (set `use_fake_user = True`), then delete every object the import added. Bone-name parity across Mixamo files makes the Action transplant cleanly.
- Blender's glTF exporter, with `export_nla_strips=True`, emits one `AnimationGroup` per NLA *track* (and names it after the track). A track with multiple strips collapses to a single animation in `'actions'` mode — so use **one track per clip, one strip per track**.
- `bpy.data.actions` is **sorted alphabetically**, not chronologically. `bpy.data.actions[-1]` after an import does *not* reliably return the just-imported action once any have been renamed (the renamed snake_case names sort after FBX-default `Armature|…` names). Capture new actions by set-diff against a `pre_actions` snapshot.
- glTF exporter caveat: pass `use_selection=True` and select only the character armature + its skinned meshes, otherwise stray imported objects can leak into the output.

### Spike B — `tools/blender_animate.py` headless rig + animation export
- **Goal:** confirm we can produce an `<id>.glb` with skeleton + named `AnimationGroup` clips from a Blender source file, callable from `branch_animated` in `tools/asset_pipeline.py`.
- **Output:** working CLI that takes `--mesh <hunyuan.glb> --rig <skeleton.blend> --anims <library.blend> --out <id.glb>` and emits a glTF with the right structure.
- **Decision point:** whether to author skeleton+anims as separate `.blend` files or one combined file.

Phase 1 (M26) does not start until both spikes resolve. Cost: ~1–2 working days each.

---

## 12. References & Further Reading

### Babylon.js Animation System
- **Animation Introduction:** `docs/reference/babylon.js-documentation/content/features/featuresDeepDive/animation/animation_introduction.md`
- **Animation Design:** `docs/reference/babylon.js-documentation/content/features/featuresDeepDive/animation/animation_design.md`
- **Advanced Animation Methods:** `docs/reference/babylon.js-documentation/content/features/featuresDeepDive/animation/advanced_animations.md`
- **Camera Behaviors:** `docs/reference/babylon.js-documentation/content/features/featuresDeepDive/behaviors/cameraBehaviors.md`

### Project Design Docs
- **RENDERING.md:** Material system + lighting context for body appearance
- **ASSET_PIPELINE.md:** How to generate skeletal character meshes
- **MASTER.md:** Repo overview + system boundaries
- **CHRONOS_SWITCH.md:** Era-aware rendering (body mesh layering)

### Modded Skyrim References
- [SkyrimLE Modding Guide: Immersive First-Person](https://www.loverslab.com/topic/98211-immersive-first-person/)
- [FNIS Creature Pack (animation retargeting)](https://www.nexusmods.com/skyrim/mods/70158)
- [Immersive Animations (blended locomotion)](https://www.nexusmods.com/skyrim/mods/11721)

---

## Appendix A: Animation Frame Budget

**v1.1 scope revision.** The v1.0 estimate of "~3 hours hand-authored animation" for three characters × ~20 clips is unrealistic — industry estimate for keyframed locomotion + interaction sets is 20–40 hours **per character** with motion-capture reference, more without. To de-risk:

- **v1 ships one character only**: Investigator (2026). M26–M33 produce, integrate, and polish the Investigator embodiment end-to-end.
- **Minimal viable clip set for v1**: `idle_loop`, `walk_forward_loop`, `walk_backward_loop`, `breathing_additive_loop`, `reach_left`, `reach_right`. Strafe, crouch, and sit are deferred to v1.1.
- **Protector & Hidden are moved from M34 → M34–M40** as a follow-on phase, after the Investigator loop is shipped and playtested. Era-specific stance/timing variants come from blend-tree parameters, not new clip libraries, wherever possible.

Original budget retained below for reference (full three-character target):

Assuming 30 FPS animation export and ~40–60 frame clips:

```
Per character (Investigator, Protector, Hidden):
- Locomotion (8 clips): ~320 frames
- Transitions (4 clips): ~80 frames
- Interactions (6 clips): ~150 frames
- Additive (breathing, sway): ~270 frames
- Total: ~820 frames per character

All three characters: ~2,460 frames
Blender source: ~3 hours hand-authored animation (reference-based motion capture keyframing)
Export pipeline: Automated via `witness.py generate --kind animated`
Runtime cost: ~2–4 MB per character (GLB with KTX2 compression)
```

---

## Appendix B: Example: PlayerAnimator State Machine Pseudocode

```typescript
// Simplified state machine + blending orchestrator
class PlayerAnimator {
  private skeleton: Skeleton;
  private currentState: "idle" | "walk" | "crouch" | "interact" = "idle";
  private animations: Map<string, Animatable> = new Map();
  private transitionDuration = 0.3; // seconds

  onPlayerInputChanged(input: PlayerMovementState) {
    const nextState = this.computeNextState(input);
    if (nextState !== this.currentState) {
      this.transitionToState(nextState, input);
    }
    this.blendAnimationsByDirection(input.moveDirection, input.moveSpeed);
  }

  private computeNextState(
    input: PlayerMovementState
  ): "idle" | "walk" | "crouch" | "interact" {
    if (input.interactionTarget) return "interact";
    if (input.isCrouching) {
      return input.isMoving ? "crouch" : "idle"; // crouching affects base state
    }
    return input.isMoving ? "walk" : "idle";
  }

  private async transitionToState(
    nextState: string,
    input: PlayerMovementState
  ) {
    const currentAnim = this.animations.get(this.currentState);
    const nextAnim = this.animations.get(nextState);

    // Cross-fade
    if (currentAnim) {
      await this.fadeOut(currentAnim, this.transitionDuration);
    }
    if (nextAnim) {
      await this.fadeIn(nextAnim, this.transitionDuration);
    }

    this.currentState = nextState;
  }

  private blendAnimationsByDirection(
    moveDir: Vector3,
    speed: number
  ) {
    // Pseudo-code: blend idle/walk-fwd/walk-back/strafe based on input vector
    const fwdWeight = Math.max(0, moveDir.z);
    const bkdWeight = Math.max(0, -moveDir.z);
    const lftWeight = Math.max(0, -moveDir.x);
    const rgtWeight = Math.max(0, moveDir.x);

    // Normalize so they sum to 1
    const total = fwdWeight + bkdWeight + lftWeight + rgtWeight;
    if (total > 0) {
      this.animations.get("walk_forward")!.weight = (fwdWeight / total) * speed;
      this.animations.get("walk_backward")!.weight = (bkdWeight / total) * speed;
      this.animations.get("walk_strafe_left")!.weight = (lftWeight / total) * speed;
      this.animations.get("walk_strafe_right")!.weight = (rgtWeight / total) * speed;
    }

    // Breathing always plays at low weight, blended additively
    this.animations.get("breathing")!.weight = 0.3;
  }

  private async fadeOut(anim: Animatable, duration: number) {
    // Implement fade-out as in Babylon docs
  }

  private async fadeIn(anim: Animatable, duration: number) {
    // Implement fade-in as in Babylon docs
  }
}
```

---

## Appendix C: File Structure After Implementation

```
witness-interactive-3D/
├── docs/design-docs/EMBODIED_FIRST_PERSON.md (this file)
├── witness-interactive-vite/src/
│   ├── engine/
│   │   ├── PlayerAnimator.ts (state machine)
│   │   ├── PlayerBodyManager.ts (character instantiation)
│   │   ├── CameraBreathSystem.ts (idle motion)
│   │   └── InteractionAnimator.ts (action handling)
│   ├── interaction/
│   │   └── PlayerController.ts (updated: feeds animation input)
│   └── core/
│       ├── TimeManager.ts (updated: era-aware character reload)
│       └── AnimationDirector.ts (updated: coordinate with PlayerAnimator)
├── witness-interactive-vite/public/assets/
│   ├── figure_investigator_2026.glb
│   ├── figure_investigator_2026.lod1.glb
│   ├── figure_protector_1994.glb
│   ├── figure_protector_1994.lod1.glb
│   ├── figure_hidden_1994.glb
│   └── figure_hidden_1994.lod1.glb
├── tools/
│   ├── witness.py (updated: support --kind animated)
│   └── asset_pipeline.py (updated: skeletal character export)
└── docs/asset-index.md (entries for three character assets)
```

---

**End of PRD v1.0**
