/**
 * CaptionOverlay
 *
 * Fixed-position subtitle bar styled per the "Archival Solemnity" design
 * system (screen 02, HUD subtitle element). Displays narrator text synced
 * from WebVTT cue files, or plain text via showText().
 *
 * Structure:
 *   · Speaker line  — mono uppercase, brass dot, "Narrator"
 *   · Caption line  — Cormorant Garamond 26px, filmic text-shadow
 *
 * Default ON for accessibility; toggleable at runtime.
 * Per ARCHITECTURE.md §5.11, AUDIO_ARCHITECTURE.md §4.
 */

interface VttCue {
  startSec: number;
  endSec:   number;
  text:     string;
  speaker?: string;
}

class CaptionOverlayImpl {
  private el:          HTMLElement | null = null;
  private speakerEl:   HTMLElement | null = null;
  private lineEl:      HTMLElement | null = null;
  private enabled      = true;
  private cueTimer:    ReturnType<typeof setTimeout> | null = null;
  private hideTimer:   ReturnType<typeof setTimeout> | null = null;
  private currentSpeaker = "Narrator";

  /** Build and attach the DOM overlay. Idempotent. */
  attach(): void {
    if (this.el) return;

    const div = document.createElement("div");
    div.id = "caption-overlay";
    div.setAttribute("role", "status");
    div.setAttribute("aria-live", "polite");
    div.setAttribute("aria-label", "Subtitles");

    const speaker = document.createElement("p");
    speaker.className = "wit-caption-speaker";

    const dot = document.createElement("span");
    dot.className = "wit-caption-dot";
    dot.setAttribute("aria-hidden", "true");

    const speakerText = document.createElement("span");
    speakerText.textContent = this.currentSpeaker;

    speaker.appendChild(dot);
    speaker.appendChild(speakerText);

    const line = document.createElement("p");
    line.className = "wit-caption-line";

    div.appendChild(speaker);
    div.appendChild(line);
    document.body.appendChild(div);

    this.el        = div;
    this.speakerEl = speakerText;
    this.lineEl    = line;
  }

  /** Toggle caption display. Persists in sessionStorage. */
  setEnabled(on: boolean): void {
    this.enabled = on;
    sessionStorage.setItem("captions_enabled", on ? "1" : "0");
    if (!on) this._hide();
  }

  get isEnabled(): boolean { return this.enabled; }

  /** Set the speaker name shown in the header line. Default "Narrator". */
  setSpeaker(name: string): void {
    this.currentSpeaker = name;
    if (this.speakerEl) this.speakerEl.textContent = name;
  }

  /** Restore the user preference stored in sessionStorage (call once at boot). */
  restorePreference(): void {
    const stored = sessionStorage.getItem("captions_enabled");
    this.enabled = stored !== "0";
  }

  /**
   * Display a text line immediately, optionally auto-hiding after
   * `durationSec` seconds. Pass 0 to keep visible until hide() is called.
   */
  showText(text: string, durationSec = 0): void {
    this._clearTimers();
    if (!this.enabled) return;
    if (!this.el) this.attach();

    if (this.lineEl) this.lineEl.innerHTML = _formatLine(text);
    this.el!.classList.add("visible");

    if (durationSec > 0) {
      this.hideTimer = setTimeout(() => this._hide(), durationSec * 1000);
    }
  }

  /** Hide and clear the overlay immediately. */
  hide(): void {
    this._clearTimers();
    this._hide();
  }

  /**
   * Drive the overlay from a WebVTT cue sequence. Returns a cleanup
   * function that cancels all pending timers.
   */
  playCues(cues: VttCue[]): () => void {
    this._clearTimers();
    if (!this.enabled || cues.length === 0) return () => {};

    const timers: ReturnType<typeof setTimeout>[] = [];
    const t0 = performance.now();

    for (const cue of cues) {
      const showDelay = Math.max(0, cue.startSec * 1000 - (performance.now() - t0));
      const hideDelay = cue.endSec * 1000 - (performance.now() - t0);

      timers.push(
        setTimeout(() => {
          if (cue.speaker) this.setSpeaker(cue.speaker);
          this.showText(cue.text);
        }, showDelay),
        setTimeout(() => this._hide(), hideDelay),
      );
    }

    return () => timers.forEach(clearTimeout);
  }

  // -------------------------------------------------------------------------

  private _hide(): void {
    if (!this.el) return;
    this.el.classList.remove("visible");
    if (this.lineEl) this.lineEl.textContent = "";
  }

  private _clearTimers(): void {
    if (this.cueTimer  !== null) { clearTimeout(this.cueTimer);  this.cueTimer  = null; }
    if (this.hideTimer !== null) { clearTimeout(this.hideTimer); this.hideTimer = null; }
  }
}

/** Wrap italic text (surrounded by *…*) in <em> tags for the serif styling. */
function _formatLine(text: string): string {
  return text.replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

/** App-wide singleton. */
export const captionOverlay = new CaptionOverlayImpl();

// ---------------------------------------------------------------------------
// VTT parser — minimal, no NOTE/STYLE blocks.

/**
 * Parse a WebVTT string into an array of timed cues.
 * Timestamps must be HH:MM:SS.mmm or MM:SS.mmm.
 * Returns an empty array on parse failure.
 */
export function parseCues(vttText: string): VttCue[] {
  const cues: VttCue[] = [];
  const lines = vttText.replace(/^﻿/, "").replace(/\r\n?/g, "\n").split("\n");

  let i = 0;
  while (i < lines.length && !lines[i].startsWith("WEBVTT")) i++;
  i++;

  while (i < lines.length) {
    while (i < lines.length && lines[i].trim() === "") i++;
    if (i >= lines.length) break;

    let timingLine = lines[i];
    if (!timingLine.includes("-->")) {
      i++;
      if (i >= lines.length) break;
      timingLine = lines[i];
    }

    const arrowIdx = timingLine.indexOf("-->");
    if (arrowIdx === -1) { i++; continue; }

    const startSec = _parseTimestamp(timingLine.slice(0, arrowIdx).trim());
    const endPart  = timingLine.slice(arrowIdx + 3).trim().split(/\s+/)[0];
    const endSec   = _parseTimestamp(endPart);

    if (startSec === null || endSec === null) { i++; continue; }

    i++;
    const textLines: string[] = [];
    while (i < lines.length && lines[i].trim() !== "") {
      textLines.push(lines[i]);
      i++;
    }

    if (textLines.length > 0) {
      cues.push({ startSec, endSec, text: textLines.join("\n") });
    }
  }

  return cues;
}

/**
 * Fetch and parse a .vtt file from the given URL.
 * Returns an empty cue list on network error or bad content.
 */
export async function fetchCues(url: string): Promise<VttCue[]> {
  try {
    const res = await fetch(url);
    if (!res.ok) return [];
    return parseCues(await res.text());
  } catch {
    return [];
  }
}

function _parseTimestamp(ts: string): number | null {
  const m = ts.match(/^(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})$/);
  if (!m) return null;
  const h   = m[1] ? parseInt(m[1], 10) : 0;
  const min = parseInt(m[2], 10);
  const sec = parseInt(m[3], 10);
  const ms  = parseInt(m[4], 10);
  return h * 3600 + min * 60 + sec + ms / 1000;
}
