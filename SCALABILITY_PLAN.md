# Scalability Plan — Adding a New Historical Mission

- **Status:** Draft
- **Last updated:** 2026-04-18
- **Owners:** @royceshannon2
- **Companion docs:** [`ARCHITECTURE.md`](ARCHITECTURE.md) (subsystem contracts), [`docs/design-docs/MISSION_BLUEPRINT.md`](docs/design-docs/MISSION_BLUEPRINT.md) (authoring template), [`docs/design-docs/ASSET_PIPELINE.md`](docs/design-docs/ASSET_PIPELINE.md) (how to generate the geometry/textures), [`docs/design-docs/NARRATIVE.md`](docs/design-docs/NARRATIVE.md) (graph authoring), [`docs/design-docs/AUDIO_ARCHITECTURE.md`](docs/design-docs/AUDIO_ARCHITECTURE.md) (zones and ambiences).

---

## 0. What this document is for

This is the authoritative guide for authoring a **second** mission, a **third** mission, and every mission after that. It specifies the **Mission Manifest** schema, the on-disk folder layout, the validation rules, and the anti-patterns that would collapse the template. The engine ships with exactly one mission — *The Shepherd's Ledger* — and that mission is the reference implementation of every contract in this document.

The guiding principle is inverted from a normal game: **the engine is the template, the mission is the content**. If you find yourself modifying `src/` to ship a second mission, you are doing it wrong and this document will tell you so.

---

## 1. Engine vs. mission — what lives where

| Concern | Lives in | Versioned with |
|---|---|---|
| Rendering pipeline, tone mapping, freeze pass, SceneOptimizer | `src/rendering/`, `src/performance/` | Engine code |
| Time-of-day / era switch, layer masks, Chronos transition | `src/core/` | Engine code |
| Narrative state machine, action bus, serialization | `src/narrative/` | Engine code |
| Mission loader, manifest schema, teardown | `src/mission/` | Engine code |
| Asset library, save system | `src/io/` | Engine code |
| Spatial audio primitives, zone fade logic | `src/audio/` | Engine code |
| HUD framework (ledger, ortho camera) | `src/ui/` | Engine code |
| AI dialogue client, fallback, cache | `src/ai/` | Engine code |
| **A specific story's graph, anchors, assets, audio, dialogue fallbacks** | **`public/missions/<mission-id>/`** | **Per-mission data** |

The division is hard. The engine knows **nothing** about Bisesero, 1994, the Shepherd's Ledger, or any character name. Those are manifest entries, graph nodes, asset filenames, and audio files inside a single mission folder. Swap the folder, swap the mission.

See [`ARCHITECTURE.md` §5](ARCHITECTURE.md#5-subsystem-contracts) for the per-subsystem contract that enforces this split.

---

## 2. On-disk layout of a mission

Every mission is a single folder under `witness-interactive-vite/public/missions/<mission-id>/`. The `<mission-id>` is a lowercase kebab-case slug used as the URL segment, the manifest `id`, and the cache scope.

```
public/missions/<mission-id>/
├── manifest.json                  # Mission Manifest (see §3)
├── narrative/
│   ├── Graph.json                 # DAG of branches, puzzles, endings
│   └── dialogue/                  # Per-anchor fallback text and optional ink
│       ├── cellar_door_latch.md
│       └── ...
├── assets/                        # .glb per asset id
│   ├── structure_rugo_wall.glb
│   ├── prop_jerrycan.glb
│   └── ...
├── audio/
│   ├── zones/                     # Per-location ambiences, per era
│   │   ├── family_compound_present.ogg
│   │   ├── family_compound_past.ogg
│   │   └── ...
│   ├── narrator/                  # Investigator / ledger VO (if any)
│   └── sfx/                       # Anchor-specific cues
├── ai-cache/                      # Shipped read-only LLM responses, bundled at build
│   ├── a4c2e1...<contextHash>.json
│   └── ...
├── environment/                   # Optional per-era .env skybox IBL
│   ├── present.env
│   └── past.env
├── preview.jpg                    # Mission-select thumbnail
└── README.md                      # One-page mission brief, historical sources, citations
```

**Rules:**

1. Nothing outside this folder is allowed to reference a mission by name. If the engine `grep`s for `"shepherds-ledger"`, that's a bug.
2. File names are deterministic. The manifest's `requiredAssets: ["prop_jerrycan"]` resolves to `assets/prop_jerrycan.glb`. No aliases, no redirects.
3. `README.md` is required. It names the historical period, the geographical location, the primary sources, and the contact for whoever is responsible for the content. See §9.

---

## 3. The Mission Manifest

`manifest.json` is the single source of truth for everything the engine needs to boot a mission. It is validated at load time by `MissionLoader`; a validation failure aborts the mission load cleanly and returns the user to the title screen with a readable error.

### 3.1 Full schema

```json
{
  "$schema": "../../schemas/mission-manifest.schema.json",
  "id": "shepherds-ledger",
  "version": "1",
  "title": "The Shepherd's Ledger",
  "subtitle": "Bisesero, 1994 — 2026",

  "historical": {
    "location": { "name": "Bisesero Hills", "country": "Rwanda", "lat": -2.26, "lon": 29.27 },
    "period": { "pastYear": 1994, "presentYear": 2026, "durationDays": 100 },
    "contentWarning": "Depicts the aftermath and memory of the 1994 genocide against the Tutsi. No graphic imagery is shown on-screen; narrative references are direct.",
    "sources": [
      { "title": "Bisesero resistance — Wikipedia", "url": "https://en.wikipedia.org/wiki/Bisesero" },
      { "title": "African Rights survivor testimony archive (1995)", "citation": "..." }
    ]
  },

  "performance": {
    "minimumProfile": "LOW",
    "recommendedProfile": "MEDIUM",
    "lowProfileUseLod1AsLod0": true,
    "maxSceneMeshesHint": 3500,
    "maxShadowCasters": 32
  },

  "requiredAssets": [
    "structure_rugo_wall",
    "structure_rugo_roof",
    "prop_jerrycan",
    "prop_ledger_book",
    "vegetation_eucalyptus",
    "terrain_compound",
    "terrain_ridge"
  ],

  "environment": {
    "present": { "skybox": "environment/present.env", "intensity": 1.0 },
    "past":    { "skybox": "environment/past.env",    "intensity": 0.85 }
  },

  "locations": [
    {
      "id": "family_compound",
      "label": "Family compound",
      "position": { "x": 0, "y": 0, "z": 0 },
      "assets": [
        { "asset": "structure_rugo_wall", "count": 8, "placementSeed": 14421 },
        { "asset": "structure_rugo_roof", "count": 3 },
        { "asset": "prop_jerrycan", "count": 2 },
        { "asset": "terrain_compound", "count": 1 }
      ],
      "audioZones": [
        { "id": "compound_ambient_present", "era": "present", "clip": "audio/zones/family_compound_present.ogg", "radius": 40, "gain": 0.6 },
        { "id": "compound_ambient_past",    "era": "past",    "clip": "audio/zones/family_compound_past.ogg",    "radius": 40, "gain": 0.7 }
      ],
      "era": "both"
    }
  ],

  "anchors": [
    {
      "id": "cellar_door_latch",
      "location": "family_compound",
      "localPosition": { "x": -3.2, "y": 0.4, "z": 5.1 },
      "era": "past",
      "label": "A latch, newly cut",
      "requiredFlags": [],
      "unlocksFlags": ["found_cellar_evidence"],
      "fallbackDialogue": "The wood around the latch is paler than the rest of the door. Someone cut this in a hurry.",
      "ai": {
        "prompt": "You are the investigator examining a wooden cellar door latch that was installed in 1994 during the genocide. The surrounding wood is weathered but the latch is newly cut. Offer a single paragraph observation in the register of a memorial documentary. Do not invent details not present in the scene or the ledger.",
        "promptTemplate": "anchor_observation",
        "maxTokens": 120,
        "temperature": 0.35
      }
    }
  ],

  "narrativeGraph": "narrative/Graph.json",

  "ai": {
    "endpoint": "http://localhost:8082",
    "relevantFlags": [
      "found_cellar_evidence",
      "met_protector",
      "chose_path_hidden",
      "chose_path_escapist",
      "chose_path_silent"
    ],
    "cacheDir": "ai-cache/",
    "cacheBudgetMB": 50,
    "disableOn": ["LOW"]
  },

  "ui": {
    "ledgerTitle": "The Ledger",
    "openingCardMs": 2500,
    "hudProfile": "memorial"
  },

  "save": {
    "slotPrefix": "witness.shepherds-ledger.v1",
    "resumeAlwaysInEra": "present"
  }
}
```

### 3.2 Field-by-field

#### Top-level identity
| Field | Required | Notes |
|---|---|---|
| `id` | yes | Matches folder name. Must be unique across all shipped missions. |
| `version` | yes | Bump when you make a backwards-incompatible graph or flag change. `SaveSystem` uses this to decide migration. See [`docs/decisions/adrs/0001-narrative-edge-cases.md` §4](docs/decisions/adrs/0001-narrative-edge-cases.md). |
| `title`, `subtitle` | yes | Shown on the mission-select card and the opening title. |

#### `historical` — content provenance
A mission about real events is required to declare where the facts come from. This block is read by the in-game credits screen and is never bypassed.

| Field | Required | Notes |
|---|---|---|
| `location` | yes | Real place. `lat`/`lon` are optional but recommended for the future world-map select screen. |
| `period` | yes | Two years and a duration. Informs the era model. |
| `contentWarning` | yes | Shown on the title card and in the mission-select screen. |
| `sources` | yes, ≥1 | Citations for every non-fictional claim in the mission. |

#### `performance` — engine tuning hints
Consumed by `src/performance/`. See [`ARCHITECTURE.md` §6](ARCHITECTURE.md#6-target-hardware-profiles).

| Field | Required | Notes |
|---|---|---|
| `minimumProfile` | yes | `"LOW"` means the mission has been smoke-tested on a Chromebook. If you cannot verify this, author LOW-only assets and set `"LOW"`. Do not ship a mission whose `minimumProfile` you have not run. |
| `recommendedProfile` | yes | The tier that plays *well*, not just *at all*. |
| `lowProfileUseLod1AsLod0` | no | When true, LOW profile skips the LOD0 download entirely. Saves ~40% transfer for large missions. |
| `maxSceneMeshesHint`, `maxShadowCasters` | no | Soft caps. The SceneOptimizer will log a warning if the loaded scene exceeds these. |

#### `requiredAssets` — what to preload
Flat list of asset ids. Every id must resolve to `assets/<id>.glb`. No globs, no wildcards. The asset library pre-fetches these in parallel, bounded to N=4 concurrent fetches (see [`ARCHITECTURE.md` §8.2](ARCHITECTURE.md#82-assetlibrarypreload)).

#### `environment` — IBL and skybox
One `.env` per era. Use `createDefaultEnvironment` in the scene setup, swap textures on era transition. Keep file size under 4 MB for LOW profile parity.

#### `locations` — physical places in the mission
Each location is a logical group of meshes and audio zones. A mission may have one location (short memorial-visit missions) or many (exploration-driven missions). Every asset placed in a location is an instance of a `requiredAssets` entry.

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable slug. Anchors reference locations by id. |
| `position` | yes | World-space origin of the location's transform node. |
| `assets[].count` | yes | Uses Thin Instances for `count > 1`. See [Thin Instances doc](docs/reference/Documentation/content/features/featuresDeepDive/mesh/copies/thinInstances.md). |
| `assets[].placementSeed` | no | Deterministic seed for procedural placement. Required if you want reproducible screenshots. |
| `audioZones` | no | Spatial audio zones — see [`AUDIO_ARCHITECTURE.md`](docs/design-docs/AUDIO_ARCHITECTURE.md). |
| `era` | yes | `"present"`, `"past"`, or `"both"`. Controls the layer mask applied to this location's meshes. |

#### `anchors` — every interactive point
Anchors are the heart of the mission. An anchor is a single place the investigator can examine. Each anchor produces a ledger entry and may unlock flags that gate other anchors or graph nodes.

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable slug. |
| `location` | yes | Must match a `locations[].id`. |
| `localPosition` | yes | Local-space relative to the location origin. |
| `era` | yes | `"present"`, `"past"`, or `"both"`. Gates visibility via layer mask. |
| `requiredFlags`, `unlocksFlags` | no | Flag gates. Must be consistent with `narrativeGraph`. |
| `fallbackDialogue` | **yes** | Authored line that is returned when the AI service is unreachable, when the cache misses, or when the LOW profile disables AI. **Every anchor has one.** This is the narrative truth. |
| `ai.prompt` | no | If present, the AI service may synthesize a variant of `fallbackDialogue`. |
| `ai.promptTemplate` | no | Name of a project-wide prompt template (see §7). |
| `ai.maxTokens`, `ai.temperature` | no | Model settings. Defaults: 150 / 0.3. |

#### `narrativeGraph` — path to Graph.json
Relative to the mission folder. The engine requires a graph; a one-anchor mission still needs a graph with a start node and an end node.

#### `ai` — dialogue service configuration
| Field | Required | Notes |
|---|---|---|
| `endpoint` | no | Defaults to `http://localhost:8082`. Override per mission only for research setups. |
| `relevantFlags` | yes | **Allowlist** of flags that participate in the cache key hash. See [`ARCHITECTURE.md` §5.11](ARCHITECTURE.md#511-ai-dialogue-service). A flag that is not in this list does not invalidate the dialogue cache even if it changes. This prevents cache-key explosion. |
| `cacheDir` | no | Default `"ai-cache/"`. |
| `cacheBudgetMB` | no | Default 50. The runtime IndexedDB cache evicts LRU above this. |
| `disableOn` | no | Profile names where AI is fully disabled and all dialogue comes from `fallbackDialogue`. Default: `["LOW"]`. |

#### `ui` — HUD presentation
| Field | Required | Notes |
|---|---|---|
| `ledgerTitle` | yes | Header text on the ledger panel. |
| `openingCardMs` | no | Duration of the title card before control is returned. |
| `hudProfile` | yes | Must match a profile in `src/ui/profiles/`. Default for memorial-register missions: `"memorial"`. |

#### `save` — persistence
| Field | Required | Notes |
|---|---|---|
| `slotPrefix` | yes | Prevents save collisions between missions. Use `witness.<id>.v<version>`. |
| `resumeAlwaysInEra` | no | Default `"present"`. Locks in the save-always-resumes-in-Present contract from [`ADR-0001`](docs/decisions/adrs/0001-narrative-edge-cases.md). |

---

## 4. Step-by-step: adding a new mission

The following is a complete walkthrough. It assumes you have already authored the historical research and the narrative outline using [`docs/design-docs/MISSION_BLUEPRINT.md`](docs/design-docs/MISSION_BLUEPRINT.md) as a template.

### Step 1 — Pick an id and create the folder

```
witness-interactive-vite/public/missions/<mission-id>/
```

Kebab-case. No spaces, no capitals, no version suffix. Create the subfolders shown in §2.

### Step 2 — Write `README.md` first

Before a single asset is generated, the mission folder must contain a `README.md` that answers:

1. **What event is this about?** (Place, year, scope, population affected.)
2. **Who are the sources?** (Primary testimony, archival records, academic references.)
3. **What is the tonal register?** (Documentary? Memorial? Investigative?)
4. **What is explicitly off-limits?** (Graphic imagery, identifiable living persons, specific invented dialogue.)
5. **Who is the content owner?** (Someone accountable for historical accuracy, not just the engineer authoring the manifest.)

A mission without a written-and-reviewed `README.md` must not ship. The review step catches register drift before it becomes a thousand anchors deep.

### Step 3 — Author the narrative graph

Follow [`NARRATIVE.md`](docs/design-docs/NARRATIVE.md) for DAG rules. Place the result at `narrative/Graph.json`. Run `tools/validate_graph.py` (see follow-up in `CHANGELOG_DETAILED.md` 2026-04-18) for cycle detection.

### Step 4 — Author the Mission Blueprint

Use [`MISSION_BLUEPRINT.md`](docs/design-docs/MISSION_BLUEPRINT.md) as the template. Define anchors, echoes, and the three (or however many) moral paths **before** touching 3D. Every anchor named here becomes a `manifest.anchors[]` entry.

### Step 5 — Generate assets

Run the Hunyuan3D 2.1 pipeline described in [`ASSET_PIPELINE.md`](docs/design-docs/ASSET_PIPELINE.md) for every asset id you will reference. The output goes directly into `assets/<id>.glb`. Validate each one with `npx babylonjs-viewer`.

### Step 6 — Record audio zones

Per [`AUDIO_ARCHITECTURE.md`](docs/design-docs/AUDIO_ARCHITECTURE.md), record one present-era ambience and one past-era ambience per location, at minimum. Place in `audio/zones/`. Spatial clip format: OGG Vorbis 44.1 kHz mono, target ≤ 2 MB per clip for LOW profile parity. Spatial playback uses `spatialSound: true` with `distanceModel: 'exponential'` and `panningModel: 'HRTF'`. See the Babylon audio engine docs at [`audio/sounds.md`](docs/reference/Documentation/content/features/featuresDeepDive/audio/sounds.md).

### Step 7 — Author fallback dialogue for every anchor

For each `anchors[].id`, write the `fallbackDialogue` line. This is the authored line — the one that ships if the LLM is offline, the cache is cold, or the LOW profile is active. Treat it as the *canonical* line. Anything the LLM generates is a variant of this, not a replacement for it.

### Step 8 — Write `manifest.json`

Fill every required field per §3. Run `tools/validate_manifest.py` (to be written — see §5.5 validation rules). The validator catches missing files, broken flag references, and missing fallbacks.

### Step 9 — Generate the shipped AI cache

If the mission uses the AI dialogue service, run a scripted generation pass that iterates every anchor under every plausible flag combination from `ai.relevantFlags`, writes each response to `ai-cache/<contextHash>.json`. For a typical 60-anchor mission with 5 relevant flags, this is 60 × 2^5 = 1920 JSON files at roughly 1 KB each → ~2 MB shipped. The runtime uses this as a read-through cache so offline classrooms still get dialogue variation.

### Step 10 — Test on the minimum profile

The final step is not a line of code: it is a Chromebook. Boot the mission on the lowest machine declared in `performance.minimumProfile` and play it end to end. If it does not maintain 25 fps on that hardware, either drop assets, drop effects, or raise `minimumProfile`. Do not ship a mission whose declared floor you have not stood on.

### Step 11 — Add the mission to the mission-select screen

The mission-select screen reads `public/missions/index.json`, which is a flat list of mission-id strings. Append the new id and ship it. No source code is modified.

```json
// public/missions/index.json
["shepherds-ledger", "example-plaza"]
```

---

## 5. Validation rules

`tools/validate_manifest.py` (to be written) runs these checks. `MissionLoader` runs a subset of them at runtime and aborts cleanly on failure.

### 5.1 File existence
- Every id in `requiredAssets` resolves to an existing `.glb`.
- Every `audioZones[].clip` path exists.
- Every `environment.*.skybox` path exists.
- `narrativeGraph` path exists and parses as JSON.

### 5.2 Referential integrity
- Every `anchors[].location` matches a `locations[].id`.
- Every flag in `ai.relevantFlags` is defined somewhere in `Graph.json` (either as `requiredFlags` or `unlocksFlags` on some node).
- Every `anchors[].unlocksFlags` entry is consumed by at least one graph node's `requiredFlags`. (Unconsumed flags are almost always a typo.)
- Every `anchors[].requiredFlags` is produced by at least one graph node's `unlocksFlags` or another anchor's `unlocksFlags`.

### 5.3 Fallback completeness
- **Every** anchor has a non-empty `fallbackDialogue`. No exceptions.
- Every `fallbackDialogue` is ≤ 400 characters. (Longer lines usually mean the author is writing a scene, not a ledger entry — split into multiple anchors.)

### 5.4 Narrative graph integrity
- `Graph.json` has exactly one start node.
- Every non-terminal node has ≥ 1 outgoing edge.
- No cycles. (Run `tools/validate_graph.py`.)
- Every edge's `requiredFlags` are reachable from the start node.

### 5.5 Performance declaration honesty
- If `minimumProfile = "LOW"`, `requiredAssets.length * 2 MB (avg) ≤ 80 MB` total wire budget.
- If `performance.lowProfileUseLod1AsLod0 = true`, every required asset ships with a LOD1 tier.

### 5.6 Historical provenance
- `historical.sources.length ≥ 1`.
- `historical.contentWarning` is non-empty.

### 5.7 AI safety
- Every `anchors[].ai.prompt` passes the prompt-safety linter (§7).

---

## 6. Mission lifecycle

When the player selects a mission:

1. `MissionLoader.load(id)` reads `public/missions/<id>/manifest.json`.
2. The manifest is validated against the schema. On failure, abort with a readable error.
3. `io/AssetLibrary.preload(manifest.requiredAssets)` begins with N=4 parallelism.
4. `Scene` is constructed with a single primary camera and the ortho HUD camera (see [`ARCHITECTURE.md` §10](ARCHITECTURE.md#10-ui-rendering-strategy)).
5. `environment.present.skybox` and `environment.past.skybox` are loaded; only the active era's IBL is bound to `scene.environmentTexture` at any time.
6. Locations are materialized in declaration order. Each location's assets are instantiated and tagged with era scope via `core.tagNode(mesh, era)`.
7. Audio zones are registered with the `AudioManager`.
8. Anchors are registered with the `InteractableRegistry`.
9. `narrative/NarrativeController.loadGraph(manifest.narrativeGraph)` wires up state.
10. `performance.runFreezePass(scene)` sweeps the scene. (See [`ARCHITECTURE.md` §7.1](ARCHITECTURE.md#71-the-freeze-pass).)
11. `ai/AIDialogueService.init(manifest.ai)` probes `/health`. On failure, `isAvailable = false` for the session.
12. `ui/TitleCard.show(manifest.openingCardMs)` and then hands over control.

When the player exits to title screen:

1. `MissionLoader.unload()` disposes every asset container, clears the scene, unregisters audio zones and anchors, and tears down the narrative state. See the teardown sequence in [`ARCHITECTURE.md` §8.4](ARCHITECTURE.md#84-mission-teardown). On LOW profile this completes in under 2 seconds; without `blockfreeActiveMeshesAndRenderingGroups` it would take 10+.

No global state survives between missions. The engine returns to the title screen fully reset.

---

## 7. AI prompt templates

The AI service does not invent history. It synthesizes variants of authored lines. To enforce this, anchors may reference a **prompt template** by name instead of writing a freeform `ai.prompt`. Templates live in `src/ai/promptTemplates/` and are linted at build time.

Every template takes two inputs:
1. **Scene context:** the anchor's `fallbackDialogue`, the current era, the investigator's relevant unlocked flags.
2. **Tonal frame:** instructions like "respond in one paragraph as a memorial documentary narrator".

Every template is required to include these negative constraints:

- **Do not invent historical figures, dates, places, or events not present in the context.**
- **Do not produce graphic descriptions of violence.**
- **Do not speak in the first person of any named historical victim or perpetrator.**
- **If the context is insufficient, respond with the fallback line verbatim.**

The prompt-safety linter (`tools/lint_prompts.py`, to be written) verifies these constraints are present in every template and in every freeform `ai.prompt` in any manifest.

Missions that set `ai.disableOn: ["LOW", "MEDIUM"]` bypass the AI service entirely on those profiles; every anchor returns `fallbackDialogue`. This is the correct default for first-author missions still building trust in their prompt templates.

---

## 8. A concrete template example — `example-plaza`

A minimal hypothetical second mission, shipped alongside the Shepherd's Ledger as a *template smoke test*. It is **not historically authored**; it exists to prove the template works in isolation and to give manifest-level reviewers something concrete to compare against.

```
public/missions/example-plaza/
├── manifest.json
├── README.md                      # "This is a template test, not a real mission."
├── narrative/Graph.json            # 3 nodes: start → anchor_fountain → end
├── assets/
│   ├── plaza_tile.glb
│   ├── plaza_fountain.glb
│   └── plaza_bench.glb
├── audio/zones/
│   ├── plaza_ambient_present.ogg
│   └── plaza_ambient_past.ogg
├── environment/
│   ├── present.env
│   └── past.env
├── ai-cache/                       # empty; AI disabled
└── preview.jpg
```

```json
// manifest.json (abridged)
{
  "id": "example-plaza",
  "version": "1",
  "title": "Plaza (Template Test)",
  "historical": {
    "location": { "name": "—", "country": "—" },
    "period": { "pastYear": 1900, "presentYear": 2000, "durationDays": 1 },
    "contentWarning": "This is a template fixture. No historical events are depicted.",
    "sources": [{ "title": "N/A — template fixture", "citation": "internal" }]
  },
  "performance": { "minimumProfile": "LOW", "recommendedProfile": "LOW" },
  "requiredAssets": ["plaza_tile", "plaza_fountain", "plaza_bench"],
  "environment": {
    "present": { "skybox": "environment/present.env", "intensity": 1.0 },
    "past":    { "skybox": "environment/past.env",    "intensity": 1.0 }
  },
  "locations": [{
    "id": "plaza",
    "label": "Plaza",
    "position": { "x": 0, "y": 0, "z": 0 },
    "assets": [
      { "asset": "plaza_tile", "count": 48 },
      { "asset": "plaza_fountain", "count": 1 },
      { "asset": "plaza_bench", "count": 4 }
    ],
    "audioZones": [
      { "id": "plaza_present", "era": "present", "clip": "audio/zones/plaza_ambient_present.ogg", "radius": 30, "gain": 0.5 },
      { "id": "plaza_past",    "era": "past",    "clip": "audio/zones/plaza_ambient_past.ogg",    "radius": 30, "gain": 0.5 }
    ],
    "era": "both"
  }],
  "anchors": [{
    "id": "fountain_basin",
    "location": "plaza",
    "localPosition": { "x": 0, "y": 0.6, "z": 0 },
    "era": "both",
    "label": "The fountain",
    "unlocksFlags": ["examined_fountain"],
    "fallbackDialogue": "The basin is empty. A coin rests on the lip."
  }],
  "narrativeGraph": "narrative/Graph.json",
  "ai": { "relevantFlags": ["examined_fountain"], "cacheDir": "ai-cache/", "disableOn": ["LOW", "MEDIUM", "HIGH"] },
  "ui": { "ledgerTitle": "Ledger", "openingCardMs": 500, "hudProfile": "memorial" },
  "save": { "slotPrefix": "witness.example-plaza.v1", "resumeAlwaysInEra": "present" }
}
```

This fixture is checked into the repo and runs as part of CI smoke-testing: if the engine can boot `example-plaza`, unload it, boot `shepherds-ledger`, unload it, and boot `example-plaza` again without a memory leak, the template is healthy.

---

## 9. Anti-patterns — what will collapse the template

If you find yourself doing any of the following, stop. You are about to create mission-specific code that future missions will have to carry or duplicate.

### 9.1 Hardcoding a mission name in engine code
**Do not** write `if (missionId === "shepherds-ledger") { ... }` anywhere in `src/`. If a mission needs special behavior, that behavior belongs in the manifest as a capability flag (e.g., `performance.lowProfileUseLod1AsLod0`) that every mission declares explicitly.

### 9.2 Adding a character name or place name to `src/`
**Do not** add a constant like `BISESERO_LAT = -2.26` to `src/world/constants.ts`. Coordinates live in `manifest.historical.location`.

### 9.3 Branching the narrative graph outside the graph
**Do not** short-circuit `Graph.json` with hand-written `if (flag)` logic inside an action handler. All branching lives in the graph. Actions execute side effects (audio, camera, visual) deterministically in response to state changes.

### 9.4 Shipping an anchor without a fallback
**Do not** rely on the AI service to produce the canonical line. If the service is down — which on a school network happens often — an anchor without `fallbackDialogue` is a dead spot in the mission. Authorship means writing the line first; AI is variation, not origin.

### 9.5 Referencing an asset by literal path
**Do not** write `await LoadAssetContainerAsync("assets/prop_jerrycan.glb", scene)` inside `src/world/`. The asset library resolves every id. A literal path means the asset cannot be reused across missions and cannot be swapped via LOD.

### 9.6 Inventing history in the prompt template
**Do not** write a prompt like *"Continue the story of Marie, who was 8 years old in 1994."* The engine must never produce a historical claim that is not in `fallbackDialogue`. Every `ai.prompt` is a paraphrase instruction over the fallback line, not a continuation instruction.

### 9.7 Shipping a mission you have not run on its declared floor
**Do not** declare `minimumProfile: "LOW"` without having played the mission end-to-end on a Chromebook. Performance regressions caught in production are an order of magnitude more expensive than ones caught at the target hardware.

### 9.8 Bundling shared assets into a single mission folder
**Do not** put a generic `vegetation_eucalyptus.glb` in one mission folder and reference it from another. If two missions share an asset, the asset belongs in `public/shared/assets/` and both manifests reference it via a `shared:` prefix: `requiredAssets: ["shared:vegetation_eucalyptus", "structure_rugo_wall"]`. (The `AssetLibrary` resolver understands this prefix.)

### 9.9 Mutating narrative state from a scene handler
**Do not** write `stateManager.setFlag(...)` inside `src/world/locations/family_compound.ts`. Scenes emit events; the narrative layer mutates state. One-way data flow.

### 9.10 Skipping the README
A mission without a reviewed `README.md` (§4 step 2) must not ship. This is a content policy, not a code policy, and it matters more than any of the others.

---

## 10. Checklist for shipping a new mission

Before opening a PR that ships a new mission:

- [ ] `public/missions/<id>/README.md` exists and names the event, sources, content warnings, and content owner.
- [ ] `manifest.json` passes `tools/validate_manifest.py` with zero errors.
- [ ] `narrative/Graph.json` passes `tools/validate_graph.py` with zero errors.
- [ ] Every anchor has a non-empty `fallbackDialogue`.
- [ ] Every `requiredAssets` entry resolves to a real `.glb` with LOD0/LOD1/LOD2.
- [ ] `ai-cache/` contains responses for the full `relevantFlags` cross-product for every anchor with `ai.prompt` declared.
- [ ] The mission plays end-to-end on a device that matches `performance.minimumProfile`.
- [ ] Teardown → reload → teardown cycles leak zero MB over 5 iterations (inspect via `performance.memory.usedJSHeapSize` in DevTools).
- [ ] `public/missions/index.json` includes the new id.
- [ ] `docs/decisions/CHANGELOG_DETAILED.md` has an entry for the mission.
- [ ] At least one reviewer has signed off on the historical provenance (not just the code).

---

## 11. Forward compatibility

When the manifest schema changes in a backwards-incompatible way, bump the top-level `"schema"` number (to be added in v2) and write a migration in `src/mission/migrations/<fromVersion>_<toVersion>.ts`. The mission's own `version` field is independent of the manifest schema version and tracks narrative/flag changes within a mission.

All future schema additions are additive by default. Removal requires a `schema` bump and a migration path.

---

## 12. References

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — engine subsystem contracts this document builds on.
- [`docs/design-docs/MASTER.md`](docs/design-docs/MASTER.md) — repo map and gap matrix.
- [`docs/design-docs/MISSION_BLUEPRINT.md`](docs/design-docs/MISSION_BLUEPRINT.md) — the authoring template for mission content.
- [`docs/design-docs/NARRATIVE.md`](docs/design-docs/NARRATIVE.md) — narrative graph rules.
- [`docs/design-docs/ASSET_PIPELINE.md`](docs/design-docs/ASSET_PIPELINE.md) — how the `.glb` files are generated and compressed.
- [`docs/design-docs/AUDIO_ARCHITECTURE.md`](docs/design-docs/AUDIO_ARCHITECTURE.md) — audio zone authoring and spatial playback.
- [`docs/design-docs/CHRONOS_SWITCH.md`](docs/design-docs/CHRONOS_SWITCH.md) — era-switch runtime behavior.
- [`docs/design-docs/RENDERING.md`](docs/design-docs/RENDERING.md) — HIGH-tier rendering spec (desktop contract).
- [`docs/decisions/adrs/0001-narrative-edge-cases.md`](docs/decisions/adrs/0001-narrative-edge-cases.md) — save-resume and flag-migration contracts.
- Babylon.js — `LoadAssetContainerAsync`: [`loadingFileTypes.md`](docs/reference/Documentation/content/features/featuresDeepDive/importers/loadingFileTypes.md).
- Babylon.js — Thin Instances: [`thinInstances.md`](docs/reference/Documentation/content/features/featuresDeepDive/mesh/copies/thinInstances.md).
- Babylon.js — SceneOptimizer: [`sceneOptimizer.md`](docs/reference/Documentation/content/features/featuresDeepDive/scene/sceneOptimizer.md).
- Babylon.js — Optimize Your Scene: [`optimize_your_scene.md`](docs/reference/Documentation/content/features/featuresDeepDive/scene/optimize_your_scene.md).
- Babylon.js — Layer Masks & Multi-Camera: [`layerMasksAndMultiCam.md`](docs/reference/Documentation/content/features/featuresDeepDive/cameras/layerMasksAndMultiCam.md).
