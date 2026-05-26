/**
 * RemembranceSequence
 *
 * Act 4 DOM overlay per MISSION_BLUEPRINT.md §5 ("Remembrance").
 * Fires once the last puzzle flag for the chosen path is set.
 *
 * Two phases:
 *   1. Climactic ledger entry — path-specific quote. Held on screen for
 *      PHASE1_AUTO_SEC, or until the player presses any non-modifier key.
 *   2. Four non-branching reflection options per MISSION_BLUEPRINT §5.
 *      On selection the closing voice-over text is shown for CLOSING_SEC,
 *      then the overlay fades and the promise resolves.
 *
 * DOM only — no Babylon GUI dependency. Same transient, full-bleed pattern
 * as ChoiceOverlay and IntroSequence. The caller (main.ts) sets
 * game_complete + memorialization_complete on globalState after resolution.
 */

const FADE_IN_SEC = 1.6;
const FADE_OUT_SEC = 1.2;
const PHASE_CROSS_SEC = 0.45;
const PHASE1_AUTO_SEC = 9;
const CLOSING_BUTTON_DELAY_SEC = 4;

export type RemembrancePath = "a" | "b" | "c";
export type MemorializationKey = "shrine" | "note" | "photograph" | "silence";

interface PathContent {
  quote: string;
  attribution: string;
}

const PATH_CONTENT: Record<RemembrancePath, PathContent> = {
  a: {
    quote:
      "I stayed so they could leave. If they find me here alone, they will know someone was hidden. I will tell them nothing.",
    attribution: "— Grandfather's ledger, June 1994. He never came home.",
  },
  b: {
    quote:
      "I came back for a second group. The lake had changed hands. I could not go back. Eighty-seven names circled. The rest, blank space.",
    attribution: "— Grandfather's ledger, May 1994. The boat did not return.",
  },
  c: {
    quote:
      "I survived by being invisible. But invisibility is its own curse. He saw us die. He said nothing. But he saw.",
    attribution: "— Grandfather's ledger and a visitor's account, June 1994.",
  },
};

const REFLECTION_OPTIONS: Array<{
  key: MemorializationKey;
  action: string;
  label: string;
}> = [
  { key: "shrine",     action: "Place the ledger on the family shrine.", label: "Honoring the past" },
  { key: "note",       action: "Leave a note for future visitors.",       label: "Passing the story on" },
  { key: "photograph", action: "Photograph the ledger.",                  label: "Preserving it" },
  { key: "silence",    action: "Sit in silence.",                         label: "Simply being present" },
];

const CLOSING_VOICE =
  "Your grandfather made a choice. All choices in genocide are terrible. " +
  "But survivors carry the weight of their choices into the rest of their lives. " +
  "Now you carry the weight of knowing.";

function applyStyle(el: HTMLElement, styles: Partial<CSSStyleDeclaration>): void {
  Object.assign(el.style, styles);
}

/** Fade inner's opacity out, replace children, fade back in. */
function crossFade(inner: HTMLElement, newContent: HTMLElement): void {
  applyStyle(inner, { transition: `opacity ${PHASE_CROSS_SEC}s ease-in-out`, opacity: "0" });
  setTimeout(() => {
    inner.replaceChildren(newContent);
    requestAnimationFrame(() => { inner.style.opacity = "1"; });
  }, PHASE_CROSS_SEC * 1000 + 20);
}

function buildPhase1(path: RemembrancePath, onAdvance: () => void): HTMLElement {
  const { quote, attribution } = PATH_CONTENT[path];

  const root = document.createElement("div");
  applyStyle(root, {
    display: "flex",
    flexDirection: "column",
    gap: "1.8rem",
    padding: "2.4rem",
    maxWidth: "min(600px, 90vw)",
  });

  const label = document.createElement("p");
  label.textContent = "The Shepherd's Ledger";
  applyStyle(label, {
    margin: "0",
    fontSize: "clamp(10px, 1.1vw, 12px)",
    letterSpacing: "0.18em",
    textTransform: "uppercase",
    opacity: "0.34",
  });
  root.appendChild(label);

  const quoteEl = document.createElement("blockquote");
  quoteEl.textContent = quote;
  applyStyle(quoteEl, {
    margin: "0",
    fontSize: "clamp(16px, 2vw, 22px)",
    lineHeight: "1.6",
    fontStyle: "italic",
    opacity: "0.9",
  });
  root.appendChild(quoteEl);

  const attr = document.createElement("p");
  attr.textContent = attribution;
  applyStyle(attr, {
    margin: "0",
    fontSize: "clamp(11px, 1.2vw, 13px)",
    opacity: "0.44",
  });
  root.appendChild(attr);

  const hint = document.createElement("p");
  hint.textContent = "Press any key to continue.";
  applyStyle(hint, {
    margin: "0.6rem 0 0 0",
    fontSize: "clamp(10px, 1.05vw, 11px)",
    opacity: "0.2",
  });
  root.appendChild(hint);

  let advanced = false;
  const advance = () => {
    if (advanced) return;
    advanced = true;
    clearTimeout(timer);
    document.removeEventListener("keydown", keyHandler);
    onAdvance();
  };

  // Advance on any meaningful keypress; ignore bare modifiers.
  const MODIFIER_KEYS = new Set(["Shift", "Control", "Alt", "Meta", "CapsLock", "Tab"]);
  const keyHandler = (e: KeyboardEvent) => {
    if (!MODIFIER_KEYS.has(e.key)) advance();
  };
  document.addEventListener("keydown", keyHandler);
  const timer = setTimeout(advance, PHASE1_AUTO_SEC * 1000);

  return root;
}

function buildPhase2(onSelect: (key: MemorializationKey) => void): HTMLElement {
  const root = document.createElement("div");
  applyStyle(root, {
    display: "flex",
    flexDirection: "column",
    gap: "1.6rem",
    padding: "2.4rem",
    maxWidth: "min(560px, 90vw)",
  });

  const heading = document.createElement("p");
  heading.textContent = "You have returned to the compound.";
  applyStyle(heading, {
    margin: "0",
    fontSize: "clamp(15px, 1.7vw, 19px)",
    lineHeight: "1.4",
    opacity: "0.88",
  });
  root.appendChild(heading);

  const subheading = document.createElement("p");
  subheading.textContent = "What will you do with this knowledge?";
  applyStyle(subheading, {
    margin: "0",
    fontSize: "clamp(13px, 1.4vw, 15px)",
    opacity: "0.48",
    fontStyle: "italic",
  });
  root.appendChild(subheading);

  const divider = document.createElement("hr");
  applyStyle(divider, {
    border: "none",
    borderTop: "1px solid rgba(233,227,214,0.14)",
    margin: "0",
  });
  root.appendChild(divider);

  for (const opt of REFLECTION_OPTIONS) {
    const item = document.createElement("div");
    item.setAttribute("role", "button");
    item.setAttribute("tabindex", "0");
    applyStyle(item, {
      cursor: "pointer",
      borderLeft: "2px solid rgba(233,227,214,0.18)",
      paddingLeft: "1.2rem",
      transition: "border-color 0.18s ease",
      outline: "none",
    });

    const actionEl = document.createElement("p");
    actionEl.textContent = opt.action;
    applyStyle(actionEl, {
      margin: "0",
      fontSize: "clamp(14px, 1.6vw, 18px)",
      lineHeight: "1.4",
    });

    const labelEl = document.createElement("p");
    labelEl.textContent = opt.label;
    applyStyle(labelEl, {
      margin: "0.25rem 0 0 0",
      fontSize: "clamp(10px, 1.1vw, 12px)",
      fontStyle: "italic",
      opacity: "0.36",
      letterSpacing: "0.07em",
      textTransform: "uppercase",
    });

    item.appendChild(actionEl);
    item.appendChild(labelEl);
    root.appendChild(item);

    const select = () => onSelect(opt.key);
    item.addEventListener("click", select);
    item.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") select();
    });
    item.addEventListener("mouseenter", () => {
      item.style.borderLeftColor = "rgba(233,227,214,0.78)";
    });
    item.addEventListener("mouseleave", () => {
      item.style.borderLeftColor = "rgba(233,227,214,0.18)";
    });
  }

  return root;
}

function buildClosingVoice(onRestart: () => void): HTMLElement {
  const root = document.createElement("div");
  applyStyle(root, {
    display: "flex",
    flexDirection: "column",
    gap: "2rem",
    padding: "2.4rem",
    maxWidth: "min(560px, 90vw)",
  });

  const voice = document.createElement("p");
  voice.textContent = CLOSING_VOICE;
  applyStyle(voice, {
    margin: "0",
    fontSize: "clamp(14px, 1.65vw, 19px)",
    lineHeight: "1.7",
    fontStyle: "italic",
    opacity: "0.8",
  });
  root.appendChild(voice);

  // "Play Again?" button appears after CLOSING_BUTTON_DELAY_SEC so the
  // closing voice has time to settle before the option surfaces.
  const btn = document.createElement("button");
  btn.textContent = "Play again";
  applyStyle(btn, {
    alignSelf: "flex-start",
    background: "none",
    border: "1px solid rgba(233,227,214,0.3)",
    color: "#e9e3d6",
    fontFamily: "inherit",
    fontSize: "clamp(12px, 1.3vw, 14px)",
    letterSpacing: "0.12em",
    padding: "0.6rem 1.4rem",
    cursor: "pointer",
    opacity: "0",
    transition: "opacity 0.6s ease-in-out, border-color 0.18s ease",
  });
  btn.addEventListener("mouseenter", () => {
    btn.style.borderColor = "rgba(233,227,214,0.78)";
  });
  btn.addEventListener("mouseleave", () => {
    btn.style.borderColor = "rgba(233,227,214,0.3)";
  });
  btn.addEventListener("click", onRestart);
  root.appendChild(btn);

  setTimeout(() => {
    btn.style.opacity = "1";
  }, CLOSING_BUTTON_DELAY_SEC * 1000);

  return root;
}

/**
 * Show the Act 4 Remembrance overlay. Resolves with the memorialization
 * key the player chose. Never rejects. See MISSION_BLUEPRINT.md §5.
 */
export function showRemembranceSequence(path: RemembrancePath): Promise<MemorializationKey> {
  return new Promise<MemorializationKey>((resolve) => {
    const overlay = document.createElement("div");
    applyStyle(overlay, {
      position: "fixed",
      inset: "0",
      background: "rgba(0, 0, 0, 0.97)",
      color: "#e9e3d6",
      fontFamily: "ui-serif, Georgia, 'Times New Roman', serif",
      display: "grid",
      placeItems: "center",
      zIndex: "1000",
      opacity: "0",
      transition: `opacity ${FADE_IN_SEC}s ease-in-out`,
      pointerEvents: "auto",
    });
    document.body.appendChild(overlay);

    const inner = document.createElement("div");
    overlay.appendChild(inner);

    // Phase 1 → Phase 2 → Closing (with "Play Again?" button) → reload
    inner.appendChild(
      buildPhase1(path, () => {
        crossFade(
          inner,
          buildPhase2((key) => {
            const onRestart = () => {
              applyStyle(overlay, {
                transition: `opacity ${FADE_OUT_SEC}s ease-in-out`,
                opacity: "0",
              });
              setTimeout(() => {
                overlay.remove();
                resolve(key);
                // Give the resolve handler a tick to fire before reload.
                // Strip ?resume=1 and other params — "Play again" starts fresh.
                setTimeout(() => { window.location.href = window.location.pathname; }, 50);
              }, FADE_OUT_SEC * 1000 + 80);
            };
            crossFade(inner, buildClosingVoice(onRestart));
          }),
        );
      }),
    );

    // Defer so the browser lays out the overlay before the transition starts.
    requestAnimationFrame(() => {
      overlay.style.opacity = "1";
    });
  });
}
