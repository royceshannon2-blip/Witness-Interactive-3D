/**
 * LedgerUI
 *
 * Full-screen DOM overlay — the player's collected evidence archive.
 * Implements the "Archival Solemnity" Ledger panel (screen 03) from the
 * UI/UX system: 4-column thumb grid, detail panel on the right, filter
 * tabs, keyboard hints footer.
 *
 * Opens on J / closes on J or Esc. DOM-based for clean CSS typography.
 * Per ARCHITECTURE.md §9.4.
 */

import type { LedgerEntry } from "../narrative/LedgerStore";

const OVERLAY_ID = "wit-ledger-panel";
const TOTAL_TRACES = 32; // canonical total from MISSION_BLUEPRINT

// Stripe palette cycles through cell thumbnails for visual variety.
const STRIPE_CLASSES = ["sa", "sb", "sc"] as const;

/** Derive a display tag from the entry key, e.g. "found_cellar_evidence" → "evidence". */
function _kindFromKey(key: string): string {
  if (/testimony|voice|statement/i.test(key)) return "testimony";
  if (/photograph|photo|image/i.test(key))    return "photograph";
  if (/letter|note|list/i.test(key))          return "letter";
  return "evidence";
}

class LedgerUIImpl {
  private el: HTMLElement | null = null;
  private selectedIndex = -1;
  private currentEntries: readonly LedgerEntry[] = [];

  open(entries: readonly LedgerEntry[]): void {
    this.close();
    this.currentEntries = entries;
    this.selectedIndex  = entries.length > 0 ? 0 : -1;

    const overlay = document.createElement("div");
    overlay.id = OVERLAY_ID;

    // ── Header ──────────────────────────────────────────────────────────
    const head = document.createElement("div");
    head.className = "wit-lp-head";

    const headLeft = document.createElement("div");
    headLeft.className = "wit-lp-head-left";

    const eyebrow = document.createElement("p");
    eyebrow.className = "wit-lp-eyebrow";
    eyebrow.textContent = "The Ledger";

    const title = document.createElement("h2");
    title.className = "wit-lp-title";
    title.textContent = "Traces gathered";
    const countSpan = document.createElement("span");
    countSpan.className = "wit-lp-title-count";
    countSpan.textContent = `${entries.length} of ${TOTAL_TRACES}`;
    title.appendChild(countSpan);

    headLeft.appendChild(eyebrow);
    headLeft.appendChild(title);

    const closeBtn = document.createElement("button");
    closeBtn.className = "wit-lp-close";
    closeBtn.setAttribute("aria-label", "Close ledger");
    closeBtn.innerHTML = `<span class="wit-kbd">J</span> Close`;
    closeBtn.addEventListener("click", () => this.close());

    head.appendChild(headLeft);
    head.appendChild(closeBtn);

    // ── Body: grid + detail ─────────────────────────────────────────────
    const body = document.createElement("div");
    body.className = "wit-lp-body";

    const grid = document.createElement("div");
    grid.className = "wit-lp-grid";
    this._populateGrid(grid, entries);

    const detail = document.createElement("div");
    detail.className = "wit-lp-detail";
    this._renderDetail(detail, entries.length > 0 ? entries[0] : null, 0);

    body.appendChild(grid);
    body.appendChild(detail);

    // ── Footer ───────────────────────────────────────────────────────────
    const foot = document.createElement("footer");
    foot.className = "wit-lp-foot";

    const hints = document.createElement("div");
    hints.className = "wit-lp-hints";
    hints.innerHTML = `
      <span><span class="wit-kbd">←→</span> browse</span>
      <span><span class="wit-kbd">J</span> close</span>
      <span><span class="wit-kbd">Esc</span> close</span>
    `;

    const sig = document.createElement("code");
    sig.className = "wit-lp-sig";
    sig.textContent = `Bisesero Ledger · ${entries.length} collected`;

    foot.appendChild(hints);
    foot.appendChild(sig);

    // ── Assemble ─────────────────────────────────────────────────────────
    overlay.appendChild(head);
    overlay.appendChild(body);
    overlay.appendChild(foot);
    document.body.appendChild(overlay);
    this.el = overlay;

    // Wire keyboard navigation.
    overlay.addEventListener("keydown", this._onKey.bind(this));

    // Defer so the class triggers CSS transition if we add one.
    requestAnimationFrame(() => overlay.classList.add("open"));
    closeBtn.focus();
  }

  close(): void {
    this.el?.remove();
    this.el = null;
    this.selectedIndex = -1;
  }

  isOpen(): boolean { return this.el !== null; }

  toggle(entries: readonly LedgerEntry[]): void {
    if (this.isOpen()) { this.close(); } else { this.open(entries); }
  }

  // -------------------------------------------------------------------------

  private _populateGrid(
    grid: HTMLElement,
    entries: readonly LedgerEntry[],
  ): void {
    if (entries.length === 0) {
      const empty = document.createElement("div");
      empty.style.cssText = "grid-column:1/-1; display:flex; align-items:center; justify-content:center; height:200px;";
      const p = document.createElement("p");
      p.style.cssText = "font-family:var(--serif); font-style:italic; font-size:18px; color:var(--stone); text-align:center; max-width:280px; line-height:1.6;";
      p.textContent = "Nothing gathered yet. Walk through the hills. The evidence will reveal itself.";
      empty.appendChild(p);
      grid.appendChild(empty);
      return;
    }

    entries.forEach((entry, idx) => {
      const cell = this._makeCell(entry, idx, STRIPE_CLASSES[idx % STRIPE_CLASSES.length]);
      cell.addEventListener("click", () => {
        this.selectedIndex = idx;
        grid.querySelectorAll(".wit-lp-cell").forEach((c, i) => {
          c.classList.toggle("selected", i === idx);
        });
        const detail = this.el?.querySelector(".wit-lp-detail");
        if (detail) this._renderDetail(detail as HTMLElement, entry, idx);
      });
      if (idx === 0) cell.classList.add("selected");
      grid.appendChild(cell);
    });

    // Show undiscovered placeholders.
    const remaining = TOTAL_TRACES - entries.length;
    for (let i = 0; i < Math.min(remaining, 8); i++) {
      grid.appendChild(this._makeUndiscoveredCell(entries.length + i + 1));
    }
  }

  private _makeCell(
    entry: LedgerEntry,
    idx: number,
    stripeClass: typeof STRIPE_CLASSES[number],
  ): HTMLElement {
    const cell = document.createElement("div");
    cell.className = "wit-lp-cell";
    cell.setAttribute("role", "button");
    cell.setAttribute("tabindex", "0");
    cell.setAttribute("aria-label", entry.text);

    const thumb = document.createElement("div");
    thumb.className = `wit-cell-thumb ${stripeClass}`;
    const tag = document.createElement("span");
    tag.className = "wit-cell-tag";
    tag.textContent = _kindFromKey(entry.key);
    thumb.appendChild(tag);

    const name = document.createElement("p");
    name.className = "wit-cell-name";
    name.textContent = entry.text;

    const meta = document.createElement("p");
    meta.className = "wit-cell-meta";
    const ref = `EV-${String(idx + 1).padStart(3, "0")}`;
    meta.textContent = ref;

    cell.appendChild(thumb);
    cell.appendChild(name);
    cell.appendChild(meta);

    cell.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") cell.click();
    });

    return cell;
  }

  private _makeUndiscoveredCell(n: number): HTMLElement {
    const cell = document.createElement("div");
    cell.className = "wit-lp-cell undiscovered";
    cell.setAttribute("aria-hidden", "true");

    const thumb = document.createElement("div");
    thumb.className = "wit-cell-thumb undiscovered";

    const name = document.createElement("p");
    name.className = "wit-cell-name";
    name.textContent = "— not yet gathered —";

    const meta = document.createElement("p");
    meta.className = "wit-cell-meta";
    meta.textContent = `EV-${String(n).padStart(3, "0")}`;

    cell.appendChild(thumb);
    cell.appendChild(name);
    cell.appendChild(meta);
    return cell;
  }

  private _renderDetail(
    container: HTMLElement,
    entry: LedgerEntry | null,
    idx: number,
  ): void {
    container.innerHTML = "";

    if (!entry) {
      const empty = document.createElement("div");
      empty.className = "wit-lp-detail-empty";
      const p = document.createElement("p");
      p.textContent = "Select a trace to read its record.";
      empty.appendChild(p);
      container.appendChild(empty);
      return;
    }

    const stripeClass = STRIPE_CLASSES[idx % STRIPE_CLASSES.length];

    // Thumbnail
    const thumb = document.createElement("div");
    thumb.className = `wit-lp-thumb-big wit-cell-thumb ${stripeClass}`;
    const thumbTag = document.createElement("span");
    thumbTag.className = "wit-cell-tag";
    thumbTag.textContent = _kindFromKey(entry.key);
    thumb.appendChild(thumbTag);

    // Reference number
    const ref = document.createElement("p");
    ref.className = "wit-lp-d-ref";
    ref.textContent = `EV-${String(idx + 1).padStart(3, "0")}`;

    // Name
    const name = document.createElement("h3");
    name.className = "wit-lp-d-name";
    name.textContent = entry.text;

    // Meta table
    const meta = document.createElement("dl");
    meta.className = "wit-lp-d-meta";

    const addRow = (label: string, value: string) => {
      const row = document.createElement("div");
      row.className = "wit-lp-d-meta-row";
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      row.appendChild(dt);
      row.appendChild(dd);
      meta.appendChild(row);
    };

    addRow("Gathered", "Bisesero Hills");
    addRow("Kind", _kindFromKey(entry.key));

    // Body text (extended description)
    const body = document.createElement("p");
    body.className = "wit-lp-d-body";
    body.textContent = entry.body ?? "No further notes.";

    // Badges
    const badges = document.createElement("div");
    badges.className = "wit-lp-d-badges";
    const b1 = document.createElement("span");
    b1.className = "wit-badge dusk";
    b1.textContent = "echo linked";
    badges.appendChild(b1);
    const b2 = document.createElement("span");
    b2.className = "wit-badge brass";
    b2.textContent = "significant";
    badges.appendChild(b2);

    container.appendChild(thumb);
    container.appendChild(ref);
    container.appendChild(name);
    container.appendChild(meta);
    container.appendChild(body);
    container.appendChild(badges);
  }

  private _onKey(e: KeyboardEvent): void {
    if (e.key === "j" || e.key === "J" || e.key === "Escape") {
      e.preventDefault();
      this.close();
    }
    if ((e.key === "ArrowRight" || e.key === "ArrowDown") && this.currentEntries.length > 0) {
      e.preventDefault();
      this.selectedIndex = (this.selectedIndex + 1) % this.currentEntries.length;
      this._selectCell(this.selectedIndex);
    }
    if ((e.key === "ArrowLeft" || e.key === "ArrowUp") && this.currentEntries.length > 0) {
      e.preventDefault();
      this.selectedIndex = (this.selectedIndex - 1 + this.currentEntries.length) % this.currentEntries.length;
      this._selectCell(this.selectedIndex);
    }
  }

  private _selectCell(idx: number): void {
    if (!this.el) return;
    const cells = this.el.querySelectorAll(".wit-lp-cell:not(.undiscovered)");
    cells.forEach((c, i) => c.classList.toggle("selected", i === idx));
    (cells[idx] as HTMLElement | undefined)?.focus();

    const detail = this.el.querySelector(".wit-lp-detail");
    if (detail) {
      this._renderDetail(
        detail as HTMLElement,
        this.currentEntries[idx] ?? null,
        idx,
      );
    }
  }
}

export const ledgerUI = new LedgerUIImpl();
