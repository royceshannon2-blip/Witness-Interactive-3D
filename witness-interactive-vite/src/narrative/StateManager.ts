export interface GameState {
  currentBranch: string;
  progress: {
    puzzlesCompleted: string[];
    pathsUnlocked: string[];
    flagsSet: Record<string, boolean>;
  };
  timestamp: number;
}

class StateManager {
  private state: GameState;

  constructor() {
    this.state = {
      currentBranch: 'intro',
      progress: {
        puzzlesCompleted: [],
        pathsUnlocked: [],
        flagsSet: {},
      },
      timestamp: Date.now(),
    };
  }

  getState(): GameState {
    return { ...this.state };
  }

  setState(updates: Partial<GameState>): void {
    this.state = { ...this.state, ...updates };
    this.state.timestamp = Date.now();
  }

  setFlag(key: string, value: boolean): void {
    this.state.progress.flagsSet[key] = value;
  }

  getFlag(key: string): boolean {
    return this.state.progress.flagsSet[key] ?? false;
  }

  completePuzzle(puzzleId: string): void {
    if (!this.state.progress.puzzlesCompleted.includes(puzzleId)) {
      this.state.progress.puzzlesCompleted.push(puzzleId);
    }
  }

  unlockPath(pathId: string): void {
    if (!this.state.progress.pathsUnlocked.includes(pathId)) {
      this.state.progress.pathsUnlocked.push(pathId);
    }
  }

  serialize(): string {
    return JSON.stringify(this.state);
  }

  deserialize(json: string): void {
    this.state = JSON.parse(json);
  }
}

export const globalState = new StateManager();
