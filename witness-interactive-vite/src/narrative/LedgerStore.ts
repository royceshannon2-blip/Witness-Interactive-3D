/**
 * LedgerStore
 *
 * In-memory ordered collection of ledger entries unlocked by the player
 * during a session. Each entry is keyed by the narrative flag that unlocked
 * it so duplicates are silently skipped even if a fragment fires twice.
 *
 * Intentionally separate from StateManager: entries are display artefacts
 * derived from narrative flags — they don't need to be serialized on their
 * own because they can be reconstructed from the flag set on load. The
 * current implementation keeps them in memory only; a future "resume"
 * feature can re-derive them from the saved flag set via `rehydrate()`.
 *
 * Per ARCHITECTURE.md §5.8 + NARRATIVE.md §3.4.
 */

export interface LedgerEntry {
  /** Narrative flag that unlocked this entry (e.g. "found_cellar_evidence"). */
  key: string;
  /** Short one-line text shown in the HUD banner toast. */
  text: string;
  /** Full journal body shown in the LedgerUI overlay. Falls back to `text`. */
  body?: string;
  /** `Date.now()` at collection time — used for newest-first ordering. */
  unlockedAt: number;
}

class LedgerStoreImpl {
  private _entries: LedgerEntry[] = [];
  private _listeners: Set<() => void> = new Set();

  /**
   * Record a new entry. Idempotent: a second call with the same `key` is
   * silently ignored, so callers need not guard against double-fire.
   */
  add(key: string, text: string, body?: string): void {
    if (this._entries.some((e) => e.key === key)) return;
    this._entries.push({ key, text, body, unlockedAt: Date.now() });
    this._listeners.forEach((l) => l());
  }

  /** All entries in collection order (oldest first). */
  entries(): readonly LedgerEntry[] {
    return this._entries;
  }

  count(): number {
    return this._entries.length;
  }

  /**
   * Subscribe to entry additions. Returns an unsubscribe function.
   * Called from main.ts to update the HUD ledger indicator.
   */
  onChanged(listener: () => void): () => void {
    this._listeners.add(listener);
    return () => {
      this._listeners.delete(listener);
    };
  }

  /** Reset on New Game+. */
  clear(): void {
    this._entries = [];
    this._listeners.forEach((l) => l());
  }
}

export const ledgerStore = new LedgerStoreImpl();
