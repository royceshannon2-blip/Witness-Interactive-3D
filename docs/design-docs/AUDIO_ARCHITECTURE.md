# Audio Architecture: The Shepherd's Ledger

**Status:** Production  
**Last Updated:** 2026-04-18  
**Owner:** @royceshannon2  

Audio is one of two narratives—visual + sonic. This document maps the GDC audio bundle to Witness Interactive 3D's dual-era (2026 Present / 1994 Past) experience, specifying which sounds support which locations, states, and transitions.

---

## 1. Audio Design Philosophy

The PRD mandates: "emotionally restrained, not spectacle." This applies to audio equally.

**2026 Present Era:**
- Sparse, meditative, emphasizing absence
- Wind, water, empty spaces
- No music (only in very specific moments like the final credits)
- Grandfather's voice-over reading ledger entries (minimal, respectful)

**1994 Past Era (echoes):**
- Layered, immediate, visceral
- Environmental (1994 was alive; 2026 is a ruin)
- Militia movements, whispered conversation, daily routine sounds
- No dialogue (only voice-over; no acted dialogue that would aestheticize the experience)

**Mixing principle:** Audio should ground the player in the specific location and era, not overwhelm it. The story is in the evidence, not the soundtrack.

---

## 2. Audio Zones & Ambient Layers

The world has **five canonical locations**, each with distinct acoustic signatures.

### 2.1 Family Compound (Mid-level, starting area)

**2026 Present Audio Signature:**
- **Base ambience (loop, 4–6 min):** `Epic Stock Media - Public Spaces - Storms Lakes Parks and Rural Nature Exteriors / AMBPark_Berlin City Humboldthain Park Strong Wind On Trees Foliage Traffic Wash 03`
- **Secondary layer:** `344 Audio - East Coast America Vol. 1 / AMBSubn_Ambience, Forest Crickets, Birds, Connecticut 02` (sparse birdsong, crickets; adds emptiness)
- **Occasional wind gusts:** `The Noisery - City Rain / WINDTonl_Wind Strong Gusts Hurricane Vents Rattle 06` (peaks every 30–60 sec)
- **Interactive elements:**
  - Footsteps on stone: `Epic Stock Media - HD Game Materials` (foley library, specific footstep SFX)
  - Door creaks (entering cellar): generic wooden creak (Antique or architectural foley)
- **Emotional tone:** Quiet dread. Beauty overlaid with emptiness. The compound is overgrown but alive—birds, wind, water in the well.

**1994 Past Audio Signature (during echoes):**
- **Base ambience:** `Epic Stock Media - Public Spaces - Urban Life Exteriors / AMBTown_City Courtyard Calm Street Distant Traffic Children Playing 03` (substituting "street" for compound; adds human activity without centering it)
- **Secondary layer:** `Epic Stock Media - Public Spaces - Crowds Walla and Everyday Ambiences / CRWDChld_Walla Children Kids Daytime School Playing Laughing Playground 01` (children playing nearby; indicates neighbors)
- **Specific diegetic sounds during echoes:**
  - Water collection from well (splashing, pouring)
  - Footsteps on packed earth (different from 2026 stone)
  - Militia patrol sounds (distant boots, leather, rifle slings) — use `344 Audio - Historical Weapons Vol. 2` for **authentic 1994 military hardware**
  - Whispered conversation (neighbor family below cellar) — use `Sonik Sound Library - Spanish Crowds / Walla` as reference; re-record with appropriate voices
- **Emotional tone:** Alive, immediate, dangerous. Every sound is suspicious. Water collection is routine but fraught.

---

### 2.2 Lake Shore (Low ground, escape route)

**2026 Present Audio Signature:**
- **Base ambience (loop, 5–8 min):** `Just Sound Effects - Rocky Coast of Norway / WATRWave_Soft Waves Cliffs_JSE_RCoN_Stereo` + `WATRWave_Medium Waves at Pebble Beach`
- **Secondary layer:** `Epic Stock Media - Public Spaces - Storms Lakes Parks and Rural Nature Exteriors / WATRLap_Summer Tennessee Lake Dock Water Ripples Wake Wave Gentle 05 Distant_ESM_CPS` (lake lapping, adds vastness)
- **Wind:** `The Noisery - City Rain / WINDInt_Wind Strong Metal Rattle` (metal dock creaks; emphasizes abandonment)
- **Interactive elements:**
  - Footsteps on rocky beach (gravel crunch)
  - Dock wood creaking
- **Emotional tone:** Beautiful and haunted. Water as barrier and memory. Echoes of departures that never return.

**1994 Past Audio Signature (during echoes):**
- **Base ambience:** Same water, but layered with:
  - Human activity: `Epic Stock Media - Public Spaces - Basic Transportation Sounds` (loading boats, pushing off)
  - Whispered urgency: groups of people boarding, quiet instructions
  - Breathing, stress sounds: `Sonik Sound Library - Urban Life / AMBUrbn_Ambience, City, Madrid, Spain, Soft Traffic and Human Activity`
- **Specific diegetic sounds during boat echo:**
  - Boat paddle striking water (use `344 Audio - Historical Weapons Vol. 2 / WEAPBlnt_Spear And Stick Impact` as reference; adapt for wooden paddle)
  - Boots on wet wood
  - Fabric rustling (people climbing in)
  - Low voices: "Keep down." "Don't let them see us."
  - Water lapping beneath the boat
- **Emotional tone:** Tension underneath routine. People waiting. Desperate hope. A boat that will depart and never return for others.

---

### 2.3 Cellar (Underground, sanctuary and tomb)

**2026 Present Audio Signature:**
- **Base ambience:** Silence + **dampness**
  - Very low-level dripping water (1 drop every 10–15 seconds)
  - Distant echo of well water above
  - Minimal air movement (slight air circulation in old stone)
- **Interactive elements:**
  - Footsteps on packed earth (muffled, intimate)
  - Stone creaks (settling, age)
- **Emotional tone:** Sacred quiet. A place that held life. Now holds only evidence.

**1994 Past Audio Signature (during echoes):**
- **Base ambience:**
  - Sleeping breath (soft breathing, 5–8 people in darkness)
  - Heartbeat-like pulse: settling stone, barely audible
  - Dripping water (same, but now the only clock)
- **Diegetic sounds:**
  - Careful footsteps (Grandfather moving to check on hidden people)
  - Whispered conversation (one person asks about food, another worries about militia)
  - Soft coughing (a child, quickly stifled)
  - Fabric shifts (sleeping mats, repositioning)
  - Careful water pouring (rationing the day's supply)
- **Critical silence:** Periods where the only sound is breathing and dripping water. The sound of waiting.
- **Emotional tone:** Claustrophobic safety. The weight of bodies depending on silence. The terror of discovery.

---

### 2.4 Ravine (High-mid level, observer vantage)

**2026 Present Audio Signature:**
- **Base ambience:** Wind + isolation
  - Strong wind through narrow ravine: `Epic Stock Media - Public Spaces - Storms Lakes Parks and Rural Nature Exteriors / AMBPark_Berlin...` (wind in exposed heights)
  - Occasional rock shift (settling stone)
  - No birdsong (ravine is isolated, shadowed)
- **Interactive elements:**
  - Footsteps on unstable stone (loose rock, careful movement)
  - Stone echo (thrown rock, sound bounces)
- **Emotional tone:** Exposed, windswept, lonely. The place where Grandfather watched.

**1994 Past Audio Signature (during echoes):**
- **Base ambience:**
  - Wind (same as 2026, but now a cover for other sounds)
  - Distant sounds carrying up from the valley below
- **Diegetic sounds during observation echo:**
  - Militia column passing in valley below (distant boots, organization, threat)
    - Use `SoundBits - Pass-By - Trains, Trucks & Cars 2 / TRNTram_Generic Tram Pass Py 13` as reference for organized movement
    - Adapt to human footsteps with occasional shouted orders
  - Neighbors fleeing downslope (panicked footsteps, whispered warnings)
  - Grandfather's pencil scratching on paper (documentation, guilt, numbness)
  - His whispered voice-over reading his notes: "Militia column, 40 men. Heading north toward the lake. I could warn them..."
- **Critical silence:** Moments where Grandfather stops writing and just watches, says nothing, does nothing.
- **Emotional tone:** Witness without agency. The weight of seeing and silence. Moral paralysis.

---

### 2.5 Heights (High ground, final perspective)

**2026 Present Audio Signature:**
- **Base ambience:** Vast wind + distance
  - Open, sustained wind: `The Noisery - City Rain / WINDTonl_Wind Strong Gusts...` (continuous, not gusts; hints at exposure)
  - Sounds carry from far below (lake water, distant settlement)
- **Interactive elements:**
  - Footsteps on exposed stone (clear, echoing)
  - Voices echo (player's own breathing sounds larger)
- **Emotional tone:** Perspective. The landscape opens up. You can see everything from here.

**1994 Past Audio Signature (during optional echo):**
- **Base ambience:** Same wind, but now carrying sounds of conflict
  - Distant sounds: militia columns, fleeing people, organized resistance
  - Wind carries smoke smell (implied; audio suggestion only)
- **Diegetic sounds:**
  - Stone fortifications being reinforced (tools, organization by people fighting back)
  - Grandfather's isolation: his footsteps are alone; no one else is here with him
  - Voice-over: "Others fought from these heights. I did not fight."
- **Emotional tone:** Last stand. Resistance. Grandfather's absence from resistance. The cost of not choosing a side.

---

## 3. Narrator Voice & Ledger Readings

The **Grandfather's voice** is the constant thread. He reads ledger entries, internal monologues, reflections. This is not dialogue—it's documentation.

### Narrator Recording Spec

**Voice characteristics:**
- Elderly male (not ancient, but aged)
- Accent: Kinyarwandan-accented English (historical accuracy; the language beneath the English)
- Tone: Measured, reflective, bearing weight
- Delivery: Slow, intentional, pauses for breath and thought
- Volume: Intimate (as if speaking directly to the player)
- Emotion: Restrained grief. No melodrama. Historical rather than theatrical.

**Recording locations (examples from audios):**
- Quiet room (minimal reverb; intimate)
- Optional: outdoor recording with very subtle wind (hints at Bisesero landscape)

**Ledger entry readings:**
- One voice-over per discovered ledger page
- Duration: 30–90 seconds per entry
- Timing: triggered when player examines the ledger, or as ambient narration when near significant locations

**Example ledger readings (to be recorded):**
1. "June 1994. Bisesero. One night changed everything." (opening)
2. "I made a space. 8 people. 47 days." (cellar evidence)
3. "The boat is our only hope. It leaves at dawn." (boat evidence)
4. "From here, I can see the entire valley. Nothing escapes my eyes." (observer evidence)
5. "I stayed so they could leave. If they find me here alone, they'll know someone was hidden." (Path A climax)
6. "I carry their names with me." (Path B climax)
7. "I survived by being invisible. But invisibility is its own curse." (Path C climax)

**Recording source:** Professional voice actor or narrator to be hired. Budget should prioritize authenticity (Rwandan or diaspora voice) over celebrity.

---

## 4. Transition Audio: Temporal Uplink

When a player touches an anchor and enters a 1994 echo, the audio must transition from 2026 to 1994.

### Transition Sequence (2–3 seconds)

**Phase 1: Fade-out of 2026 ambience (0.5 sec)**
- Current location ambience (compound wind, lake water, ravine wind) gradually lowers volume
- High-frequency content gradually disappears (bass remains briefly)
- Emotional note: the present era is fading

**Phase 2: Momentary silence (0.2 sec)**
- Absolute silence (or near-silence)
- Uncomfortable pause; the player's sense of time is disrupted
- This silence is intentional—it marks the shift

**Phase 3: Fade-in of 1994 ambience (1.3 sec)**
- New location ambience (1994 state of that location) gradually appears
- Low frequencies build first (grounding)
- Specific diegetic sounds (footsteps, voices, activity) layer in
- The echo is now active

**Phase 4: Diegetic echo begins (full volume)**
- 1994 moment begins
- Grandfather's voice-over (internal monologue) may begin immediately or after 3–5 seconds

### Reverse Transition (Echo end → 2026)

When the echo ends (automatically after 30 sec–2 min, or player presses ESC):

**Phase 1: Grandfather's voice-over ends (0.5 sec)**
- Last line of his narration fades to silence

**Phase 2: Fade-out of 1994 ambience (0.5 sec)**
- Diegetic 1994 sounds fade
- Location ambience dims

**Phase 3: Momentary silence (0.2 sec)**
- Same disorienting pause

**Phase 4: Fade-in of 2026 ambience (1 sec)**
- Present-era location ambience returns
- Player is back in the overgrown compound, the shore, the ravine

**UI reinforcement:** During transitions, the ledger page briefly glows or updates to signal the era shift.

---

## 5. Mapping Audio Library to Locations

Here's the **concrete map** of GDC bundle files to locations and moments:

### Present Era (2026) Base Ambiences

| Location | Primary Ambience | Secondary Layer | Use Case |
|---|---|---|---|
| **Compound** | `Epic Stock Media - Public Spaces - Storms Lakes Parks and Rural Nature Exteriors / AMBPark_Berlin City Humboldthain Park Strong Wind On Trees Foliage Traffic Wash 03` | `344 Audio - East Coast America Vol. 1 / AMBSubn_Ambience, Forest Crickets, Birds, Connecticut 02` | Background loop while exploring compound |
| **Lake Shore** | `Just Sound Effects - Rocky Coast of Norway / WATRWave_Soft Waves Cliffs_JSE_RCoN_Stereo` | `Epic Stock Media.../ WATRLap_Summer Tennessee Lake Dock Water Ripples Wake Wave Gentle 05 Distant` | Background loop at shore |
| **Cellar** | *Custom: silence + dripping* | *N/A* | Underground space (mostly custom recording needed) |
| **Ravine** | `Epic Stock Media - Public Spaces - Storms Lakes Parks and Rural Nature Exteriors / AMBPark_Berlin...` | `InMotionAudio - Chimney Wind` (wind through narrow space) | Background loop at heights |
| **Heights** | `The Noisery - City Rain / WINDTonl_Wind Strong Gusts Hurricane Vents Rattle 06` | *Optional*: distant water/settlement | Vast, exposed ambience |

### Past Era (1994) Layered Elements

| Echo Moment | Primary Ambience | Diegetic Layer 1 | Diegetic Layer 2 | Narrator Voice |
|---|---|---|---|---|
| **Cellar echo** | *Silence + dripping* | Soft breathing, body shifts | Whispered conversation | "I made a space. 8 people. 47 days." |
| **Boat departure** | `Epic Stock Media - Public Spaces - Basic Transportation Sounds` | Boat paddle, footsteps on wet wood | Whispered instructions, fabric rustling | "The boat is our only hope." |
| **Water collection** | `Epic Stock Media - Public Spaces - Urban Life Exteriors / AMBTown_...` | Water pouring, splashing, careful movement | Distant threat (militia patrol) | *Optional: internal monologue about risk* |
| **Militia patrol** | `Epic Stock Media - Public Spaces - Urban Life Exteriors / AMBPark_...` (wind in hills) | Organized footsteps, rifle slings, voice commands | Breathing (fear), pencil scratching | "Militia column, 40 men..." (voice-over) |
| **Ravine observation** | Wind + distance | Distant column sounds, footsteps below | Grandfather's pencil, his breathing | "From here, I can see everything..." |
| **Post-genocide return** | `Epic Stock Media - Public Spaces - Storms Lakes Parks and Rural Nature Exteriors / WATRLap_...` (lake at dusk) | Empty dock, no boats, wind | Silence; only environmental sound | *Optional: survivor's voice, distant memory* |

### Foley & Interactive Sounds

| Action | Source / Recommendation | Notes |
|---|---|---|
| Footsteps on stone (2026) | `Epic Stock Media - HD Game Materials` (generic foley library) | Use tight, clear footsteps; emphasize solitude |
| Footsteps on earth (1994) | *Custom or generic foley* | Softer, muffled; indicate caution |
| Footsteps on wet wood (boat) | *Custom or generic foley* | Slippery, careful; emphasize danger |
| Door/cellar opening (creaks) | `Antique Luggage` or `InMotionAudio - Instrument Case` (wood foley) | Slow, aged creak; emphasize entry into the past |
| Rifle/militia equipment | `344 Audio - Historical Weapons Vol. 2` | Leather sling, metal clinks, boots; grounded in authenticity |
| Water splashing/pouring | *Custom recording (best source: actual water)* | Intimate, immediate; varies by quantity and speed |
| Stone shifting/settling | `Epic Stock Media - HD Game Materials` or *custom* | Rare; emphasizes age and geology |
| Pencil scratching (Grandfather documenting) | `344 Audio - Antique Typewriter` or *custom pencil sound* | Intimate, purposeful; records his paralysis |

---

## 6. Dynamic Audio Mixing Rules

Audio is context-driven. The mixer is the StateManager.

### Era Switching (When Echoes Trigger)

```
if (in_echo_fragment) {
  fade_out(present_era_ambience, 0.5s)
  fade_in(past_era_ambience, 1.3s)
  play(narrator_voice_over)
  active_master_volume = 0.75  // slightly reduced to emphasize intimacy
} else {
  fade_out(past_era_ambience, 0.5s)
  fade_in(present_era_ambience, 1.0s)
  active_master_volume = 1.0
}
```

### Location-Based Ambience Switching

```
if (player_location_change) {
  cross_fade(old_location_ambience, new_location_ambience, 2.0s)
  // adjust reverb based on indoor/outdoor
  // adjust wind/water based on geography
}
```

### Voice Layering (Narrator Priority)

```
if (narrator_voice_over.playing) {
  reduce_ambience_volume(0.5)  // push back background audio
  reduce_diegetic_effects_volume(0.7)  // but keep footsteps, breathing audible
} else {
  full_ambience_volume()
  full_diegetic_effects_volume()
}
```

### Stress Audio Cues (During 1994 echoes)

Subtle audio cues hint at emotional state without being manipulative:

```
if (militia_nearby && grandfather_hidden) {
  // Grandfather's breathing becomes slightly faster
  // A distant dog barks (militia dogs?)
  // Neighbor's breathing becomes audible
  // Shared tension without dialogue
}
```

---

## 7. Master Mix Strategy

### Target Mix Levels (in decibels, relative to 0 dB = full scale)

| Element | 2026 Present | 1994 Echo | Notes |
|---|---|---|---|
| Master output | -6 dB | -6 dB | Headroom for peaks |
| Ambience (base) | -18 dB | -20 dB | Background; should be felt more than heard |
| Narrator voice | -12 dB | -12 dB | Clear, intimate; present always |
| Diegetic effects | -16 dB | -14 dB | Footsteps, water, equipment; layered |
| Wind/weather | -14 dB | -14 dB | Atmospheric; constant unless inside |
| Surround/reverb | -24 dB | -22 dB | Spatial context; subtle |

**Mixing principle:** Everything is **-3 dB lower than commercial music/games.** This is intentional. Witness is meditative, not cinematic. Silence is as important as sound.

---

## 8. Audio Implementation in Babylon.js

### AudioManager Module

**Location:** `witness-interactive-vite/src/audio/AudioManager.ts`

**Responsibilities:**
- Load audio assets from the GDC bundle (organized by location)
- Manage ambience layer crossfades (2026 → 1994 transitions)
- Trigger narrator voice-overs at correct times
- Mix diegetic effects based on player action (footsteps, interaction)
- Subscribe to StateManager for era/location changes

**API (example):**
```typescript
class AudioManager {
  // Initialize with scene and asset loader
  constructor(scene: BABYLON.Scene, assetLoader: AssetLoader)

  // Change location ambience
  setLocation(location: "compound" | "lake" | "cellar" | "ravine" | "heights")

  // Trigger era transition (2026 → 1994 or reverse)
  transitionToEra(era: "present" | "past", durationMs: number = 2000)

  // Play narrator voice-over
  playNarratorEntry(textKey: string, durationMs: number)

  // Play foley/diegetic sound
  playEffect(effectKey: string, position?: BABYLON.Vector3)

  // Subscribe to scene updates
  onInteraction(actionType: string)
}
```

**Implementation notes:**
- Use **Babylon.js Sound class** for all audio
- Use **SoundTrack** for layered ambiences (one per location, one per era)
- Keep narrator voice on a **separate, non-pausable track** (continues during menus/reflection)
- Use **spatial audio** for diegetic effects (footsteps, water, militia sounds position in 3D space)

---

## 9. Audio Quality & Compression

**Format & Codec:**
- **Master format:** WAV (uncompressed) in production docs; store originals for future remastering
- **Delivery format:** OGG Vorbis (best browser support + quality/file-size ratio)
- **Bitrate:** 192 kbps stereo (transparent quality for most listeners; 1–2 MB per 10 minutes of ambience)

**File organization:**
```
witness-interactive-vite/
├── public/
│   └── audio/
│       ├── 2026-present/
│       │   ├── compound-base.ogg
│       │   ├── compound-secondary.ogg
│       │   ├── lake-base.ogg
│       │   └── ...
│       ├── 1994-past/
│       │   ├── compound-echo.ogg
│       │   ├── lake-echo.ogg
│       │   └── ...
│       ├── narrator/
│       │   ├── ledger-entry-01.ogg
│       │   ├── ledger-entry-02.ogg
│       │   └── ...
│       └── effects/
│           ├── footstep-stone.ogg
│           ├── footstep-earth.ogg
│           ├── water-splash.ogg
│           └── ...
```

---

## 10. Accessibility Considerations

**Hearing-impaired players:**
- Visual cue system (HUD icons) hints at audio events (militia approaching, water sounds, narrator starting)
- Closed captions for narrator voice-overs (displayed in ledger UI)
- Vibration/haptic feedback (on supported devices) for major audio events

**Tinnitus/hypersensitivity:**
- All ambiences include a **low-frequency cutoff** (no sub-bass below 40 Hz in ambiences)
- No sudden loud peaks; dynamic range is compressed (-6 dB max)
- Option to disable ambient layers (toggle: "Ambient sounds" on/off in settings)

---

## 11. Future Audio Expansion

### Phase 2 (post-launch)

- **Live voice recording:** Hire voice actor to record all narrator entries (currently placeholder specs)
- **Spatial audio:** Implement Dolby Atmos or WebAudio 3D panning for militia footsteps, echoes
- **Reactive audio:** Dynamism based on player emotion (breathing, heartbeat tempo tied to stress)
- **Survivor testimony audio:** Post-1994 recorded voice samples (real survivors, if permissions secured) layered into location echoes

### Phase 3 (long-term)

- **Kinyarwanda audio:** Integrate whispered Kinyarwanda (neighbor conversations, militia commands) with English subtitles
- **Music composition:** Sparse, historically informed compositions for key moments (opening, choice point, endings)
- **Immersive audio:** Full 7.1 surround or Ambisonics for cinema-quality experience

---

## 12. Connection to Other Subsystems

| Subsystem | Audio Dependency |
|---|---|
| **TimeManager** | Triggers ambience/narrator transitions when era changes |
| **StateManager** | Audio responds to flags (which evidence found, which path chosen) |
| **InteractableRegistry** | Triggers foley effects when objects are touched (door, water, etc.) |
| **Rendering (lighting/camera)** | Audio intensity correlates with visual density (brighter = more activity sounds) |
| **UI/Ledger** | Narrator entries play when ledger pages update |

---

## 13. Testing & QA Checklist

- [ ] Ambience loops seamlessly (no clicks or pops at crossfade)
- [ ] Narrator voice is clear and audible at all mix levels
- [ ] 2026 → 1994 transition is smooth and disorienting (intended effect)
- [ ] Diegetic effects are spatially accurate (footsteps ahead sound ahead, etc.)
- [ ] Stress audio cues (militia breathing, etc.) enhance tension without manipulation
- [ ] All three locations have distinct sonic identity
- [ ] Captions accurately reflect narrator voice-over timing
- [ ] Audio levels are consistent across all browsers (headphone + speaker listening)

---

## 14. References & Inspiration

**Documentary audio design:**
- *Shoah* (Claude Lanzmann) — sparse, meditative interview format
- *The Act of Killing* (Joshua Oppenheimer) — environmental storytelling, ambient texture
- *Rwandan genocide survivor testimony recordings* (USC Shoah Foundation, Kigali Memorial Centre archives) — authentic vocal register and pace

**Game audio precedents:**
- *Firewatch* — minimalist ambience, narrator-driven narrative, strong location identity
- *What Remains of Edith Finch* — intimate, family-focused voice-over + environmental sound design
- *The Forgotten City* — historical atmosphere without spectacle

---

## 15. Next Steps

1. **Categorize GDC bundle:** Map all 100+ folders to project-relevant sounds (ambience, foley, voices)
2. **Create recording brief:** Specification for hiring narrator voice actor
3. **Develop AudioManager module:** Babylon.js integration spec (see §8)
4. **Record custom foley:** Water, footsteps, militia equipment (may supplement GDC library)
5. **Playtest audio mix:** Test at different volumes, on headphones + speakers, with hearing-impaired captions
6. **Integrate with CHRONOS_SWITCH:** Audio transition timing must align with layer mask crossfade
