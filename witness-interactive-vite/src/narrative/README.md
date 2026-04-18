# Narrative System

The narrative system separates **story logic** from **3D rendering**, enabling branching gameplay without spaghetti code.

## Files

| File | Purpose |
|------|---------|
| **StateManager.ts** | Tracks game progress, flags, and puzzle completions. Fully serializable for save/load. |
| **Actions.ts** | Event bus that bridges narrative decisions to 3D scene responses. |
| **NarrativeController.ts** | High-level API for triggering puzzles, branches, and state changes. Use this in your scene code. |
| **Graph.json** | DAG definition of all story nodes, branches, and dependencies. No code needed to update the story tree. |
| **INTEGRATION_EXAMPLE.md** | Copy-paste patterns showing how to connect your 3D scenes to narrative events. |

## Quick Start

### 1. Set up your scene
```typescript
import { narrativeController } from './narrative/NarrativeController';

// Subscribe to narrative changes
narrativeController.subscribe((event) => {
  if (event.type === 'puzzleSolved') {
    // Update 3D scene (animations, audio, etc.)
  }
});
```

### 2. Trigger a puzzle completion
```typescript
await narrativeController.triggerPuzzleCompletion('puzzle_01');
```

### 3. Handle a branch choice
```typescript
await narrativeController.triggerBranchChoice('path_a_01');
```

### 4. Save and load
```typescript
const saved = narrativeController.saveGame();
localStorage.setItem('save_slot_1', saved);

// Later...
const loaded = localStorage.getItem('save_slot_1');
narrativeController.loadGame(loaded);
```

## Story Design

Edit `Graph.json` to add new story nodes. Each node defines:
- `id` — Unique identifier
- `type` — 'scene', 'puzzle', 'branch', 'dialogue', 'event', 'ending'
- `requiredFlags` — Conditions that must be true to reach this node
- `unlocksFlags` — Flags set when this node completes
- `next` — Possible next nodes

See `docs/design-docs/NARRATIVE.md` for the full story tree and Mermaid diagram.

## State Architecture

```
StateManager (Global State)
  ├── currentBranch: string
  └── progress:
      ├── puzzlesCompleted: string[]
      ├── pathsUnlocked: string[]
      └── flagsSet: Record<string, boolean>
```

All state is immutable and serializable. Access via `narrativeController.getGameState()`.

## Extending the Narrative

### Add a New Puzzle
1. Update `Graph.json` with the puzzle node
2. Add a listener in your scene's `setupNarrativeListeners()` method
3. When puzzle is solved, call `narrativeController.triggerPuzzleCompletion()`

### Add a Branch Choice
1. Define the choice node and options in `Graph.json`
2. Create a UI component that calls `narrativeController.triggerBranchChoice()`
3. The scene automatically responds based on the new flag

### Add an Ending
1. Add ending node to `Graph.json`
2. Set appropriate flag requirements
3. Subscribe to that flag in your scene finale handler

## No Spaghetti Code

This architecture prevents spaghetti code through:
- **Separation of Concerns**: Story logic lives in StateManager/Graph, rendering in 3D scenes
- **Event-Driven**: Scenes subscribe to events rather than polling state
- **Single Source of Truth**: Graph.json is the canonical story definition
- **Dependency Injection**: NarrativeController is passed to scenes that need it
- **Testability**: You can test story branches without rendering anything

## Future Enhancements

- **InkJS Integration**: For dialogue-heavy narratives
- **XState Visualizer**: For complex state machines
- **Dialogue System**: Node-based dialogue trees with branching dialogue
- **Analytics**: Track which paths players choose, where they get stuck
- **Multiple Endings**: Tracked and triggered via flag combinations
