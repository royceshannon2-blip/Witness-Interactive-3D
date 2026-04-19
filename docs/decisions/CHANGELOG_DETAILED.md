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
