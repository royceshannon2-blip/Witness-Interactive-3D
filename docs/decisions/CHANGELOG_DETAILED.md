# Detailed Change Log

Per [`.claude/rules/documentation.md`](../../.claude/rules/documentation.md), every completed task appends a technical summary here. Architectural decisions with trade-offs go into [`adrs/`](adrs/) as individual ADRs; this log is the running narrative.

Format per entry:

```
## YYYY-MM-DD — <short subject>
**Author:** <who>
**Scope:** <subsystem(s) touched>
**Files:** <bullet list of changed paths>

<one-paragraph technical summary — what changed and why>

**Follow-ups:** <TODOs, related ADRs, unblocked work>
```

Entries newest-first.

---

## 2026-05-20 — UI design system implementation ("Archival Solemnity")

**Author:** @royceshannon2 (via Claude)
**Scope:** `witness-interactive-vite/src/ui/`, `witness-interactive-vite/src/bootstrap/`, `witness-interactive-vite/src/style.css`
**Files:**
- `src/style.css` — full design token system (OKLCH palette, Google Fonts import, all HUD/Ledger/Caption/Choice CSS classes)
- `src/ui/HUD.ts` — rewritten as DOM overlay; drops Babylon GUI ADT in favour of CSS-class-driven elements (compass, ledger badge, echo indicator, interaction prompt, toast)
- `src/ui/LedgerUI.ts` — complete overhaul: grid + detail panel layout, stripe thumbnails, keyboard navigation, `_kindFromKey` heuristic for evidence tags
- `src/ui/CaptionOverlay.ts` — styled subtitle bar with speaker name, brass dot, Cormorant Garamond caption line; added `setSpeaker()` method and italic `*...*` formatting
- `src/bootstrap/ChoiceOverlay.ts` — rewritten with roman-numeral option list, serif hierarchy, brass hover rail, keyboard 1–N quick-select

The HUD is now fully DOM-based (no `@babylonjs/gui` imports) which gives CSS hot-module-replacement, full typography control, and simpler z-index layering. The compass SVG needle accepts `setHeading(deg)` for future wiring to the player controller. Design tokens (--brass, --dusk, --bone, etc.) are surfaced as CSS custom properties on `:root`, making them reusable by all overlays.

**Follow-ups:** Wire `hud.setHeading()` from `PlayerController` heading readout. Wire `hud.setEchoDistance()` from `InteractableRegistry` proximity probe. Consider updating `RemembranceSequence.ts` and `IntroSequence.ts` to use design tokens.

---

## 2026-05-20 — M19: Narrator audio generation script

**Author:** @royceshannon2 (via Claude)
**Scope:** `tools/`, `audios/narrator/`
**Files:**
- `tools/generate_narrator_audio.py` — M19 narrator generation script (new)
- `audios/narrator/manifest.json` — key→file map, created on dry-run

`tools/generate_narrator_audio.py` generates all 77 pre-baked narrator WAV clips for the game: 50 ambient banter lines (5 per location × 2 eras × 5 locations), 4 vista reflection lines, 4 breather sequence lines, 3 path reflection paragraphs, and 16 ledger journal entry readings. All text is sourced from `BanterLibrary.ts` and `main.ts` LEDGER_ENTRIES, duplicated as a Python manifest so no TS parser is needed at generation time. The script uses `HiggsAudioModelClient` from `higgs_audio_src/examples/generation.py`, loaded once with the `en_man` reference voice steered by a narrator scene prompt (quiet interior, elderly East African male, reflective). Deterministic per-key seeds ensure reproducible re-generation. FFmpeg two-pass loudnorm normalizes every clip to −16 LUFS / −1 dBTP / 24 kHz s16. The script is idempotent (skips existing WAVs) and supports `--dry-run` and `--key KEY` flags. Output at `audios/narrator/manifest.json`.

**Follow-ups:** Run `LD_LIBRARY_PATH=/usr/local/lib/ollama/cuda_v12:$LD_LIBRARY_PATH python3 -W ignore tools/generate_narrator_audio.py` to generate all clips. M20 (`tools/generate_ambient_audio.py`) is next.

---

## 2026-05-19 — M18: Local AI stack installed and validated
**Author:** @royceshannon2 (via Claude)
**Scope:** host Python environment, `tools/`
**Files:**
- `tools/M18_INSTALL_RUNBOOK.md` — completed, documents actual install path + patches
- `tools/higgs_audio_src/` — Higgs-Audio v2 source (boson-ai/higgs-audio, editable install, gitignored)
- `.gitignore` — `tools/higgs_audio_src/` excluded

All 7 M18 checks pass: FFmpeg · FLUX deps · AudioCraft · MusicGen/AudioGen · Higgs-Audio v2 · CUDA · RTX 5090. Three compatibility patches applied: (1) torchaudio 2.11.0+cu128 version-check bypassed (no cu132 torchaudio exists; CUDA 12 libs from Ollama provide the missing `libcudart.so.12`); (2) AudioCraft's `import spacy` made optional (blis won't build on Python 3.14; spacy is unused by MusicGen/AudioGen); (3) Higgs-Audio's `LLAMA_ATTENTION_CLASSES` import patched for transformers 5.x. All audio generation needs `LD_LIBRARY_PATH=/usr/local/lib/ollama/cuda_v12` set. Higgs-Audio package is `boson_multimodal` (import: `boson_multimodal.serve.serve_engine.HiggsAudioServeEngine`).

**Follow-ups:** M19 (narrator audio via Higgs-Audio), M20 (ambient beds + SFX via AudioCraft), M22 (FLUX reference images).

---

## 2026-05-19 — M21: AmbienceEngine — per-location/era bed manager + ducking
**Author:** @royceshannon2 (via Claude)
**Scope:** `src/audio/`, `ARCHITECTURE.md` §5.11
**Files:**
- `src/audio/AmbienceEngine.ts` (new) — bed-management singleton
- `src/audio/AudioManager.ts` — delegates `setLocation` / `transitionToEra` / `duckAmbience` to `AmbienceEngine`; accepts legacy long-form location ids via the `LOCATION_ALIASES` table (`family_compound` → `compound`, `lake_shore` → `lakeshore`, etc.)
- `src/audio/index.ts` — re-exports `ambienceEngine` for tests + dev overlays
- `ARCHITECTURE.md` §5.11 — internal layout subsection documenting `AudioManager` / `AmbienceEngine` / `NarratorSystem`; expanded invariants now name the single-flight swap chain and the `bed_<location>_<era>` id convention

`AmbienceEngine` owns the Babylon `AudioEngineV2` ambient layer: one bed at a time, crossfaded when location or era changes, attenuated to 50% under narrator playback. Bed ids follow `bed_<location>_<era>` (e.g. `bed_compound_present`) and resolve to `/audios/ambience/<id>.ogg`. `CreateSoundAsync` is called lazily on first reference and cached; a 404 logs a warning and caches `null` so we don't retry on every swap — that keeps the narrative runnable before M20 generates the 10 bed clips. Volume ramps go through `StaticSound.setVolume(target, { duration, shape: Linear })` per the v9 AudioParameter API. Swap calls are single-flight via a private `swapChain` promise tail, so two rapid `setLocation` calls can't leave a stale bed playing. `duckAmbience(true)` ramps the current bed to `BASE_VOLUME * DUCK_FACTOR` (0.7 × 0.5 = 0.35) over 0.3 s; `duckAmbience(false)` restores it. Crossfade defaults (2.0 s location, 1.3 s era) match AUDIO_ARCHITECTURE.md §4. `npm run build` clean.

**Follow-ups:**
- M19: generate the 86 narrator clips (Higgs-Audio v2) from `BanterLibrary` keys → `/audios/narrator/<key>.ogg` + matching `.vtt`.
- M20: generate the 10 ambient beds (AudioCraft / MusicGen) and 38 SFX → `/audios/ambience/bed_<location>_<era>.ogg` and `/audios/sfx/<key>.ogg`. Bed file names must match the id format `bed_<location>_<era>.ogg` so they slot into the engine without code changes.
- Wire `AmbienceEngine.setLocation` directly from world-region triggers in M23 once `PassiveBanter` lands — currently location changes only fire from the bootstrap proximity probe and the era-flip subscription.
- Replace symmetric era crossfades with the doc's asymmetric pair (0.5 s fade-out + 1.3 s fade-in with overlap) once acoustic tuning starts.

---

## 2026-05-18 — M17: Story content — BanterLibrary, ledger journal entries, path descriptions
**Author:** @royceshannon2 (via Claude)
**Scope:** `src/narrative/`, `src/bootstrap/`, `src/ui/`
**Files:**
- `src/narrative/BanterLibrary.ts` (new) — all authored story content
- `src/narrative/LedgerStore.ts` — added optional `body` field to `LedgerEntry`, updated `add()` signature
- `src/ui/LedgerUI.ts` — renders `entry.body` when present, falls back to `entry.text`
- `src/bootstrap/main.ts` — `LEDGER_ENTRIES` expanded to `{ toast, body }` pairs; `recordEcho` + rehydration loop updated
- `src/bootstrap/ChoiceOverlay.ts` — path description paragraphs wired from `BanterLibrary.CHOICE_DESCRIPTIONS`

`BanterLibrary.ts` is the single source of truth for all authored text in the session. It exports: `BANTER_LINES` (50 ambient narrator lines, 5 per location per era, across compound/cellar/lakeshore/ravine/heights); `VISTA_LINES` (4 single-sentence reflections keyed to VistaSystem `narratorKey`s); `BREATHER_LINES` (caption fallback text for 5 breather audio keys); `CHOICE_DESCRIPTIONS` (path description paragraphs for ChoiceOverlay, one per path); `REFLECTION_LINES` (post-Act-3 reflection paragraphs, one per path, with Higgs-Audio v2 target keys). All 16 ledger entries now carry a short HUD toast and a full first-person journal body (1-4 sentences, historically grounded, grandfather's voice, Bisesero Hills 1994). Audio generation targets M19 (narrator clips) and M23 (PassiveBanter wiring).

**Follow-ups:** M18 (install AI stack), M19 (generate narrator audio from BanterLibrary keys), M23 (PassiveBanter system consumes `BANTER_LINES`).

---

## 2026-05-18 — M16: NarratorSystem + CaptionOverlay
**Author:** @royceshannon2 (via Claude)
**Scope:** `src/audio/`, `src/ui/`, `src/interaction/`, `src/bootstrap/main.ts`
**Files:**
- `src/audio/NarratorSystem.ts` (new) — narrator queue singleton
- `src/ui/CaptionOverlay.ts` (new) — WebVTT-driven caption DOM overlay
- `src/audio/AudioManager.ts` — added `duckAmbience(bool)` stub
- `src/interaction/InteractableRegistry.ts` — added `hasNearby()` getter
- `src/audio/index.ts` — exports `narratorSystem`
- `src/ui/index.ts` — exports `captionOverlay`, `parseCues`, `fetchCues`
- `src/bootstrap/main.ts` — attaches `captionOverlay` + `narratorSystem` at boot

`NarratorSystem` serialises narrator playback: lines are queued and played back-to-back (current + 0.8 s silence before next). Ambience ducking is delegated to `AudioManager.duckAmbience()` (stub until AmbienceEngine lands in M21). E-key skip fires only when `interactableRegistry.hasNearby()` returns false, so it can't conflict with the E-key interactable handler. `CaptionOverlay` is a fixed DOM element (default ON, toggleable via `setEnabled()`), driven by `.vtt` cue timestamps via `playCues()`; degrades gracefully to direct `showText()` calls when no .vtt file exists (expected until M19). Both singletons are stub-safe: no actual audio plays until M19 WAV files land.

**Follow-ups:** M17 (story content drafts), M19 (real audio replaces stub waits in NarratorSystem), M21 (AmbienceEngine fills in duckAmbience).

---

## 2026-05-17 — Asset pipeline Stages 2 + 3: PBR bake + validation renders
**Author:** @royceshannon2 (via Claude)
**Scope:** `tools/texture_asset.py` (new), `tools/blender/bake_pbr.py` (new), `tools/blender/material_families.py` (new), `tools/blender/render_validation.py` (new), `prompts/_pbr_workflows/sdxl_depth_pbr.json` (new), `tools/asset_pipeline.py`
**Files:**
- `tools/blender/material_families.py` *(new)* — Eight PBR family presets mirroring the `_STYLE_GUIDE.md` material table (mud_brick, tin, wood, stone, cloth, leather, wax, skin) plus a `vegetation` fallback. Each preset is a `FamilyPreset` TypedDict: base_color, roughness (mean + variance), metallic, specular, normal_strength, ao_strength, displacement_mid, notes. `pick_family(asset_id)` runs ordered substring matches against `ID_PATTERNS` so the 13 Phase 1 ids resolve to the right family without hand-mapping. Plain data module — no `bpy` imports — so both the in-Blender bake script and the out-of-Blender orchestrator can import it.
- `tools/blender/bake_pbr.py` *(new)* — Blender 5.1 headless script. Resets the scene, switches Cycles to OPTIX GPU on the 5090, imports the raw GLB, Smart-UV-Projects any mesh missing UVs, builds a Principled BSDF + voronoi/noise network parametrised by the chosen family preset, renders 6 canonical views (`±X/±Y/±Z`) with beauty + 16-bit depth EXR passes for the optional stage 2b AI projector, then bakes Albedo (DIFFUSE COLOR-only), MR pack (R-unused / G-roughness / B-metallic per Babylon convention), Normal (data-space), and AO at the configured resolution (default 8192²). Re-exports a textured GLB. Wraps `main()` in a top-level try/except → SystemExit so Blender's "exit 0 on uncaught exception" cannot mask failure.
- `tools/texture_asset.py` *(new)* — Stage 2 orchestrator. Spawns Blender headless with `bake_pbr.py`, then normalises the Compositor File Output suffixes (`<view>_beauty_0001.png` → `<view>.beauty.png`) for predictable downstream consumption. Stage 2b path: for each canonical view, uploads beauty + depth to ComfyUI `/upload/image`, loads `prompts/_pbr_workflows/sdxl_depth_pbr.json` with `__PROMPT__` (built from the asset's `<id>.md` body + PBR style modifiers), `__VIEW_FILENAME__`, `__DEPTH_FILENAME__` substituted, polls `/history`, downloads the projected PNG to `processed/views/<id>/<view>.pbr.png`. UV reprojection of projected views back to an 8K Albedo is the documented next step.
- `prompts/_pbr_workflows/sdxl_depth_pbr.json` *(new)* — SDXL base + ControlNet (depth) workflow. Strength 0.85, denoise 0.72, 28 steps, dpmpp_2m + karras, embedded anti-stylization negative prompt. Substitutable placeholders match `texture_asset.py`'s string substitution.
- `tools/blender/render_validation.py` *(new)* — Stage 3 Blender headless. Imports the textured GLB, builds the world environment (either `--hdri <path>` Environment Texture or a procedural Sky Texture — `MULTIPLE_SCATTERING` for Blender 5 with `HOSEK_WILKIE`/`PREETHAM` fallbacks, since Blender 5 dropped the `NISHITA` enum value), drops a bbox-scaled 3-point rig (warm key 5500 K at upper-front-left, cool fill 6500 K at lower-front-right ⅓ intensity, white rim at upper-back ½ intensity), renders 4 turntable angles (0°/90°/180°/270°) + 1 hero ¾-angle shot. All sizes (light distance, light energy, camera radius) scale linearly with the asset's bbox diagonal so a ledger book (≈ 0.25 m) and a eucalyptus tree (≈ 8 m) frame consistently. Writes `processed/renders/<id>/renders.json` index for CHANGELOG references.
- `tools/asset_pipeline.py` — Inserted stage 1.5 (PBR bake) and stage 4.5 (validation renders) into `branch_mesh()`. New CLI flags: `--auto-texture` + `--texture-family` + `--texture-size` + `--view-size` + `--bake-samples` + `--skip-views` + `--ai-project`, `--validation-renders` + `--hdri` + `--render-samples` + `--render-resolution`. When `--auto-texture` runs, the optimiser consumes the textured GLB (`<id>.textured.glb`) instead of the raw one.

Validation: ran stages 2 + 3 end-to-end on the existing `vegetation_eucalyptus_mature.glb` (the only asset Hunyuan had already produced). Stage 2 wrote four 1024² PBR maps (albedo, MR pack, normal, AO) + a 77 MB textured GLB in ~10 s. Stage 3 wrote 5 PNG renders (turntable_0/90/180/270 + hero) at 512² in ~5 s using procedural sky + 3-point. Two Blender 5 API changes caught and fixed during validation: `BakeSettings.pass_filter` is now read-only (pass as `bpy.ops.object.bake(pass_filter=...)` kwarg); `ShaderNodeTexSky.sky_type` enum no longer accepts `NISHITA`.

**Follow-ups:** UV reprojection step (`tools/texture_asset.py --ai-project` currently only generates per-view PBR maps; the bake into a single 8K Albedo via projection painting is not yet wired). Family preset tuning — the eucalyptus albedo bake reads near-white because the procedural MULTIPLY mix scales below the base_color; consider switching to an additive overlay or raising the family base_color brightness. Procedural Sky Texture is a placeholder; supplying real overcast HDRIs under `processed/hdris/` will make stage 3 renders match the Digital Diorama style guide more faithfully.

---

## 2026-05-17 — Asset pipeline Stage 0: ComfyUI + Flux.1 [dev] image gen
**Author:** @royceshannon2 (via Claude)
**Scope:** `tools/generate_ref_image.py` (new), `tools/asset_pipeline.py`, `tools/COMFY_RUNBOOK.md` (new), `prompts/_flux_workflows/` (new), `docs/design-docs/ASSET_PIPELINE.md`
**Files:**
- `tools/generate_ref_image.py` *(new)* — Stage 0 client. Parses an asset's `<id>.md` template (frontmatter + body), extracts the `## Reference image` section, strips markdown + path-reference framing, appends a Digital Diorama style suffix to compose a Flux-friendly natural-language prompt. Loads a workflow JSON, substitutes `__PROMPT__` + `__SEED__` placeholders, POSTs to ComfyUI `/prompt`, polls `/history/{prompt_id}` until outputs land, downloads via `/view`, writes to `prompts/asset-templates/<id>/ref.png`. Idempotent — no-ops when ref.png already exists unless `--force` is passed. `--print-prompt-only` skips the HTTP path for prompt-builder debugging.
- `prompts/_flux_workflows/default.json` *(new)* — Flux.1 [dev] fp8 workflow at 1024² / 20 steps / guidance 3.5. UNETLoader + DualCLIPLoader (t5xxl_fp8 + clip_l) + VAELoader + SamplerCustomAdvanced. Peaks ~14 GB VRAM, leaves headroom for an idle Hunyuan container.
- `prompts/_flux_workflows/hero.json` *(new)* — Higher-fidelity variant at 1536² / 40 steps with fp16 T5-XXL. ~22 GB VRAM peak — operator must stop the Hunyuan container before running. Used for hero assets (ledger, altar, hands).
- `tools/asset_pipeline.py` — Added `maybe_auto_ref()` stage-0 hook called from `branch_mesh()` and `branch_animated()`. New CLI flags: `--auto-ref` (chain stage 0 → 1), `--auto-ref-force` (regenerate existing ref), `--auto-ref-workflow {default|hero}`, `--auto-ref-seed <int>`, `--comfy-server <url>`. Idempotent when a ref.png already exists.
- `tools/COMFY_RUNBOOK.md` *(new)* — Mirrors `HUNYUAN_RUNBOOK.md` structure. Pre-flight, Docker run commands (foreground + detached), model layout under `model_cache/comfyui/`, HuggingFace download commands for the four Flux files, sequential vs concurrent VRAM coordination with Hunyuan, troubleshooting matrix.
- `docs/design-docs/ASSET_PIPELINE.md §3` — Mermaid pipeline diagram extended: `Prompt → RefGen → Ref → Gen → Raw → Texture → Bake → Baked → Optimize → Final`, with `Raw → Render → Renders` as a parallel validation-render branch.

Closes the long-standing gap where `ref.png` was placed by hand into each `prompts/asset-templates/<id>/`. The user has the authored templates and `_STYLE_GUIDE.md`; stage 0 now turns those into reference photos automatically.

**Follow-ups:** Stage 2 (`tools/texture_asset.py` + `tools/blender/bake_pbr.py`) — AI-projected PBR textures + 8K Cycles bake. Stage 3 (`tools/blender/render_validation.py`) — HDRI + 3-point lighting + 4-view turntable + hero shot. ComfyUI Docker image requires PyTorch built for CUDA 12.6+ to run on sm_120 (Blackwell) — `yanwk/comfyui-boot:latest` is the recommended baseline.

---

## 2026-05-17 — CinematicDirector + VistaSystem + 3 pacing interludes (M15)
**Author:** @royceshannon2 (via Claude)
**Scope:** `core/CinematicDirector.ts` (new), `core/VistaSystem.ts` (new), `bootstrap/BreatherSequences.ts` (new), `core/index.ts`, `bootstrap/main.ts`, `tools/validate_fragments.py`
**Files:**
- `witness-interactive-vite/src/core/CinematicDirector.ts` *(new)* — Multi-beat, multi-track cinematic sequencer built on AnimationDirector primitives. Beat union type covers 11 action kinds: `camera-dolly`, `camera-approach`, `fov`, `audio-play`, `audio-effect`, `wait`, `overlay-text`, `overlay-hide`, `control-lock`, `control-unlock`, and `parallel` (runs child beats in parallel via `Promise.all`, resolves when the longest completes). Sequences are skippable via Escape (registered on `scene.onKeyboardObservable`). Camera beats are skipped and snapped under `prefers-reduced-motion`. DOM overlay: fixed-position text panel at 12% from bottom, CSS opacity transitions for fade in/out, pointer-events:none. Designed as a disposable tool (not singleton) — callers construct, `play()`, then `dispose()`.
- `witness-interactive-vite/src/core/VistaSystem.ts` *(new)* — Stillness-detection system for location-specific narrator reflections. Registers `VistaDef` anchor points (world position + radius + narrator key); uses a per-frame render-loop observer to compare camera position delta against `STILL_THRESHOLD_M = 0.08 m`. After `DWELL_REQUIRED_SEC = 5.0 s` of uninterrupted stillness within a vista radius, calls `audioManager.playNarratorEntry()` once per session (fired IDs tracked in a `Set<string>`). Exported as singleton `vistaSystem` via `core/index.ts`.
- `witness-interactive-vite/src/bootstrap/BreatherSequences.ts` *(new)* — Three mandatory pacing interludes. (1) `runReturnToShrineBreather` (~11 s, no camera lock): narrator line + text overlay, fires after `all_evidence_found` during `allEvidenceCinematic`. (2) `runMidPathVistaBreather` (~20 s, camera locked): three path variants (hider/escapist/observer) with distinct narrator keys and overlay text; fires after the second puzzle in each Act 3 path via `onReturnToPresent` hook of the mid-path fragment. (3) `runPreRemembranceBreather` (~21 s, camera locked): 0.3 m camera-approach toward shrine + FOV narrow to 0.98 + narrator, FOV restored to 1.05 before unlock; runs after path completion, shrine registration deferred until sequence resolves.
- `witness-interactive-vite/src/core/index.ts` — Added exports for `CinematicDirector`, all 11 `Beat` subtypes, `vistaSystem`, and `VistaDef`.
- `witness-interactive-vite/src/bootstrap/main.ts` — (1) `vistaSystem.attach(scene, camera)` added to boot system-attachment block. (2) Four vista anchor points registered after world construction (compound heights, lake shore, ravine high, heights overlook) — positions are scaffold placeholders to be tuned once assets land. (3) `runReturnToShrineBreather` called at the start of `allEvidenceCinematic` before camera lock. (4) `runPreRemembranceBreather` deferred shrine registration with async IIFE in `makePathChecker` — proximity HUD prompt pushed immediately, shrine interactable registered only after breather resolves. (5) `runMidPathVistaBreather` wired into `onReturnToPresent` of `waterScheduleFragment` (path A puzzle_2), `boatCapacityFragment` (path B puzzle_2), and `checkpointRecordsFragment` (path C puzzle_2).
- `tools/validate_fragments.py` — Updated `BEGIN_OPEN_RE` to also match `beginWithBreath({`, since the `beginWithBreath` wrapper spreads the spec via `{...spec}` and the validator could not previously see `fragmentId`/`unlocksFlag` at the `pastSceneController.begin` internal call. Added skip logic for spread-relay calls whose body starts with `...`.

The validator now exits 0 on all 15 fragments. TypeScript build is clean.

**Follow-ups:** M16 — `NarratorSystem.ts` (queued narrator + .vtt sync + ambience ducking + E-key skip) + `CaptionOverlay.ts`. Vista anchor positions need visual tuning once world geometry loads in-browser.

## 2026-05-17 — Cinematic system audit + per-fragment profiles + camera breath (M14)
**Author:** @royceshannon2 (via Claude)
**Scope:** `core/EchoProfiles.ts` (new), `core/AnimationDirector.ts`, `core/index.ts`, `bootstrap/main.ts`
**Files:**
- `witness-interactive-vite/src/core/EchoProfiles.ts` *(new)* — Per-fragment cinematic profiles for the echo pre-roll and dwell phases. Defines `EchoPrerollProfile` (`fovDelta`, `durationSec`, `pullMag`) and a 15-entry `ECHO_PROFILES` map keyed by `fragmentId`. Each profile encodes a distinct spatial register: cellar echoes narrow the FOV and pull hard (underground compression), ravine/observer echoes open slightly (elevated detachment), altar echoes tighten intimately, path-A echoes grow heavier with each puzzle, path-B echoes expand outward, path-C echoes widen to the most detached. Total camera motion ≤ 0.22 m, |fovDelta| ≤ 0.08 rad — within perceptual non-disorientation bounds. Fallback `DEFAULT_ECHO_PROFILE` for unregistered fragments. Exported via `core/index.ts`.
- `witness-interactive-vite/src/core/AnimationDirector.ts` — Added two exports: (1) `startCameraBreath(scene, camera, opts)` — continuous sinusoidal Y-axis oscillation (0.007 m amplitude, 0.28 Hz) using an additive delta pattern so it doesn't fight WASD or mouse-look. Returns a `stop()` function for clean cancellation. Used during the 12–20 s Past echo dwell to sell "inhabiting a memory" at sub-perceptual levels. (2) `cameraApproach(scene, camera, anchorPos, pullMag, durationSec)` — brief camera pull toward an anchor (the "being drawn in" moment before an era transition). Detaches input, dollies `pullMag` metres toward anchor, re-attaches. 0.45 m minimum-distance guard prevents camera entering a mesh. Safe to run in `Promise.all` with `fovTween` since they target different camera properties.
- `witness-interactive-vite/src/core/index.ts` — Exports `cameraApproach`, `startCameraBreath`, `ECHO_PROFILES`, `DEFAULT_ECHO_PROFILE`, `getEchoProfile`, and `EchoPrerollProfile`.
- `witness-interactive-vite/src/bootstrap/main.ts` — Five cinematic gaps closed: (1) All 15 `onActivate` calls updated from a flat `echoPreroll` stub to a profile-aware version that reads `getEchoProfile(fragmentId)` and runs `cameraApproach` + asymmetric `fovTween` in parallel — each fragment now has a unique spatial feel. (2) `beginWithBreath` wrapper added: wraps `pastSceneController.begin(...)` to start `startCameraBreath` on `onEnterPast` and cancel it on `onReturnToPresent`, injecting the embodied-presence effect across all 15 dwells. (3) `allEvidenceCinematic` closure: camera lifts 1.5 m + FOV widens + `memoryDissolve` in parallel over 2.2 s, brief apex pause, `showChoiceOverlay`, then camera settles back — the all-evidence moment is now a full act-break beat rather than an abrupt modal. (4) Shrine approach (Act 4): `makePathChecker` augmented with `scene`, `camera`, `pipeline` args; interaction handler dollies 0.65 m toward shrine + narrows FOV to 0.82 + `memoryDissolve` before `showRemembranceSequence`. (5) Asymmetric era FOV breath: `ECHO_FOV_BREATH_ENTRY = 0.06` (pull inward on Past entry) vs `ECHO_FOV_BREATH_RETURN = 0.12` (wider burst on Present return) — the "breaking free" feeling is now visually distinct from the "falling in" feeling. `checkAllEvidence` is now late-bound (assigned after `allEvidenceCinematic` is defined) to avoid forward-reference; `checkPathA/B/C` also updated to pass the new `scene, camera, pipeline` params.

Build verifies clean (`tsc && vite build` exits 0, zero TypeScript errors).

**Follow-ups:** Per-fragment mesh emissive flash at activation moment; animated lighting envelope on era transition (sun tween, sky tint lerp); depth-of-field rack focus on `memoryDissolve` (deferred — needs depth-buffer prepass cost measured on LOW profile first); Playwright smoke test covering Phase 1 → Phase 4.

---

## 2026-05-17 — Phase 1 closure + studio-quality echo cinematics (M13)
**Author:** @royceshannon2 (via Claude)
**Scope:** `core/AnimationDirector.ts` (new), `engine/RenderingPipeline.ts`, `interaction/InteractableHighlight.ts` (new), `bootstrap/LedgerOpening.ts` (new), `bootstrap/IntroSequence.ts`, `bootstrap/main.ts`
**Files:**
- `witness-interactive-vite/src/core/AnimationDirector.ts` *(new)* — Cinematic-grade animation primitives over Babylon's `Animation` system. Exports `cameraDolly` (position + look-at via yaw/pitch), `fovTween`, `meshMove`, `meshRotate`, `waitFrames`, and a `softEase` (sine ease-in-out) helper. All return Promises driven by `scene.beginDirectAnimation`, so they are frame-rate independent and obey engine pause. Defaults to `CubicEase` ease-in-out per the project's "weighted" tonal register.
- `witness-interactive-vite/src/engine/RenderingPipeline.ts` — Added `memoryDissolve(durationSec) → Promise<void>`. Burst-enables chromatic aberration (peak 22) + grain (peak 14) on a symmetric 4t(1-t) envelope, then snaps both back to baseline. Independent of `fadeToEra` (which still handles exposure/contrast/vignette) but called in parallel so an era flip looks like one motion. Chromatic aberration is now armed at attach time with `aberrationAmount = 0` so the burst can ramp without per-transition pipeline thrash.
- `witness-interactive-vite/src/interaction/InteractableHighlight.ts` *(new)* — Single `HighlightLayer` wrapper that pulses a low-alpha cream outline (matching the HUD palette) on the nearest proximate interactable. Driven by the same per-frame proximity probe in `bootstrap/main.ts` that sets the HUD prompt — at most one mesh is highlighted at a time. Slow sine pulse (period 2.6 s) so the outline reads as "this is worth approaching" without becoming a neon objective marker.
- `witness-interactive-vite/src/bootstrap/LedgerOpening.ts` *(new)* — Phase 1's closing cinematic. Choreographed promise: camera dolly + FOV tween to a reading pose (1.2 s) in parallel with the ledger lifting / rotating to face the camera; DOM modal fades in with "The ledger will tell you why he never came home. — Grandma, before she died."; player presses Space to dismiss; everything settles back over 1.4 s; `act_1_complete` is set; HUD toast nudges the player toward Act 2. Boundary-clean: imports `cameraDolly`/`fovTween`/`meshMove`/`meshRotate` from `core/`; no narrative writes beyond what the calling registration owns.
- `witness-interactive-vite/src/bootstrap/IntroSequence.ts` — `onFadeStart` now passes `{ reduceMotion }` so the bootstrap can snap the camera to spawn pose on `prefers-reduced-motion: reduce` (per OPENING_SEQUENCE.md §9). The `?skipIntro` path still fires the callback (treated as reduced-motion intent) so cinematic state always lands.
- `witness-interactive-vite/src/bootstrap/main.ts` —
  - Cinematic intro hand-off: camera spawns at an elevated wide pose (`(0, 4.2, -7)`, fov 1.28) hidden behind the DOM overlay; `onFadeStart` dollies it down to the player spawn pose (`(0, 1.65, -2)`, fov 1.05) over 2.4 s, landing as the overlay clears. Snap path for reduced-motion.
  - Phase 1 ledger pickup: `compound.ledgerBook` registered as an interactable that runs `runLedgerOpening(...)`. On success sets `act_1_complete`, autosaves, unregisters, and emits a ledger toast guiding the player into Act 2. The four Act 2 evidence anchors gained `requiredFlags: ["act_1_complete"]` so they don't surface a prompt until the ledger has been read.
  - `LEDGER_ENTRIES` gained an `act_1_complete` entry so the first page is captured in the Ledger overlay.
  - Echo pre-roll: every Memory Fragment's `onActivate` is now `async` and awaits a 0.55 s symmetric FOV pull (-0.04 in / +0.04 back) before calling `pastSceneController.begin(...)`. The world holds for a beat as the player "remembers."
  - Era transition wiring: `timeManager.subscribe(transitionStarted)` now fires `fadeToEra` + `memoryDissolve` + a half-duration FOV breath in parallel. Chromatic aberration + grain spike at midpoint; vision lens widens for the first half then settles — the era flip is a perceptible "moment of dissociation" per CHRONOS_SWITCH.md §3.6.
  - Proximity probe: also calls `interactableHighlight.setHovered(bestMesh | null)` per frame and clears the highlight on era transitions.

End-to-end this closes the mission's first part as a complete cinematic loop: page-load → satellite-descent intro → cinematic camera lands at the gate → walk to altar → ledger pickup choreography → Act 2 evidence anchors light up → echo pre-roll + studio-quality Past↔Present dissolve → echo dwell → return dissolve → ledger update. The 15-fragment Act 2 → Act 3 → Remembrance chain continues to validate (tools/validate_fragments.py exit 0) and `npm run build` completes with no TypeScript errors.

**Follow-ups:** Per-fragment mesh emissive flash at activation moment (currently only camera FOV moves); animated lighting envelope on era transition (sun direction tween, sky tint lerp); browser smoke test via Playwright covering the Phase 1 → Phase 4 loop; depth-of-field rack focus on memory dissolve (deferred — needs the depth buffer prepass cost to be measured on LOW profile first).

## 2026-05-16 — Ledger rehydration on resume + Play-again fresh-start fix
**Author:** @royceshannon2 (via Claude)
**Scope:** `bootstrap/main.ts`, `bootstrap/RemembranceSequence.ts`
**Files:**
- `witness-interactive-vite/src/bootstrap/main.ts` — Added `LEDGER_ENTRIES: Readonly<Record<string, string>>` constant mapping all 15 unlock flags to their display text. This is now the single source of truth: `recordEcho` looks up text from the map instead of receiving it as a parameter (signature simplified to `recordEcho(flag: string | undefined)`), and the `?resume=1` boot path iterates the map after `applyState()` to rehydrate the `LedgerStore` from restored flags. Changed `hud.setLedgerCount(0)` → `hud.setLedgerCount(ledgerStore.count())` so resumed sessions show the correct badge count immediately on HUD attach.
- `witness-interactive-vite/src/bootstrap/RemembranceSequence.ts` — Changed the "Play again" reload from `window.location.reload()` to `window.location.href = window.location.pathname`. `reload()` preserves the current URL including `?resume=1`, which would start a "fresh" game with the prior session's flags. Navigating to `pathname` strips all query params and guarantees a clean state.

Prior to this change, players who saved mid-session and reopened with `?resume=1` would have their narrative flags restored but find the Ledger overlay empty. Now the Ledger is populated from the flag set immediately — no re-collecting required. The rehydration path adds entries silently (before the `onChanged` listener is registered) so no HUD pulse fires; the indicator count is set correctly when the HUD is attached.

**Follow-ups:** Playwright smoke test for echo → save → close → `?resume=1` → ledger count correct. Audio wiring (replace `audioManager.playNarratorEntry()` stubs with Babylon `Sound` objects) remains the next functional feature.

## 2026-05-14 — Phase 1 asset addendum: per-asset image descriptions + style guide + Hunyuan runbook
**Author:** @royceshannon2 (via Claude)
**Scope:** prompts/asset-templates/ (new style guide + 15 reference-image sections + 15 README rewrites), tools/ (new runbook), docs/design-docs/PHASE1_ASSET_LIST.md (style-guide crosslink)
**Files:**
- `prompts/asset-templates/_STYLE_GUIDE.md` (new) — single-source style spec applied to every Phase 1 asset. Codifies the "Digital Diorama" rule (`memory/visual_style_digital_diorama.md`): tactile weathered realism, hyper-realistic PBR (Albedo + Normal + Roughness + AO), filmic desaturated palette, macro-friendly surface detail. Includes a reference-image specification table (≥ 1024², overcast ~5000 K, neutral background, no watermarks) and a per-material-family "what tactile looks like" matrix (mud brick / corrugated tin / hand-hewn wood / stone+mortar / cotton / leather / wax / skin).
- `prompts/asset-templates/<id>.md` × 15 — `## Style` block (links the style guide) + `## Reference image` block (describes exactly what the `ref.png` must depict: subject, angle, lighting, framing, materials emphasis, exclusions) appended to each template. The reference-image descriptions reflect the project's setting (rural Rwandan highlands 1994/2026), not the style memory's example imagery (which referenced 16th-century European materiality).
- `prompts/asset-templates/<id>/README.md` × 15 (rewrite) — replaced the generic dropoff-instruction READMEs with per-asset summaries that link to the template's `## Reference image` section + the style guide, plus the exact orchestrator one-liner for that id. The README is now a navigable shim, not a duplicate spec.
- `tools/HUNYUAN_RUNBOOK.md` (new) — operational runbook for booting the Hunyuan3D 2.1 container and running the orchestrator end-to-end. Eight sections: pre-flight, stale-container cleanup (the driver-bump failure we hit on 2026-05-13), foreground/detached/`start_api.sh` boot flavours, verification (`curl /docs`), single-asset + batch loop invocations, shutdown, eight-row troubleshooting table (driver mismatch, port conflict, OOM, raw-GLB missing, etc.), and a quick-reference card. The image's actual entry point (`python3 api_server.py` on port 8081 with `-v model_cache:/workspace/model_cache`) was confirmed by introspecting the image's `DOCKER_OVERVIEW.md` and `start_api.sh`.
- `docs/design-docs/PHASE1_ASSET_LIST.md` — added a "Visual style" front-matter line pointing at the new style guide; expanded the lede to note that each template now contains a `## Reference image` section.

**Technical summary:** This addendum closes the gap between "Phase 1 templates exist" and "Phase 1 templates are actionable by anyone who didn't write them." The earlier templates described the *object* but not the *photograph* that should serve as Hunyuan3D's input — leaving the reference-image step ambiguous. Each template now names the framing, angle, lighting, palette, and exclusions for its `ref.png`, plus a top-of-template style banner that pulls the cross-cutting Digital Diorama rule into the prompt's review surface (so an LLM-assisted reference-image generator sees the style in context).

The Hunyuan runbook was written against the actual image, not against memory. I introspected `kechiro/hunyuan3d-2.1-cachedstart:latest` to confirm the workspace structure, the `start_api.sh` defaults (port 8081, host 0.0.0.0, device cuda, model path `tencent/Hunyuan3D-2.1`), and the `DOCKER_OVERVIEW.md` quick-start. The runbook documents both the foreground and detached startup flavours, the cleanup procedure for stale containers (a real failure we hit when the host driver was bumped from 595.45.04 to 595.71.05 between the original container's creation and 2026-05-13), and a batch loop that walks `PHASE1_ASSET_LIST.md` skipping ids whose `ref.png` is not yet present.

The per-asset READMEs are no longer dead documentation. The first iteration was a generic "drop an image here, ≥ 1024²" boilerplate identical across 15 directories. The rewrite makes each README usable as a single-glance briefing for whoever drops the photo — they see the specific subject and framing for that asset's reference, not the generic dropoff specs.

**Verification:** `cd witness-interactive-vite && npx tsc --noEmit` → no errors (no runtime code changed in this addendum). `grep -l '## Reference image' prompts/asset-templates/*.md | wc -l` → 15. `grep -l '_STYLE_GUIDE.md' prompts/asset-templates/*/README.md | wc -l` → 15. `docker run --rm kechiro/hunyuan3d-2.1-cachedstart:latest cat /workspace/Hunyuan3D-2.1-CachedStart/start_api.sh | head -1` → confirms the script's shebang + start procedure documented in the runbook.

**Follow-ups:**
- (Unchanged from M11.) Reference images per id at `prompts/asset-templates/<id>/ref.png` are the blocker — every other step in `HUNYUAN_RUNBOOK.md` is mechanical once the photos land.
- Consider extending `tools/asset_pipeline.py` with a `--all` mode that reads `PHASE1_ASSET_LIST.md` and runs the loop in the runbook — saves one shell-loop authoring step per session.
- The style guide's per-material-family table is currently descriptive; a future pass could attach swatch images (one per family) for visual lookup.

## 2026-05-13 — Phase 1 asset pipeline kickoff: templates + scaffold TODOs (M11)
**Author:** @royceshannon2 (via Claude)
**Scope:** prompts/asset-templates/ (new), world/locations/FamilyCompound.ts, docs/design-docs/PHASE1_ASSET_LIST.md (new), infra (npm install)
**Files:**
- `prompts/asset-templates/<id>.md` × 15 (new) — one prompt template per Phase 1 asset, with the frontmatter schema from `ASSET_PIPELINE.md §3.1`: `asset_name`, `category`, `era_scope`, `reference_image`, `seed`, `inference_steps`, `target_poly_lod0`, plus `materials_runtime`, `collision`, and `notes` extensions where they clarify runtime intent. Bodies describe the object in neutral, PBR-bake-friendly terms (no violence, no militaria, no people in non-figure assets, neutral overcast 5000 K lighting). IDs split into structure × 7 (rugo_main_house, tin_roof, rugo_door, compound_gate, well_stone_ring, well_cover_plank, family_shrine_slab), vegetation × 3 (eucalyptus_mature, eucalyptus_sapling, elephant_grass), prop × 3 (ledger_book, altar_photo_frame, altar_candle), figure × 2 (investigator_hands, grandfather_hands).
- `prompts/asset-templates/<id>/` × 15 (new) — per-asset reference-image dropoff directories, each with a `README.md` that documents the expected `ref.png` specs (≥ 1024² neutral background) and the exact one-line orchestrator invocation.
- `witness-interactive-vite/src/world/locations/FamilyCompound.ts` — three classes of edit: (1) file-header docstring expanded with an "Asset Pipeline Swap Manifest" block that names the swap pattern (primitive `mk*` → `assetLibrary.instantiate("<id>")`); (2) inline `// TODO(asset-pipeline): <id>` comments added at every primitive cluster head, naming exactly the canonical asset id from `prompts/asset-templates/`; (3) new `ledgerBook` placeholder added on top of the altar slab (per `OPENING_SEQUENCE.md §6` — the ledger is the first interactable at first-frame composition, previously missing from the scaffold). `FamilyCompoundHandle.ledgerBook: AbstractMesh` exposed so bootstrap can wire interactability in a future M12.
- `docs/design-docs/PHASE1_ASSET_LIST.md` (new) — itemised catalogue of the 15 Phase 1 assets with status tracking (`template ✓ · ref ✗ · glb ✗`), per-asset orchestrator-invocation recipe, and an explicit "out of scope" section enumerating the Act 2 / Act 3 anchor props at the compound that stay as primitives until the Phase 1 catalogue is complete.

**Technical summary:** This entry kicks off the long-running asset production pass. The runtime scaffold has carried primitives since the vertical-slice M3 work; per `.claude/rules/asset-pipeline.md §5`, primitives are tolerated only when annotated with an asset-id TODO. The pre-existing primitives carried no such annotation, which left readers unable to tell which boxes were intentional design choices vs. placeholders. The 15 TODO comments now mechanically bind each primitive to its replacement spec — the swap is one find-and-replace away once a GLB lands.

The prompt templates are the canonical input to the orchestrator (`tools/asset_pipeline.py`). They are authored *before* reference images on purpose: reference photos are cheap to collect (Pexels / Unsplash / archival) and easy to swap, but the prompt body and target poly budget are the design decisions that survive multiple reference-image iterations. With the prompt body fixed, an iteration only changes the reference image, not the entire template.

The ledger placeholder was added because the existing `FamilyCompound.ts` scaffold was *visually* complete but *narratively* incomplete — `OPENING_SEQUENCE.md §6` mandates the ledger be visible at first-frame composition on the altar slab, but the scaffold had no mesh there. The added `mkBox` is a faithful primitive (centred on the slab top, slightly skewed toward the spawn camera) that the `prop_ledger_book` GLB will replace cleanly.

Infra: `gltf-pipeline` and `gltf-transform` installed to `~/.npm-global/bin/` (user-prefix, no sudo). KTX-Software (`toktx`) deferred — available in AUR as `ktx-software-bin`; the optimize stage tolerates its absence with a warning. Hunyuan3D container deferred — the image's CMD is `/bin/bash` and expects manual interactive startup; the FastAPI server start procedure is documented in `PHASE1_ASSET_LIST.md` for when reference images land.

**Verification:** `cd witness-interactive-vite && npx tsc --noEmit` → no errors. `ls prompts/asset-templates/*.md` → 15 files. `ls prompts/asset-templates/*/README.md` → 15 dropoff dirs. `grep -c 'TODO(asset-pipeline)' witness-interactive-vite/src/world/locations/FamilyCompound.ts` → 15 occurrences (one per asset id, plus the file-header reference). Visual smoke: opening `?skipIntro=1` still produces the existing compound scaffold (the new ledger primitive is a 21 × 3 × 15 cm dark-brown box on the altar slab, visible at spawn).

**Follow-ups:**
- Collect reference photographs for all 15 ids and drop them at `prompts/asset-templates/<id>/ref.png`. Sources should be neutral-background, single-subject, ≥ 1024². Recommended channels: Pexels (`eucalyptus tree`, `corrugated tin roof`, `mud brick wall`), Unsplash (`well stone`, `wooden gate rural`), Wikimedia Commons (rural Rwanda architecture under CC-BY). Hands references can be neutral 3D-model preview shots or DALL·E generations.
- Boot Hunyuan: `docker run -it --rm --gpus all -p 8081:8080 kechiro/hunyuan3d-2.1-cachedstart:latest` then start the FastAPI server inside the container (consult image's internal README for the exact `python -m ...` command). Verify with `curl http://localhost:8081/docs`.
- Install `paru -S ktx-software-bin` for KTX2 texture compression. Run the orchestrator without it first if needed — `optimize_asset.py` warns and skips KTX2 cleanly.
- After each successful pipeline run, swap the matching `TODO(asset-pipeline): <id>` block in `FamilyCompound.ts` to use `assetLibrary.instantiate("<id>")`. Tick the row in `PHASE1_ASSET_LIST.md`.
- Wire the FP-hands rig (M12+): both `figure_*_hands` ids are kind=`animated`; the orchestrator's `--kind animated` branch produces a geometry-only GLB and prints a reminder that the Blender pass for skeleton + AnimationGroups is still required. The rig spec is in each template's `notes:` block.

## 2026-05-13 — Ledger reading system + autosave (M10)
**Author:** @royceshannon2 (via Claude)
**Scope:** narrative (new LedgerStore), ui (LedgerUI rewrite, HUD badge), bootstrap (keyboard wiring, autosave), ARCHITECTURE.md
**Files:**
- `witness-interactive-vite/src/narrative/LedgerStore.ts` (new) — in-memory ordered store of `LedgerEntry { key, text, unlockedAt }`. Idempotent `add(key, text)` so double-fires from any fragment are silently skipped. `onChanged(fn)` subscriber pattern wired to the HUD badge. `clear()` for New Game+ (session already resets via `window.location.reload()` so clear is a safety net for future in-page reset). Intentionally separate from `StateManager` — ledger entries are display artefacts derived from narrative flags, not authoritative state.
- `witness-interactive-vite/src/ui/LedgerUI.ts` (rewrite) — replaced the Babylon GUI `AdvancedDynamicTexture` prototype with a DOM overlay consistent with `ChoiceOverlay`, `IntroSequence`, and `RemembranceSequence`. Layout: dark semi-opaque field, serif documentary register, header ("The Shepherd's Ledger"), entry count sub-label, entries newest-first with 1-px warm separator lines, "Close [J]" button. The HUD toast prefix "Ledger entry unlocked: " is stripped in the ledger view so the text reads as a clean journal entry rather than a notification copy. `toggle(entries)` is the primary call from the keyboard handler.
- `witness-interactive-vite/src/ui/HUD.ts` — `setLedgerCount(count: number)` added. Lazy-creates a bottom-right `TextBlock` ("Ledger  [J]  N") on first call, so the indicator is zero-cost when HUD is not attached. On count increase: alpha → 1.0 for 2 s (pulse), then settles at 0.45. Three new private fields: `ledgerIndicator`, `ledgerPulseTimer`, `ledgerCount`. Three constants added at module level: `LEDGER_INDICATOR_IDLE_ALPHA`, `LEDGER_INDICATOR_PULSE_ALPHA`, `LEDGER_PULSE_DURATION_MS`. `detach()` updated to clear the pulse timer and null the indicator reference.
- `witness-interactive-vite/src/bootstrap/main.ts` — (1) Added imports: `ledgerUI` from `../ui`, `ledgerStore` from `../narrative/LedgerStore`, `save`/`load`/`applyState` from `../io/SaveSystem`. (2) `recordEcho(flag, text)` helper: calls `ledgerStore.add`, `hud.showLedgerToast`, `save("autosave", "witness")` — all 15 `onReturnToPresent` callbacks now call `recordEcho` instead of `hud.showLedgerToast` directly, eliminating the risk that a future callback adds a toast but forgets the ledger or autosave. (3) `ledgerStore.onChanged(() => hud.setLedgerCount(ledgerStore.count()))` + `hud.setLedgerCount(0)` initialiser. (4) `keydown` handler: J-key toggle (blocked in Past era or during transition), F5 manual save (toast "Session saved."), F9 manual restore (toast + log). (5) `?resume=1` URL param applied before intro + engine init so narrative flags are live during world construction — the blob is applied, then the world is built with the restored flag state.
- `ARCHITECTURE.md` — module-status callout rewritten for M10. Last-updated bumped to 2026-05-13.

**Technical summary:** M10 closes the player-facing narrative read loop. Before this change, each echo completion showed a 5 s toast that then vanished — there was no way to re-read what had been collected. `LedgerStore` accumulates entries keyed by flag (so duplicate fires are structurally impossible), and `LedgerUI` renders them in a clean DOM overlay the player can open at any time with `J`. The choice to rewrite `LedgerUI` from Babylon GUI to DOM was straightforward: the three existing full-screen modals (`IntroSequence`, `ChoiceOverlay`, `RemembranceSequence`) are all DOM-based for exactly the same reason — managing interaction-mode coupling between a Babylon `AdvancedDynamicTexture` and the gameplay camera is unnecessary complexity for a full-screen text block. Consistency here also means a single visual register (dark semi-opaque, serif, warm cream) applies across all four overlays without duplicating GUI style sheets.

The `recordEcho` helper is a justified abstraction at 15 callsites: it co-locates three responsibilities (display, persistence, collection) that must always fire together, while keeping each responsibility in its own module. A missed `save()` call on any single fragment callback would silently break autosave for that fragment — the helper removes that class of bug permanently. The autosave is written after every echo completion, so the maximum state loss on unexpected closure is one unsaved echo.

`?resume=1` is the correct UX for resume (not auto-resume on every page load) because auto-resume would break `?skipIntro=1` dev flows and any future "new game" flow that intentionally clears state. The player (or a future "Continue" button) opts in explicitly.

**Verification:** `python3 tools/validate_fragments.py` → 15 fragments / 15 bindings, exit 0. `cd witness-interactive-vite && npm run build` → tsc + vite, no TypeScript errors, builds in ~730 ms. Manual smoke: `?skipIntro=1` → trigger cellar echo → J key opens ledger showing "Bisesero, April 1994 — the cellar held nine." → close → F5 saves → F9 restores → HUD bottom-right shows "Ledger  [J]  1" pulsed to full alpha, settles at 0.45.

**Follow-ups:**
- Add `?resume=1` to the "Play again" button's `window.location.reload()` in `RemembranceSequence` — currently New Game+ always starts fresh; a "Continue where you left off" path is desirable for Act 3+ replays.
- Rehydrate `LedgerStore` from the saved flag set on `?resume=1` so the ledger is populated on load, not empty. Requires a `LEDGER_ENTRIES` map keyed by `unlocksFlag` → text (the 15 strings already exist in main.ts; extract to a constant).
- Replace `hud.showLedgerToast("Session restored. Reload the page to apply.", ...)` with an in-place state rebuild — F9 currently requires a page reload to take effect because the 3D world was built with the pre-restore flag state. Full in-place restore requires rebuilding the proximity target activations from the restored flag set.
- Add Playwright integration test: trigger cellar echo → assert `ledgerStore.count() === 1` → assert J-key opens overlay containing the correct text → close → assert F5 autosave writes to localStorage → F9 restore reports correct slot.

## 2026-05-13 — Act 4 Remembrance + path completion loop (MISSION_BLUEPRINT.md §5, M8)
**Author:** @royceshannon2 (via Claude)
**Scope:** bootstrap (new RemembranceSequence), narrative graph (act_4_remembrance fix), main.ts (path checkers + build fix), ARCHITECTURE.md
**Files:**
- `witness-interactive-vite/src/bootstrap/RemembranceSequence.ts` (new) — two-phase Act 4 DOM overlay per MISSION_BLUEPRINT §5. Phase 1 shows the path-specific climactic ledger entry (9 s auto-advance or any keypress). Phase 2 presents four non-branching reflection options: place ledger on shrine / leave a note / photograph / sit in silence. After a selection, the closing voice-over ("Your grandfather made a choice…") is shown for 4 s, then the overlay fades and resolves with a `MemorializationKey`. The caller (`main.ts`) sets `game_complete` + `memorialization_complete` on `globalState`. Same DOM-only, full-bleed pattern as `ChoiceOverlay` and `IntroSequence` — no Babylon GUI dependency.
- `witness-interactive-vite/src/bootstrap/main.ts` — three changes: (1) import `showRemembranceSequence`; (2) new `makePathChecker(path, puzzleFlags)` factory producing a one-shot closure that checks all `puzzleFlags` are set, sets `path_*_complete`, shows a HUD toast, then presents `RemembranceSequence`; (3) path checkers wired into `onReturnToPresent` of the terminal puzzle per path: `neighbor_letter` → `checkPathA()`, `survivor_letter` → `checkPathB()`, `visitor_account` → `checkPathC()`. Also: six U+201C/U+201D smart-quote characters used as string delimiters (a pre-existing M7 bug) replaced with ASCII `"` — the build was silently broken on those lines.
- `witness-interactive-vite/src/narrative/Graph.json` — `act_4_remembrance.requiredFlags` corrected from `["path_a_complete","path_b_complete","path_c_complete"]` to `[]`. The original required all three paths to be complete simultaneously, which is unreachable in a single playthrough. Act 4 is reached via `next` edges from each `act_3{a,b,c}_ending` node; the `requiredFlags` field was documentation-drift, not routing.
- `ARCHITECTURE.md` — module-status callout rewritten for M8. Last-updated bumped to 2026-05-13.

**Technical summary:** M8 closes the full narrative game loop: the player can now complete any one of the three Act 3 paths and reach Act 4 Remembrance. The three `makePathChecker` closures are structurally identical to `makeChoiceChecker()` — each is a one-shot fired from the last puzzle of its path, guarded by `fired` to prevent double-invocation even if the player somehow re-triggers a fragment after all flags are set. `RemembranceSequence` phases: (1) climactic quote block held 9 s to give the player time to absorb it without forcing them to rush; (2) four reflection options in the same serif / documentary visual register as `ChoiceOverlay`; (3) closing voice for 4 s; overlay fades. The choice of reflection option is non-branching — all four set the same `memorialization_complete` flag. The distinction is logged for future analytics but carries no narrative weight.

The `Graph.json` fix addresses a conceptual error from the initial DAG authoring: `act_4_remembrance` was annotated as if the game required experiencing all three paths, which conflicts with MISSION_BLUEPRINT §8's "intended for single session" and §3 ("No rewind. The choice is locked"). The routing is correct (each ending's `next` array already pointed to `act_4_remembrance`); only the `requiredFlags` was wrong.

**Verification:** `python3 tools/validate_fragments.py` → 15 fragments / 15 bindings, exit 0. `cd witness-interactive-vite && npm run build` → tsc + vite, no TypeScript errors, no new warnings. Manual smoke path: start dev server, skip intro, complete all four Act 2 echoes, choose a path in `ChoiceOverlay`, complete all puzzles for that path, on the last echo's return the HUD toast "The ledger reveals its final page" appears, then `RemembranceSequence` fades in with the path-appropriate quote, advances to reflection options, shows closing voice, fades out.

**Follow-ups:**
- Add Playwright integration test: trigger all four Act 2 echoes → assert ChoiceOverlay → click path → trigger all path puzzles → assert RemembranceSequence Phase 1 text matches path → click reflection option → assert `game_complete` and `memorialization_complete` set.
- Replace HUD toast + timed overlay with a proper "return to compound" proximity trigger: add a shrine anchor to `FamilyCompound` that only activates when `path_*_complete` is set, so the player physically walks back to the shrine before Act 4 begins.
- Extend `PastSceneController` to support `returnTrigger: { kind: "interaction" }` so Act 3 echoes can end on a player action (placing bread, lashing the paddle) rather than a timer — already flagged in M7 follow-ups.
- Wire `act_4_conclusion` node fully: currently `game_complete` is set by the closure in `main.ts`, but `NarrativeController` is never informed. Connect `narrativeController.triggerBranchChoice("act_4_conclusion")` so the save system and any future UI subscriptions see the completed state.
- New Game+ support: after `game_complete`, offer a "Begin again" prompt that resets all flags except `game_complete` and `memorialization_complete`, allowing the player to replay and choose a different path.

## 2026-05-12 — Act 3 path fragments + choice overlay (CHRONOS_SWITCH.md §8 M7)
**Author:** @royceshannon2 (via Claude)
**Scope:** bootstrap (new ChoiceOverlay), world/locations (3 handle extensions), narrative graph, ARCHITECTURE.md
**Files:**
- `witness-interactive-vite/src/bootstrap/ChoiceOverlay.ts` (new) — DOM overlay for the Act 3 path-selection prompt per MISSION_BLUEPRINT.md §3. Presents three text blocks ("He hid people / helped them escape / stayed neutral") in the documentary/memorial register. Fades in over the live 3D scene; one click resolves a `Promise<string>` with the chosen path flag. No Babylon GUI dependency — pure DOM so it blocks all 3D input cleanly. Designed with the same `ui-serif` palette as `IntroSequence.ts`.
- `witness-interactive-vite/src/world/locations/FamilyCompound.ts` — `FamilyCompoundHandle` extended with five new Act 3 anchor meshes: `cellarMats` (act_3a_puzzle_1), `waterSchedule` (act_3a_puzzle_2), `neighborLetter` (act_3a_puzzle_3), `survivorLetter` (act_3b_puzzle_4), `visitorAccount` (act_3c_puzzle_4). All five are `present`-tagged — the echo always presents the 1994 moment regardless of when the physical object existed.
- `witness-interactive-vite/src/world/locations/LakeShore.ts` — `LakeShoreHandle` extended with three Act 3B anchor meshes: `passengerList` (act_3b_puzzle_1), `boatCapacityBoard` (act_3b_puzzle_2), `escapeRouteMap` (act_3b_puzzle_3). All `present`-tagged.
- `witness-interactive-vite/src/world/locations/Ravine.ts` — `RavineHandle` extended with three Act 3C anchor meshes: `chalkPatrolMarks` (act_3c_puzzle_1), `checkpointRecords` (act_3c_puzzle_2), `reflectionLetters` (act_3c_puzzle_3). All `present`-tagged.
- `witness-interactive-vite/src/narrative/Graph.json` — `fragmentId` added to all eleven Act 3 puzzle nodes: `act_3a_puzzle_{1,2,3}`, `act_3b_puzzle_{1,2,3,4}`, `act_3c_puzzle_{1,2,3,4}`. Validator now reports 15 fragments / 15 bindings, exit 0.
- `witness-interactive-vite/src/bootstrap/main.ts` — full rewrite of fragment registration. Added `makeChoiceChecker()` — a closure that watches the four Act 2 evidence flags and fires the `ChoiceOverlay` exactly once when all four are set, then sets the chosen path flag + the corresponding `path_*_started` flag. Registered eleven new `MemoryFragment`s with `PastSceneSpec`s. Extended `ProximityTarget` with `requiredFlags?: string[]`; the per-frame probe skips a fragment if any required flag is unset (path gate + puzzle chain gate). Act 3A dwell times: 16/14/12 s. Act 3B: 16/14/16/10 s. Act 3C: 20/18/20/12 s (longer dwells for the quiet-observation path per CHRONOS_SWITCH §5.2 guidance). Observer path echoes use `setPerspective("hidden")` on enter and `setPerspective("investigator")` on return, consistent with M4.
- `ARCHITECTURE.md` — module-status callout rewritten for M7 (15 fragments, choice overlay, requiredFlags gate, handle extensions). Last-updated bumped to 2026-05-12.

**Technical summary:** M7 closes the Act 3 authoring layer. The player can now walk all four Act 2 evidence anchors in any order; when the last echo resolves, `makeChoiceChecker()` detects `all_evidence_found`, sets the flag, and presents the `ChoiceOverlay`. The player commits to one of three paths; the overlay fades, the path flag is set, and the `path_*_started` flag is immediately live. From that point forward, the proximity probe gates Act 3 fragments by `requiredFlags` — a player on the Hider path sees only the three Hider anchors, sequenced by `puzzle_a{1,2,3}_complete`. The fifteen-fragment runtime satisfies CHRONOS_SWITCH §8 M7 exactly as specified: "Per-path Fragment set. ~4 fragments per path × 3 paths." The actual count is 3 + 4 + 4 = 11 Act 3 fragments + the 4 Act 2 anchors that were already wired.

The `ChoiceOverlay` is intentionally free of Babylon GUI. Rendering a HUD-layer modal via `AdvancedDynamicTexture` would require managing the ortho camera's interaction mode; a full-screen DOM overlay at z-index 1000 achieves the same result without coupling to the render pipeline. The same pattern is used by `IntroSequence.ts` — both are transient, full-bleed DOM events that wrap the 3D scene.

The helpers-hoist threshold was not crossed: all eleven new anchor meshes were added to the three existing location modules (`FamilyCompound`, `LakeShore`, `Ravine`). A fourth location module (e.g., Heights or Heights vantage) would be the trigger — not reached in M7.

The `makeChoiceChecker()` factory avoids a module-level `let choiceShown = false` mutable in favour of a closure that travels with the check function. This is important because the check is called from four separate `onReturnToPresent` callbacks — a module-level flag would work too, but the factory makes the one-shot guarantee co-located with the function that owns it.

**Verification:** `python3 tools/validate_fragments.py` reports 15 fragments / 15 bindings, exit 0. `cd witness-interactive-vite && npm run build` completes in 808 ms (tsc + vite), no TypeScript errors, no new warnings. Manual smoke-test path for choice overlay: `npm run dev → ?skipIntro=1` → trigger all four Act 2 echoes in any order → on the fourth return the `ChoiceOverlay` fades in → click a path → toast appears → Act 3 anchor prompts for the chosen path become active when the player approaches the first anchor.

**Follow-ups:**
- Add Playwright integration test: load page, skip intro, trigger all four Act 2 fragments, assert `ChoiceOverlay` appears, click one path, assert path flag set, assert Act 3 puzzle 1 prompt appears near the first anchor, trigger it, assert `puzzle_{a,b,c}1_complete`.
- Extend `PastSceneController` to accept `returnTrigger: { kind: "interaction", meshName: string }` — the four Act 3A echoes most naturally end when the player performs an action (placing bread, lashing the paddle), not on a timer. Wire one fragment per path to use interaction-driven return before M8.
- Add the Act 3 reflection and ending nodes (`act_3{a,b,c}_reflection`, `act_3{a,b,c}_ending`) as runtime events: once all puzzle flags for a path are set, a ledger toast should prompt the player to return to the compound for the reflection scene. These nodes currently exist only in `Graph.json`.
- Hoist `mkBox` / `mkCyl` / `deriveMat` into `world/_primitives.ts` when a fourth location module is authored (M8 or beyond).
- Wire `act_4_remembrance` — all three path completion flags (`path_{a,b,c}_complete`) trigger a shared ending sequence back at the Family Compound.

## 2026-05-09 — Asset pipeline wired: orchestrator + splat/tileset runtime + normative rule
**Author:** @royceshannon2 (via Claude)
**Scope:** tools/ (orchestrator), .claude/rules/ (new rule), witness-interactive-vite/src/io/ (splat + tileset libraries), CLAUDE.md
**Files:**
- `.claude/rules/asset-pipeline.md` (new) — normative rule mandating `tools/asset_pipeline.py` as the single entry point for any 3D asset (mesh / splat / tileset / navmesh / nme / animated). Includes the decision tree, naming/registration rules, and a pre-flight checklist. Cross-links the existing `babylon-patterns.md` and `documentation-standards.md` rules.
- `tools/asset_pipeline.py` (new, executable) — single entry-point orchestrator. Dispatches on `--kind` to one of six branches: `mesh` calls the existing `generate_asset.py` → `optimize_asset.py` → `register_asset.py` chain and promotes the `.optimized.glb` to the canonical `<id>.glb`; `animated` does the mesh chain plus a Blender skeletal-rig pass (TBD); `splat` ingests `.ply`/`.splat`/`.spz`/`.sog` captures; `tileset` writes a `<id>.tileset.json` record; `navmesh` writes a `<id>.navmesh.json` record with default Recast parameters; `nme` registers a Node Material Editor JSON snapshot. Every branch ends with the asset copied into `witness-interactive-vite/public/assets/` and a row appended to `docs/asset-index.md`.
- `witness-interactive-vite/src/io/SplatLibrary.ts` (new) — runtime owner for Gaussian splats. Imports the Babylon SPLAT loader plugin (`@babylonjs/loaders/SPLAT/splatFileLoader`) once at module load. Exposes `load(id, { flipY? })` that resolves an id → URL via an injectable resolver, calls `ImportMeshAsync` with the splat plugin options, caches by id, and surfaces a `dispose()` per-asset and a bulk `dispose(ids?)`. Throws on plugin failure rather than falling back silently — splats are usually hero assets.
- `witness-interactive-vite/src/io/TilesetMount.ts` (new) — runtime owner for 3D Tilesets. Reads the `<id>.tileset.json` record produced by the pipeline, then dynamically imports the local adapter `_3dTilesAdapter.ts`. The adapter hands off to `3d-tiles-renderer` (npm) when present and throws an install-hint error otherwise, so the engine doesn't fail to start when no mission needs tilesets. Tracks mounted tilesets in a Map for `detachAll()` on mission unload.
- `witness-interactive-vite/src/io/_3dTilesAdapter.ts` (new) — stub adapter that throws with an install hint. To wire 3D Tiles in production: `npm install 3d-tiles-renderer` and replace the throw with the actual `attach(scene, rootUrl) → TransformNode` calls. Kept in a separate file so the dynamic import in `TilesetMount` can fail closed when the package is absent.
- `witness-interactive-vite/src/io/index.ts` — barrel re-exports `SplatLibrary`, `SPLAT_EXTENSIONS`, `TilesetMount`, and the related types alongside the existing `AssetLibrary` and `SaveSystem` exports. Header docstring updated to name the three runtime owners + their pipeline kinds.
- `CLAUDE.md` — Asset Pipeline section rewritten to lead with the single-entry-point command, list the six kinds and their runtime owners, and crosslink the new normative rule. Splats / 3D Tiles / nav-meshes / NME shaders are first-class kinds, not sidebars.

**Technical summary:** This change closes the "is the Hunyuan pipeline actually wired?" question by making one command — `python tools/asset_pipeline.py <id> --kind <k>` — the only sanctioned path to add an asset, and by giving the runtime three explicit owners that map 1:1 to the pipeline's output kinds. Per the rule's §5, inline `MeshBuilder.CreateBox` for visible content now requires a `// TODO(asset-pipeline)` comment naming the asset id that will replace it; this preserves the vertical-slice prototype's right to ship primitives while making the migration path traceable.

The orchestrator composes the existing leaf scripts rather than replacing them — `generate_asset.py`, `optimize_asset.py`, `register_asset.py`, `export_babylon.py`, `generate_scene.py` continue to be the iteration tools. Smoke-tested the `tileset` branch end-to-end (`python3 tools/asset_pipeline.py test_smoke_id --kind tileset --root https://example.com/tileset.json`); the artefact, the public copy, and the `asset-index.md` row all land in the correct places. The `mesh` branch was not run end-to-end here because Hunyuan3D is a long-running Docker job, but the chain compiles and matches `generate_asset.py`'s existing CLI exactly.

The runtime side is intentionally surgical: `AssetLibrary` is unchanged (already the single owner of `LoadAssetContainerAsync`); `SplatLibrary` and `TilesetMount` are new sibling modules with the same shape (id → URL resolver, cache by id, explicit `dispose`). The 3D Tiles dependency is genuinely optional — most missions won't use streamed geospatial data — so the dynamic-import + adapter-stub pattern keeps the bundle clean and the build green when `3d-tiles-renderer` isn't installed. `npm install 3d-tiles-renderer` plus an edit to `_3dTilesAdapter.ts` are the only steps to flip tilesets from "registered" to "mounting at runtime."

`SplatLibrary` uses Babylon's native splat plugin verified against `docs/reference/babylon.js-documentation/content/features/featuresDeepDive/importers/gaussianSplatting.md` and `.../mesh/gaussianSplatting.md`. The static import `import "@babylonjs/loaders/SPLAT/splatFileLoader"` is the v9 idiom (the alternative `<script src="...">` form noted in the docs is reserved for non-bundled pages and is forbidden by §5 of the new rule).

**Verification:** `cd witness-interactive-vite && npx tsc --noEmit` passes (no TypeScript errors after the adapter stub). `python3 tools/asset_pipeline.py --help` lists every kind with usage examples. The tileset smoke run wrote `processed/tilesets/test_smoke_id.tileset.json`, copied it to `public/assets/`, and appended an index row — all three confirmed before cleanup. The `mesh`, `animated`, `splat`, `navmesh`, `nme` branches were inspected for argument validation but not executed end-to-end (Hunyuan, Blender, Recast, real splat captures all require live infrastructure).

**Follow-ups:**
- Implement `tools/generate_lods.py` (Blender headless decimate) and `tools/generate_collision.py` (V-HACD CLI) to unblock the LOD0/1/2 + collision steps in the `mesh` branch — currently logged as placeholders.
- Implement `tools/blender_animate.py` for the `animated` branch's skeletal-rig export. Today the branch reuses the mesh chain but does not embed `AnimationGroup` data in the GLB.
- Replace `_3dTilesAdapter.ts` stub with a real adapter once a tileset is needed by a mission. Pin the `3d-tiles-renderer` version in `package.json` at that point.
- Build `engine/Navigation.ts` that consumes `processed/navmeshes/<id>.navmesh.json` at scene init: instantiate `RecastJSPlugin`, call `createNavMesh(sources, parameters)`, optionally serialise the result with `getNavmeshData()` so cold loads can skip the recompute.
- Extend `MaterialLibrary` to load NME JSON snapshots registered by the `nme` branch (`MaterialLibrary.loadNode(id)` returns a `NodeMaterial`).
- Replace the Family Compound + LakeShore + Ravine primitives with real Hunyuan-generated GLBs registered via the orchestrator. Each `// TODO(asset-pipeline): replace with <id>` comment becomes one orchestrator run.

---

## 2026-05-09 — Full Act 2 evidence anchors: lake + altar fragments (CHRONOS_SWITCH.md §8 M6)
**Author:** @royceshannon2 (via Claude)
**Scope:** world/locations (new + extended), bootstrap, narrative graph, ARCHITECTURE.md
**Files:**
- `witness-interactive-vite/src/world/locations/LakeShore.ts` (new) — third canonical location per WORLD.md §"The Lake Shore" + MISSION_BLUEPRINT.md §2 (boat-paddle anchor). Water plane + dock planks + pilings + landward bench are `shared` (the geology persists across eras); only the boat hull, paddle wood-tone, jerrycans, crates, and fishing net differ. `LAKE_DOCK_POSITION = (-25, 0.4, 18)` so the player walks west-north-west from the gate without leaving the 80 m terrain block. Same `mkBox` / `mkCyl` / `deriveMat` primitives helpers as `FamilyCompound.ts` and `Ravine.ts` (intentionally duplicated — three call sites is still under the 2026-05-09 vertical-slice memo's hoist-into-`world/_primitives.ts` threshold of four).
- `witness-interactive-vite/src/world/locations/FamilyCompound.ts` — extended with the household altar in both eras: 2026 has a cracked concrete slab with a fallen wooden frame and faded photograph; 1994 has the same slab clean, the frame upright with photo visible, and a candle stub beside it. The 2026 frame is the new `familyRecords` anchor exposed on `FamilyCompoundHandle`.
- `witness-interactive-vite/src/world/locations/index.ts`, `witness-interactive-vite/src/world/index.ts` — barrels re-export `buildLakeShore`, `LakeShoreHandle`, `LAKE_DOCK_POSITION`.
- `witness-interactive-vite/src/bootstrap/main.ts` — register two more `MemoryFragment`s. (a) `boat_paddle` bound to `lakeShore.boatPaddle`, Protector dwell (no perspective flip), 14 s, `unlocksFlag = "found_boat_evidence"`, `pastChangeKey = "boat_paddle_witnessed"`; matches `Graph.json#act_2_evidence_lake`. Narrator key `lake_echo_intro`. (b) `family_records` bound to `compound.familyRecords`, Protector dwell, 10 s (the quietest of the four — an inventory of names, not a scene of action), `unlocksFlag = "found_family_records"`, `pastChangeKey = "family_records_witnessed"`; matches `Graph.json#act_2_evidence_compound`. Narrator key `altar_echo_intro`. Both fragments are pushed into the existing `proximityTargets[]` array — no second observer; the batched per-frame scan still runs once with closest-wins selection. Header docstring updated to list M3 → M6.
- `witness-interactive-vite/src/narrative/Graph.json` — added `"fragmentId": "boat_paddle"` to `act_2_evidence_lake` and `"fragmentId": "family_records"` to `act_2_evidence_compound`. Both nodes already declared the matching evidence flag in `unlocksFlags`, so this is a metadata add, not a flag rewire. The existing `act_2_check_all_evidence` requires all four (`found_cellar_evidence` + `found_boat_evidence` + `found_observer_evidence` + `found_family_records`) → with M6, every requirement to advance Act 2 has a diegetic source.
- `ARCHITECTURE.md` — module-status callout rewritten for M6 (lists all four fragments + their dwell modes + that timer returns are used; flags `interaction`-return as deferred). §5.4 entry rewritten to describe `buildLakeShore`, the LakeShore handle, and the duplicate-helpers stance with the four-location threshold.

**Technical summary:** This is the M6 milestone — "Full Act 2 fragments. All four evidence anchors wired." With this change the four narrative branches in Act 2 (`act_2_evidence_cellar`, `act_2_evidence_lake`, `act_2_evidence_ravine`, `act_2_evidence_compound`) all have working diegetic triggers and the convergence node (`act_2_check_all_evidence`) is reachable end-to-end from anchor activation alone — the player can in principle walk all four in any order, trigger each echo, and unlock the path-choice branch at `act_3_the_choice`. Two of the four fragments share the Family Compound location (cellar latch + altar) — they sit on the existing handle without a new module, demonstrating that "anchor count per location" can scale freely as long as the handle exposes named anchor meshes.

The two new fragments use Protector dwell with timer returns (14 s and 10 s respectively). The CHRONOS_SWITCH §5.1 spec describes the Protector return-trigger as typically `"puzzle"` — performing a specific action like placing an item or giving water — but `PastSceneController` only supports timer returns today. Extending the controller to accept an interaction-driven `whenReturn` predicate is a discrete piece of work (a new spec field, a registration callback, and at least one mesh-bound interaction inside the Past scene to release it). It's not in M6's scope, which is "all four anchors wired"; the four work, the dwells just resolve on time. Captured as a follow-up.

The validator catches the cross-checks: 4 fragments / 4 bindings, all paired, exit 0. The `family_records` graph node has only `["found_family_records"]` in its `unlocksFlags` (no `evidence_*_path` cross-flag), which is correct — the family-records evidence is path-neutral and confirms the family inventory rather than nominating a moral path. The other three each contribute one `evidence_*_path` cross-flag toward `act_3_the_choice`'s readout.

The LakeShore module is the third location and the helpers are still inlined per the 2026-05-09 memo; if a fourth location lands and `mkBox` / `mkCyl` / `deriveMat` still agree across all four, that is the time to lift them into `world/_primitives.ts`. The Lake Shore layout uses the existing `mat_water_lake` (which has been sitting unused in the MaterialLibrary since the early scaffold) — first user.

**Verification:** `python3 tools/validate_fragments.py` reports 4 fragments (`boat_paddle` → `found_boat_evidence` at bootstrap/main.ts:197; `cellar_door_latch` → `found_cellar_evidence` at bootstrap/main.ts:129; `family_records` → `found_family_records` at bootstrap/main.ts:233; `observer_notes` → `found_observer_evidence` at bootstrap/main.ts:159) and 4 bindings (act_2_evidence_lake, act_2_evidence_cellar, act_2_evidence_compound, act_2_evidence_ravine) with exit 0. `cd witness-interactive-vite && npm run build` (tsc + vite) succeeds in 757 ms. No TypeScript errors. Pre-existing chunk-size warnings from Babylon.js bundling are unchanged. Manual smoke-test path: `npm run dev` → `?skipIntro=1` → walk forward to cellar latch (M3), walk east ~22 m to ravine (M4), walk back and left to lake shore at (-25, _, +18) (M6 boat paddle), walk back to compound and approach the altar at (-1.85, _, +3.5) (M6 family records). Each anchor's prompt is unique ("Press E to remember / read / lift / look") so the player can't confuse them.

**Follow-ups:**
- Extend `PastSceneController` to accept an `interaction`-driven return: a new `returnTrigger?: { kind: "timer", seconds: number } | { kind: "interaction", meshName: string }` discriminated union on `PastSceneSpec`, with the controller registering a one-shot interactable-handler when `kind === "interaction"`. Wire one fragment (the boat-loading echo's lashing-the-paddle act, or the cellar's giving-bread beat) to use it. This is the M5 follow-up + the CHRONOS_SWITCH §4.2 / §5.1 / §5.2 explicit spec point.
- Add ambient audio assets `public/audio/2026-present/lake_shore.ogg`, `public/audio/1994-past/lake_shore.ogg`, and the narrator clips `lake_echo_intro.ogg` + `altar_echo_intro.ogg` per AUDIO_ARCHITECTURE.md. The `audioManager.playNarratorEntry` call is currently a stub log, so the missing files are non-blocking until the audio mixer goes live.
- Hoist `mkBox` / `mkCyl` / `deriveMat` into `world/_primitives.ts` once a fourth location lands and the call sites still agree.
- Replace the LakeShore primitives with GLB outputs from the Hunyuan3D pipeline (per ASSET_PIPELINE.md). The dock planks + pilings should reuse a shared `dock_plank` / `dock_piling` asset; the boat hull + paddle become per-era variants of `prop_boat_hull` + `prop_boat_paddle`.
- Add Playwright integration test that drives all four fragments in any order — load page, skip intro, walk-and-press-E at each anchor, assert era + flag + toast text after each, then assert all four `found_*_evidence` flags are set and the implicit `act_2_check_all_evidence` requirement is satisfied. Defer until at least one Past-side return-trigger variant lands so the test exercises both timer + interaction paths.
- Per CHRONOS_SWITCH.md §5.2 polish ("FOV clamped to 50°; soft vignette intensified to 0.5; bloom reduced") still applies only to the Hidden-mode `observer_notes` fragment; the new Protector fragments inherit era baseline as designed. Extend `interaction.setPerspective` to also push FOV/post-fx into `playerController` + `RenderingPipeline` only on Hidden, not on every Protector echo.
- The next milestone (M7 — Act 3 path fragments) requires ~12 fragments across three paths. A `fragments/` data file or per-path module under `world/locations/` is likely the next abstraction once the fourth location triggers the helpers hoist; revisit module organisation when M7 begins.

---

## 2026-05-09 — Fragment ↔ Graph.json validator (CHRONOS_SWITCH.md §8 M5)
**Author:** @royceshannon2 (via Claude)
**Scope:** tooling (new), narrative graph schema, ARCHITECTURE.md
**Files:**
- `tools/validate_fragments.py` (new) — stdlib-only Python script. Walks `witness-interactive-vite/src/**/*.ts` (skipping `_prototype-archive`, `node_modules`, `.vite`, `dist`) for two regex patterns: `new MemoryFragment(<anchor>, "<id>", ...)` constructor calls and `pastSceneController.begin({ ... })` Past-scene spec blocks. The spec block uses a string-/comment-aware brace balancer (`find_balanced_block`) so nested arrow-function bodies with `{}` (e.g. `onEnterPast: () => { ... }`) don't throw off the count. From each spec it extracts `fragmentId` and `unlocksFlag`. Joins the two halves by id, then loads `Graph.json` and pulls every node carrying a `fragmentId` field. Cross-validates: (a) each fragment's `unlocksFlag` is in its bound graph node's `unlocksFlags`, (b) each graph binding has a corresponding code fragment, (c) no duplicate fragment ids, (d) no orphan `pastSceneController.begin` specs, (e) no fragments without specs. Emits a human-readable text report by default and `--json` for CI. Exits 0 when clean, 1 on any authoring error, 2 on missing source root.
- `witness-interactive-vite/src/narrative/Graph.json` — added `"fragmentId": "cellar_door_latch"` to `act_2_evidence_cellar` and `"fragmentId": "observer_notes"` to `act_2_evidence_ravine`. These are the two graph nodes that the M3 + M4 fragments unlock; both already declared the matching evidence flag (`found_cellar_evidence`, `found_observer_evidence`) in their `unlocksFlags`, so this is a metadata add, not a flag rewire.
- `ARCHITECTURE.md` — module-status callout extended to mention M5 + the validator. Added a `core/` invariant: every authored fragment must have a paired spec **and** a `fragmentId`-tagged graph node whose `unlocksFlags` contains the spec's `unlocksFlag`. Added a `narrative/` invariant: graph nodes that anchor a fragment carry the new `fragmentId` field; the validator enforces both directions.

**Technical summary:** The M5 milestone is the *authoring guard* for Memory Fragments — the bidirectional check that catches the silent-drift class of bugs that otherwise compile cleanly. Three concrete failure modes the validator now catches end-to-end (verified in `/tmp` test fixtures, since deleted): (A) a graph node loses its `fragmentId` annotation but the fragment still exists in code → "narrative would not advance after the echo" with file:line; (B) the graph node's `unlocksFlags` is rewritten and no longer contains the fragment's flag → "unlocks flag '<X>' but graph node declares unlocksFlags=[...]"; (C) a graph `fragmentId` points at an id no `new MemoryFragment(..., "X", ...)` exists for → "graph node declares fragmentId 'X' but no … exists in code". Each error is one line per cause and points at exactly the file the author touched. Exit codes match standard CI conventions (0 = ok, 1 = data error, 2 = invocation error).

The choice of `fragmentId` as the binding lives next to the node rather than in a separate `metadata.fragmentBindings` table because the binding is a property of the node, and grepping for `fragmentId` from either side now reaches the other side directly. The CHRONOS_SWITCH.md §4.5 spec mentions a `pastSceneRef` field for a parallel future binding (anchor → authored Past-scene state); that's a distinct concept (which scene state to activate, not which fragment fires) and can layer on later without touching this validator's scope.

The script is regex-driven rather than parse-driven (no TypeScript Compiler API dependency) because the construction patterns are stable across the codebase, the brace balancer handles the only real edge case (nested function bodies in spec literals), and we want the tool to run with `python3` against a fresh checkout — no `npm install` of `typescript` to bootstrap the validator. If the project later needs symbol-level checks (e.g. flag references in `narrative/Actions.ts`), upgrading to a real AST is a contained change inside `collect_code_fragments`.

**Verification:** `python3 tools/validate_fragments.py` on the live tree reports 2 fragments (cellar_door_latch → found_cellar_evidence at bootstrap/main.ts:126; observer_notes → found_observer_evidence at bootstrap/main.ts:156) and 2 bindings (act_2_evidence_cellar, act_2_evidence_ravine) with no errors and exit 0. `--json` mode emits structured output with the same data plus `"ok": true`. Three deliberately-corrupt fixtures (binding deleted, flag rewritten, fragmentId pointed at a nonexistent fragment) each produce exit 1 with the specific error message naming the misalignment. `npm run build` from `witness-interactive-vite/` still type-checks + bundles cleanly in 928 ms — the new optional `fragmentId` field on graph nodes does not affect the JSON import surface (TypeScript treats unknown fields as `any` by default for `resolveJsonModule`).

**Follow-ups:**
- Wire the validator into a pre-commit hook or `npm run` script (e.g. `npm run validate`). Adding a `pre-commit` config or a small wrapper script under `package.json` would make this run on every change. Defer until at least one CI surface exists for the project.
- Add the validator to the M5 follow-up list once the third fragment lands (Path A's `act_3a_puzzle_1` Cellar Reconstruction is the next likely candidate). Annotate that node with `fragmentId` when its fragment is authored.
- Per CHRONOS_SWITCH.md §4.5 future field, when the first authored "Past-scene state" data file lands, extend the validator to also enforce `pastSceneRef` on the graph side maps to a real state id consumed by `PastSceneController`.
- The validator currently scans only `*.ts`. If `*.tsx` enters the project (none today), update `iter_typescript_files` accordingly.
- Consider extracting `find_balanced_block` if a sibling validator (e.g. `tools/validate_graph.py` mandated by ADR-0001) would also benefit from string-/comment-aware brace balancing.

---

## 2026-05-09 — Second Memory Fragment: Ravine `observer_notes` (Hidden dwell, M4)
**Author:** @royceshannon2 (via Claude)
**Scope:** world/locations, bootstrap, ARCHITECTURE.md
**Files:**
- `witness-interactive-vite/src/world/locations/Ravine.ts` (new) — second canonical location per WORLD.md §"The Ravine" + MISSION_BLUEPRINT.md §2 (observer's-journal anchor). Outcrop + cairn are `shared` (the rocks persist across eras); only the journal+paper, chalk-marked stones, low fortifications, and distant valley smoke columns differ. `RAVINE_VANTAGE_POSITION = (22, 0.6, 4)` so the player can walk east from the compound gate without leaving the 80 m terrain block. Same `mkBox` / `mkCyl` / `deriveMat` primitives helpers as `FamilyCompound.ts` (intentionally duplicated — three call sites, still under the abstraction threshold).
- `witness-interactive-vite/src/world/locations/index.ts` — re-export `buildRavine`, `RavineHandle`, `RAVINE_VANTAGE_POSITION`.
- `witness-interactive-vite/src/world/index.ts` — barrel.
- `witness-interactive-vite/src/bootstrap/main.ts` — register a second `MemoryFragment` (`observer_notes`) bound to `ravine.observerJournal`. Its `pastSceneController.begin(...)` spec (a) sets `pastChangeKey = "observer_notes_witnessed"` and `unlocksFlag = "found_observer_evidence"` (matches `Graph.json#act_2_evidence_ravine`), (b) calls `setPerspective("hidden")` in `onEnterPast` so the player's movement profile flips to `PROFILE_HIDDEN` (crouched, 0.18 m/s, FOV-clamped intent encoded in `interaction/Perspective.ts`), and (c) calls `setPerspective("investigator")` in `onReturnToPresent` so 2026 mobility is restored. Replaced the cellar-only per-frame proximity check with a single batched `onBeforeRenderObservable` scan over `proximityTargets[]` (closest unactivated fragment within `PROXIMITY_RADIUS_M = 3.5 m` wins; era + transition state still gates everything) — addresses the 2026-05-07 vertical-slice memory's instruction to batch fragments behind one observer.
- `ARCHITECTURE.md` — module-status callout updated to mention M4 + the batched proximity probe; §5.4 lists `buildRavine` alongside `buildFamilyCompound`; last-updated bumped to 2026-05-09.

**Technical summary:** Vertical slice now exercises **both** dwell modes specified in CHRONOS_SWITCH.md §5. The cellar fragment continues to drop the player into Past with full Protector mobility (`PROFILE_PROTECTOR`); the new ravine fragment drops them into Hidden mode where they can walk slowly and look around but not interact, mirroring the spec's "child the grandparent is hiding" framing. The fragment itself is mode-agnostic — `MemoryFragment.activate()` calls the spec's `onActivate` hook, which is where the perspective flip happens. That keeps `core/MemoryFragment` free of any `interaction/` import (still upholding ARCHITECTURE.md §5.2's import discipline). The dwell length is 14 s (vs. the cellar's 12) — a small concession to the spec's "Hidden mode is typically 30–90 s" guidance, kept short for the demo. Ravine post-fx, lighting, and audio crossfades flow through the existing `TimeManager → RenderingPipeline.fadeToEra + audioManager.transitionToEra` subscription with no further wiring; the second fragment is a pure data add. Proximity prompts now read "Press E to remember" near the cellar latch and "Press E to read" near the observer's journal — both prompts are dispatched from the single batched probe so adding a third fragment in M5 will be one entry in the array.

**Why duplicate the primitives helpers in `Ravine.ts`:** Three call sites (FamilyCompound × 1, Ravine × 1, with a likely third location coming) is below my hoist-into-a-shared-module threshold. The helpers are nine-line factories; pulling them into `world/_primitives.ts` now would add an import line in every location module without saving real code. If a fourth location lands and the signatures still agree, lift them then.

**Verification:** `npm run build` (`tsc --strict` + `vite build`) succeeds in 826 ms. No TypeScript errors. The bundle gained ~1 KB (the Ravine module is mostly literal mesh transforms — Vite tree-shakes nothing here because every helper is reachable). The boot path is unchanged in shape, so the existing manual smoke-test still covers it; specifically, the cellar latch still triggers M3 and the observer's journal now triggers M4 from a single browser session. Runtime camera-perspective behaviour is not yet pixel-verified — no headless playwright test exists.

**Follow-ups:**
- Add a Playwright integration test that drives **both** fragments in sequence (load page, skip intro, walk to cellar latch + raycast E-press, assert era + flag set + toast text, walk to ravine + raycast E-press, assert Hidden-mode movement profile + flag set + toast text, assert returned to Present after dwell). Defer until at least one Past-side return-trigger variant lands so the test exercises the full timer + interaction matrix.
- Wire real ambient audio assets (`public/audio/2026-present/ravine.ogg`, `public/audio/1994-past/ravine.ogg`, `public/audio/narrator/ravine_echo_intro.ogg`) so the era transition actually crossfades the ravine zone.
- Per CHRONOS_SWITCH.md §5.2 "FOV clamped to 50°; soft vignette intensified to 0.5; bloom reduced," extend the Hidden-mode hooks to push these into `playerController` + `RenderingPipeline`. The current implementation only changes the movement profile; FOV and post-fx stay at era baseline.
- Replace the Ravine outcrop/cairn primitives with GLB outputs from the Hunyuan3D pipeline (per ASSET_PIPELINE.md). Anchor positions, era tags, and the `observerJournal` reference do not change.
- Hoist `mkBox` / `mkCyl` / `deriveMat` into `world/_primitives.ts` once a fourth location lands and the call sites still agree.
- Per CHRONOS_SWITCH.md §8 M5 (next milestone), write `tools/validate_fragments.py` that walks `world/locations/*.ts` for `MemoryFragment` constructions and `Graph.json` for puzzle nodes, fails on (a) fragments whose `unlocksFlag` is unreachable in the graph and (b) graph nodes whose `unlocksFlags` do not have a corresponding fragment. Add the cellar + observer fragments to its golden file once it exists.
- Hoist the bootstrap's `TimeManager → pipeline + audio` + perspective subscriptions into `core/ChronosOrchestrator.ts` once a third subsystem (Lighting rig swap with `setEnabled`, particles, scene optimizer pause) needs the same hook — at two we still don't justify the extra module.

---

## 2026-05-07 — Vertical slice: Chronos era switch end-to-end (cellar_door_latch)
**Author:** @royceshannon2 (via Claude)
**Scope:** core, engine, world, ui, bootstrap; first runnable Memory Fragment
**Files:**
- `witness-interactive-vite/src/world/locations/FamilyCompound.ts` (new) — Family Compound layout per OPENING_SEQUENCE §6: gate posts (shared), main house + ruined roof + overgrown grass + eucalyptus grove (Present), intact house + clean roof + open door + hearth-smoke column + younger eucalyptus (Past), well + cellar-cover plank in both eras. Primitives only; helpers (`mkBox`, `mkCyl`, `deriveMat`) carry the era tag at construction time so a later swap to `assetLibrary.instantiate(id, era, transform)` is mechanical.
- `witness-interactive-vite/src/world/locations/index.ts` — re-export `buildFamilyCompound`.
- `witness-interactive-vite/src/world/index.ts` — barrel export.
- `witness-interactive-vite/src/core/TimeManager.ts` — added `transitionMidpoint` event; `transition(target, durationSec)` now waits `durationSec/2`, flips the camera mask, emits midpoint, waits another `durationSec/2`, emits complete. Per-era subscribers tween between Started and Completed. Event payloads now carry `durationSec` so subscribers can drive their own fades.
- `witness-interactive-vite/src/core/PastSceneController.ts` (new) — owns the return-trigger lifecycle (CHRONOS_SWITCH §4.4). `begin(spec)` from a fragment's `onActivate`; on `to: "past"` complete it arms a return timer, on `to: "present"` complete it records the past change and sets `unlocksFlag`. Audio + UI side effects come in via callbacks (`onEnterPast`, `onReturnToPresent`) so `core/` keeps clean of `audio/` / `ui/` imports.
- `witness-interactive-vite/src/core/index.ts` — exports `pastSceneController`, `DEFAULT_PAST_DWELL_SEC`, `DEFAULT_TRANSITION_SEC`.
- `witness-interactive-vite/src/engine/RenderingPipeline.ts` — added `fadeToEra(target, durationSec)` lerping `imageProcessing.exposure / contrast / vignetteWeight` along an ease-in-out cubic via `scene.onBeforeRenderObservable` (frame-locked). Per-era coefficients hoisted to a top-level `ERA_COEFF` table per CHRONOS_SWITCH §3.4. Re-entrant — a second call cancels the first observer.
- `witness-interactive-vite/src/ui/HUD.ts` — added centre proximity reticle (10 px ring, alpha 0.55), fragment prompt ("Press E to remember"), and ledger toast (bottom-centre band with 5 s default fade). Public API: `setProximity(active, prompt?)`, `showLedgerToast(text, durationMs?)`.
- `witness-interactive-vite/src/bootstrap/IntroSequence.ts` (new) — DOM overlay opening sequence per OPENING_SEQUENCE §2 (abridged to 12 s). Honors `?skipIntro=1` and `prefers-reduced-motion: reduce`.
- `witness-interactive-vite/src/bootstrap/main.ts` — full rewire: builds both lighting rigs (tagged Present/Past via `tagLight`), builds FamilyCompound, constructs `MemoryFragment` for `cellar_door_latch`, registers it through `interactableRegistry`, subscribes `TimeManager` events to drive `pipeline.fadeToEra` and `audioManager.transitionToEra` together, runs a per-frame proximity probe (3.5 m radius, gated on Present era + un-activated fragment), spawns the camera at OPENING_SEQUENCE §6 first-frame composition. Intro runs in parallel with engine init.

**Technical summary:** First end-to-end demonstration of the Chronos Switch architecture's payoff. Player loads the page → DOM intro overlay fades through "BISESERO HILLS / WESTERN PROVINCE, RWANDA" / "April 2026" / archive entries → the overlay fades out, exposing the 3D Family Compound at the gate (eucalyptus grove left, well right, ruined house ahead). Walking forward into proximity of the well's plank cover triggers a centre reticle and "Press E to remember" prompt. Pressing E activates `cellar_door_latch`: post-fx fades to warmer Past coefficients while audio crossfades to the 1994 ambient mix; at fade midpoint the camera's `layerMask` flips so the Past meshes (intact house, hearth smoke, clean well cover) become visible while the Present meshes (overgrown ruin) are hidden. After 12 s of Past dwell, the system transitions back: fade to Present coefficients, mask flip, audio crossfade. On Present arrival, `pastSceneController` records `past_cellar_evidence_witnessed`, sets `found_cellar_evidence` in `globalState`, and shows a ledger toast. Subsequent visits to the cellar latch are no-ops (the proximity probe gates on `cellarFragment.activated`). The slice exercises every event seam in ARCHITECTURE.md §3.2 and CHRONOS_SWITCH.md §4.4 sequence diagrams except the `AssetContainer` instantiate path (placeholder primitives instead of GLB loads).

**Why primitives, not GLB:** The architectural payoff is the *event flow*, not the visual fidelity. Substituting `assetLibrary.instantiate(id, era, transform)` for the local `mkBox` / `mkCyl` helpers is a one-edit-per-call swap once the Hunyuan3D pipeline produces real meshes. Era tags, anchor positions, and the fragment binding are unchanged by that swap.

**Verification:** `npm run build` produces a clean `tsc && vite build` (type-check + production bundle). `npx vite` boots in 104 ms with no errors. Runtime not yet pixel-verified — no headless playwright test exists for the Chronos transition; manual browser testing is the next step.

**Follow-ups:**
- Add a Playwright integration test that drives the cellar latch end-to-end (load page, skip intro, raycast E-press, assert era transition, assert flag set, assert toast text).
- Wire real ambient audio assets (`public/audio/2026-present/family_compound.ogg`, `public/audio/1994-past/family_compound.ogg`) so `audioManager.transitionToEra` actually crossfades between zones.
- Replace primitive house/eucalyptus/well meshes with GLB outputs of the Hunyuan3D pipeline (per ASSET_PIPELINE.md). The era-tagging and fragment registration code does not change.
- Add `?eraToggle=1` dev flag to `bootstrap/main.ts` that binds the `T` key to `timeManager.transition` for ad-hoc QA without going through the fragment.
- Consider hoisting the bootstrap's `TimeManager → pipeline + audio` subscription into a `core/ChronosOrchestrator.ts` once a second subsystem (lighting rig swap with `setEnabled`, particles, scene optimizer pause) needs the same hook.
- Add a Past-era return-trigger variant ("interaction" — the player hands a child a piece of bread) so we exercise both timer and interaction return modes before M4.

---

## 2026-04-19 — Audio architecture: Remove runtime LLM synthesis, require pre-baked audio only
**Author:** @royceshannon2
**Scope:** architecture (audio); reverts AI dialogue service from 2026-04-18
**Files:**
- `ARCHITECTURE.md`: Removed `ai/` subsystem (§5.11) and entire "AI dialogue service" section (former §9). Removed AI Dialogue node from system overview diagram. Removed `aiDialogueService` from dependency graph. Updated `audioManager.playNarratorEntry()` API signature to accept `entryKey` only (previously accepted `textKey | dialogueResponse`). Removed "AI service failures are silent" from error handling contract (§10.3).

**Technical summary:** The 2026-04-18 architecture introduced a runtime Hunyuan LLM service (HTTP endpoint at `:8082`) that would synthesize narrator dialogue on-the-fly, with local caching and deterministic fallback lines. This created three undesirable dependencies: (1) teacher must run a separate service on the lab machine; (2) network latency during gameplay; (3) classroom Wi-Fi blocking localhost services breaks offline play. Instead, all narrator lines (ledger entries, voice-overs, internal monologues) are now recorded upfront by the professional voice actor and bundled in the game at `public/audio/narrator/`. The `AudioManager` loads these pre-baked files by key only, eliminating service dependency, latency, caching complexity, and fallback logic. This aligns with the original project intent—Hunyuan3D 2.1 is used strictly for 3D asset generation; audio is delivered pre-rendered.

**Follow-ups:**
- Complete voice-actor recording for all 20+ narrator lines specified in `AUDIO_ARCHITECTURE.md §3` and `MISSION_BLUEPRINT.md` echoes and climactic moments.
- Finalize audio bundle organization: `public/audio/2026-present/<location>.ogg`, `public/audio/1994-past/<location>.ogg`, `public/audio/narrator/<entry-id>.ogg`.
- Update mission manifest schema (remove `manifest.ai` section from `SCALABILITY_PLAN.md`; simplify to `manifest.audioLayers` pointing to directory of pre-rendered zone mixes).
- Remove validation rules for AI cache completeness from `SCALABILITY_PLAN.md`.

---

## 2026-04-18 — Engine architecture v2: Chromebook-floor profiles, mission-as-template, Hunyuan LLM dialogue service
**Author:** @royceshannon2 (via Claude)
**Scope:** system architecture; no source code yet

**Files:**
- Rewrote `ARCHITECTURE.md` end-to-end. New contents include: (§1) three architectural commitments — event-only subsystem isolation, engine-as-template, Chromebook performance floor. (§5.9) new `mission/` subsystem with `MissionLoader` contract. (§5.10) new `performance/` subsystem with `detectProfile`, `applyProfile`, `runFreezePass`, `startSceneOptimizer`. (§5.11) new `ai/` subsystem — AIDialogueService with SceneContext/DialogueResponse interfaces, `sha256(missionId|anchorId|era|sortedFlagsJson|seed)` cache key restricted to a manifest-declared flag allowlist, shipped `ai-cache/*.json` + runtime IndexedDB cache, deterministic `fallbackDialogue` mandate, `/health` probe with no-retry fallback-only mode on failure. (§6) target hardware profiles — LOW=Chromebook (Lenovo 100e ref), MEDIUM=MacBook Air M1, HIGH=RTX 3060 — with per-profile dimension table (texture budget, shadow casters, post-fx, SceneOptimizer priority). (§6.1) profile detection — query param → localStorage → `navigator.deviceMemory`/`hardwareConcurrency` heuristics → FPS probe. (§7) freeze pass code walking every mesh: `freezeWorldMatrix`, `alwaysSelectAsActiveMesh`, `doNotSyncBoundingInfo`, `cullingStrategy = CULLINGSTRATEGY_BOUNDINGSPHERE_ONLY`, `material.freeze`, then `scene.freezeActiveMeshes + skipPointerMovePicking + blockMaterialDirtyMechanism`. Respects `mesh.metadata.interactive` and `material.metadata.dynamic` as opt-outs. (§7.4) SceneOptimizer factory in Shadows → PostProcess → Texture → HardwareScaling progression. (§8) asset library lifecycle — N=4 bounded-concurrency `preload`, `instantiate` via `LoadAssetContainerAsync`, teardown wrapped in `blockfreeActiveMeshesAndRenderingGroups` per Babylon doc. (§9) AI dialogue service lifecycle — shipped cache → IndexedDB cache → service → fallback hierarchy. (§10) UI rendering strategy — orthographic second HUD camera on `scene.activeCameras`, lights `excludeWithLayerMask` for `LAYER_HUD`, no post-fx pass on UI.
- Created `SCALABILITY_PLAN.md`. Complete Mission Manifest JSON schema with 12 top-level sections (identity, historical provenance, performance, requiredAssets, environment, locations, anchors, narrativeGraph, ai, ui, save). Field-by-field documentation for every manifest key. On-disk folder layout spec at `public/missions/<mission-id>/`. 11-step walkthrough for adding a new mission (pick id → write README → author graph → author blueprint → generate assets → record audio → author fallbacks → write manifest → generate AI cache → test on minimum profile → register in `public/missions/index.json`). 7 validation-rule categories (file existence, referential integrity, fallback completeness, graph integrity, performance-declaration honesty, historical provenance, AI safety). Mission lifecycle sequence (load: validate → preload → scene → IBL → locations → audio zones → anchors → graph → freeze pass → AI init → title card; unload: full dispose with `blockfreeActiveMeshesAndRenderingGroups`). AI prompt-template constraints — no inventing historical figures/dates/places, no graphic violence, no first-person speech as named victims/perpetrators, fallback-on-insufficient-context. `example-plaza` template smoke-test mission spec for CI (AI disabled on all profiles). 10 anti-patterns — hardcoded mission names, mission-specific engine constants, branching outside the graph, shipping anchors without fallback, literal asset paths, invented history in prompts, undeclared floor hardware, duplicated shared assets, scene mutating narrative state, missing README. Shipping checklist. Forward-compatibility policy for schema bumps.

**Why this is a version jump, not an incremental edit:**
The prior architecture targeted a single mission ("The Shepherd's Ledger") on desktop-class hardware ("60 fps at 1920×1080 on RTX 3060" per `RENDERING.md`). The new architecture keeps that as the HIGH-tier contract but adds LOW (Chromebook) as the *baseline*, and adds `mission/` as a subsystem so a second or third historical mission can be authored as pure data under `public/missions/<id>/` rather than as additional `src/` code. The engine-vs-content split is now load-bearing: every claim about the Bisesero story was extracted from engine code into the manifest. The Hunyuan LLM dialogue service at `:8082` is new and is distinct from the existing Hunyuan3D 2.1 asset-generation container at `:8081` — name collision risk flagged in the AI subsystem contract.

**Tonal discipline:** the user's prompt asked for "AAA 'Tactical' aesthetic" and a "Tactical HUD". The 2026-04-18 changelog entry and the project's documentary/memorial register preclude that vocabulary (Modern-Warfare framing on a genocide-memorial project is a category error). I translated the operational intent — clean, information-dense, performance-isolated UI — into the register the project uses: the HUD is the **investigator's ledger**, rendered on an orthographic camera so its performance is decoupled from the 3D scene. The translation is flagged in `ARCHITECTURE.md §10` so the user can correct the register if my reading was wrong.

**Follow-ups:**
- Create `src/mission/MissionLoader.ts` plus `src/performance/`, `src/ai/` module skeletons. None exist yet.
- Write `tools/validate_manifest.py` — enforces §5 validation rules.
- Write `tools/validate_graph.py` — mandated by ADR-0001.
- Write `tools/lint_prompts.py` — enforces §7 prompt-safety constraints.
- Relocate Bisesero coordinates and character names from any `src/` reference into `public/missions/shepherds-ledger/manifest.json`. A grep pass on `src/` for `"Bisesero"`, `"Rwanda"`, `"1994"`, `"Shepherd"` should return zero hits.
- Add `"@babylonjs/havok"` to `witness-interactive-vite/package.json` before `src/engine/Physics.ts` is written (already open from prior changelog).
- Ship the `example-plaza` template fixture (manifest + minimal assets) for CI smoke testing of mission load/unload.
- Confirm with user whether the "Tactical HUD" vocabulary in the original prompt was literal — if yes, this architecture is wrong about the UI register and needs a one-line correction. See `ARCHITECTURE.md §10`.
- Hunyuan LLM dialogue service — separate spec document needed, distinct from Hunyuan3D 2.1 asset-gen container. Endpoint contract: `/health` (GET), `/dialogue` (POST with `{ missionId, anchorId, era, flags, seed, template, maxTokens, temperature }`). Response schema to be formalized.

---

## 2026-04-18 — Design-doc stub fills: Chronos, Rendering, Asset Pipeline + Opening Sequence + Narrative edge-case ADR
**Author:** @royceshannon2 (via Claude)
**Scope:** documentation only; no source code touched

**Files:**
- Filled `docs/design-docs/CHRONOS_SWITCH.md` §1–§9 (objective, scope, era model, layer masks, TimeManager reference, post-fx profile summary, lighting strategy, transition sequence 1.8 s cadence, Memory Fragment authoring/registration/lifecycle, Protector/Hidden perspective modes, layer-mask-vs-scene-swap rationale, failure modes, milestones M1–M8).
- Filled `docs/design-docs/RENDERING.md` §1–§11 (documentary-realism visual bar, 60 fps / RTX 3060 cost bar, 14-entry PBR material library, per-era lighting rig with duplicated DirectionalLight/HemisphericLight, shared + per-era post-fx profiles with small grading deltas, Havok init contract, performance budgets, forward/deferred trade-off, failure modes, milestones M1–M7).
- Filled `docs/design-docs/ASSET_PIPELINE.md` §1–§9 (end-to-end Hunyuan3D 2.1 → bake → Draco + KTX2 → LOD → collision → registry → runtime pipeline, `kechiro/hunyuan3d-2.1-cachedstart:latest` Docker container + FastAPI contract on :8081, prompt-template frontmatter schema, 3-tier LOD at 15m/50m thresholds, V-HACD collision hulls, asset-index.md schema, `AssetLoader.ts` runtime contract with era-scope tagging, size budgets, failure modes, 6-phase milestone plan).
- Created `docs/design-docs/OPENING_SEQUENCE.md` — second-by-second opening spec in documentary/memorial register (Shoah / Act of Killing reference points). 45-second descent from page load to first-frame control, 5 archive entries sourced only from verifiable Bisesero history, investigator's interface (not HUD), zero military-game vocabulary, asset-streaming behavior, replay and save-resume variations, accessibility considerations.
- Created `docs/decisions/adrs/0001-narrative-edge-cases.md` — ADR covering five runtime edge cases: (1) circular flag dependency in Graph.json, (2) fragment triggered in wrong era, (3) save mid-Chronos-transition, (4) missing past_* flags on version migration, (5) branch choice committed before requiredFlags met. Commits handling at each owning subsystem (`SaveSystem`, `NarrativeController`, `TimeManager`, `InteractableRegistry`). Locks in save-always-resumes-in-Present contract.
- Updated `docs/design-docs/MASTER.md` repo map (promoted 3 stubs to production, added OPENING_SEQUENCE and ADR-0001) and gap matrix rows for Chronos, Rendering, Materials, Asset Pipeline, Audio, Opening Sequence.

**Tonal discipline:** the plan flagged that earlier /loop prompt vocabulary ("Modern Warfare HUD", "Intel Fragments", "Tactical UI", "Historical Drop", "Mission Engine", "Historical Weight") would frame a game about the Rwandan genocide in the register of a military shooter, violating the PRD's explicit restraint requirement. Every artifact here uses the documentary/memorial register: "investigator's interface," "archive entries," "descent," "Narrative Engine," "moment of weight." No file at `docs/architecture/` or `docs/ui/` was created — those paths do not exist and do not need to.

**Content constraint:** all historical fragments in OPENING_SEQUENCE.md §4 are traceable to `WORLD.md` and `NARRATIVE.md`. No history was invented. The five opening archive entries name Bisesero's elevation, the 100-day period, the self-defense on the heights, the survival numbers, and the grandfather's ledger.

No runtime behavior change. Cross-references throughout link back to `TIMELINE_SYNC.md` (already implemented), to `AUDIO_ARCHITECTURE.md` and `MISSION_BLUEPRINT.md` (2026-04-18), and to the existing `src/core/TimeManager.ts` / `LayerMasks.ts` implementation.

**Follow-ups:**
- Write `tools/validate_graph.py` before M3 — mandated by ADR-0001 for cycle detection in CI.
- Write `tools/validate_fragments.py` per `CHRONOS_SWITCH.md §7` (catches authoring mismatches between Memory Fragment `unlocksFlags` and `Graph.json` nodes).
- Fill `docs/current-state/PROTOTYPE_AUDIT.md` (still referenced as "to be written" in MASTER.md).
- Confirm installed Hunyuan3D version (2.1 vs 3.0) via `docker inspect` and update `ASSET_PIPELINE.md §3.2` if 3.0.
- Add `@babylonjs/havok` to `witness-interactive-vite/package.json` before implementing `engine/Physics.ts`.
- Optional next: expand `Graph.json` with 3–5 new decision nodes per plan `§6`, and add NARRATIVE.md `§X` (expanded branch points) / `§Y` (in-world real-time choices). Deferred; not part of stub-fill scope.
- Optional next: write `AI_PIPELINE.md` (Hunyuan world-state → generation → feedback loop). Deferred.

---

## 2026-04-17 — Core subsystem v1: TimeManager + LayerMasks + Timeline Sync
**Author:** @royceshannon2 (via Claude)
**Scope:** `core/` (new subsystem), narrative integration via flag namespace

**Files:**
- Added `witness-interactive-vite/src/core/LayerMasks.ts` — bit constants `LAYER_PRESENT`, `LAYER_PAST`, `LAYER_SHARED`, `LAYER_ALL`; `CAMERA_MASK_PRESENT`/`CAMERA_MASK_PAST`; `EraScope` type; `tagNode(mesh, scope)` and `tagLight(light, scope)` helpers.
- Added `witness-interactive-vite/src/core/TimeManager.ts` — class + singleton `timeManager`. Tracks the active era (`"present"` | `"past"`), drives camera `layerMask` on `attach()`/`transition()`, and exposes `recordPastChange(key, value?)` / `hasPastChange(key)` / `getPastChanges()` as the bridge into narrative state. Emits `transitionStarted`, `transitionCompleted`, `pastChangeRecorded` events to subscribers. Single-flight transition guard.
- Added `witness-interactive-vite/src/core/index.ts` — barrel export.
- Added `docs/design-docs/TIMELINE_SYNC.md` — design doc for the Past ⇄ Present state bridge. Specifies the `past_` flag prefix convention, API, usage patterns, failure modes, and open questions.
- Updated `docs/design-docs/MASTER.md` and `ARCHITECTURE.md` to reflect the `src/core/` directory name (previously `src/time/`) throughout diagrams, tables, and subsystem contracts.
- Updated `docs/design-docs/CHRONOS_SWITCH.md` stub with the corrected code-home path and a link to `TIMELINE_SYNC.md`.

The TimeManager piggybacks on the existing narrative `StateManager` for persistence: every `recordPastChange(key)` call writes a `past_<key>` boolean into `globalState.flagsSet`, which is already serializable via `StateManager.serialize()`. No new storage, no new save-file schema. The Present reads via `hasPastChange(key)` — symmetric accessor over the same namespace.

Camera layer-mask wiring: `LAYER_SHARED | LAYER_PRESENT` when in Present, `LAYER_SHARED | LAYER_PAST` when in Past. Lights use `includeOnlyWithLayerMask` with the same scoping so per-era lighting (1994 warm sun vs. 2026 overcast) can coexist in one scene.

Type-check (`tsc --noEmit`) clean for `src/core/**` and `src/narrative/StateManager.ts`. Pre-existing type errors in `main.ts` (prototype, do-not-touch) and `NarrativeController.ts` (2× `verbatimModuleSyntax` type-import issues, unused `NarrativeAction` import) remain — flagged here but out of scope for this task.

**Follow-ups:**
- Fix `NarrativeController.ts` type-only import errors (trivial, 2 lines) so `npm run build` can pass.
- Decide on ADR for open question: should `recordPastChange` reject calls made outside the Past era? (See `TIMELINE_SYNC.md §9 Q1`.)
- Unit tests for TimeManager — no Babylon required; test against `globalState` directly.
- `MemoryFragment.ts` is the next core-module addition; it will be the runtime trigger that calls `recordPastChange`.
- `CHRONOS_SWITCH.md` body still stubbed — now partially superseded by `TIMELINE_SYNC.md` for the state-bridge portion; remaining content is the era-switch mechanic + transition crossfade.

---

## 2026-04-17 — Documentation pass: master design doc and repo reorganization
**Author:** @royceshannon2 (via Claude)
**Scope:** documentation only; no source code touched

**Files:**
- Added `docs/design-docs/MASTER.md` (umbrella design doc, repo map, gap matrix, work ordering).
- Added `ARCHITECTURE.md` (system-level Mermaid diagrams, module dependency graph, subsystem contracts).
- Added `docs/current-state/PROTOTYPE_AUDIT.md` (brutal line-level critique of `main.ts`; verdict: throw out, salvage patterns).
- Added stub design docs: `docs/design-docs/CHRONOS_SWITCH.md`, `docs/design-docs/ASSET_PIPELINE.md`, `docs/design-docs/RENDERING.md`.
- Added `docs/decisions/CHANGELOG_DETAILED.md` (this file) and `docs/decisions/adrs/0000-template.md`.
- Renamed `docs/design-docs/STORY_TREE_SHEPHERD_LEDGER.md` → `NARRATIVE.md`.
- Renamed `docs/design-docs/SETTING_BISESERO.md` → `WORLD.md`.
- Deleted `docs/design-docs/STORY_TREE.md` (stale generic template — contradicted the canonical Shepherd's Ledger).
- Rewrote `CLAUDE.md`: corrected Babylon version (6.0+ → 9), removed fabricated "Migration from REST to gRPC" reference, removed meaningless "Architecture Version 1.2.0" line, fixed `npm start` → `npm run dev`, pointed entry-point readers to `MASTER.md`.
- Updated `witness-interactive-vite/src/narrative/README.md` to reference `NARRATIVE.md` (was `STORY_TREE.md`).
- Relocated `docs/adrs/` → `docs/decisions/adrs/` per `MASTER.md` structure.

Documentation-only pass. No behaviour change. The repository now has an anchored design hierarchy: `MASTER.md` is the umbrella; subsystem docs (`NARRATIVE.md`, `WORLD.md`, `PUZZLE_DESIGN.md`, `CHRONOS_SWITCH.md`, `ASSET_PIPELINE.md`, `RENDERING.md`) each own one concern; `ARCHITECTURE.md` captures the module contract; `PROTOTYPE_AUDIT.md` documents the gap between current prototype and target. Stub docs are intentionally thin — they exist so cross-links resolve and so the next writing pass has a skeleton.

**Follow-ups:**
- Fill in `CHRONOS_SWITCH.md` body (currently §1–§7 are stubs). Blocks vertical-slice work.
- Fill in `RENDERING.md` body. Blocks `engine/` module extraction.
- Fill in `ASSET_PIPELINE.md` body. Not on critical path, but blocks asset work.
- Consider ADRs for: (a) snap-vs-preserve camera on era change, (b) Havok necessity in Acts 1–2, (c) language/localization strategy. See `MASTER.md §10`.
- Clean up `tools/*.py.py` doubled extensions when asset pipeline work begins.
- Rename `docs/asset-{index,log}.md.txt` → `.md`.
- Preserve current `main.ts` on a `prototype/kigali-sketch` branch before any refactor begins.

## 2026-04-27 — Architecture scaffold pass: empty-scene boot under strict TS
**Author:** Claude (Opus 4.7) on behalf of @royceshannon2
**Scope:** `witness-interactive-vite/src/` — every subsystem listed in ARCHITECTURE.md §5 + §11; `ARCHITECTURE.md`; `index.html`; `package.json`.
**Files:**
- Moved `src/main.ts`, `src/counter.ts` → `_prototype-archive/*.bak` (out of `tsconfig.include`); added `_prototype-archive/README.md` pointing to `docs/current-state/PROTOTYPE_AUDIT.md` §9.
- New: `src/engine/{config,SceneFactory,Lighting,Materials,RenderingPipeline,Physics,index}.ts` — frozen `engineConfig` + `worldConstants` (real `gravityY: -9.81`, rejecting prototype's `-9.81 * 0.06`), three-light per-era rigs with PCSS shadows, 14-id `MaterialLibrary` of frozen PBR seeds, ACES + FXAA + conditional SSAO/bloom/grain pipeline, Havok wrapper enforcing per-profile dynamic-body cap.
- New: `src/performance/{PerformanceManager,SceneOptimizerFactory,index}.ts` — `?perf=` → localStorage → `deviceMemory`/`hardwareConcurrency` heuristic profile pick, freeze pass per ARCHITECTURE.md §7.1 (skips `metadata.interactive`/`metadata.dynamic`), profile-keyed `SceneOptimizerOptions`.
- New: `src/mission/{Manifest,MissionLoader,index}.ts` — TypeScript schema for mission JSON, validating loader stub with subscribe API.
- New: `src/io/{AssetLibrary,SaveSystem,index}.ts` — `LoadAssetContainerAsync`-based library with concurrency cap of 4; `localStorage` save slots under `witness:save:` prefix.
- New: `src/world/{Terrain,index}.ts` and barrel placeholders for `world/{locations,vegetation,structures,props}/index.ts`. Terrain salvages prototype patterns per audit §3.
- New: `src/interaction/{PlayerController,InteractableRegistry,Perspective,index}.ts` — pointerlock-on-click via `onPointerObservable` (no global handler override per audit §5), three movement profiles (Investigator / Protector / Hidden), pick-on-click-or-E registry that flags meshes `metadata.interactive`.
- New: `src/audio/{AudioManager,index}.ts` and `src/ui/{HUD,LedgerUI,index}.ts` — `CreateAudioEngineAsync` boot stub respecting profile voice cap; ortho HUD camera on `LAYER_HUD = 0x80000000` with all scene lights excluded; full-screen ledger modal on the same HUD layer.
- New: `src/core/MemoryFragment.ts` — Present-era proximity trigger; `bindInteraction(register)` keeps `core/` independent of `interaction/`; idempotent `activate()` writes `fragment_<id>_activated` flag, calls `narrativeController.triggerPuzzleCompletion`, then `timeManager.transition('past')`.
- New: `src/log.ts` — tagged logger with `debug` stripped via `import.meta.env.PROD`.
- New: `src/bootstrap/main.ts` — single entry point booting subsystems in ARCHITECTURE.md §11 order. `index.html` updated to `/src/bootstrap/main.ts`. `src/style.css` replaced with full-bleed canvas reset.
- Fix: `src/narrative/NarrativeController.ts` — type-only imports for `GameState`/`NarrativeAction` (was breaking `verbatimModuleSyntax`). `src/engine/Materials.ts` — replaced parameter property with explicit field (was breaking `erasableSyntaxOnly`).
- Dep: added `@babylonjs/havok ^1.3.12` (CLAUDE.md prerequisite for `Physics.ts`).
- Doc: `ARCHITECTURE.md` last-updated bumped to 2026-04-27 + module-status callout under §5.

The prototype's responsibilities have been split along the boundaries documented in ARCHITECTURE.md §2 — every module imports only from layers it is permitted to (e.g., `engine/` imports only Babylon; `performance/` imports only `engine/`; `core/` is the single seam where world triggers and narrative meet via `MemoryFragment`). Stubs (audio playback, era crossfade, narrator) log and resolve so callers can be wired today and replaced incrementally as content lands. `npm run build` succeeds end-to-end under `tsc --strict` + `verbatimModuleSyntax` + `erasableSyntaxOnly`; bootstrap renders an empty scene with the Present-era lighting rig. The 5.6 MB index chunk is dominated by Babylon and is expected — code-splitting can wait until the asset pipeline ships and a real measurement matters.

**Follow-ups:**
- Wire mission JSON loading: `bootstrap/main.ts` should call `missionLoader.load("public/missions/bisesero/manifest.json")` once a v1 mission exists.
- Implement `world/locations/`, `world/vegetation/`, `world/structures/`, `world/props/` — each a thin builder that takes a `LocationDecl` from the manifest and emits tagged Babylon nodes.
- Replace `audioManager` stubs with the real spatial-zone implementation per `AUDIO_ARCHITECTURE.md` once the first ogg/mp3 bundle ships.
- Wire the freeze pass + scene optimizer into a `missionReady` lifecycle hook (per ARCHITECTURE.md §11) — currently both are exported but called nowhere.
- Add `?inspect=1` query-param hook in `bootstrap/main.ts` to load `@babylonjs/inspector` on demand for dev sanity-checking.
- Surface `engineConfig[profile].targetFps` to the SceneOptimizer (currently hard-coded inside `buildOptimizerOptions` — keep them in sync via a shared helper).
- The 5,593 kB warning chunk should be revisited once Babylon's `import` graph stabilizes; consider Vite `build.rolldownOptions.output.codeSplitting`.

## 2026-05-13 — Act 4 polish: shrine proximity trigger, interaction-driven echo, New Game+ reset
**Author:** Claude (Sonnet 4.6) on behalf of @royceshannon2
**Scope:** `src/core/PastSceneController.ts`, `src/narrative/{StateManager,NarrativeController}.ts`, `src/world/locations/FamilyCompound.ts`, `src/bootstrap/{main,RemembranceSequence}.ts`
**Files:**
- `src/narrative/StateManager.ts`: Added `reset()` method — clears all flags, puzzles, and paths back to the `intro` branch. Enables New Game+.
- `src/narrative/NarrativeController.ts`: Added `onGameComplete(path, memorialization)` — emits `endingReached` to all subscribers. Completes the game-complete→narrative-layer wire.
- `src/core/PastSceneController.ts`: Added `interactionDriven?: boolean` to `PastSceneSpec`. When true, the automatic dwell timer is skipped after entering Past; callers drive the return by calling the new `returnNow()` method. Enables future fragments where the player controls the exit via E-key rather than waiting.
- `src/world/locations/FamilyCompound.ts`: Exposed `shrineAnchor: AbstractMesh` in `FamilyCompoundHandle` (mapped to `altarSlabPresent`). Act 4 proximity trigger uses this as the physical return point.
- `src/bootstrap/RemembranceSequence.ts`: Replaced the CLOSING_SEC auto-dismiss timer with a "Play again" button that appears after the delay and calls `window.location.reload()` via an `onRestart` callback. This implements New Game+ at the session level.
- `src/bootstrap/main.ts`: 
  - `ProximityTarget.fragment` refactored to `ProximityTarget.isActivated: () => boolean` — decouples the probe from `MemoryFragment` so shrine targets (which have no era transition) can participate in the same scan.
  - `makePathChecker` extended: instead of immediately firing `showRemembranceSequence`, it now registers `compound.shrineAnchor` as a one-shot `InteractableRegistry` handler, pushes a shrine `ProximityTarget` gated by `path_*_complete`, and calls `narrativeController.onGameComplete()` after the sequence resolves.
  - Path checkers (`checkPathA/B/C`) moved to after `proximityTargets` is defined so `compound.shrineAnchor` + the live array can be passed in. No-op defaults prevent TypeScript from flagging potential uninitialized use.
  - `narrativeController` imported and wired at game-complete.

**Outcome:** When the player completes the last puzzle on any path:
1. HUD toast: "The ledger reveals its final page. Return to the family shrine."
2. Player physically walks to the altar slab → "Press E to remember him" prompt appears.
3. E-press → `showRemembranceSequence(path)` — the two-phase overlay runs.
4. After the closing voice, a "Play again" button fades in. Clicking it reloads the session (New Game+).
5. `narrativeController.onGameComplete(path, memorialization)` fires so any future analytics/subscriber can react.

`npm run build` passes clean. `tools/validate_fragments.py` exits 0 (15/15 fragments bound).

## 2026-05-18 — Asset pipeline stage 0.5: Zero123++ multi-view + detached-island strip
**Author:** Claude (Opus 4.7) on behalf of @royceshannon2
**Scope:** `tools/generate_multi_views.py` (new), `tools/hunyuan_patch/model_worker.py`, `tools/asset_pipeline.py`, `tools/generate_asset.py`, `tools/optimize_asset.py`, `tools/HUNYUAN_RUNBOOK.md`, `docs/design-docs/ASSET_PIPELINE.md`
**Why:** Validation renders of `vegetation_eucalyptus_mature` shipped with a visibly flat crown — a known failure mode of single-view Hunyuan inference where the model can't see the top of the silhouette. We also noticed the raw GLB occasionally carries small disconnected mesh islands (silhouette-bleed reconstructions) that inflate face counts and break collision generation. Fix is a new stage 0.5 (Zero123++ canonical novel-view synthesis) plus a trimesh-based cleanup pass at the head of `optimize_asset.py`.
**Files:**
- New: `tools/generate_multi_views.py` — standalone diffusers script. Loads `sudo-ai/zero123plus-v1.2` via `DiffusionPipeline.from_pretrained(custom_pipeline="sudo-ai/zero123plus-pipeline")`, runs Euler-Ancestral with `timestep_spacing="trailing"`, slices the 960×640 grid into six 320² PNGs at `prompts/asset-templates/<id>/views/view_{0..5}.png` (azimuths 30°/90°/150°/210°/270°/330°, alternating 30°/−20° elevations). Idempotent: no-ops when six views already exist (`--force` overrides). ComfyUI was deliberately bypassed for this stage — Zero123++ is a single-shot inference with no graph value-add, and the ComfyUI-3D-Pack custom nodes fight our Flux fp8 install's torch pin.
- `tools/hunyuan_patch/model_worker.py`: extended `ModelWorker.generate()` to accept `params['images']` (list of base64 strings) alongside the legacy `params['image']`. Decodes each, normalises (RGBA + rembg) per-view, passes the list to `Hunyuan3DDiTFlowMatchingPipeline` (which natively accepts a list per the upstream Tencent repo). Falls back to single-image submit on `TypeError` so an unpatched hy3dshape build still produces a mesh. Texture pass continues to use the first (front) view as its colour reference, preserving the legacy paint path.
- `tools/asset_pipeline.py`: new `maybe_multi_view()` stage runs between stage 0 (ref) and stage 1 (Hunyuan), gated by `--multi-view`. New flags: `--multi-view`, `--multi-view-force`, `--multi-view-seed`, `--multi-view-steps`, `--multi-view-guidance`, `--multi-view-dtype`. Views are passed through to `generate_asset.py` as repeated `--view <path>` flags.
- `tools/generate_asset.py`: new `--view` (repeatable) flag. When views are supplied, `submit()` sends both the legacy `image` (primary view) and the new `images` list to `/send`. Order is the upstream Zero123++ azimuth ordering.
- `tools/optimize_asset.py`: new `strip_detached_components()` pass runs as stage 1/3 (before Draco). Uses `trimesh.split(only_watertight=False)`, keeps every connected component whose absolute volume is at least `--cleanup-min-volume-ratio` × max-component-volume (default 0.01 = 1 %). Concatenates survivors back into a single mesh and re-attaches under the original geometry name. Skipped gracefully when `trimesh` is missing or load/export fails. Disable via `--no-cleanup`.
- `docs/design-docs/ASSET_PIPELINE.md`: added `MultiView` + `Views` nodes between `RefGen` and `Gen` in the stage-graph mermaid. Added a stage-0.5 callout describing the optional path, the patched payload contract, and the sequential-VRAM coordination on the 5090.
- `tools/HUNYUAN_RUNBOOK.md`: updated the patch callout to document item (c) — the `images: [base64, …]` list payload — and the requirement to restart the container after pulling a new patch (the bind-mount is read at FastAPI import time, not per-request).

**Pipeline shape (new):**
```
Stage 0   (Flux → ref.png)
   │
   ├──────────────── Stage 0.5 (Zero123++ → 6 views) ── optional
   │                                  │
   ▼                                  ▼
Stage 1   (Hunyuan3D: single OR multi-view → raw .glb)
   │
   ▼
Stage 2   (PBR bake + optional AI projection)
   │
   ▼
Stage 3   (validation renders)
   │
   ▼
Optimize  (1/3 detached-island strip → 2/3 Draco → 3/3 KTX2)
   │
   ▼
Register + Export
```

**Outcome:** Multi-view path is plumbed end-to-end (`asset_pipeline.py --multi-view` → `generate_multi_views.py` → `generate_asset.py --view` → patched worker → `/send` with `images: [...]`). `py_compile` is clean across all four modified scripts; `--help` resolves for each CLI. Verification on `vegetation_eucalyptus_mature` (re-run with `--multi-view --validation-renders`) is the next manual check. Detached-island cleanup runs by default at the optimize step; existing assets remain bit-stable when no islands are present (the pass logs "No detached components found" and writes nothing).

**Follow-ups:**
- Smoke-test the full chain on `vegetation_eucalyptus_mature` with `--multi-view --validation-renders` and compare the new crown render against the original flat-top.
- Add a `--multi-view-views` flag once we have data on how few views Hunyuan needs — fewer views may reduce ref-pose bias on shy assets.
- Zero123++ is Objaverse-trained (compact household-object bias); trees may be out-of-distribution. If the crown improves but proportions warp, fall back to a Flux-Redux ensemble or sketch the upper canopy manually.
- The `model_worker.py` bind-mount must be restarted after each patch push — note this in the daily run script when one exists.

## 2026-05-18 — Stage 0.5 interpreter wiring (`--multi-view-python`)
**Author:** Claude (Opus 4.7) on behalf of @royceshannon2
**Scope:** `tools/asset_pipeline.py`, `tools/HUNYUAN_RUNBOOK.md`, `/home/royce3/ComfyUI/venv` (installed `diffusers==0.38.0` + `accelerate==1.13.0`)
**Why:** First end-to-end run of `--multi-view` failed at stage 0.5 with `ModuleNotFoundError: No module named 'diffusers'` because the orchestrator was using `sys.executable` (system `/usr/bin/python`, which lacks GPU deps). The pipeline's other stages run under system python fine — only stage 0.5 needs torch + CUDA wheels — so the right shape is per-stage interpreter override rather than forcing the orchestrator into a heavy venv.
**Files:**
- `tools/asset_pipeline.py`: new `MULTI_VIEW_PYTHON_DEFAULT = "/home/royce3/ComfyUI/venv/bin/python"` constant; new `--multi-view-python` flag with env-var override `WITNESS_MULTI_VIEW_PYTHON`. `maybe_multi_view()` now uses the resolved path instead of `sys.executable` and dies early with a clear message if the path does not exist. `import os` added for env-var resolution.
- `tools/HUNYUAN_RUNBOOK.md`: §0 pre-flight import-check now invokes ComfyUI's venv directly (`/home/royce3/ComfyUI/venv/bin/python -c "import diffusers, accelerate, torch"`) and lists expected versions. §4 multi-view subsection gained an "Interpreter selection" callout describing the default, the env-var override, and the fail-fast behaviour. §6 troubleshooting got a new row for "stage 0.5 aborts with `No module named 'diffusers'` or `--multi-view-python <path> does not exist`" with the exact remediation commands.
- ComfyUI's venv (`/home/royce3/ComfyUI/venv`): `pip install "diffusers>=0.30" accelerate`. ComfyUI already carried `torch==2.11.0+cu130`, `transformers==5.7.0`, `einops==0.8.2`, `huggingface_hub==1.13.0` — net new surface is the two diffusers + accelerate wheels.

**Outcome:** `python tools/asset_pipeline.py vegetation_eucalyptus_mature --kind mesh --auto-ref --multi-view --era shared` now resolves stage 0.5's interpreter to ComfyUI's venv automatically. The orchestrator's `--help` lists `--multi-view-python MULTI_VIEW_PYTHON` with the env-var override hint. `py_compile` clean.

**Follow-ups:**
- Actually re-run the eucalyptus smoke test now that stage 0.5 has a working interpreter — this is what the previous entry's first follow-up was waiting on.

## 2026-05-18 — Stage 0.25 ref refinement (FLUX.2 [klein] 9B Base img2img)
**Author:** Claude (Opus 4.7) on behalf of @royceshannon2
**Scope:** `tools/refine_ref_image.py` (new), `prompts/_flux_workflows/refine.json` (new), `tools/asset_pipeline.py`, `tools/HUNYUAN_RUNBOOK.md`, `docs/design-docs/ASSET_PIPELINE.md`, `prompts/asset-templates/_STYLE_GUIDE.md`
**Why:** Hand-picked reference images for the 1994 Rwandan Bisesero Hills setting are scarce and inconsistent — open-web photos vary wildly in palette, lighting, and stylistic alignment with Digital Diorama. Pure-Flux generation (stage 0) is style-coherent but drifts toward generic-African-village tropes when regional specificity matters. The hybrid solution: keep hand-picked refs (or stage-0 Flux outputs) and run them through a low-strength FLUX.2 [klein] 9B Base img2img pass that preserves geometry/composition while normalising palette, lighting, and material feel. Inserted between stage 0 and stage 0.5 so downstream stages are oblivious — they still read `ref.png`.
**Files:**
- `prompts/_flux_workflows/refine.json` (new): FLUX.2 klein img2img workflow. Node layout mirrors `hero.json` for diff-ability; the only structural change is `LoadImage → VAEEncode` replacing `EmptyLatentImage`. Variable `__STRENGTH__` placeholder on `BasicScheduler.denoise` lets the orchestrator push different categories harder. `__REF_FILENAME__` placeholder lets `refine_ref_image.py` point `LoadImage` at the uploaded source.
- `tools/refine_ref_image.py` (new): stage 0.25 driver. Uploads the source via ComfyUI's `/upload/image` endpoint (deterministic filename `witness_refine_<id>.png`), substitutes the four placeholders, submits, polls `/history`, downloads the result, and overwrites `ref.png`. Archive-and-swap idempotency: first run copies `ref.png → ref.original.png` *before* the ComfyUI round-trip (crash-safe); re-runs read from `ref.original.png` so denoise never compounds. Defaults to no-op when `ref.original.png` exists; `--force` re-refines from the archive. Re-uses `generate_ref_image.py`'s template parser via lazy import so prompts stay consistent across stages.
- `tools/asset_pipeline.py`: new `REFINE_STRENGTH_BY_CATEGORY` table (vegetation 0.60, structure 0.40, prop 0.50, figure 0.50, animated 0.50, default 0.50) keyed off the asset-id category prefix. New `maybe_refine_ref()` stage runs between `maybe_auto_ref()` and `maybe_multi_view()` in `branch_mesh` (and via that, `branch_animated`). Always-on for `--kind mesh|animated`; opt-out is `--no-refine-ref`. New flags: `--no-refine-ref`, `--refine-ref-force`, `--refine-ref-strength`, `--refine-ref-seed`, `--refine-ref-prompt-suffix`. Re-uses `--comfy-server` from stage 0.
- `tools/HUNYUAN_RUNBOOK.md`: §0 pre-flight gained a FLUX.2 klein checkpoint presence check + a new "Downloading FLUX.2 [klein] 9B Base" subsection with the `huggingface-cli download` block (UNet + shared CLIP-L / T5-XXL / VAE). §4 gained a "Refining ref images (stage 0.25)" subsection covering the per-category defaults table, override flag, archive scheme, three example invocations, and VRAM coordination notes. §6 troubleshooting got three new rows (missing checkpoint, identical/warped output, upload size error).
- `docs/design-docs/ASSET_PIPELINE.md`: added `Refine` / `Archive` / `RefRefined` nodes to the §3 mermaid graph with the dashed `Refine -.-> Archive` audit edge. New stage-0.25 callout block above the existing stage-0.5 one explains the why, the per-category strength table, the archive-and-swap scheme, and the transparency to downstream stages.
- `prompts/asset-templates/_STYLE_GUIDE.md`: new "Stage 0.25 — automatic ref refinement" section. Canonical `REFINE_PROMPT_SUFFIX` text is checked in here as a quotation block and called out as needing to stay byte-identical with the constant in `refine_ref_image.py`. Per-category denoise table is duplicated for author-facing visibility with a pointer to `tools/asset_pipeline.py` for permanent edits.

**Pipeline shape (new):**
```
Stage 0     (Flux → ref.png  OR  hand-drop ref.png)
   │
   ▼
Stage 0.25  (FLUX.2 [klein] img2img → refined ref.png; ref.original.png archived)  ← always-on for mesh/animated
   │
   ▼
Stage 0.5   (Zero123++ → 6 views) ── optional
   │
   ▼
Stage 1     (Hunyuan3D → raw .glb)
   ...
```

**Outcome:** `python tools/asset_pipeline.py --help` lists all five new `--refine-ref-*` flags. `python tools/refine_ref_image.py --help` parses cleanly. `python tools/refine_ref_image.py vegetation_eucalyptus_mature --strength 0.6 --print-prompt-only` resolves the template via the cross-script import and produces the expected suffix-appended prompt.

**Correction (same day, before download):** After scoping the workflow against ComfyUI's official FLUX.2 Klein 9B template, three assumptions in the first draft of `refine.json` were wrong and have been fixed:
1. **Loader directory.** FLUX.2 Klein lives in `models/diffusion_models/` (not `models/unet/`); ComfyUI's `UNETLoader` resolves both, but the canonical Klein workflow uses the former.
2. **Text encoder.** FLUX.2 Klein uses a *single* Qwen 3 8B encoder with `CLIPLoader(type="flux2")`, not the FLUX.1 `DualCLIPLoader` + CLIP-L + T5-XXL pair. Swapped the node class and dropped the second loader.
3. **Guidance.** FLUX.2 does not use `FluxGuidance`. Collapsed the FLUX.1 `BasicGuider + FluxGuidance + SamplerCustomAdvanced + RandomNoise + KSamplerSelect + BasicScheduler` chain into a single `KSampler` node (CFG 1.0, euler, simple, 40 steps, variable denoise). Added a negative `CLIPTextEncode` for KSampler's required `negative` input.

Filenames + repos (verified against HF Hub directory listings):
- `models/diffusion_models/flux-2-klein-base-9b-fp8.safetensors` (9.57 GB) ← `black-forest-labs/FLUX.2-klein-base-9b-fp8` (gated).
- `models/text_encoders/qwen_3_8b_fp8mixed.safetensors` (8.66 GB) ← `Comfy-Org/vae-text-encorder-for-flux-klein-9b` at `split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors` (ungated; note "encorder" typo in the actual repo name).
- `models/vae/flux2-vae.safetensors` (321 MB) ← `Comfy-Org/flux2-dev` at `split_files/vae/flux2-vae.safetensors` (ungated).

Runbook download block + troubleshooting row updated to match. The `_comment` field at the top of `refine.json` documents the FLUX.1 → FLUX.2 node-graph delta so a future maintainer doesn't have to re-derive it.

**Download status (all complete, 2026-05-18):**
- `flux2-vae.safetensors` — 321 MB at `models/vae/`.
- `qwen_3_8b_fp8mixed.safetensors` — 8.1 GB at `models/text_encoders/`.
- `flux-2-klein-base-9b-fp8.safetensors` — 9.0 GB at `models/diffusion_models/`. Required gated-repo auth via `hf auth login --token <…>` after accepting the FLUX Non-Commercial License in a browser. Total: ~17.4 GB on disk.

**Smoke test (2026-05-18, vegetation_eucalyptus_mature):**
- `python tools/refine_ref_image.py vegetation_eucalyptus_mature --strength 0.6` completed in 12 s wall clock (40 steps × 0.6 denoise = 24 effective sampling steps on RTX 5090, FLUX.2 Klein 9B FP8 warm-cache).
- `ref.original.png` (50 KB hand-picked source from 2026-05-13) preserved; `ref.png` rewritten to 288 KB refined output. MD5s differ as expected.
- Re-run no-op confirmed: second invocation skipped with "ref.original.png present (use --force to re-refine)".
- ComfyUI workflow JSON accepted on first submit; no node-class mismatch errors. The corrected FLUX.2 contract (single CLIPLoader + KSampler + flux2-vae) works end-to-end against the live ComfyUI server.

**Follow-ups:**
- Smoke-test stage 0.25 on `vegetation_eucalyptus_mature` once the diffusion model lands. Compare the refined ref against `ref.original.png` to confirm vegetation 0.60 is the right denoise — too low ≈ no visible palette shift, too high ≈ silhouette warping.
- Combined chain run: `--auto-ref --multi-view --era shared` should now exercise stages 0 → 0.25 → 0.5 → 1 → 2 → optimize → register sequentially. This was the previous entry's open follow-up; stage 0.25 slots in front of it.
