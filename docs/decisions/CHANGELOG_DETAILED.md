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
