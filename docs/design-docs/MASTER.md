# Witness Interactive 3D — Master Design Document

- **Status:** Draft
- **Owners:** @royceshannon2
- **Last updated:** 2026-04-17

This document is the umbrella. It names what the project is, what exists today, what is missing, and which per-subsystem design doc owns each detail. It deliberately does **not** duplicate content from those docs — it links to them.

---

## 1. Vision

A first-person, photoreal, historically grounded interactive work set in the Bisesero Hills of Rwanda's Western Province. The player returns as a modern-day investigator (2026) to a grandparent's abandoned compound and, by touching environmental evidence, snaps into 1994 to re-live fragments of the Rwandan genocide from the grandparent's perspective. Progress is non-linear: players reconstruct a single night from three morally valid interpretations of the same evidence. The game never judges the interpretation — it only reveals what each entails.

Built on **Babylon.js 9** + **Havok Physics**, with assets generated locally on an RTX 5090 via **Hunyuan3D 2.1**, baked to 8K PBR, and delivered as Draco/KTX2-compressed `.glb`.

See: [`PRD.md`](PRD.md) for the full product vision and acceptance criteria.

---

## 2. Repository map

Complete inventory with honest status. Status values:

- **production** — meets quality bar, actively used
- **skeleton** — real code, correct shape, thin
- **prototype** — works but unacceptable for shipping
- **stub** — placeholder file, empty or near-empty
- **stale** — contradicts current direction, must be removed or rewritten
- **empty** — directory exists with no useful content

```
Witness-Interactive-3D/
├── CLAUDE.md                                       production   (post-fix)
├── ARCHITECTURE.md                                 MISSING (rule requires it)
├── .claude/rules/{documentation,babylon-patterns}  production
├── .claude/projects/witness-interactive/memory/    skeleton     (auto-memory)
├── assets/source/{generated,references}/           empty
├── processed/{collisions,glb,lods,textures}/       empty
├── prompts/{asset-templates,scene-requests}/       empty
├── scenes/scene-001/*.md.txt                       stub
├── tools/*.py.py                                   stub         (doubled extension)
├── docs/
│   ├── design-docs/
│   │   ├── MASTER.md                               this doc
│   │   ├── PRD.md                                  production
│   │   ├── NARRATIVE.md                            production   (renamed from STORY_TREE_SHEPHERD_LEDGER.md)
│   │   ├── WORLD.md                                production   (renamed from SETTING_BISESERO.md)
│   │   ├── PUZZLE_DESIGN.md                        production
│   │   ├── CHRONOS_SWITCH.md                       stub         (to be written)
│   │   ├── ASSET_PIPELINE.md                       stub         (to be written)
│   │   ├── RENDERING.md                            stub         (to be written)
│   │   ├── STORY_TREE.md                           DELETED      (was stale template)
│   │   └── 0000-design-doc-template.md             production
│   ├── current-state/PROTOTYPE_AUDIT.md            to be written
│   ├── decisions/
│   │   ├── CHANGELOG_DETAILED.md                   to be created
│   │   └── adrs/0000-template.md                   production
│   ├── asset-{index,log}.md.txt                    stub         (rename to .md)
│   └── mental-cache.md                             skeleton     (engineering log template)
└── witness-interactive-vite/
    ├── package.json                                production   (Babylon 9, Vite 8, TS 5.9 — Havok missing)
    ├── index.html, tsconfig.json                   production
    ├── public/                                     empty
    └── src/
        ├── main.ts                                 prototype    (see PROTOTYPE_AUDIT.md)
        ├── counter.ts                              stale        (Vite template leftover)
        ├── style.css                               skeleton
        ├── assets/                                 stub         (Vite boilerplate art)
        └── narrative/
            ├── StateManager.ts                     skeleton
            ├── Actions.ts                          skeleton
            ├── NarrativeController.ts              skeleton
            ├── Graph.json                          production   ("Shepherd's Ledger" DAG)
            ├── README.md                           production
            └── INTEGRATION_EXAMPLE.md              production
```

---

## 3. Subsystem list

Each subsystem owns a design doc and will own a directory under `src/`. The master doc is the only place the full list lives; every other doc stays scoped to its one concern.

| Subsystem | Purpose | Design doc | Target code home |
|---|---|---|---|
| **Narrative** | State, flags, branches, save/load | [`NARRATIVE.md`](NARRATIVE.md) + [`PUZZLE_DESIGN.md`](PUZZLE_DESIGN.md) | `src/narrative/` |
| **Chronos (Time)** | Present ↔ Past era switching, memory fragments | [`CHRONOS_SWITCH.md`](CHRONOS_SWITCH.md) · [`TIMELINE_SYNC.md`](TIMELINE_SYNC.md) | `src/core/` |
| **World** | Terrain, locations, vegetation, structures, props | [`WORLD.md`](WORLD.md) | `src/world/` |
| **Rendering** | Scene, lighting, post-fx, materials | [`RENDERING.md`](RENDERING.md) | `src/engine/` |
| **Assets** | Hunyuan3D pipeline, bake, compress, load | [`ASSET_PIPELINE.md`](ASSET_PIPELINE.md) | `tools/`, `src/io/` |
| **Physics** | Havok integration | (section in RENDERING.md) | `src/engine/Physics.ts` |
| **Interaction** | Input, raycast, pickup, fragment triggers | (section in CHRONOS_SWITCH.md) | `src/interaction/` |
| **Audio** | Ambience, narration, diegetic layers | (TBD — own doc later) | `src/audio/` |
| **UI** | Ledger, HUD, reflection prompts | (TBD — own doc later) | `src/ui/` |
| **Bootstrap** | Engine + canvas lifecycle, scene graph root | (trivial, no doc) | `src/bootstrap/` |

---

## 4. Target source layout

The prototype is one file. The target is a clean subsystem tree. This layout is the contract — every module belongs in exactly one directory.

```
witness-interactive-vite/src/
├── bootstrap/
│   └── main.ts                 # engine, canvas, render loop, top-level scene wiring
├── engine/
│   ├── SceneFactory.ts         # scene construction, fog, camera
│   ├── RenderingPipeline.ts    # DefaultRenderingPipeline config, tone-map, vignette, SSAO
│   ├── Lighting.ts             # sun, sky, storm rim, shadow generator
│   ├── Materials.ts            # shared PBRMaterial library
│   └── Physics.ts              # Havok init, PhysicsAggregate helpers
├── world/
│   ├── Terrain.ts              # ground, heightfield, isFlat helper
│   ├── locations/              # one module per canonical location
│   │   ├── FamilyCompound.ts
│   │   ├── LakeShore.ts
│   │   ├── Cellar.ts
│   │   ├── Ravine.ts
│   │   └── Heights.ts
│   ├── vegetation/             # matooke, eucalyptus, grass
│   ├── structures/             # rugo, shopfront, church, dock
│   └── props/                  # jerrycan, bicycle, sandbag, truck
├── core/
│   ├── TimeManager.ts          # era state, crossfade, layer mask toggle
│   ├── LayerMasks.ts           # bitmask constants, tagging helpers
│   ├── MemoryFragment.ts       # proximity trigger objects (TBD)
│   └── index.ts                # barrel export
├── narrative/                  # already present
│   ├── StateManager.ts
│   ├── Actions.ts
│   ├── NarrativeController.ts
│   └── Graph.json
├── interaction/
│   ├── PlayerController.ts     # movement, pointerlock, gravity
│   ├── InteractableRegistry.ts # picks, hovers, fragment detection
│   └── Perspective.ts          # Protector vs. Hidden mode modifiers
├── audio/
│   └── AudioManager.ts
├── ui/
│   ├── HUD.ts                  # date label, crosshair, hints
│   └── LedgerUI.ts             # the unfinished letter + ledger pages
└── io/
    ├── AssetLoader.ts          # .glb + Draco + KTX2
    └── SaveSystem.ts           # thin wrapper over narrative state serializer
```

Detailed module responsibilities, public APIs, and dependency arrows live in [`ARCHITECTURE.md`](../../ARCHITECTURE.md).

---

## 5. Current state, honestly

The project is **roughly 10% implemented** against the vision, with the prototype front-loaded into rendering and the remaining 90% concentrated in: narrative integration, the time-switching mechanic, the actual game content, and the asset pipeline.

What is real:
- The narrative data model and event bus (`src/narrative/*`) — correct architecture, no tests, no scenes using it.
- `Graph.json` — a complete 35-node DAG for "The Shepherd's Ledger."
- Design docs for setting, story, and puzzles — comprehensive.
- A single Babylon scene (`main.ts`) that renders a plausible 1994 Kigali road with procedural buildings, figures, and a checkpoint. See [`PROTOTYPE_AUDIT.md`](../current-state/PROTOTYPE_AUDIT.md) for why it is not salvageable as-is.

What is pretended:
- Bisesero Hills environment — not built. The prototype is Kigali, not Bisesero. Every location in `WORLD.md` is a design, not an asset.
- Havok physics — mandated by `CLAUDE.md` and `babylon-patterns.md`, not installed.
- Hunyuan3D asset pipeline — the PRD describes it; `tools/*.py.py` are empty stubs with a doubled file extension.
- Narrative ↔ 3D bridge — zero lines of code connect them. The narrative system has never been imported by a scene.
- Save/load, audio, interaction system, UI for the ledger — none designed, none built.

---

## 6. Gap matrix

Each subsystem rated across four gates. `—` means the column does not apply.

| Subsystem | Designed | Documented | Implemented | Tested |
|---|---|---|---|---|
| Narrative (state + events) | ✅ | ✅ | 🟡 skeleton | ❌ |
| Narrative content (Graph.json) | ✅ | ✅ | ✅ | ❌ |
| Chronos Switch | 🟡 sketched in chat | ❌ | ❌ | ❌ |
| World — Bisesero locations | ✅ | ✅ | ❌ | — |
| World — prototype Kigali | — | ❌ | 🟡 prototype | ❌ |
| Rendering pipeline | 🟡 inline in prototype | ❌ | 🟡 prototype | ❌ |
| Materials library | 🟡 inline in prototype | ❌ | 🟡 prototype | — |
| Physics (Havok) | ✅ in CLAUDE.md | ❌ | ❌ (not installed) | ❌ |
| Asset pipeline | ✅ in PRD | ❌ | ❌ | ❌ |
| Interaction / input | ❌ | ❌ | 🟡 keyboard-only in prototype | ❌ |
| Audio | ❌ | ❌ | ❌ | ❌ |
| UI — Ledger | ✅ in design | 🟡 in NARRATIVE.md | ❌ | ❌ |
| UI — HUD | — | ❌ | 🟡 prototype | — |
| Save/Load | 🟡 serializer only | 🟡 in README | 🟡 serializer only | ❌ |

---

## 7. Work ordering

This is a dependency graph, not a schedule. Each node unblocks the next. The goal is to make the first vertical slice — one fragment, one era switch, one narrative advance — work end-to-end before widening.

```mermaid
graph TD
  A[Master doc + ARCHITECTURE.md + per-subsystem stubs] --> B[Prototype audit — decide what to salvage]
  B --> C[Extract engine/ and world/ modules from main.ts<br/>no behaviour change]
  C --> D[Install Havok, wire Physics.ts]
  C --> E[Design Chronos Switch: TimeManager + LayerMasks]
  D --> F[Vertical slice: Family Compound, Present era only]
  E --> F
  F --> G[Add Past era variant of compound]
  G --> H[First MemoryFragment — shrine → ledger page 1]
  H --> I[Wire fragment → narrativeController.triggerPuzzleCompletion]
  I --> J[Ledger UI shows updated page]
  J --> K[Widen: second location (Cellar), second fragment]
  K --> L[Second location's puzzle triggers act_2 flag]
  L --> M[Branch choice UI at act_3_the_choice]
  M --> N[Path A cellar reconstruction puzzle — full loop]
  N --> O[Paths B and C in parallel]
  O --> P[Act 4 Remembrance + all three endings]
  P --> Q[Audio pass, UI pass, save/load polish]
  Q --> R[Asset pipeline: replace procedural with Hunyuan3D GLBs]
```

The critical path is A → B → C → E → F → H → I. Everything to the right of that can be deferred.

---

## 8. Documentation rules

From [`.claude/rules/documentation.md`](../../.claude/rules/documentation.md):

1. `ARCHITECTURE.md` is updated whenever a new service, schema, or API contract is introduced.
2. Every completed task appends a technical summary to `docs/decisions/CHANGELOG_DETAILED.md`.
3. Every new function/class has a docstring explaining its role in the larger architecture.
4. Diagrams are always Mermaid.

Design docs live under `docs/design-docs/`. ADRs (decisions with trade-offs that outlive a single task) live under `docs/decisions/adrs/`. Engineering-session notes live in `docs/mental-cache.md`. Auto-memory for Claude lives in `.claude/projects/witness-interactive/memory/` — not checked into design docs.

---

## 9. Glossary

Terms that show up across multiple docs. Definition lives here; other docs link back.

- **Act** — One of four narrative sections (Return, Evidence, Choice, Remembrance).
- **Bisesero** — The hills in Rwanda's Western Province where the game is set.
- **Branch** — A point in `Graph.json` where the player commits to one of multiple mutually-exclusive continuations.
- **Chronos Switch** — The mechanic that snaps the player between Present (2026) and Past (1994) eras.
- **Compound** — The grandparent's abandoned family home; the game's hub location.
- **Era** — One of two timeline states: `Present` (2026) or `Past` (1994).
- **Evidence** — Environmental artifact in Act 2 that suggests one of the three survival paths.
- **Flag** — A named boolean in `StateManager.progress.flagsSet`. Persisted across save/load.
- **Fragment** (Memory Fragment) — A Present-era world object that, when interacted with, triggers an era switch.
- **Ledger** — The grandfather's journal. The player's primary UI surface and the source of narrative text.
- **Letter** — The fragmented 1994 letter the grandchild carries. Drives Act 1 → Act 2 exploration.
- **Node** — A vertex in `Graph.json`. Types: `scene`, `puzzle`, `branch`, `event`, `ending`.
- **Path** — One of three branches from `act_3_the_choice`: Hider, Escapist, Observer (a.k.a. Silent).
- **Perspective mode** — Within Path A, a gameplay modifier: `Protector` (mobile) vs. `Hidden` (constrained).
- **Rugo** — A traditional Rwandan household compound; the building archetype used in the prototype.
- **Shepherd's Ledger** — The full title of the in-game narrative.

---

## 10. Unresolved questions

Things that must be decided before relevant work starts. Each should become an ADR when answered.

1. **Chronos Switch — snap vs. preserve camera?** On era change, does the camera teleport to a scripted anchor in the Past, or stay in place while the world transforms around the player? (Leaning snap. See `CHRONOS_SWITCH.md` when written.)
2. **Asset volume.** The target is four locations × two eras = 8 full environments. Is that in scope for v1, or does v1 ship with Compound only?
3. **Havok necessity.** `CLAUDE.md` mandates it. But if nothing in Acts 1–2 actually needs physics (no stacking, no debris simulation), is the cost worth the dependency footprint? Candidate ADR.
4. **Language / localization.** Is the ledger English-only, English + Kinyarwanda, or Kinyarwanda-first with English subtitles? Affects UI and audio scope.
5. **NPC authoring model.** `WORLD.md` says "no NPCs, only environmental storytelling," but the 1994 Past eras will plausibly need figures in the distance. Decide: silhouettes only, or full figures with animation?
6. **Target platforms.** Desktop browser only, or also VR (WebXR)? The Chronos Switch mechanic reads very differently in VR.

---

## 11. Where to go next

- Read [`PROTOTYPE_AUDIT.md`](../current-state/PROTOTYPE_AUDIT.md) before touching `main.ts`.
- Read [`NARRATIVE.md`](NARRATIVE.md) and [`PUZZLE_DESIGN.md`](PUZZLE_DESIGN.md) to understand the story content.
- Read [`WORLD.md`](WORLD.md) for the environmental target.
- Read [`CHRONOS_SWITCH.md`](CHRONOS_SWITCH.md) for the core mechanic spec (once written).
- Read [`ARCHITECTURE.md`](../../ARCHITECTURE.md) for module boundaries and dependency graph.
