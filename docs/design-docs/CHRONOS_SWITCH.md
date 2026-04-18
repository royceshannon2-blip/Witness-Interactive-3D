# Chronos Switch — Design Document

- **Status:** Stub (outline only — content TBD)
- **Owner:** @royceshannon2
- **Parent:** [`MASTER.md`](MASTER.md) · **Architecture:** [`ARCHITECTURE.md §4`](../../ARCHITECTURE.md#4-era-representation-chronos)
- **Target code home:** `witness-interactive-vite/src/core/`
- **Related:** [`TIMELINE_SYNC.md`](TIMELINE_SYNC.md) — Past ⇄ Present state bridge (implemented).

The mechanic that snaps the player between Present (2026, investigator) and Past (1994, grandparent). One scene, two eras, crossfade-mediated. Not a scene swap.

---

## 1. Objective
*(To be written.)*

Summarise what Chronos Switch is, what it is not, and what narrative purpose it serves.

## 2. Scope
- **In scope:** *(TBD)*
- **Out of scope:** *(TBD)*

## 3. High-level design
*(To be written — lift and expand the sketch from the chat plan of 2026-04-17.)*

Subsections to fill:
- 3.1 Era model: `Era.Present | Era.Past`, single active at a time.
- 3.2 Layer masks: bit allocation, tagging helper, `LAYER_SHARED` semantics.
- 3.3 `TimeManager` class: public API, event emission, re-entry rules.
- 3.4 Post-fx profiles per era (Present: desaturated, overgrown; Past: warm, high-contrast).
- 3.5 Lighting strategy: duplicated lights masked per era, not animated intensity.
- 3.6 Transition sequence: crossfade curve, audio ducking, camera behaviour.

## 4. Memory Fragments
Subsections to fill:
- 4.1 What a Fragment is (a Present-era pickup that triggers an era switch).
- 4.2 Authoring format (JSON under `src/world/fragments/` or inline in location modules).
- 4.3 Registration and lifecycle.
- 4.4 Interaction flow (see ARCHITECTURE.md §3.1 sequence diagram).
- 4.5 Link between Fragment and `Graph.json` node.

## 5. Perspective modes (inside Past era)
- 5.1 `Protector` mode — full movement, dialogue, checkpoint puzzles.
- 5.2 `Hidden` mode — constrained movement, audio-forward, clamped FOV.
- 5.3 Transition between modes (narrative-driven, not player-chosen).

## 6. Trade-offs and alternatives
- **A. Layer mask vs. scene swap** — why we chose masks.
- **B. Camera snap vs. in-place transformation** — unresolved; see MASTER.md §10.
- **C. Duplicated lights vs. animated single lights** — why we chose duplication.

## 7. Failure modes
- Transition interrupted mid-crossfade.
- Fragment triggered while already in target era.
- Save file captured during transition.
- Memory pressure from duplicated mesh sets.

## 8. Milestones
*(To be written once §1–§7 are filled.)*

## 9. Open questions
Any question here that becomes answered with rationale should move to [`docs/decisions/adrs/`](../decisions/adrs/) as an ADR.

- Q1: Snap vs. preserve camera on era change?
- Q2: Do Fragments persist after triggering (revisitable) or disappear?
- Q3: How is the return from Past era triggered — timer, puzzle completion, or explicit player input?
