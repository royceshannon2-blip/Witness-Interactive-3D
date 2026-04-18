# Narrative-3D Integration Example

This example shows how to connect the narrative engine to Babylon.js scene events **without spaghetti code**.

## Pattern: Observer Subscription

```typescript
// In your Babylon.js scene setup file (e.g., src/scenes/MainScene.ts)
import { narrativeController } from './narrative/NarrativeController';

export class MainScene {
  private scene: BABYLON.Scene;

  constructor(engine: BABYLON.Engine) {
    this.scene = new BABYLON.Scene(engine);
    this.setupNarrativeListeners();
  }

  private setupNarrativeListeners(): void {
    // Subscribe to narrative events
    const unsubscribe = narrativeController.subscribe((event) => {
      switch (event.type) {
        case 'puzzleSolved':
          this.onPuzzleSolved(event.data as { puzzleId: string });
          break;
        case 'branchUnlocked':
          this.onBranchUnlocked(event.data as { branchId: string });
          break;
        case 'stateChanged':
          this.updateSceneState(event.data as any);
          break;
      }
    });
    
    // Store unsubscribe function to clean up on scene dispose
    this.scene.onDisposeObservable.add(() => unsubscribe());
  }

  private onPuzzleSolved(data: { puzzleId: string }): void {
    console.log(`Puzzle solved: ${data.puzzleId}`);
    
    if (data.puzzleId === 'puzzle_01') {
      // Play unlock animation
      this.animateUnlock();
      // Play celebratory sound
      this.playAudio('victory.wav');
    }
  }

  private onBranchUnlocked(data: { branchId: string }): void {
    console.log(`Branch unlocked: ${data.branchId}`);
    
    if (data.branchId === 'path_a_01') {
      // Fade in library, fade out garden
      this.transitionToPath('library');
    } else if (data.branchId === 'path_b_01') {
      // Fade in garden, fade out library
      this.transitionToPath('garden');
    }
  }

  private updateSceneState(state: any): void {
    // React to any state change
    if (state.progress.flagsSet['path_a_chosen']) {
      // Show library-specific UI elements
      this.showLibraryUI();
    }
  }

  private animateUnlock(): void {
    const door = this.scene.getMeshByName('door');
    if (door) {
      BABYLON.Animation.CreateAndStartAnimation(
        'doorOpen',
        door,
        'rotation.y',
        30,
        60,
        0,
        Math.PI / 2,
        BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT
      );
    }
  }

  private playAudio(filename: string): void {
    const sound = new BABYLON.Sound('victory', `/assets/audio/${filename}`, this.scene);
    sound.play();
  }

  private transitionToPath(pathName: string): void {
    const camera = this.scene.activeCamera as BABYLON.UniversalCamera;
    // Pan camera to new path
    BABYLON.Animation.CreateAndStartAnimation(
      'cameraMove',
      camera,
      'position',
      30,
      60,
      camera.position,
      new BABYLON.Vector3(0, 10, pathName === 'library' ? -20 : 20),
      BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT
    );
  }

  private showLibraryUI(): void {
    // Update UI without touching narrative code
    console.log('Showing library-specific UI');
  }
}
```

## Pattern: Trigger Narrative Events from 3D Interactions

```typescript
// In a puzzle interaction handler (e.g., src/interactions/PuzzleHandler.ts)
import { narrativeController } from './narrative/NarrativeController';

export class PuzzleHandler {
  static async onPuzzleObjectInteract(meshName: string): Promise<void> {
    if (meshName === 'artifact_pedestal') {
      // Solve puzzle logic...
      const puzzleSolved = checkIfPuzzleSolved();
      
      if (puzzleSolved) {
        // Let narrative controller handle the state update
        await narrativeController.triggerPuzzleCompletion('puzzle_01', {
          solvedTime: Date.now(),
          attempts: 3,
        });
      }
    }
  }
}
```

## Pattern: Branch Choice UI

```typescript
// In a UI component for branch choices (e.g., src/ui/BranchChoiceUI.ts)
import { narrativeController } from './narrative/NarrativeController';

export class BranchChoiceUI {
  async selectPath(pathId: string): Promise<void> {
    // Don't directly change 3D state here
    // Let the narrative controller handle it
    await narrativeController.triggerBranchChoice(pathId, {
      selectedAt: new Date().toISOString(),
    });
    
    // The scene will automatically update via the subscription
    // No need to manually update meshes/cameras here
  }
}
```

## Save/Load Pattern

```typescript
// In your menu/persistence layer (e.g., src/systems/SaveManager.ts)
import { narrativeController } from './narrative/NarrativeController';

export class SaveManager {
  static saveGame(slotId: number): void {
    const gameState = narrativeController.saveGame();
    localStorage.setItem(`save_${slotId}`, gameState);
  }

  static loadGame(slotId: number): void {
    const saved = localStorage.getItem(`save_${slotId}`);
    if (saved) {
      narrativeController.loadGame(saved);
      // Scene will automatically update via the subscription
    }
  }
}
```

## Key Principles

1. **Narrative tells, 3D responds**: The narrative controller never directly manipulates the scene.
2. **3D listens, never asks**: Scene components subscribe to events; they don't query the narrative engine.
3. **Clean separation**: Puzzle logic is isolated from animation logic.
4. **Easy testing**: You can test narrative branches without rendering a single triangle.
5. **Save/load is automatic**: State serialization happens at the narrative layer.

## Next Steps

- Implement your puzzles using this pattern
- Add dialogue system (consider InkJS for complex branching)
- Add environmental reactions (sound, lighting, particle effects)
- Test all branches with a narrative test suite
