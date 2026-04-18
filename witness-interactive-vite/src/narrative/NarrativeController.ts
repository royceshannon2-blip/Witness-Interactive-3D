import { globalState, GameState } from './StateManager';
import { actionBus, NarrativeAction, setupDefaultActions } from './Actions';

interface NarrativeEvent {
  type: 'stateChanged' | 'puzzleSolved' | 'branchUnlocked' | 'endingReached';
  data: unknown;
}

type NarrativeListener = (event: NarrativeEvent) => void;

export class NarrativeController {
  private listeners: Set<NarrativeListener> = new Set();

  constructor() {
    setupDefaultActions();
    this.setupStateObserver();
  }

  private setupStateObserver(): void {
    actionBus.onStateChange((state) => {
      this.notifyListeners({
        type: 'stateChanged',
        data: state.getState(),
      });
    });
  }

  subscribe(listener: NarrativeListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notifyListeners(event: NarrativeEvent): void {
    this.listeners.forEach(listener => listener(event));
  }

  async triggerPuzzleCompletion(puzzleId: string, metadata?: Record<string, unknown>): Promise<void> {
    await actionBus.executeAction({
      id: `puzzle_${puzzleId}_${Date.now()}`,
      type: 'puzzle',
      trigger: puzzleId,
      payload: { puzzleId, ...metadata },
    });

    this.notifyListeners({
      type: 'puzzleSolved',
      data: { puzzleId },
    });
  }

  async triggerBranchChoice(branchId: string, metadata?: Record<string, unknown>): Promise<void> {
    await actionBus.executeAction({
      id: `branch_${branchId}_${Date.now()}`,
      type: 'branch',
      trigger: branchId,
      payload: { branchId, ...metadata },
    });

    this.notifyListeners({
      type: 'branchUnlocked',
      data: { branchId },
    });
  }

  async unlockPath(pathId: string): Promise<void> {
    await actionBus.executeAction({
      id: `unlock_${pathId}_${Date.now()}`,
      type: 'unlock',
      trigger: pathId,
      payload: { pathId },
    });
  }

  getGameState(): GameState {
    return globalState.getState();
  }

  hasCompletedPuzzle(puzzleId: string): boolean {
    return this.getGameState().progress.puzzlesCompleted.includes(puzzleId);
  }

  hasUnlockedPath(pathId: string): boolean {
    return this.getGameState().progress.pathsUnlocked.includes(pathId);
  }

  getFlag(flagKey: string): boolean {
    return globalState.getFlag(flagKey);
  }

  setFlag(flagKey: string, value: boolean): void {
    globalState.setFlag(flagKey, value);
  }

  saveGame(): string {
    return globalState.serialize();
  }

  loadGame(savedState: string): void {
    globalState.deserialize(savedState);
    this.notifyListeners({
      type: 'stateChanged',
      data: this.getGameState(),
    });
  }
}

export const narrativeController = new NarrativeController();
