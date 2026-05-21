/**
 * ChoiceOverlay
 *
 * Act 3 path-selection prompt styled per the "Archival Solemnity" design
 * system (screen 05 — Choice interface). Full-screen DOM overlay that
 * presents 3–5 branching narrative options with serif hierarchy and
 * a brass left-rail on hover.
 *
 * Returns a Promise<string> resolving to the chosen path flag. No timers.
 * Per MISSION_BLUEPRINT.md §3.
 */

import { CHOICE_DESCRIPTIONS } from "../narrative/BanterLibrary";
import type { PathFlag } from "../narrative/BanterLibrary";

const FADE_OUT_MS = 850;

interface PathOption {
  flag:          PathFlag;
  evidenceLine:  string;
  pathName:      string;
  description:   string;
}

const PATH_OPTIONS: PathOption[] = [
  {
    flag:         "path_hider_chosen",
    evidenceLine: "He hid people. I found the cellar.",
    pathName:     "The Path of the Righteous",
    description:  CHOICE_DESCRIPTIONS.path_hider_chosen,
  },
  {
    flag:         "path_escapist_chosen",
    evidenceLine: "He helped them escape. I found the boat paddle.",
    pathName:     "The Path of the Survivor",
    description:  CHOICE_DESCRIPTIONS.path_escapist_chosen,
  },
  {
    flag:         "path_silent_chosen",
    evidenceLine: "He stayed neutral to survive. I found his observer's notes.",
    pathName:     "The Path of the Silent",
    description:  CHOICE_DESCRIPTIONS.path_silent_chosen,
  },
];

// Roman numerals for up to 5 options.
const NUMERALS = ["i", "ii", "iii", "iv", "v"];

/**
 * Show the Act 3 choice prompt over the live 3D scene.
 * Resolves with the chosen path flag string.
 */
export function showChoiceOverlay(): Promise<string> {
  return new Promise<string>((resolve) => {
    const overlay = document.createElement("div");
    overlay.id = "wit-choice-overlay";
    document.body.appendChild(overlay);

    // Trigger fade-in after layout.
    requestAnimationFrame(() => {
      overlay.classList.add("open");
      requestAnimationFrame(() => overlay.classList.add("visible"));
    });

    const inner = document.createElement("div");
    inner.className = "wit-choice-inner";

    // ── Header ─────────────────────────────────────────────────────────
    const head = document.createElement("div");
    head.className = "wit-choice-head";

    const stamp = document.createElement("code");
    stamp.className = "wit-choice-stamp";
    stamp.textContent = "Act III · The reckoning";

    const prompt = document.createElement("h2");
    prompt.className = "wit-choice-prompt";
    prompt.textContent = "Your grandfather survived that night. But how?";

    const sub = document.createElement("p");
    sub.className = "wit-choice-sub";
    sub.textContent = "The evidence you gathered points to one path. Whatever you choose, you cannot return to this moment.";

    head.appendChild(stamp);
    head.appendChild(prompt);
    head.appendChild(sub);

    // ── Options ────────────────────────────────────────────────────────
    const optList = document.createElement("ol");
    optList.className = "wit-choice-options";
    optList.setAttribute("role", "listbox");
    optList.setAttribute("aria-label", "Choose a path");

    const commit = (flag: string) => {
      overlay.style.transition = `opacity ${FADE_OUT_MS}ms ease-in-out`;
      overlay.classList.remove("visible");
      setTimeout(() => {
        overlay.remove();
        resolve(flag);
      }, FADE_OUT_MS + 60);
    };

    PATH_OPTIONS.forEach((opt, idx) => {
      const li = document.createElement("li");
      li.className = "wit-choice-opt";
      li.setAttribute("role", "option");
      li.setAttribute("tabindex", "0");

      const num = document.createElement("span");
      num.className = "wit-choice-num";
      num.setAttribute("aria-hidden", "true");
      num.textContent = NUMERALS[idx] ?? String(idx + 1);

      const body = document.createElement("div");
      body.className = "wit-choice-body";

      const text = document.createElement("p");
      text.className = "wit-choice-text";
      text.textContent = opt.evidenceLine;

      const meta = document.createElement("div");
      meta.className = "wit-choice-meta";

      const trace = document.createElement("span");
      trace.className = "wit-choice-trace";
      trace.textContent = `leads to · ${opt.pathName}`;

      const desc = document.createElement("span");
      desc.style.cssText = `
        font-family:var(--serif);
        font-style:italic;
        font-size:13px;
        color:var(--ash);
        display:block;
        margin-top:4px;
      `;
      desc.textContent = opt.description;

      meta.appendChild(trace);
      body.appendChild(text);
      body.appendChild(meta);
      body.appendChild(desc);

      const keyHint = document.createElement("span");
      keyHint.className = "wit-choice-key";
      keyHint.setAttribute("aria-hidden", "true");
      keyHint.textContent = String(idx + 1);

      li.appendChild(num);
      li.appendChild(body);
      li.appendChild(keyHint);
      optList.appendChild(li);

      const doCommit = () => commit(opt.flag);
      li.addEventListener("click", doCommit);
      li.addEventListener("keydown", (e: KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); doCommit(); }
      });
    });

    // Keyboard shortcut: 1/2/3 → pick option directly.
    const onDocKey = (e: KeyboardEvent) => {
      const n = parseInt(e.key, 10);
      if (n >= 1 && n <= PATH_OPTIONS.length) {
        document.removeEventListener("keydown", onDocKey);
        commit(PATH_OPTIONS[n - 1].flag);
      }
    };
    document.addEventListener("keydown", onDocKey);

    // ── Footer ─────────────────────────────────────────────────────────
    const foot = document.createElement("div");
    foot.className = "wit-choice-foot";

    const note = document.createElement("p");
    note.className = "wit-choice-foot-note";
    note.textContent = "Your previous choices remain. The path forks here.";

    const hints = document.createElement("div");
    hints.className = "wit-choice-hints";
    hints.innerHTML = `
      <span><span class="wit-kbd">↑↓</span> consider</span>
      <span><span class="wit-kbd">↵</span> commit</span>
      <span><span class="wit-kbd">1–${PATH_OPTIONS.length}</span> quick-select</span>
    `;

    foot.appendChild(note);
    foot.appendChild(hints);

    inner.appendChild(head);
    inner.appendChild(optList);
    inner.appendChild(foot);
    overlay.appendChild(inner);

    // Focus first option for keyboard accessibility.
    requestAnimationFrame(() => {
      const firstOpt = optList.querySelector<HTMLElement>(".wit-choice-opt");
      firstOpt?.focus();
    });
  });
}
