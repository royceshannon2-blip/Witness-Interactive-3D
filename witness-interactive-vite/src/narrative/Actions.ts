import { globalState } from './StateManager';

export interface NarrativeAction {
  id: string;
  type: 'puzzle' | 'branch' | 'event' | 'unlock' | 'dialogue';
  trigger: string;
  payload: Record<string, unknown>;
}

type ActionCallback = (action: NarrativeAction) => Promise<void>;
type StateChangeCallback = (state: typeof globalState) => void;

class ActionBus {
  private listeners: Map<string, ActionCallback[]> = new Map();
  private stateListeners: Set<StateChangeCallback> = new Set();

  registerAction(actionType: string, callback: ActionCallback): void {
    if (!this.listeners.has(actionType)) {
      this.listeners.set(actionType, []);
    }
    this.listeners.get(actionType)!.push(callback);
  }

  async executeAction(action: NarrativeAction): Promise<void> {
    const callbacks = this.listeners.get(action.type) || [];
    for (const callback of callbacks) {
      await callback(action);
    }
    this.notifyStateChange();
  }

  onStateChange(callback: StateChangeCallback): void {
    this.stateListeners.add(callback);
  }

  private notifyStateChange(): void {
    this.stateListeners.forEach(cb => cb(globalState));
  }
}

export const actionBus = new ActionBus();

export const setupDefaultActions = () => {
  actionBus.registerAction('puzzle', async (action) => {
    globalState.completePuzzle(action.payload.puzzleId as string);
    console.log(`Puzzle completed: ${action.payload.puzzleId}`);
  });

  actionBus.registerAction('branch', async (action) => {
    const branchId = action.payload.branchId as string;
    globalState.setState({ currentBranch: branchId });
    console.log(`Switched to branch: ${branchId}`);
  });

  actionBus.registerAction('unlock', async (action) => {
    const pathId = action.payload.pathId as string;
    globalState.unlockPath(pathId);
    console.log(`Path unlocked: ${pathId}`);
  });
};
