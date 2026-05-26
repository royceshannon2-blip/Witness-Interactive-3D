# Embodied First-Person POC — Phase 0 Spike A

Standalone scene that proves the **frame-weighted locomotion blend tree** from
[`EMBODIED_FIRST_PERSON.md`](../../../../docs/design-docs/EMBODIED_FIRST_PERSON.md) §6.1
end-to-end against a real rigged glTF.

This is **not** the embodied camera, body controller, or Havok capsule. It is
*only* the animation blend system, viewed third-person, so we can verify:

1. `scene.beginWeightedAnimation` blends per-bone Animation tracks correctly.
2. All locomotion clips share the scene clock → phase-locked (no foot slipping).
3. The directional weighting math produces clean 4-way + run blending.
4. `Animation.enableBlending = true` + `blendingSpeed` smooths weight transitions.

## Running the POC

The POC is not wired into `main.ts` by default. To run it, temporarily add to a route:

```typescript
import { mountEmbodiedPOC } from "./experiments/embodied_poc/EmbodiedPOC";
const canvas = document.getElementById("renderCanvas") as HTMLCanvasElement;
mountEmbodiedPOC(canvas);
```

Then `npm run dev` and open the page.

## Required assets

The POC needs two files at `witness-interactive-vite/public/assets/`:

- `poc_rigged.glb` — a rigged character with all clips concatenated on a single NLA track
- `poc_rigged.anim.json` — clip manifest (see `poc_rigged.anim.example.json` here for shape)

### Quick path: Mixamo

1. Download a free Mixamo character (T-pose).
2. Download the following animations onto that character, all "In Place":
   `Idle`, `Walking`, `Walking Backwards`, `Strafe Left`, `Strafe Right`, `Running`.
3. In Blender, import all six, place them on the same armature's NLA editor
   end-to-end. Note the start/end frame of each.
4. Export as glTF Binary (`.glb`) with **animations enabled** and
   **"Group by NLA Track"** disabled (we want one consolidated track).
5. Hand-author `poc_rigged.anim.json` from the frame ranges Blender showed.

This is the same shape `tools/blender_animate.py` will eventually produce
automatically (Spike B). For the POC, manual is fine.

## Controls

| Key      | Action |
|----------|--------|
| W/A/S/D  | directional input vector |
| Shift    | hold to run |
| `        | toggle Babylon inspector |

The diagnostic overlay (top-left) shows live per-clip weights and a phase
indicator. If footsteps slip across directions, the NLA-track clips are not
phase-aligned — re-author so the same gait phase lands at the same frame
offset in every directional variant.

## Spike acceptance criteria

- [ ] All six locomotion clips load and play at weight 0 without visible jitter.
- [ ] Pressing W ramps `walk_forward` to 1.0 over ~80ms (the `blendingSpeed`).
- [ ] Holding W+D blends `walk_forward` and `strafe_right` at ~0.5 / 0.5 with no foot pop.
- [ ] Shift+W transitions cleanly from walk to run with footsteps remaining synced.
- [ ] FPS stays at 60 on the dev workstation (RTX 5090).
- [ ] Inspector shows ~N Animatables per bone × clip count (sanity check).

If any of these fail, write findings into the parent PRD §11 (Phase 0) and
re-spec before starting M26.
