# ADR-0001: Narrative System Edge Cases and Recovery Strategy

- **Status:** Accepted
- **Date:** 2026-04-18
- **Deciders:** @royceshannon2
- **Context tags:** #narrative, #chronos, #state-management, #save-load

## Context

The narrative system combines three independent state surfaces:

1. **`StateManager.flagsSet`** — a `Record<string, boolean>` of narrative flags.
2. **`Graph.json`** — the DAG of nodes (puzzles, scenes, branches, endings) with `requiredFlags` / `unlocksFlags`.
3. **`TimeManager`** — the current era and the `past_*`-prefixed subset of `flagsSet` that represents intergenerational state (see [`TIMELINE_SYNC.md`](../../design-docs/TIMELINE_SYNC.md)).

Each surface has been designed individually, but their interaction produces edge cases that could leave the player in an unrecoverable state (stuck, missing narrative content, or with a corrupted save). Before we land the first Memory Fragment in M3, we need a documented recovery strategy for every foreseeable failure mode. This ADR enumerates five such cases and commits to handling for each.

The edge cases are:

1. **Circular flag dependency** — two nodes each depend on a flag the other unlocks.
2. **Fragment triggered while already in target era** — player activates a fragment's anchor mesh during Chronos transition or while already in Past.
3. **Save file captured mid-transition** — game crashes or is force-closed during the 1.8 s Chronos crossfade.
4. **Missing `past_*` flag on load** — save file pre-dates the `past_` namespace convention.
5. **Branch choice made before required flags set** — node is reachable by navigation but its `requiredFlags` are not satisfied.

## Decision

**We accept all five edge cases as predictable failure modes and commit to the following handling for each. Recovery must never leave the player without a path forward.**

### Case 1: Circular flag dependency

A dependency cycle in `Graph.json` (node A requires `x`, unlocks `y`; node B requires `y`, unlocks `x`) makes both nodes unreachable. This is a **development-time error**, not a runtime one.

**Handling:**
- `tools/validate_graph.py` (to write — blocks M3) performs a topological sort of `Graph.json` at build time. Cycles cause the script to exit non-zero with a clear error citing the cycle: `Cycle detected: act_3a_puzzle_1 → act_3a_puzzle_2 → act_3a_puzzle_1`.
- The check runs in CI (GitHub Action on every commit to `src/narrative/Graph.json`).
- No runtime handling — if a cycle lands in a shipped build, it is a regression and a patch release is the correct response.

### Case 2: Fragment triggered while already in target era

A player double-clicks the cellar door latch during the Chronos transition, or uses a fragment that points to Past while already in Past (e.g. due to Past-era authoring mistakes).

**Handling (runtime):**
- `InteractableRegistry.onFragmentActivated` checks `timeManager.currentEra === fragment.targetEra` before calling `transition()`. If true, the activation is a no-op (no error, no sound, no visual feedback beyond the mesh's normal interaction).
- `TimeManager.transition(target)` is additionally guarded by `isTransitioning` and by `currentEra === target` — both short-circuit with a resolved promise. This is existing behavior; see [`TIMELINE_SYNC.md §8`](../../design-docs/TIMELINE_SYNC.md#8-failure-modes-and-mitigations).
- Double-guarding is deliberate: the registry check prevents the wrong-era case; the TimeManager check prevents the mid-transition case.

### Case 3: Save file captured mid-transition

A browser crash, tab close, or auto-save fire during the 1.8 s crossfade could persist a state with `isTransitioning = true`, an ambiguous era, or partial `past_*` flags.

**Handling:**
- `SaveSystem.save()` refuses to write while `timeManager.isTransitioning === true`, returning `{ ok: false, reason: "transitioning" }`. Auto-saves silently skip; explicit saves show a one-line message: "Saving paused — please wait a moment."
- **`timeManager.isTransitioning` and `timeManager.currentEra` are deliberately not serialized.** On load, the game always resumes in Present era. Any Past-era state the player recorded via `recordPastChange` is already in `flagsSet` (per TIMELINE_SYNC.md) and survives normally.
- Rationale: the save file represents narrative progress, not camera position or active era. If the player saved while in the Past, reloading them to Present is correct — they can re-trigger the fragment to revisit.

### Case 4: Missing `past_*` flag on load (save-format migration)

A save file written before the `past_` namespace was introduced (hypothetically — no shipped builds predate it, but the case matters for ongoing schema evolution) has no `past_*` flags at all. Present-era scenes that read `hasPastChange(key)` will get `false` for every key — the "nothing happened" branch.

**Handling:**
- This is **not** a failure mode, it is the correct behavior. The player experiences the Present as if they have not yet visited the Past. Subsequent Chronos visits record flags normally.
- For saves whose flag *semantics* change across versions (e.g., `past_hid_child_in_cellar` means something different in v1.1 than in v1.0), the convention per [`TIMELINE_SYNC.md §8`](../../design-docs/TIMELINE_SYNC.md#8-failure-modes-and-mitigations) is: rename the flag (`past_hid_child_in_cellar_v2`), and — if needed — write a migration stub in `SaveSystem.deserialize()` that maps old → new.
- Every released game version freezes its flag vocabulary. A `saveFormatVersion` integer is written to each save file; migrations run in version order on load.

### Case 5: Branch choice committed before required flags set

The `act_3_the_choice` branch node has `requiredFlags: ["all_evidence_found"]`. If the UI allows the player to commit to a path before that flag is set (e.g., a bug in the UI gating, or a debug-mode flag jump), the narrative state becomes inconsistent: a path is locked in that the player's evidence does not justify.

**Handling:**
- `NarrativeController.chooseBranchOption(nodeId, optionId)` checks that every flag in the node's `requiredFlags` is true in `globalState.flagsSet` before applying `unlocksFlags`. If any flag is missing, the call returns `{ ok: false, reason: "requiredFlagsNotMet", missing: [...] }` — no state mutation occurs.
- The UI is expected to gate the choice affordance on `canChoose(nodeId)` (helper added to `NarrativeController`). If the UI bug-somehow presents an ungated choice, the controller still refuses it.
- Development mode: a console warning logs when a choice is refused, naming the missing flags. This surfaces the issue to the developer; the player sees no visible error (the choice just doesn't take effect).

## Consequences

**Easier:**
- Save/load reliability is preserved across crashes and version bumps.
- Narrative design changes can evolve without breaking prior saves (as long as the flag-rename migration pattern is followed).
- Chronos transitions are robustly re-entrant; fragment authoring can ignore the "what if already in Past" edge case.
- CI catches the most common authoring error (graph cycles) before merge.

**Harder:**
- Every new `save-format` migration requires a version bump + migration stub. This is a small tax on narrative flag refactors.
- `NarrativeController` now has a `canChoose` API that the UI must consult — one more thing for UI code to call. But the alternative (silent bad state) is worse.
- `tools/validate_graph.py` must be written and integrated into CI before M3. Not optional.

**New risks:**
- None introduced. Each case is handled by guards at the owning subsystem (`SaveSystem`, `NarrativeController`, `TimeManager`, `InteractableRegistry`). No new shared surface is created.

**Locked in by this ADR:**
- Save files always resume in Present era, not the era they were saved in.
- Saves refuse during Chronos transitions.
- Flag vocabulary is frozen per version; migrations are the only evolution path.
- Branch choices are server-side-refused by `NarrativeController` — a UI bug cannot corrupt state.

Changing any of these requires a new ADR.

## Alternatives considered

- **A. Serialize `currentEra` across save/load.** Would preserve the player's active era. Rejected: saves in Past have an ambiguous contract (what if the Past scene has been re-authored?); replaying into Past requires re-running the fragment trigger, which is complex. Cleaner to always resume in Present.
- **B. Runtime cycle detection in `NarrativeController`.** Catch cycles at first-reach. Rejected in favor of build-time detection: cycles are a development error, and runtime graph-walking has cost. Build-time check is cheap and catches more cases (including unreachable nodes).
- **C. Soft-fail save during transition (write anyway).** Simpler for the save code, but produces saves that load into ambiguous state. Rejected — the 1.8 s transition window is a tiny cost to pay for consistency.
- **D. Migrate all flags to typed keys (string-enum).** Catches the "typo in flag name" case at compile time. Rejected for now — requires a significant refactor of `Graph.json` (which uses string literals) and of authoring tooling. Candidate for a v1.1 ADR.
- **E. Allow the UI to commit a choice optimistically and roll back on controller rejection.** Rejected — makes UI state-reconciliation complicated and allows flicker. Better to gate the affordance up front via `canChoose`.

## References

- [`TIMELINE_SYNC.md`](../../design-docs/TIMELINE_SYNC.md) — the `past_` flag convention and save-load behavior.
- [`CHRONOS_SWITCH.md §7`](../../design-docs/CHRONOS_SWITCH.md#7-failure-modes) — runtime failure modes the Chronos subsystem owns.
- [`NARRATIVE.md`](../../design-docs/NARRATIVE.md) — the Graph.json content and branch structure.
- [`MASTER.md §10`](../../design-docs/MASTER.md#10-unresolved-questions) — related open questions, several of which this ADR partially addresses.
