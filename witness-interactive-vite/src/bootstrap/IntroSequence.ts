/**
 * IntroSequence
 *
 * The DOM-based opening sequence per `docs/design-docs/OPENING_SEQUENCE.md`.
 *
 * What it does:
 *   1. Creates a full-screen black overlay above the canvas.
 *   2. Fades through title + dateline + archive entries.
 *   3. Crossfades the overlay out, exposing the 3D scene.
 *
 * What it deliberately does not do:
 *   - No loading bar, no spinner — assets stream behind a quiet text frame
 *     (per §3 "load-state behavior").
 *   - No music, no logo, no opening sting (per §7 + AUDIO_ARCHITECTURE §3).
 *
 * Demo abridgement: the spec's 45-second sequence is collapsed to ~12 s
 * here so iteration loops stay tight. Production timing lands when audio
 * + satellite imagery ship; the structure already tracks the spec's beats.
 *
 * Dev flags (per OPENING_SEQUENCE §8):
 *   - `?skipIntro=1`        → resolves immediately, no DOM created.
 *   - `prefers-reduced-motion: reduce` → static frame, no fades.
 */

const OVERLAY_ID = "witness-intro-overlay";

interface Beat {
  /** Seconds from intro start when this beat appears. */
  at: number;
  /** Seconds from intro start when this beat fades out (or `Infinity`). */
  until: number;
  /** Lines of text to render. Each line is a separate paragraph. */
  lines: string[];
  /** Visual register — controls font + size. */
  size?: "title" | "dateline" | "archive";
}

const ABRIDGED_BEATS: Beat[] = [
  { at: 0.4, until: Infinity, lines: ["BISESERO HILLS", "WESTERN PROVINCE, RWANDA"], size: "title" },
  { at: 2.2, until: Infinity, lines: ["April 2026"], size: "dateline" },
  { at: 4.5, until: 8.4, lines: ["April 1994. The 100 days begin."], size: "archive" },
  { at: 8.6, until: 11.6, lines: ["Your grandfather was one of them.", "He kept a ledger."], size: "archive" },
];

const TOTAL_INTRO_SEC = 12;
const HANDOFF_FADE_SEC = 1.6;

export interface IntroSequenceOpts {
  /**
   * Called at the moment the DOM overlay begins fading out (or immediately
   * on prefers-reduced-motion). The fade is `HANDOFF_FADE_SEC` long, so a
   * camera dolly of similar duration started here will land in sync with
   * the overlay disappearing.
   *
   * The `reduceMotion` arg is true when the user has set
   * `prefers-reduced-motion: reduce`; callers should snap the camera to
   * spawn pose without animation in that case (per OPENING_SEQUENCE.md §9
   * accessibility).
   *
   * Used by `bootstrap/main.ts` to start the cinematic camera descent that
   * settles into first-person spawn pose just as the overlay clears.
   */
  onFadeStart?: (info: { reduceMotion: boolean }) => void;
}

/**
 * Run the opening sequence. Resolves when the player is ready to take
 * control — either after the full sequence + fade-out, or immediately if
 * the dev skip flag is set.
 */
export async function runIntroSequence(opts: IntroSequenceOpts = {}): Promise<void> {
  const params = new URLSearchParams(window.location.search);
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

  if (params.get("skipIntro") === "1") {
    // Even on skip, give consumers a chance to land the cinematic camera in
    // its spawn pose synchronously. Treat the skip flag as reduced-motion
    // intent — callers expect a snap, not an animated descent.
    opts.onFadeStart?.({ reduceMotion: true });
    return;
  }

  const overlay = document.createElement("div");
  overlay.id = OVERLAY_ID;
  Object.assign(overlay.style, {
    position: "fixed",
    inset: "0",
    background: "#000",
    color: "#e9e3d6",
    fontFamily: "ui-serif, Georgia, 'Times New Roman', serif",
    display: "grid",
    placeItems: "center",
    zIndex: "1000",
    transition: `opacity ${HANDOFF_FADE_SEC}s ease-in-out`,
    opacity: "1",
    pointerEvents: "auto",
  } as Partial<CSSStyleDeclaration>);
  document.body.appendChild(overlay);

  const stack = document.createElement("div");
  stack.setAttribute("aria-live", "polite");
  Object.assign(stack.style, {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "1.4rem",
    padding: "2rem",
    textAlign: "center",
    maxWidth: "min(640px, 90vw)",
  } as Partial<CSSStyleDeclaration>);
  overlay.appendChild(stack);

  if (reduceMotion) {
    // Static composition: render the title + final archive entry; hold for
    // a beat; then resolve. No fades, no per-beat scheduling.
    stack.appendChild(makeBlock(ABRIDGED_BEATS[0]));
    stack.appendChild(makeBlock(ABRIDGED_BEATS[1]));
    stack.appendChild(makeBlock(ABRIDGED_BEATS[3]));
    await sleep(3000);
    opts.onFadeStart?.({ reduceMotion });
    await fadeOut(overlay);
    return;
  }

  // Schedule each beat. Each block fades in over ~1.4 s and out over ~1.0 s
  // by inserting CSS transitions and toggling opacity.
  for (const beat of ABRIDGED_BEATS) {
    void scheduleBeat(stack, beat);
  }

  await sleep(TOTAL_INTRO_SEC * 1000);
  // Notify the bootstrap that the overlay is about to fade — gives it the
  // window to start the synchronized camera descent.
  opts.onFadeStart?.({ reduceMotion });
  await fadeOut(overlay);
}

function scheduleBeat(stack: HTMLElement, beat: Beat): Promise<void> {
  return new Promise((resolve) => {
    const block = makeBlock(beat);
    block.style.opacity = "0";
    block.style.transition = "opacity 1.4s ease-in-out";
    stack.appendChild(block);

    setTimeout(() => {
      block.style.opacity = "1";
    }, beat.at * 1000);

    if (beat.until !== Infinity) {
      setTimeout(() => {
        block.style.transition = "opacity 1s ease-in-out";
        block.style.opacity = "0";
        setTimeout(() => {
          block.remove();
          resolve();
        }, 1100);
      }, beat.until * 1000);
    } else {
      // Beats with `until: Infinity` ride out with the overlay fade.
      resolve();
    }
  });
}

function makeBlock(beat: Beat): HTMLElement {
  const wrap = document.createElement("div");
  Object.assign(wrap.style, {
    display: "flex",
    flexDirection: "column",
    gap: "0.4rem",
  } as Partial<CSSStyleDeclaration>);

  const sizing = beatStyle(beat.size ?? "archive");
  for (const line of beat.lines) {
    const p = document.createElement("p");
    p.textContent = line;
    Object.assign(p.style, sizing as Partial<CSSStyleDeclaration>);
    wrap.appendChild(p);
  }
  return wrap;
}

function beatStyle(size: NonNullable<Beat["size"]>): Record<string, string> {
  switch (size) {
    case "title":
      return {
        margin: "0",
        fontSize: "clamp(20px, 2.4vw, 28px)",
        letterSpacing: "0.16em",
        fontWeight: "500",
        textTransform: "uppercase",
      };
    case "dateline":
      return {
        margin: "0",
        fontSize: "clamp(14px, 1.5vw, 17px)",
        letterSpacing: "0.05em",
        opacity: "0.85",
      };
    case "archive":
      return {
        margin: "0",
        fontSize: "clamp(15px, 1.6vw, 18px)",
        lineHeight: "1.55",
        fontStyle: "italic",
        opacity: "0.78",
        maxWidth: "44ch",
      };
  }
}

async function fadeOut(overlay: HTMLElement): Promise<void> {
  overlay.style.opacity = "0";
  await sleep(HANDOFF_FADE_SEC * 1000);
  overlay.remove();
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
