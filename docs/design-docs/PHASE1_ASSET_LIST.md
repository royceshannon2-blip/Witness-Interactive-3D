# Phase 1 Asset List — Mission "The Shepherd's Ledger"

- **Status:** Templates + per-asset reference descriptions + Digital Diorama style guide authored 2026-05-13. Hunyuan runbook at [`tools/HUNYUAN_RUNBOOK.md`](../../tools/HUNYUAN_RUNBOOK.md). Reference images + Hunyuan run pending.
- **Owner:** @royceshannon2
- **Parent:** [`MASTER.md`](MASTER.md)
- **Scope:** Family Compound first-frame composition (OPENING_SEQUENCE §6) + Phase 1 hero props + first-person hands (both eras).
- **Visual style:** [`prompts/asset-templates/_STYLE_GUIDE.md`](../../prompts/asset-templates/_STYLE_GUIDE.md) — Digital Diorama (tactile weathered realism, filmic desaturated palette, hyper-realistic PBR). Each template's `## Reference image` section names what the corresponding `ref.png` must depict.

This list itemises every asset that must be generated, optimised, and registered before the Phase 1 arrival of `MISSION_BLUEPRINT.md` can be shipped in photoreal form. Each row maps to a prompt template at `prompts/asset-templates/<id>.md` (which now contains a `## Reference image` section describing what the photo should depict) and a reference-image dropoff at `prompts/asset-templates/<id>/ref.png`. The per-asset `README.md` at each dropoff summarises the same description.

The runtime scaffold already exists in [`witness-interactive-vite/src/world/locations/FamilyCompound.ts`](../../witness-interactive-vite/src/world/locations/FamilyCompound.ts) as primitive boxes / cylinders; each is annotated with a `TODO(asset-pipeline): <id>` comment naming the asset that will replace it. The swap from primitive → instantiated GLB is mechanical and documented in the file header.

## How to ship one

1. Drop a reference image at `prompts/asset-templates/<id>/ref.png` (≥ 1024² ideal, neutral background).
2. Start the Hunyuan container (manual; the image's CMD is `/bin/bash` and the FastAPI server is started inside).
3. Run the orchestrator:
   ```bash
   cd /home/royce3/Desktop/Witness-Interactive-3D
   python tools/asset_pipeline.py <id> --kind <mesh|animated> --image prompts/asset-templates/<id>/ref.png
   ```
4. Update the **Status** column below.
5. In `world/locations/FamilyCompound.ts`, swap the `mk*` primitive calls in the matching `TODO(asset-pipeline): <id>` block for `assetLibrary.instantiate("<id>")`.

## Catalogue

| # | Asset ID | Kind | Era | Runtime owner | Replaces (in `FamilyCompound.ts`) | Status |
|---|---|---|---|---|---|---|
| 1 | `structure_rugo_main_house` | mesh | shared | `compound.house.{present,past}` | Two `mkBox` calls (one per era) | template ✓ · ref ✗ · glb ✗ |
| 2 | `structure_rugo_tin_roof` | mesh | shared | `compound.roof.{present,past}` | Two `mkBox` calls | template ✓ · ref ✗ · glb ✗ |
| 3 | `structure_rugo_door` | mesh | past | `compound.door.past` | One `mkBox` | template ✓ · ref ✗ · glb ✗ |
| 4 | `structure_compound_gate` | mesh | shared | `compound.gate.{left,right,beam}` | Three `mkBox` calls (consolidate into one model) | template ✓ · ref ✗ · glb ✗ |
| 5 | `structure_well_stone_ring` | mesh | shared | `compound.well.{present,past}` | Two `mkCyl` calls | template ✓ · ref ✗ · glb ✗ |
| 6 | `structure_well_cover_plank` | mesh | shared | `compound.well.cover.{present,past}` (carries `cellar_door_latch` trigger) | Two `mkBox` calls | template ✓ · ref ✗ · glb ✗ |
| 7 | `structure_family_shrine_slab` | mesh | shared | `compound.altar.slab.{present,past}` (carries Act-4 `shrineAnchor`) | Two `mkBox` calls | template ✓ · ref ✗ · glb ✗ |
| 8 | `vegetation_eucalyptus_mature` | mesh | shared | `compound.eucalyptus.present.0..5` (ThinInstance source) | One `mkCyl` × 6 in loop | template ✓ · ref ✗ · glb ✗ |
| 9 | `vegetation_eucalyptus_sapling` | mesh | past | `compound.eucalyptus.past.0..4` (ThinInstance source) | One `mkCyl` × 5 in loop | template ✓ · ref ✗ · glb ✗ |
| 10 | `vegetation_elephant_grass` | mesh | shared | `compound.grass.{present,past}.*` (ThinInstance source) | `mkBox` × 14 + × 6 in loops | template ✓ · ref ✗ · glb ✗ |
| 11 | `prop_ledger_book` | mesh | shared | `compound.altar.ledger.present` (Phase 1 first interactable) | One `mkBox` (added 2026-05-13) | template ✓ · ref ✗ · glb ✗ |
| 12 | `prop_altar_photo_frame` | mesh | shared | `compound.altar.frame.{present,past}` (carries `family_records` trigger) | Two `mkBox` calls | template ✓ · ref ✗ · glb ✗ |
| 13 | `prop_altar_candle` | mesh | past | `compound.altar.candle.past` | One `mkCyl` | template ✓ · ref ✗ · glb ✗ |
| 14 | `figure_investigator_hands` | animated | present | FP-camera-attached (not yet wired in `world/`) | New asset; bootstrap will instantiate at camera | template ✓ · ref ✗ · glb ✗ · rig ✗ |
| 15 | `figure_grandfather_hands` | animated | past | FP-camera-attached (shown during all Past echoes) | New asset; same rig as investigator | template ✓ · ref ✗ · glb ✗ · rig ✗ |

**Legend:** template ✓ = prompt markdown authored · ref ✓ = reference image present · glb ✓ = pipeline complete, registered, exported · rig ✓ = animated asset has Blender skeletal rig.

## What is *not* in this list

The following anchor props are also visible at the compound but belong to **Phase 2** (evidence gathering) or **Phase 3** (path-specific puzzles), and are gated behind `requiredFlags` in [`main.ts`](../../witness-interactive-vite/src/bootstrap/main.ts) — they remain primitives for this pass:

- `cellarMats` · `waterSchedule` · `neighborLetter` (Act 3A hider path)
- `survivorLetter` (Act 3B escapist path)
- `visitorAccount` (Act 3C silent path)

Other locations are out of scope for Phase 1:

- `LakeShore.ts` props (boat paddle, passenger list, dock, capacity board, escape route map)
- `Ravine.ts` props (observer's journal, chalk patrol marks, checkpoint records, reflection letters)

Those locations have their own `*.ts` modules with primitive scaffolds; they will follow the same pattern when the Phase 1 catalogue is complete.

## Infrastructure status (2026-05-13)

| Tool | Status | Notes |
|---|---|---|
| Hunyuan3D 2.1 Docker image | installed | `kechiro/hunyuan3d-2.1-cachedstart:latest`. Container CMD is `/bin/bash` — server must be started manually inside (`docker run -it --gpus all -p 8081:8080 <image>`, then start the FastAPI server inside). Stale containers exist; clean with `docker rm -f`. |
| `gltf-pipeline` | installed | `~/.npm-global/bin/gltf-pipeline` (Draco mesh compression). |
| `gltf-transform` | installed | `~/.npm-global/bin/gltf-transform` (alt path). |
| `toktx` (KTX-Software) | **missing** | Available in AUR as `ktx-software-bin`. Install via `paru -S ktx-software-bin`. Required only at the optimize stage; pipeline tolerates absence (skips KTX2) with a warning. |
| NVIDIA driver / toolkit | OK | RTX 5090 + 595.71.05. `nvidia-container-toolkit` 1.19.0. |

## Pre-flight checklist before running the orchestrator

Per [`.claude/rules/asset-pipeline.md §6`](../../.claude/rules/asset-pipeline.md):

- [ ] Asset id matches the row above (snake_case `<category>_<name>_<variant?>`).
- [ ] Prompt template authored at `prompts/asset-templates/<id>.md`.
- [ ] Reference image dropped at `prompts/asset-templates/<id>/ref.png`.
- [ ] Hunyuan FastAPI server reachable: `curl http://localhost:8081/docs` returns 200.
- [ ] `gltf-pipeline -h` works.
- [ ] (Optional but recommended) `toktx --version` works for KTX2 textures.
- [ ] After pipeline succeeds: registry row appears in `docs/asset-index.md`; runtime artefact at `witness-interactive-vite/public/assets/<id>.glb`.
- [ ] Swap the matching `TODO(asset-pipeline): <id>` block in `world/locations/FamilyCompound.ts` to `assetLibrary.instantiate("<id>")`.
- [ ] Append a row to `docs/decisions/CHANGELOG_DETAILED.md` mentioning the new asset id.
