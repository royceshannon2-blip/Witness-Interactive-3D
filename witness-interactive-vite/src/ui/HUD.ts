/**
 * HUD
 *
 * DOM-based heads-up display rendered over the 3D canvas. Four fixed
 * elements matching the "Archival Solemnity" design system:
 *
 *   · Echo indicator   (top-left)    — dusk rings + direction code
 *   · Ledger badge     (top-right)   — icon + count + "+1" pulse
 *   · Interaction prompt (center-low)— key chip + serif verb
 *   · Compass          (bottom-left) — ring, needle, coord + location
 *
 * A toast notification (bottom-center) surfaces ledger entry messages.
 * The subtitle bar is handled separately by CaptionOverlay.
 *
 * Deliberately no Babylon GUI dependency — DOM gives us full CSS control
 * over typography and the design token system. Per ARCHITECTURE.md §9.
 */

import type { Camera, Scene } from "@babylonjs/core";

const LEDGER_NEW_SHOW_MS  = 2000;
const TOAST_SHOW_MS       = 5000;

const LEDGER_SVG = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none"
  stroke="currentColor" stroke-width="0.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M6 4 L6 20 M18 4 L18 20 M6 7 L18 7 M6 12 L18 12 M6 17 L18 17"/>
</svg>`;

const COMPASS_SVG = `<svg viewBox="0 0 72 72" width="72" height="72"
  fill="none" stroke="currentColor" stroke-linecap="round">
  <!-- outer ring -->
  <circle cx="36" cy="36" r="33" stroke-width="0.5" opacity="0.4"/>
  <!-- inner ring -->
  <circle cx="36" cy="36" r="21" stroke-width="0.5" opacity="0.22"/>
  <!-- cardinals -->
  <text x="36" y="9"  text-anchor="middle" font-family="JetBrains Mono,monospace"
    font-size="8" letter-spacing="1" fill="currentColor" stroke="none"
    style="color:var(--linen)">N</text>
  <text x="36" y="68" text-anchor="middle" font-family="JetBrains Mono,monospace"
    font-size="8" letter-spacing="1" fill="var(--ash)" stroke="none">S</text>
  <text x="65" y="39.5" text-anchor="middle" font-family="JetBrains Mono,monospace"
    font-size="8" letter-spacing="1" fill="var(--ash)" stroke="none">E</text>
  <text x="7" y="39.5" text-anchor="middle" font-family="JetBrains Mono,monospace"
    font-size="8" letter-spacing="1" fill="var(--ash)" stroke="none">W</text>
  <!-- needle — heading indicator, rotated by setHeading() -->
  <line x1="36" y1="36" x2="36" y2="9"
    stroke="var(--bone)" stroke-width="1"
    class="wit-compass-needle"/>
  <!-- target tick — brass, rotated to nearest echo by setEchoDirection() -->
  <line x1="36" y1="5" x2="36" y2="11"
    stroke="var(--brass)" stroke-width="1.5"
    class="wit-compass-target" opacity="0"/>
</svg>`;

class HUDImpl {
  private root: HTMLDivElement | null = null;

  // Echo
  private echoEl:      HTMLDivElement | null = null;
  private echoLabel:   HTMLElement    | null = null;

  // Ledger badge
  private ledgerCount: HTMLElement    | null = null;
  private ledgerTotal: HTMLElement    | null = null;
  private ledgerNew:   HTMLDivElement | null = null;
  private ledgerNewTimer: ReturnType<typeof setTimeout> | null = null;
  private _ledgerCount = 0;

  // Interaction prompt
  private promptEl:    HTMLDivElement | null = null;
  private promptKey:   HTMLDivElement | null = null;
  private promptText:  HTMLParagraphElement | null = null;

  // Compass
  private compassNeedle: SVGLineElement | null = null;
  private compassTarget: SVGLineElement | null = null;
  private coordEl:     HTMLElement    | null = null;
  private locEl:       HTMLSpanElement | null = null;

  // Toast
  private toastEl:     HTMLDivElement | null = null;
  private toastText:   HTMLSpanElement | null = null;
  private toastTimer:  ReturnType<typeof setTimeout> | null = null;

  /**
   * Build the HUD DOM and attach it to document.body.
   * `scene` and `primaryCamera` are accepted for API compatibility
   * and potential future use (e.g. reading camera heading).
   */
  attach(_scene: Scene, _primaryCamera: Camera): void {
    if (this.root) return;

    const root = document.createElement("div");
    root.id = "wit-hud";
    document.body.appendChild(root);
    this.root = root;

    this._buildEcho(root);
    this._buildLedgerBadge(root);
    this._buildPrompt(root);
    this._buildCompass(root);
    this._buildToast(root);
  }

  // -------------------------------------------------------------------------
  // Build helpers

  private _buildEcho(root: HTMLElement): void {
    const el = document.createElement("div");
    el.className = "wit-echo";

    const rings = document.createElement("div");
    rings.className = "wit-echo-rings";
    const r1 = document.createElement("div");
    r1.className = "wit-echo-ring";
    const r2 = document.createElement("div");
    r2.className = "wit-echo-ring";
    rings.appendChild(r1);
    rings.appendChild(r2);

    const code = document.createElement("code");
    code.textContent = "Echo · nearby";

    el.appendChild(rings);
    el.appendChild(code);
    root.appendChild(el);
    this.echoEl    = el;
    this.echoLabel = code;
  }

  private _buildLedgerBadge(root: HTMLElement): void {
    const el = document.createElement("div");
    el.className = "wit-ledger-badge";

    const glyph = document.createElement("div");
    glyph.className = "wit-ledger-badge-glyph";
    glyph.innerHTML = LEDGER_SVG;

    const text = document.createElement("div");
    text.className = "wit-ledger-badge-text";

    const label = document.createElement("em");
    label.textContent = "Ledger";

    const meta = document.createElement("span");
    const b = document.createElement("b");
    b.textContent = "0";
    meta.appendChild(b);
    meta.append(" of ");
    const i = document.createElement("i");
    i.textContent = "—";
    meta.appendChild(i);
    meta.append(" traces");

    text.appendChild(label);
    text.appendChild(meta);

    const newBadge = document.createElement("div");
    newBadge.className = "wit-ledger-new";
    newBadge.textContent = "+1";

    el.appendChild(glyph);
    el.appendChild(text);
    el.appendChild(newBadge);
    root.appendChild(el);

    this.ledgerCount = b;
    this.ledgerTotal = i;
    this.ledgerNew   = newBadge;
  }

  private _buildPrompt(root: HTMLElement): void {
    const el = document.createElement("div");
    el.className = "wit-prompt";

    const key = document.createElement("div");
    key.className = "wit-prompt-key";
    key.textContent = "E";

    const text = document.createElement("p");
    text.className = "wit-prompt-text";
    text.textContent = "Examine";

    el.appendChild(key);
    el.appendChild(text);
    root.appendChild(el);

    this.promptEl   = el;
    this.promptKey  = key;
    this.promptText = text;
  }

  private _buildCompass(root: HTMLElement): void {
    const el = document.createElement("div");
    el.className = "wit-compass";

    const ring = document.createElement("div");
    ring.className = "wit-compass-ring";
    ring.innerHTML = COMPASS_SVG;

    const meta = document.createElement("div");
    meta.className = "wit-compass-meta";

    const coord = document.createElement("code");
    coord.className = "wit-compass-coord";
    coord.textContent = "Bisesero Hills";

    const loc = document.createElement("span");
    loc.className = "wit-compass-loc";

    meta.appendChild(coord);
    meta.appendChild(loc);
    el.appendChild(ring);
    el.appendChild(meta);
    root.appendChild(el);

    this.coordEl   = coord;
    this.locEl     = loc;

    // Grab SVG sub-elements for rotation.
    const svg = ring.querySelector("svg");
    if (svg) {
      this.compassNeedle = svg.querySelector(".wit-compass-needle");
      this.compassTarget = svg.querySelector(".wit-compass-target");
    }
  }

  private _buildToast(root: HTMLElement): void {
    const el = document.createElement("div");
    el.className = "wit-toast";

    const icon = document.createElement("span");
    icon.className = "wit-toast-icon";
    icon.textContent = "Ledger";

    const text = document.createElement("span");
    text.className = "wit-toast-text";

    el.appendChild(icon);
    el.appendChild(text);
    root.appendChild(el);

    this.toastEl   = el;
    this.toastText = text;
  }

  // -------------------------------------------------------------------------
  // Public API

  /** Update the compass coordinate readout (replaces old date label). */
  setDateLabel(text: string): void {
    if (this.coordEl) this.coordEl.textContent = text;
  }

  /** Update the compass location line. */
  setLocationLabel(text: string): void {
    if (this.locEl) this.locEl.textContent = text;
  }

  /**
   * Show or hide the interaction prompt. When `active` is true a key chip
   * and action verb are displayed center-screen.
   *
   * @param active  Whether a proximity prompt should be visible.
   * @param prompt  Full prompt text, e.g. "Examine the broken radio [E]".
   *                If the text ends with "[X]" the key is extracted.
   */
  setProximity(active: boolean, prompt?: string): void {
    if (!this.promptEl) return;

    if (!active) {
      this.promptEl.classList.remove("visible");
      return;
    }

    // Extract key hint from end of prompt string, e.g. "Examine [E]" → key=E
    let key = "E";
    let text = prompt ?? "Examine";
    const keyMatch = text.match(/\[([A-Z0-9])\]\s*$/i);
    if (keyMatch) {
      key  = keyMatch[1].toUpperCase();
      text = text.slice(0, text.lastIndexOf("[")).trim();
    }

    if (this.promptKey) this.promptKey.textContent = key;
    if (this.promptText) this.promptText.textContent = text;
    this.promptEl.classList.add("visible");
  }

  /**
   * Flash the bottom-center toast for `durationMs` with the given text.
   * Subsequent calls cancel the prior toast.
   */
  showLedgerToast(text: string, durationMs = TOAST_SHOW_MS): void {
    if (!this.toastEl || !this.toastText) return;
    if (this.toastTimer) { clearTimeout(this.toastTimer); this.toastTimer = null; }

    // Strip the "Ledger entry unlocked: " prefix for cleaner display.
    const cleaned = text.replace(/^Ledger entry unlocked:\s*/i, "");
    this.toastText.textContent = cleaned;
    this.toastEl.classList.add("visible");

    this.toastTimer = setTimeout(() => {
      this.toastEl?.classList.remove("visible");
      this.toastTimer = null;
    }, durationMs);
  }

  /**
   * Update the ledger badge count. Pulses "+1" badge on increase.
   * @param count   Total entries collected.
   * @param total   Optional total available (shown as "N of M traces").
   */
  setLedgerCount(count: number, total?: number): void {
    const prev = this._ledgerCount;
    this._ledgerCount = count;

    if (this.ledgerCount) this.ledgerCount.textContent = String(count);
    if (this.ledgerTotal && total !== undefined) {
      this.ledgerTotal.textContent = String(total);
    }

    if (count > prev && this.ledgerNew) {
      if (this.ledgerNewTimer) { clearTimeout(this.ledgerNewTimer); this.ledgerNewTimer = null; }
      this.ledgerNew.classList.add("visible");
      this.ledgerNewTimer = setTimeout(() => {
        this.ledgerNew?.classList.remove("visible");
        this.ledgerNewTimer = null;
      }, LEDGER_NEW_SHOW_MS);
    }
  }

  /**
   * Rotate the compass needle to the given magnetic heading (0=north, CW).
   * Not yet wired to the player controller; call when heading changes.
   */
  setHeading(degrees: number): void {
    if (this.compassNeedle) {
      (this.compassNeedle as SVGLineElement).style.transform = `rotate(${degrees}deg)`;
    }
  }

  /**
   * Show the brass echo-direction tick on the compass and update the
   * echo indicator label. Pass `null` to hide.
   */
  setEchoDistance(meters: number | null, cardinalLabel?: string): void {
    if (meters === null) {
      this.echoEl?.classList.remove("visible");
      if (this.compassTarget) this.compassTarget.setAttribute("opacity", "0");
      return;
    }
    if (this.echoLabel) {
      this.echoLabel.textContent = cardinalLabel
        ? `Echo · ${meters} m ${cardinalLabel}`
        : `Echo · ${meters} m`;
    }
    this.echoEl?.classList.add("visible");
    if (this.compassTarget) this.compassTarget.setAttribute("opacity", "1");
  }

  detach(_scene: Scene): void {
    if (this.toastTimer)     { clearTimeout(this.toastTimer);     this.toastTimer     = null; }
    if (this.ledgerNewTimer) { clearTimeout(this.ledgerNewTimer); this.ledgerNewTimer = null; }
    this.root?.remove();
    this.root           = null;
    this.echoEl        = null;
    this.echoLabel     = null;
    this.ledgerCount   = null;
    this.ledgerTotal   = null;
    this.ledgerNew     = null;
    this.promptEl      = null;
    this.promptKey     = null;
    this.promptText    = null;
    this.compassNeedle = null;
    this.compassTarget = null;
    this.coordEl       = null;
    this.locEl         = null;
    this.toastEl        = null;
    this.toastText      = null;
  }
}

export const hud = new HUDImpl();
