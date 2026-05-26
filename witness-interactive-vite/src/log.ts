/**
 * log
 *
 * Tiny tagged logger. Per ARCHITECTURE.md §10.2:
 *   - Four levels: `debug | info | warn | error`.
 *   - `debug` is stripped from production bundles (gated by Vite's
 *     `import.meta.env.PROD`). Other levels survive.
 *   - Each subsystem creates a tagged logger via `createLog("audio")`
 *     so messages read `[audio] engine ready, voice cap=12`.
 *
 * No dependencies, no async sinks — `console` is the sink. Anything more
 * sophisticated (telemetry, ring buffers) belongs behind a future adapter.
 */

type Level = "debug" | "info" | "warn" | "error";

const IS_PROD = (() => {
  try {
    return Boolean(import.meta.env?.PROD);
  } catch {
    return false;
  }
})();

export interface Logger {
  debug: (...args: unknown[]) => void;
  info: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  error: (...args: unknown[]) => void;
  child: (subTag: string) => Logger;
}

function emit(level: Level, prefix: string, args: unknown[]): void {
  if (level === "debug" && IS_PROD) return;
  const sink =
    level === "error" ? console.error
    : level === "warn" ? console.warn
    : level === "debug" ? console.debug
    : console.info;
  sink(prefix, ...args);
}

/**
 * Create a tagged logger. Tags are wrapped in brackets, e.g. `[engine]`.
 * Use `child` to nest (`[engine][physics]`).
 */
export function createLog(tag: string): Logger {
  const prefix = `[${tag}]`;
  return {
    debug: (...args) => emit("debug", prefix, args),
    info: (...args) => emit("info", prefix, args),
    warn: (...args) => emit("warn", prefix, args),
    error: (...args) => emit("error", prefix, args),
    child: (subTag) => createLog(`${tag}][${subTag}`),
  };
}

/** Default app-wide logger. Subsystems should prefer their own `createLog(...)`. */
export const log = createLog("app");
