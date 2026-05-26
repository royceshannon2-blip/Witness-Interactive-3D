# Opening Sequence — Design Document

- **Status:** Draft (2026-04-18)
- **Owner:** @royceshannon2
- **Parent:** [`MASTER.md`](MASTER.md)
- **Target code home:** `witness-interactive-vite/src/bootstrap/`, `src/ui/IntroSequence.ts`
- **Related:** [`NARRATIVE.md`](NARRATIVE.md) — Act 1 arrival. [`WORLD.md`](WORLD.md) — geography. [`AUDIO_ARCHITECTURE.md`](AUDIO_ARCHITECTURE.md) — opening audio.

The seconds between application load and first in-world control. Not a loading screen. Not a cinematic. A **descent** — the grandchild returning to the place, framed as remembering, not as mission insertion.

---

## 1. Aesthetic register

**Documentary / memorial.** Reference: Shoah (Lanzmann), The Act of Killing (Oppenheimer), Night and Fog (Resnais), Notes on Blindness (Middleton/Spinney).

**What the register is:**
- Sparse. One text element, one sound, one image at a time.
- Quiet. Master mix at -18 dB per [`AUDIO_ARCHITECTURE.md §7`](AUDIO_ARCHITECTURE.md#7-master-mix-strategy); no opening sting, no musical cue.
- Grounded. Place names, dates, and testimony fragments are drawn from verifiable sources — no invented history.
- Weighted. The first frame does not prompt action. It lets the player arrive.

**What the register is not:**
- No "Modern Warfare"-style tactical overlay. No crosshair, no minimap, no objective list.
- No mission-briefing voice-over ("Intel suggests...", "Your target is...").
- No parachute-insertion aesthetic. The player does not "drop" into Bisesero; they *return*.
- No countdown, no urgency, no stakes language.

This framing is load-bearing. The game is about memory and witness; the opening must tell the player that, before it tells them anything else.

---

## 2. Sequence outline (second-by-second)

Total duration: **~45 seconds** from page load to first control (tunable ±15 s based on asset load time).

```
t = 0.0 s    Browser reaches the Vite-served HTML page.
             Black screen. No logo. No loading bar.
             Audio: silence.

t = 0.5 s    Text fades in, centered, small, white on black:
             "BISESERO HILLS"
             "WESTERN PROVINCE, RWANDA"
             1.5 s fade-in, hold.

t = 3.0 s    Second text line fades in below, thin serif, smaller:
             "APRIL 2026"

t = 4.5 s    Assets begin streaming in the background (see §3).
             Text holds. No progress indicator.
             Audio: a single distant sound — wind through high grass,
             30 s loop at -22 dB.

t = 8.0 s    First archive entry appears below the date, one at a time,
             fading through (see §4). Five entries, each held for 4 s
             before the next fades in.

t = 28.0 s   Last archive entry fades out.
             First image appears: a satellite view, Bisesero Hills from
             high altitude, grayscale, static. Text overlay bottom-left:
             "2°21′S 29°02′E".
             No zoom yet.

t = 31.0 s   Slow zoom begins. Altitude decreases over 10 s.
             Cartographic style: the image is not "cinematic orbit";
             it is an archive photograph descending into detail.
             Audio: wind layer slowly rises, -22 dB → -18 dB.

t = 41.0 s   Zoom reaches ground level. The last frame of the descent
             composites into the first rendered frame of the scene —
             the player stands at the gate of the family compound.
             The satellite image fades out; the 3D scene fades in.

t = 43.0 s   Ambient audio layer takes over from the descent audio
             (wind + distant birds, per AUDIO_ARCHITECTURE §2.1).
             First diegetic prompt: a single text line, bottom-center,
             thin, barely readable:
             "Use W A S D to walk."
             Fades after 4 s.

t = 45.0 s   Full control. No objective marker. No HUD beyond the
             investigator's interface (§5).
             The compound gate is ahead. The player moves when ready.
```

This timing assumes assets have streamed in parallel with the text / archive / satellite sequence. If asset load is faster, the sequence still runs at the full 45 s; if asset load is slower, the sequence holds on the last archive entry until assets are ready (see §3).

---

## 3. Load-state behavior

Assets stream in the background throughout the 45 s. The player sees no progress bar, no spinner, no percentage — the text/image sequence serves as the visible interface.

**Priority order for asset loading:**
1. Player controller and first-scene physics (Havok init) — required before control hand-off at t = 45 s.
2. Family Compound's Present-era meshes (the environment the player will be in at t = 45 s).
3. Family Compound's materials and textures.
4. Ambient audio for t = 43 s onward.
5. Shared terrain, distant hills.
6. Everything else (Past-era meshes, second location, etc.) — loads after control is given, streamed in.

**If assets are not ready at t = 41 s:**
The satellite zoom holds at its lowest altitude frame. The text reads a final, held archive entry. When assets are ready, the dissolve into the 3D scene begins. There is no visible retry, no error message — the player sees a quiet hold.

**If assets fail to load (fatal error):**
A single text line replaces the current content: *"The archive is unreachable. Please reload."* No technical error code, no stack trace, no "report this bug" button. Failure is framed in the register of the game.

---

## 4. Archive entries

Five text fragments shown during the load phase. Each is a **real** piece of information drawn from `WORLD.md` and `NARRATIVE.md` — no invented history.

Format: date or location + short line. 1–2 lines each. Thin serif font, small, white on black.

### Archive entry set (for the opening sequence)

1. **"Bisesero Hills, Western Province, Rwanda. 700 meters above Lake Kivu."**
2. **"April 1994. The 100 days begin."**
3. **"The people of Bisesero organized self-defense on the heights — stones, spears, terrain. They held the hills for weeks."**
4. **"Of roughly 50,000 people who sheltered in Bisesero, fewer than 2,000 survived."**
5. **"Your grandfather was one of them. He kept a ledger."**

These are not a "mission briefing." They are context, delivered in the voice of the memorial. The fifth entry is the only one that names the player's connection to the material; the first four are the historical ground on which the story rests.

**Sourcing rule:** any further archive entries added to this list must cite a verifiable source (African Rights *Death, Despair, Defiance*; the Rwanda 1994 genocide literature; survivor testimony). No entries may be fabricated to "set the mood" or to add emotional beats not present in the historical record.

---

## 5. Investigator's interface (not HUD)

At t = 45 s, the player has control. The interface they are given is deliberately sparse — one visible element at any time, no persistent overlays.

**Always visible:** nothing.

**On demand:**
- A small date-and-location marker appears bottom-left when the player pauses for > 8 s (indicates they might be disoriented). "Family Compound · April 14, 2026." Fades on movement.
- A crosshair dot (1 px) appears only when a raycast hits an interactable. Otherwise invisible.
- The ledger opens as a full-screen overlay on key press (`J`), not a HUD widget.
- The compass is diegetic: there is no screen compass. The player orients by looking at the sun (west afternoon in the Present means they're facing into it) and the hills.

**Never present:**
- Objective markers, waypoints, arrows, quest log, radar.
- Health, stamina, or any vital statistic (the player cannot die).
- Enemy indicators (there are no enemies).
- Tactical overlays, minimaps, grid coordinates visible to the player.

**Contrast with military-game HUDs:** every element absent here is absent by design. The interface should not remind the player they are in a video game.

---

## 6. First-frame composition

The frame the player sees at t = 41 s (when control is given at t = 45 s):

- **Position:** Just inside the gate of the Family Compound. Five meters from the main house.
- **Camera direction:** Facing the main house, with the eucalyptus grove to the left and the well (with its hidden cellar entrance) to the right. The ledger's hiding place is within this first field of view.
- **Time of day:** 2026 Present — overcast morning, roughly 9:00 AM local. Soft light, no shadows sharp.
- **Weather:** Wet-season, post-rain. Ground is damp, vegetation is dark green.
- **Audio:** Wind through eucalyptus (constant). A single bird, distant. No human sounds.
- **Visible story:** An abandoned compound. Overgrown. The ledger is not yet discovered; the player must walk to find it.

The frame must read as *quiet*. A photographer could have stood here. The player is that photographer, or rather, the person who came to see what the photograph described.

---

## 7. Audio during the opening

Per [`AUDIO_ARCHITECTURE.md §4`](AUDIO_ARCHITECTURE.md#4-transition-audio), but the opening has its own envelope:

| Time | Audio |
|---|---|
| 0.0 – 4.5 s | Silence. |
| 4.5 – 28.0 s | Single wind layer, -22 dB. |
| 28.0 – 41.0 s | Wind layer continues, slight rise (-22 → -18 dB). |
| 41.0 – 43.0 s | Crossfade from descent audio (single layer) to full ambient (wind + distant birds, plus faint water from Lake Kivu at -30 dB). |
| 43.0 – 45.0 s | Full ambient establishes at compound mix (per AUDIO_ARCHITECTURE §2.1 Present-era). |

**No opening sting. No title theme. No music.** The game has no non-diegetic score (per [`AUDIO_ARCHITECTURE.md §3`](AUDIO_ARCHITECTURE.md#3-narrator-voice-specification) — "No music in echoes" applies also to the frame of the work). The quietness is the point.

---

## 8. Variations

**On replay (player has completed the game at least once):**
- Archive entry #5 is replaced with: *"You have been here before. The ledger is on the shrine, where you left it."*
- The descent is slightly faster (30 s instead of 45 s).
- Player position at t = 41 s is unchanged; no assumption of remembered geography.

**After save-load (mid-game resume):**
- No opening sequence. The player resumes at their saved camera position, in the last-active era, with a 0.5 s fade-in from black. Just:
  - Title text: "FAMILY COMPOUND · APRIL 15, 2026" (or the appropriate save-file date/location).
  - Then the scene.

**During development (dev build flag):**
- Opening sequence is skipped entirely. `?skipIntro=1` URL param jumps to t = 41 s.

---

## 9. Testing checklist

- [ ] Asset preload completes before t = 41 s on a mid-range desktop (RTX 3060, 16 GB RAM) with fast broadband.
- [ ] Slow network (3G simulated) — hold behavior at t = 41 s works; no frozen UI.
- [ ] Audio fade-in is smooth; no click or pop at wind-layer start.
- [ ] Archive entries do not overlap; transitions at 4 s each.
- [ ] Satellite zoom is smooth at 60 fps; no stutter as 3D scene loads in parallel.
- [ ] Dissolve from satellite to 3D is seamless (same color grade at handoff).
- [ ] First-frame composition matches §6 exactly.
- [ ] No HUD elements visible at t = 45 s beyond the prompt "Use W A S D to walk."
- [ ] Prompt fades cleanly after 4 s; movement input removes it instantly.
- [ ] Replay variation applies on second playthrough.
- [ ] Save-resume variation applies on mid-game load.
- [ ] Dev-build skip flag works.
- [ ] Accessibility: archive entries are screen-reader-readable; satellite descent respects `prefers-reduced-motion` (static image + archive entries only).

---

## 10. Open questions

- Q1: **Should the player's name appear?** The grandchild is unnamed in the PRD. If they type a name (like old CRPGs), that name could be used in archive entry #5 ("You have returned to your grandfather's compound, [name]"). Leaning no — the silence on identity is part of the register. Decide before Phase 2 art pass.
- Q2: **Kinyarwanda vs. English title text.** Leaning English first for the target audience, but a subtle Kinyarwanda-language version for accessibility (displayed simultaneously, smaller, below). Decide with audio casting.
- Q3: **Length of the descent on very slow load.** If assets take 90 s to load, does the archive-entry sequence loop, or hold on the last entry? Leaning hold. Loop risks reading as a bug.
- Q4: **Haptic feedback.** If this ships to controllers with rumble, does the t = 41 s scene-handoff have any haptic? Leaning no — haptic feedback is reserved for key narrative beats in Chronos transitions, per AUDIO_ARCHITECTURE.md accessibility section.
