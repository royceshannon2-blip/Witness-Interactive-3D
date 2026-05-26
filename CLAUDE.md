# CLAUDE.md — Witness Interactive 3D

A first-person, photoreal historical interactive work set in the Bisesero Hills, Rwanda. Built with **Babylon.js 9** and **Havok Physics**, using **Hunyuan3D 2.1** for asset generation and delivered as 8K-PBR Draco/KTX2 `.glb` files.

**Web app location:** `witness-interactive-vite/` — all terminal commands should be prefixed with `cd witness-interactive-vite`.

---

## Start Here

1. **New to the codebase?** Read [`docs/design-docs/MASTER.md`](docs/design-docs/MASTER.md) for the umbrella overview, repo map, and gap analysis.
2. **About to modify the prototype?** Read [`docs/current-state/PROTOTYPE_AUDIT.md`](docs/current-state/PROTOTYPE_AUDIT.md) first — it documents current assumptions and known limitations.
3. **Need the module map?** See [`ARCHITECTURE.md`](ARCHITECTURE.md) for dependency graphs and component boundaries.

---

## By Topic

### Project Vision & Design
- **[PRD](docs/design-docs/PRD.md)** — product requirements and core narrative hooks.
- **[WORLD](docs/design-docs/WORLD.md)** — environment, geography, and setting.
- **[PUZZLE_DESIGN](docs/design-docs/PUZZLE_DESIGN.md)** — puzzle mechanics and player interaction.
- **[OPENING_SEQUENCE](docs/design-docs/OPENING_SEQUENCE.md)** — first-time player experience.

### Asset & Technical Pipeline
- **[ASSET_PIPELINE](docs/design-docs/ASSET_PIPELINE.md)** — full spec for generating and managing 3D assets locally (mesh, splat, tileset, navmesh, NME, animated).
  - **Entry point:** `python tools/witness.py generate <id>` — see `.claude/rules/asset-pipeline.md` for the normative rule.
- **[ASSET_GENERATION_OVERVIEW](docs/design-docs/ASSET_GENERATION_OVERVIEW.md)** — quick walkthrough of the generation stages.
- **[asset-index](docs/asset-index.md)** — registry of all generated assets.

### Rendering & Materials
- **[RENDERING](docs/design-docs/RENDERING.md)** — lighting, post-processing, PBR material setup, performance budgets.
- **[CHRONOS_SWITCH](docs/design-docs/CHRONOS_SWITCH.md)** — era-tagging system for historical context switching.

### Narrative & Gameplay
- **[NARRATIVE](docs/design-docs/NARRATIVE.md)** — branching logic, state management, action bus, narrative graph.
- **[MISSION_BLUEPRINT](docs/design-docs/MISSION_BLUEPRINT.md)** — mission structure and progression.
- **[TIMELINE_SYNC](docs/design-docs/TIMELINE_SYNC.md)** — time mechanics and synchronization.
- **[AUDIO_ARCHITECTURE](docs/design-docs/AUDIO_ARCHITECTURE.md)** — spatial audio and dialogue systems.
- **[witness-interactive-vite/src/narrative/README.md](witness-interactive-vite/src/narrative/README.md)** — API reference for StateManager, Actions, NarrativeController.

### Development Standards & Rules
- **[.claude/rules/babylon-patterns.md](.claude/rules/babylon-patterns.md)** — Babylon.js 9 conventions (PBR, Havok, ThinInstances, async loading).
- **[.claude/rules/asset-pipeline.md](.claude/rules/asset-pipeline.md)** — normative rule for authoring assets (required reading before adding any 3D content).
- **[.claude/rules/documentation-standards.md](.claude/rules/documentation-standards.md)** — how to consult cloned Babylon.js docs and handle version conflicts.
- **[.claude/rules/documentation.md](.claude/rules/documentation.md)** — architecture updates, CHANGELOG maintenance, docstring requirements.

### Current State & Decisions
- **[PROTOTYPE_AUDIT](docs/current-state/PROTOTYPE_AUDIT.md)** — honest review of main.ts prototype, known issues, and next steps.
- **[CHANGELOG_DETAILED](docs/decisions/CHANGELOG_DETAILED.md)** — technical summary of all completed tasks.
- **[SCALABILITY_PLAN](SCALABILITY_PLAN.md)** — performance targets and optimization roadmap.

---

## Quick Reference

### Essential Commands
```fish
# Launch web app
cd witness-interactive-vite && npm run dev

# Generate a 3D asset (standard mesh)
cd witness-interactive-vite && python ../tools/witness.py generate <id>

# Generate with options
python ../tools/witness.py generate <id> --multi-view        # add 6-view synthesis
python ../tools/witness.py generate <id> --no-refine-ref     # skip FLUX.2 stage 0.25
python ../tools/witness.py generate <id> --kind splat --source <file.spz>

# Server management
python ../tools/witness.py start                             # boot ComfyUI + Hunyuan3D
python ../tools/witness.py status                            # model inventory + asset state

# Build & preview
npm run build                                               # TypeScript check + prod build
npm run preview                                             # test production build locally
npx babylonjs-viewer <asset.glb>                           # preview generated assets
```

### Naming Conventions
- **Classes/Files:** `CamelCase` (e.g. `TimeManager.ts`, `FamilyCompound.ts`)
- **Variables/Functions:** `camelCase` (e.g. `initializeHavok()`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g. `MAX_TEXTURE_RES = 8192`)
- **Assets:** `snake_case` with category prefix (e.g. `prop_ledger_book`, `structure_family_compound_primary`)

### Key Runtime APIs
- **AssetLibrary** — GLB asset loading & instantiation; import from `src/io/AssetLibrary.ts`
- **SplatLibrary** — Gaussian splat loading; import from `src/io/SplatLibrary.ts`
- **TilesetMount** — 3D Tiles streaming; import from `src/io/TilesetMount.ts`
- **NarrativeController** — story progression API; import from `src/narrative/NarrativeController.ts`
- **StateManager** — player state & flags; import from `src/narrative/StateManager.ts`
- **actionBus** — narrative → 3D event bridge; subscribe in scenes

---

## Additional Resources

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — dependency graphs and module boundaries.
- **[mental-cache.md](docs/mental-cache.md)** — project context snapshots and decision history.
- **[Phase 1 Asset List](docs/design-docs/PHASE1_ASSET_LIST.md)** — prioritized asset generation plan.
- **[Babylon.js Documentation](docs/reference/babylon.js-documentation/README.md)** — complete table of contents for the cloned v6/v7 API reference. Start here for any Babylon API questions. See [documentation-standards.md](.claude/rules/documentation-standards.md) for usage guidelines.

---

## Development Checklists

### Adding a New 3D Asset
See `.claude/rules/asset-pipeline.md` §6 for the full checklist. Quick summary:
- [ ] Asset id chosen per `<category>_<name>_<variant?>`
- [ ] Prompt template authored (for mesh/animated kinds)
- [ ] `python tools/witness.py generate <id> --kind <kind>` completes
- [ ] Registry entry added to `docs/asset-index.md`
- [ ] Public copy exported to `witness-interactive-vite/public/assets/`
- [ ] Runtime code uses appropriate library (AssetLibrary/SplatLibrary/TilesetMount), not literal URL
- [ ] CHANGELOG entry documents the asset id

### Adding a New CLI Feature to Asset Generation
See `.claude/rules/asset-pipeline.md` §7 for CLI-GUI parity. Quick summary:
- [ ] New flag/option/subcommand added to `python tools/witness.py`
- [ ] **GUI controls wired in `witness-interactive-vite/src/ui/` (see ARCHITECTURE.md for current UI structure)**
- [ ] GUI and CLI behaviors are synchronized (same defaults, same validation)
- [ ] CHANGELOG entry documents the new CLI and GUI capability

### Adding a New Narrative Branch
See `docs/design-docs/NARRATIVE.md` for the full spec. Quick summary:
- [ ] Node defined in `src/narrative/Graph.json` with `requiredFlags` and `unlocksFlags`
- [ ] Handler logic added to `src/narrative/Actions.ts` if side effects needed
- [ ] NARRATIVE.md updated with new branch in Mermaid diagram
- [ ] 3D scene subscribes to `actionBus.onStateChange()` to respond visually

---

## Where Everything Is

| Topic | Live Here |
|-------|-----------|
| Project specs | `docs/design-docs/` |
| Current state | `docs/current-state/` |
| Architecture & decisions | `ARCHITECTURE.md`, `docs/decisions/` |
| Web app code | `witness-interactive-vite/src/` |
| Asset generation pipeline | `tools/` |
| Development standards | `.claude/rules/` |
| Babylon.js documentation TOC | `docs/reference/babylon.js-documentation/README.md` |
| Babylon.js API reference | `docs/reference/babylon.js-documentation/content/` |
| Cloned docs index | `docs/mental-cache.md` |

---

## For Anthropic Employees & Contributors
- **Email:** royceshannon2@gmail.com
- **Git:** main branch is `master`; always merge to `master`
- **CI:** all non-critical merges freeze after feature-cut dates (check CHANGELOG)
