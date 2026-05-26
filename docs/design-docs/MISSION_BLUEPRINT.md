# Mission Blueprint: The Shepherd's Ledger

**Status:** Production  
**Last Updated:** 2026-04-18  
**Owner:** @royceshannon2  

This document is the **master flow specification** for Witness Interactive 3D. It details the complete mission architecture from player arrival through ending, showing how 2026 investigator actions trigger 1994 historical echoes, how evidence anchors branch logic, and how three morally valid interpretations emerge from a single night.

---

## 1. Mission Premise

**Year 2026 (Present Era):**  
You return to your grandfather's abandoned compound in the Bisesero Hills for the first time since childhood. The property is overgrown, the family shrine untouched. Your grandmother, before she died, left you a single cryptic clue: *"The ledger will tell you why he never came home."*

**Year 1994 (Past Era, fragmented):  
That same night—June 1994—your grandfather faced an impossible choice in the midst of the Rwandan genocide. Three accounts of that night survive. Only one is fully true. But all three are understandable.

**The Mission:**  
Find the ledger. Gather its scattered pages across the compound and hilltops. Each discovery pulls you into a memory—a flash of 1994. Piece together what happened. Interpret the evidence. Choose which version of events you believe. Live with the weight of that choice.

---

## 2. The Anchor-Echo System

### Historical Anchors (1994 Evidence)

Evidence objects exist in physical space. When the player touches one, the game transitions them into a fragmented, first-person view of that moment.

| Anchor | Location | Type | Echo Content | Path(s) |
|---|---|---|---|---|
| **Hidden cellar door** | Family compound well | Physical space | You descend into 1994. The cellar is packed with sleeping neighbors, food rationed carefully. Grandfather discusses the risk daily. | Hider |
| **Boat paddle** | Lake shore, buried in reeds | Object | 1994 lakeside. Boats depart. Grandfather helps load people. The selection logic becomes visible—children first, then the weakest, then whoever can contribute to the journey. | Escapist |
| **Observer's journal** | Ravine vantage point, hidden in stones | Text artifact | 1994 hilltop. Grandfather watches militia columns move through the valley. He documents everything. He does nothing. | Silent |
| **Militia patrol chalk marks** | Rocks scattered across high ground | Markings | 1994. Grandfather reads the marks left by militia scouts. The threat is concrete, mapped, daily updated. | Hider (risk) |
| **Boat passenger lists** | Lake shore, wrapped in oilcloth | Document | 1994. Names. Some circled (departed safely). Some crossed out. Grandfather's handwriting shows hesitation, guilt, arithmetic of triage. | Escapist (cost) |
| **Letter from hidden neighbor** | Cellar stones, sealed | Personal letter | Post-1994. A message to Grandfather: *"You saved us. I never saw you again. Did you make it?"* | Hider (outcome) |
| **Militia checkpoint records** | Ravine stones, scratched dates | Markings | 1994. Checkpoint locations, guard rotations, which routes are safe. Grandfather's knowledge could have warned people. He didn't. | Silent (complicity) |
| **Water collection schedule** | Family compound wall, carved into stone | Logistical record | 1994. Daily water runs to the well while hidden neighbors sheltered below. The risk was routine, daily, unseen by the outside world. | Hider (routine) |
| **Boat capacity calculations** | Lake shore, faded ink on a board | Notes | 1994. Grandfather's math: "40 fit safely. Maybe 42 if they balance. I can make two runs before the lake changes hands. First group in 4 hours. Who gets on?" | Escapist (mechanics) |
| **Observer's reflection letters** | Ravine, addressed to himself | Unsent correspondence | 1994. Grandfather, writing by starlight: *"If I fight, I die. If I hide them, we all die. If I run, who cares for the rest? Staying invisible keeps my family alive."* | Silent (rationalization) |

### Echoes: What the Player Experiences

Echoes are **diegetic first-person moments**. When the player touches an anchor, the camera cuts to Grandfather's perspective in 1994. They hear his thoughts (voice-over), see his hands (animated), interact minimally. The moment is **visceral but not interactive**—the player observes, not controls.

**Echo characteristics:**
- **Duration:** 30 seconds to 2 minutes per echo
- **Perspective:** First-person only; Grandfather's hands visible
- **Audio:** Ambient (1994 sounds—water, militia footsteps, whispers), plus single voice-over (Grandfather's internal monologue)
- **Visuals:** Same locations, but 1994-state: less overgrown, different lighting, people present, immediate threat visible
- **Exit:** Echo ends automatically, or player presses a key to return to 2026
- **Recoverability:** Echoes can be re-triggered; the ledger updates with parsed text each time

---

## 3. Complete Mission Flow

### Phase 1: Arrival & Orientation (5–10 min)

**2026 Investigator Perspective**

- **State:** `act_1_arrival` → `act_1_explore`
- **Narrative flags set:** `act_1_started`, then `act_1_complete`
- **Mechanics:**
  - First-person camera begins at the entrance to the family compound
  - Tutorial: movement, interaction prompts
  - Audio: Wind through eucalyptus, water in the distance, silence of absence
  - UI: Minimal. Only a date (2026) and the ledger icon when near interactive objects
- **Story beat:**
  - Narration (voice-over by an elder or by the player themselves): *"Grandpa never spoke of this place. But I inherited his silence. Now I'm here to break it."*
  - Exploration triggers: overgrown garden, collapsed fence, family shrine visible
  - First interactive object: the ledger's first page, visible on a stone altar
- **Outcome:** Player reads the ledger's opening: *"June 1994. Bisesero. One night changed everything."*
- **Signal to continue:** Ledger discovered flag unlocks Act 2 exploration

---

### Phase 2: Evidence Gathering (15–25 min)

**Freeform Exploration**

- **State:** `act_2_begin_exploration` → parallel branches
- **Narrative flags:** `found_cellar_evidence`, `found_boat_evidence`, `found_observer_evidence`, `all_evidence_found`
- **Mechanics:**
  - Player is free to visit: family compound, lake shore, cellar, ravine, heights, in any order
  - Each location has 2–4 anchors (evidence objects)
  - Touching an anchor triggers an echo (0.5–2 min 1994 moment)
  - Echo ends; player returns to 2026 with a parsed entry added to the ledger
  - Same anchor can be triggered again (repeating the echo, or reading the ledger entry again)
- **Key locations and anchors:**

#### **Family Compound (Mid-level, starting area)**
- Cellar entrance (beneath the well) → Hidden cellar echo
- Stone wall with water-carving marks → Water collection routine echo
- Family shrine → Ledger pages, photographs, post-genocide letters
- **Narrative consequence:** Finding cellar evidence sets `found_cellar_evidence` → suggests Path A (Hider)

#### **Lake Shore (Low ground, 10-minute walk)**
- Buried boat paddle → Boat departure echo
- Oilcloth bundle with passenger lists → Selection logic echo
- Rotting dock → Post-genocide return echoes (a survivor's account of that night)
- **Narrative consequence:** Finding boat evidence sets `found_boat_evidence` → suggests Path B (Escapist)

#### **Cellar (Underground, accessible via well)**
- Sleeping mats, preserved food → Echo: 1994 morning, neighbors sleeping, footsteps above
- Journal entries on walls → Echo: rationing decisions, supply runs, risk calculus
- Photographs of hidden people → Echo: Grandfather's recollection of their names and fears
- Hidden letter from a neighbor → Post-1994 letter saying "You saved us. Did you survive?"
- **Narrative consequence:** Reinforces cellar path; unlocks deeper reflection on risk and heroism

#### **Ravine (High-mid level, steep access)**
- Observer's vantage point → 1994 hilltop echo: Grandfather watching, documenting, silent
- Chalk marks on rocks → Militia patrol routes echo
- Unsent letters → 1994 night writing: Grandfather's internal justification for staying neutral
- Stone fortifications → Evidence of resistance by others; Grandfather stayed apart
- **Narrative consequence:** Finding observer evidence sets `found_observer_evidence` → suggests Path C (Silent)

#### **Heights (High ground, 20-minute climb)**
- Panoramic view of all three paths below
- Signal stones (militia communication markers) → Echo: Grandfather realized the lake route was now watched
- Final refuge shelter → Post-genocide pilgrimage: a survivor came back, stood here, grieved
- **Narrative consequence:** Optional deepening of whichever path the player is leaning toward

**Phase 2 Mechanics Summary:**
- Player moves freely, touching anchors at their own pace
- No objectives, no quest log—only the ledger, which updates as they discover
- Audio shifts based on location: lake ambience at shore, wind at heights, dampness in cellar
- Lighting shifts with era: 2026 overgrown/gray; 1994 echoes more vivid, color-saturated
- Pacing is player-driven; estimated 15–25 minutes depending on exploration thoroughness

**End condition:** When all three evidence types have been found (`all_evidence_found`), the ledger's final page appears: *"Three paths. One night. Which one did he take?"*

---

### Phase 3: The Choice (1–2 min)

**Decision Point**

- **State:** `act_2_complete` → `act_3_the_choice`
- **Narrative flags set:** `path_hider_chosen` OR `path_escapist_chosen` OR `path_silent_chosen`
- **Mechanics:**
  - Player stands in the family compound with all three pieces of evidence visible around them
  - A reflexive UI prompt appears (minimal, centered, documentary tone):
    - *"Your grandfather survived that night. But how?"*
    - Three buttons:
      1. *"He hid people. (Cellar evidence)"*
      2. *"He helped them escape. (Boat evidence)"*
      3. *"He stayed neutral to survive. (Observer evidence)"*
  - Player selects one
  - **No rewind.** The choice is locked. Other paths become "what might have been"—still visible in the ledger, but no longer pursued
- **Narrative consequence:**
  - One of three flag sets is locked: `path_hider_chosen`, `path_escapist_chosen`, or `path_silent_chosen`
  - Subsequent puzzles are determined by this choice
  - Other evidence fades slightly in the UI (still accessible, for reference, but no new echoes)
- **Tone:**
  - The moment is **grave, not celebratory.** No music swells. No achievement popup.
  - The voice-over is quiet: *"I made my choice. Now I had to live with it."*

---

### Phase 4: Puzzle & Reflection (15–20 min per path)

Each path has a unique **Puzzle Chain** and **Climactic Moment**. See [`NARRATIVE.md`](NARRATIVE.md) §Act 3a/3b/3c for full details.

#### **Path A: The Hider** (Righteous, Risk, Sacrifice)
- **Puzzle:** Reconstruct the cellar. Match found items (child's shoe, headscarf, prayer beads) to names in the ledger.
- **Reflection:** As you match items, photographs appear. The neighbors' stories. Their gratitude (post-1994 letters). The cost: Grandfather stayed behind to maintain the deception.
- **Climactic echo:** Final journal entry: *"I stayed so they could leave. If they find me here alone, they'll know someone was hidden. I will tell them nothing."* Evidence he was taken away. But his neighbors survived.
- **Reflection moment:** Player stands in the cellar. The question: Can they leave? Or do they stay longer, as Grandpa did?
- **Flag:** `path_a_complete`

#### **Path B: The Escapist** (Survivor, Loss, Triage)
- **Puzzle:** Trace the lake route. Mark X's on the map for safe houses, checkpoints, and the final crossing point. Piece together the passenger selection logic.
- **Reflection:** Passenger lists appear. Names circled (made it). Names crossed out (didn't). Realization: Grandfather had to choose who got on the boat.
- **Climactic echo:** Boat departure. 40 people crammed into a small vessel. A second group waits on shore. Grandfather makes the return journey, but militia now occupy the lake. He cannot go back. 87 names survived. Blank space for those who didn't.
- **Reflection moment:** Player stands at the water's edge. Mist rolling in. Gratitude for those who made it. Grief for those who didn't.
- **Flag:** `path_b_complete`

#### **Path C: The Silent** (Observer, Paralysis, Complicity)
- **Puzzle:** Map the ravine vantage point. Mark all the events Grandfather could see from the heights but did not act on.
- **Reflection:** Unsent letters appear. His justifications. His paralysis: *"I could not risk my family."* But he knew where people were hiding. He told no one. He warned no one of militia movements.
- **Climactic echo:** 1994 night on the ravine. Grandfather documents what he sees. Militia columns pass. Neighbors flee downhill. Distant screams. He writes. He does nothing. The ledger: *"I survived by being invisible. But invisibility is its own curse."*
- **Reflection moment:** Post-genocide, a visitor's account: *"Your father was a good man, but he knew about us. He said nothing, but he saw us die."* Grandfather never integrated into community after 1994.
- **Flag:** `path_c_complete`

---

### Phase 5: Remembrance (5 min)

**Return to 2026**

- **State:** All paths converge at `act_4_remembrance` → `game_complete`
- **Mechanics:**
  - Player returns to the family compound (the starting point)
  - Modern-day voice-over (perhaps the player's own voice, or a family member's)
  - Reflection on what Grandpa's choice meant, and what it means to the player in 2026
- **Final ledger entry:**
  - The same across all paths: Grandpa survived
  - But the **cost of survival** is unique to each interpretation
- **Reflection options** (non-branching; player can choose):
  1. Place the ledger on the family shrine (honoring the past)
  2. Leave a note for future visitors (passing the story on)
  3. Photograph the ledger (preserving it digitally)
  4. Sit in silence (simply being present)
- **Closing voice:**
  - *"Your grandfather made a choice. All choices in genocide are terrible. But survivors carry the weight of their choices into the rest of their lives. Now you carry the weight of knowing."*
- **Final flags:** `game_complete` + `memorialization_${path_completed}`

---

## 4. Historical Anchors by Path

### Path A: The Hider (Risk & Sacrifice)

| Anchor | Meaning | Ledger Entry |
|---|---|---|
| Cellar entrance | Safe house discovered | "I made a space. 8 people. 47 days." |
| Sleeping mats | Daily life underground | "They sleep in shifts. I keep watch." |
| Preserved food | Resource management | "Rationing: 1 cup per person per day. It must last." |
| Water collection marks | Routine risk | "Every third day I run water. Each time, I risk everything." |
| Photographs | Identities, relationships | "I know their names. I know their families. If I speak, they die." |
| Hidden neighbor's letter | Post-genocide gratitude | "You saved my daughter. I will name my first granddaughter after you." |
| Militia patrol marks | Threat assessment | "Militia moves through twice per day. They searched the compound. They did not search below." |

**Anchor → Echo → Ledger Flow (Path A Example):**
1. Player touches cellar entrance in 2026
2. Camera cuts to 1994, first-person in the cellar (30 sec echo): Grandfather is arranging sleeping mats. Voice-over: "8 of them. 8 lives depending on my silence."
3. Echo ends, player back in 2026
4. Ledger updates with parsed entry: "I made a space. 8 people. 47 days."
5. Player can re-trigger the echo anytime by touching the entrance again

---

### Path B: The Escapist (Survival & Loss)

| Anchor | Meaning | Ledger Entry |
|---|---|---|
| Boat paddle | Escape vehicle | "The boat is our only hope. It leaves at dawn." |
| Passenger list (circled) | Survivors | "These 40 made it. I helped them into the boat myself." |
| Passenger list (crossed out) | Those lost | "I came back for a second group. The lake had changed hands. I could not go back." |
| Lake route map | Safe passage | "Three safe villages. 40 km. One night of crossing." |
| Dock remains | Departure point | "The boats left before dawn. By noon, militia controlled the shore." |
| Survivor's letter | Post-genocide reunion | "We reached Zaire safely. I never forgot your face in the darkness, helping us on." |
| Checkpoint records | Danger ahead | "The checkpoint killed 30 the next day. The people I could not save." |

---

### Path C: The Silent (Witness & Inaction)

| Anchor | Meaning | Ledger Entry |
|---|---|---|
| Observer's perch | Vantage point | "From here, I can see the entire valley. Nothing escapes my eyes." |
| Chalk marks (militia) | Threat documentation | "They mark the roadsafe and unsafe, day by day. I read their marks." |
| Unsent letters | Internal conflict | "If I hide them, we all die. If I escape, who will care for the rest? Staying invisible keeps my family alive." |
| Militia patrol routes | Knowledge without action | "I know where they move. I could warn people. I do not." |
| Stone fortifications | Resistance by others | "Others fought from these heights. I did not fight." |
| Post-genocide visitor account | Legacy of silence | "Your father saw us die. He said nothing. But he saw." |

---

## 5. Decision Architecture

### The Three Paths: Moral Validity

Each path is **a coherent moral position**, not a "good/bad/ugly" ranking.

#### **Path A: The Hider**
- **Moral position:** Active sacrifice. Risk everything to protect others.
- **Cost:** Capture and probable death (Grandfather never returned home).
- **Outcome:** 8 people survived because of him.
- **Burden:** The weight of knowing he will likely die, and that his family will grieve.
- **Thematic echo:** *"I stayed so they could leave."* The ultimate inversion of survival—choosing death to save others.

#### **Path B: The Escapist**
- **Moral position:** Utilitarian triage. Save as many as possible, even if you can't save everyone.
- **Cost:** 87 survived; those who didn't make the second crossing died. Grandfather lives with their absence.
- **Outcome:** 87 people lived because of him.
- **Burden:** The arithmetic of triage. Who do you put on the boat? Who do you leave behind?
- **Thematic echo:** *"I carry their names with me."* The burden of numbers: gratitude for the living, grief for the dead.

#### **Path C: The Silent**
- **Moral position:** Preservation through invisibility. Protect your family by staying outside the conflict.
- **Cost:** Complicity through inaction. Knowing where people are hiding, knowing militia movements, saying nothing.
- **Outcome:** Grandfather and his family survive. Others—people he could have warned—do not.
- **Burden:** The weight of silence. Post-genocide isolation. Never integrated back into community.
- **Thematic echo:** *"I survived by being invisible. But invisibility is its own curse."* The cost of survival through non-participation.

### Why All Three Are Valid

The PRD mandates: "The game never judges the player's interpretation. It only reveals what that interpretation entails."

In genocide, **all choices are constrained by terror.** There are no "good" options, only options with different costs.

- **Hiding people:** If caught, everyone dies.
- **Escape routes:** You can't save everyone on the boat.
- **Silence:** You live, but at the cost of inaction.

The game respects the player's choice by presenting the full weight of whatever interpretation they select. No ending is "happy." All are heavy with meaning.

---

## 6. Dynamic State & Flag Management

### Core Narrative Flags

| Flag | Set When | Consequence |
|---|---|---|
| `act_1_started` | Player first explores compound | Act 1 progresses; Act 2 becomes available |
| `act_1_complete` | Player finds ledger first page | Ledger UI unlocks; exploration opened to all areas |
| `all_evidence_found` | All three evidence types discovered | Choice prompt appears |
| `found_cellar_evidence` | Player touches cellar anchor | Ledger updates; Path A becomes visible |
| `found_boat_evidence` | Player touches boat anchor | Ledger updates; Path B becomes visible |
| `found_observer_evidence` | Player touches ravine anchor | Ledger updates; Path C becomes visible |
| `path_hider_chosen` | Player selects Path A at choice point | Other paths fade; Path A puzzles unlock |
| `path_escapist_chosen` | Player selects Path B at choice point | Other paths fade; Path B puzzles unlock |
| `path_silent_chosen` | Player selects Path C at choice point | Other paths fade; Path C puzzles unlock |
| `path_a_complete` | Path A final echo triggered | Act 4 becomes available |
| `path_b_complete` | Path B final echo triggered | Act 4 becomes available |
| `path_c_complete` | Path C final echo triggered | Act 4 becomes available |
| `game_complete` | Player completes remembrance sequence | New Game+ state enabled; player can reload and choose differently |

### Era Flags (Set by TimeManager during echoes)

| Flag | Meaning |
|---|---|
| `current_era` | "present" or "past" |
| `in_echo_fragment` | true during a triggered echo |
| `past_cellar_visited` | true if the player has experienced the cellar echo at least once |
| `past_lake_visited` | true if the player has experienced the lake echo at least once |
| `past_ravine_visited` | true if the player has experienced the ravine echo at least once |

### Save File Structure

A save captures:
```json
{
  "progress": {
    "act": 3,
    "narrative_flags": { ... },
    "era_flags": { ... }
  },
  "evidence_collected": {
    "cellar": true,
    "boat": true,
    "observer": false
  },
  "choice_made": "path_hider_chosen",
  "discovered_ledger_entries": 12,
  "playtime_seconds": 1247
}
```

**Key rule:** Save files are **immutable once the choice is made.** A player can reload an old save before `path_*_chosen`, but once they choose, that save is locked to that path. (This prevents save-scumming and preserves the weight of the choice.)

---

## 7. System Integration

### How the Mission Drives Babylon.js Rendering

**2026 Present Era:**
- Compound is overgrown, textures weathered, color desaturated
- Camera fog is thicker (obscuring distance, emphasizing isolation)
- Ledger pages appear as interactive 3D objects in the world
- Layer mask: `LAYER_PRESENT` (0x10000000)

**1994 Past Era (during echoes):**
- Same locations, but with people present, less decay
- Colors more saturated; vegetation less overgrown
- Environmental storytelling: visible militia, hidden neighbors, boats at dock
- Camera angle locked to first-person perspective (Grandfather's eyes)
- Layer mask: `LAYER_PAST` (0x20000000)
- Duration: triggered by anchors; ends automatically or by player input

**Transition between eras:**
- Crossfade (1–2 seconds) using `DefaultRenderingPipeline.bloomEnabled` fade-out, layer mask switch, fade-in
- TimeManager orchestrates the transition (see `CHRONOS_SWITCH.md`)
- Audio crossfades from 2026 ambience to 1994 ambience

### How the Mission Drives StateManager

1. **Player interacts with evidence (anchor)**
2. **InteractableRegistry detects contact**
3. **ActionBus emits `onEvidenceFound(evidence_type)`**
4. **StateManager records flag (e.g., `found_cellar_evidence = true`)**
5. **NarrativeController checks if choice can be presented**
6. **If `all_evidence_found`, choice point unlocks**
7. **Player selects a path**
8. **StateManager locks the choice (`path_hider_chosen = true`)**
9. **Subsequent echoes only trigger from the chosen path**

### How the Mission Drives UI

**Ledger UI** (in-world object and HUD):
- Shows only discovered entries
- Entries are grouped by path (Hider, Escapist, Silent)
- Once path is chosen, entries for other paths appear grayed out (still readable, but no longer pursued)
- Final page shows the ending for the chosen path

**HUD:**
- Minimal: date (2026), current location name, proximity hints for interactables
- No quest markers
- No objective list
- Optional: a small compass showing which direction the main compound is (since the world is large and players can get disoriented)

---

## 8. Pacing & Expected Playtime

| Phase | Duration | Mechanics |
|---|---|---|
| **Arrival** | 5–10 min | Tutorial, atmosphere, first ledger discovery |
| **Evidence gathering** | 15–25 min | Freeform exploration, 8–12 echoes, ledger updates |
| **Choice** | 1–2 min | Single reflexive decision; locked forever |
| **Puzzle & reflection** | 15–20 min | Path-specific puzzle chain, climactic moment, ending echo |
| **Remembrance** | 5 min | Return to compound, reflection options, closing voice |
| **Total** | **45–60 min** | Full playthrough; intended for single session |

**Replayability:** New Game+ allows player to reload before the choice and select a different path. Each path is 45–60 minutes; players typically experience one per session.

---

## 9. Narrative Quality Assurance

### What This Mission Delivers

1. ✓ **Emotional coherence:** Each path has a clear emotional arc (sacrifice, triage, silence)
2. ✓ **Moral validity:** No path is "wrong"; all are understandable in extremis
3. ✓ **Historical grounding:** Evidence anchors come from real Bisesero history (organized resistance, escape routes, witness trauma)
4. ✓ **Player agency:** Discovery order is free; choice is locked; burden is felt
5. ✓ **Minimalist UI:** No quest markers, no dialogue trees, no judgment—only evidence and interpretation
6. ✓ **Respectful tone:** Documentary/memorial register, not spectacle or gamification

### Edge Cases

**Q: What if the player doesn't find all evidence before choosing?**  
A: The choice point only appears when `all_evidence_found` is true. If a player is missing evidence, the choice prompt does not appear. They must complete exploration first.

**Q: Can the player change their choice after locking it?**  
A: No. The choice is permanent for that save file. Replayability comes from New Game+ saves before the choice.

**Q: What if the player finishes one path and wants to experience another without reloading?**  
A: Not supported. The game is designed for single-path, single-session completion. Switching paths requires a reload (preserving the weight of the first choice).

**Q: Does the player's real-world identity (ethnicity, nationality) affect the narrative?**  
A: No. The narrative treats the player as a descendant of the grandfather, regardless of their identity. The goal is to put the player in a position of inherited memory, not to judge their real-world relationship to the genocide.

---

## 10. Connection to Other Design Docs

| Doc | Connection |
|---|---|
| [`NARRATIVE.md`](NARRATIVE.md) | Full story tree, three paths, puzzle chains |
| [`WORLD.md`](WORLD.md) | Physical geography, elevation as narrative, environmental storytelling |
| [`PUZZLE_DESIGN.md`](PUZZLE_DESIGN.md) | Detailed logic for cellar reconstruction, lake route tracing, ravine mapping |
| [`CHRONOS_SWITCH.md`](CHRONOS_SWITCH.md) | Era transitions, how anchors trigger echoes, TimeManager logic |
| [`RENDERING.md`](RENDERING.md) | Visual differences between 2026 and 1994, camera behavior during echoes |
| [`ASSET_PIPELINE.md`](ASSET_PIPELINE.md) | How 1994 prop assets are generated and where they appear |
| [`PRD.md`](PRD.md) | Core product vision, acceptance criteria, "emotionally restrained" mandate |

---

## 11. Next Steps

1. **Verify decision architecture:** Ensure the three paths feel equally valid when playtested
2. **Lock Graph.json nodes:** Ensure all flags in this doc match the actual DAG in `src/narrative/Graph.json`
3. **Write CHRONOS_SWITCH.md body:** Detailed echo trigger logic
4. **Implement echo system:** Babylon.js integration for layer mask switching during anchors
5. **Write UI spec:** Ledger visual design, HUD minimalism rules
6. **Playtest first path:** Build Path A fully; playtest pacing and emotional impact
