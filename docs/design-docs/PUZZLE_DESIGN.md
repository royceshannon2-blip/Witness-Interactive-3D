# Puzzle Design: The Shepherd's Ledger

## Puzzle Philosophy
Puzzles are **environmental discovery systems**, not traditional logic puzzles. Players find evidence by exploring, observing, and piecing together what they discover. No inventory management, no pixel hunting—just careful observation and interpretation.

---

## Act 2: Evidence Collection Puzzles

### PUZZLE: Act 2 - Explore the Ruins (act_1_explore)
**Duration**: 5 minutes  
**Location**: Family Compound  
**Goal**: Clear overgrowth and decay to access the main house

**Mechanics**:
- Climbing vines block doorways (free-climb interaction)
- Collapsed walls require careful navigation
- Loose rubble shifts under weight
- A locked door teaches the player about searching for alternate routes

**Environmental Storytelling**:
- Photographs visible through grimy windows (hints at family life before)
- A child's toy in the overgrowth (first hint of loss)
- Carved initials on a doorframe (generations of family)

**Learning Goals**:
- Teach movement/navigation
- Establish mood: beauty reclaimed by nature
- Introduce artifact observation

**Success Condition**: Player reaches the interior of the main house

---

### PUZZLE: Act 2 - Discover the Ledger (act_1_find_ledger)
**Duration**: 3 minutes  
**Location**: Family Shrine (interior)

**Mechanics**:
- The shrine is partially destroyed
- The ledger is protected by a ceremonial cloth
- Discovery is reverent, not triumphant
- First page of ledger provides the mission: "Find the truth of June 10"

**Environmental Storytelling**:
- Religious artifacts (Catholic imagery mixed with family photos)
- The shrine faces a window overlooking the hills (spiritual connection to land)
- Candles (long extinguished) arranged for the dead

**Learning Goals**:
- Establish reverence for the subject matter
- Introduce the ledger as the core mechanic
- Signal: this is not an adventure game, but a memorial

**Success Condition**: Player reads the ledger's opening page

---

### PUZZLE: Act 2 - Hidden Cellar Discovery (act_2_evidence_cellar)
**Duration**: 8 minutes  
**Location**: Family Compound Well → Underground Cellar

**Mechanics**:
1. **Finding the Well**: The well is overgrown but visible in compound. A rope has rotted.
2. **Descent Puzzle**: Descend via a series of rocks/hand-holds (climbing sequence). The descent is dark; visibility increases downward (hope descending into darkness).
3. **The Cellar Interior**: 
   - Stone walls with evidence of occupation
   - Sleeping mats (faded cloth on ground)
   - Clay bowls, water jars
   - Scratched dates on stone walls
   - A journal excerpt preserved in a sealed container

**Objects to Find** (triggers as player explores):
- `child_shoe` — indicates children were hidden
- `woman_headscarf` — women's presence
- `prayer_beads` — faith/spirituality of those in hiding
- `food_scraps` — duration of hiding (measured in grain types/degradation)
- `journal_entry_1` — Grandpa's dated entry about the first night of hiding

**Environmental Interaction**:
- Player can place a torch to light the space (metaphorically "revealing" the truth)
- Touching objects adds them to the ledger with illustrations
- Reading dates on walls reveals timeline
- Audio: dripping water, distant footsteps (sounds from the surface, inaudible to those below)

**The Revelation**:
- A final scratched message: "Still here. Day 47."
- Realization: people lived underground for almost 2 months
- Ledger updates with entry: "I keep them safe below. But how long can stone protect?"

**Learning Goals**:
- Emotional impact: experiencing the cellar's claustrophobia
- Evidence gathering: matching objects to people
- Non-linearity: player discovers at their own pace

**Success Condition**: Player collects all cellar evidence and reads the final dated entry

---

### PUZZLE: Act 2 - Lake Shore Escape Route (act_2_evidence_lake)
**Duration**: 8 minutes  
**Location**: Lake Shore (Lower Elevation)

**Mechanics**:
1. **Boat Paddle Discovery**: Half-buried in sand/reeds, weathered by water.
2. **Map Discovery**: Waterproof map in a sealed container, showing X marks and route annotations.
3. **Dock Remains**: Rotting wooden structure; safe passage requires careful footing.
4. **Wave/Water Interaction**: Waves periodically submerge lower areas (time pressure mechanic).

**Objects to Find**:
- `boat_paddle` — physical evidence of boats/escape
- `escape_map` — annotated route across Lake Kivu
- `letter_fragment` — testimonial from someone who crossed
- `list_of_names` — who was considered for escape
- `journal_entry_2` — Grandpa's dated entry about boat preparation

**Environmental Interaction**:
- Player must read the map against current vantage point (orientation puzzle)
- Tracing fingers along the map path reveals locations along shore
- Timing the waves to safely reach specific spots (organic urgency, not countdown timer)
- Finding X marks on map corresponds to safe houses along the route

**The Revelation**:
- A second name list with checkmarks and X's
- Realization: Grandpa had to decide who made it on boats
- Ledger updates with entry: "87 souls crossed. 47 waiting for a return I cannot make."

**Learning Goals**:
- Evidence chain: objects + map + names tell a story
- Moral weight: names have faces (photographs are linked)
- Spatial reasoning: map reading in 3D environment

**Success Condition**: Player collects all shore evidence and reads the complete name list

---

### PUZZLE: Act 2 - Ravine Observer's Vantage (act_2_evidence_ravine)
**Duration**: 8 minutes  
**Location**: Ravine Overlook (High Ground)

**Mechanics**:
1. **Finding the Vantage Point**: Hidden path up the ravine that requires careful navigation.
2. **Observation Spot**: A sheltered rocky outcrop with clear sightlines across the valley.
3. **Marker System**: Stones arranged in specific patterns (Grandpa's markers for what he observed).

**Objects to Find**:
- `observer_notes` — shorthand observations dated by event
- `distance_markers` — Grandpa measured sight lines for accuracy
- `militia_patrol_routes` — chalk marks showing paths militia took
- `marker_stones` — arranged to point at significant locations below
- `journal_entry_3` — Grandpa's entry about watching/witnessing

**Environmental Interaction**:
- Player stands at vantage point and uses observer's notes to look at specific locations
- Stones point to where events happened (they're compass-like)
- Audio cues: sounds from the valley (shouting, vehicles—distant, as Grandpa would hear them)
- The view is beautiful and horrifying simultaneously

**The Revelation**:
- Realization: Grandpa could see where people were hiding
- Realization: Grandpa could see militia approaching
- Realization: Grandpa's silence meant both knowledge and powerlessness
- Ledger updates with entry: "I see everything from here. Seeing does not require action. But is watching a choice?"

**Learning Goals**:
- Perspective: literally seeing from Grandpa's viewpoint
- Moral ambiguity: knowledge ≠ responsibility
- Silence as action: choosing not to act is still a choice

**Success Condition**: Player collects all observer evidence and reads the full journal entry

---

### PUZZLE: Act 2 - Family Records (act_2_evidence_compound)
**Duration**: 8 minutes  
**Location**: Family Compound (Interior)

**Mechanics**:
1. **Photograph Discovery**: Photos scatter across different rooms, each showing different periods.
2. **Family Tree Reconstruction**: Connecting photos to names in ledger entries.
3. **Recognition Puzzle**: Matching faces to names mentioned in other evidence (cellar, lake, ravine).

**Objects to Find**:
- `family_photos` (pre-1994) — normalcy before
- `identity_documents` — names, birthdates
- `neighbor_photos` — those who were hidden/escaped
- `post_1994_letters` — gratitude/grief from those who survived
- `absence_markers` — photos of people, question marks beside them

**Environmental Interaction**:
- Player can examine photos closely; zoom in on faces
- Arranging photos creates a visual family tree
- Ledger updates with names as they're identified
- Some photos deliberately damaged (Grandpa removing evidence of hiding)

**The Revelation**:
- Full ledger entry reveals 134 names: hidden, escaped, lost
- Realization: This was not just Grandpa's choice, but a family's sacrifice
- Some names appear in multiple places (they survived multiple paths)

**Learning Goals**:
- Personalization: names become faces become stories
- Complexity: people were both hiders and escapists
- Documentation: photography as evidence

**Success Condition**: Player identifies and links at least 20 names to faces and locations

---

## Act 3: Path-Specific Puzzles

### PATH A: The Hider

#### PUZZLE 3A.1: Cellar Reconstruction (act_3a_puzzle_1)
**Duration**: 8 minutes  
**Location**: Family Compound Cellar

**Mechanics**:
- Player revisits the cellar with new knowledge (artifacts now have context)
- Matching objects to testimony: the shoe belongs to Pierre (age 7), the beads to Mama Therese
- Arranging items in the cellar as they would have been
- Timeline reconstruction: arranging entries by date

**Objects & Linkage**:
- shoe (Pierre, 7 years old, hidden with mother Josephine)
- beads (Therese, elderly, prayed constantly)
- scarf (Agnes, helped with supplies)
- documents (identification papers, false records Grandpa created)

**Environmental Changes**:
- As items are correctly placed, the cellar becomes more "inhabited"
- Ledger sketches appear (illustrations of daily life below)
- Audio: Soft voices, children playing (ghost memories)

**Moral Complexity**:
- Realizing this was primarily women and children
- Realizing Grandpa falsified documents (crime to hide people)
- Realizing the risk: discovery meant death for hiders and hidden alike

**Success Condition**: Correctly match and place all 4+ key artifacts; read the full entry

---

#### PUZZLE 3A.2: Evidence of Risk (act_3a_puzzle_2)
**Duration**: 8 minutes  
**Location**: Family Compound Area (Wells, Paths, Fields)

**Mechanics**:
1. **Militia Patrol Routes**: Marked by chalk on rocks; player traces these routes
2. **Cellar Vulnerability**: Finding a crack/crevice in stone that could reveal the cellar
3. **Water Source**: The well requires Grandpa to go aboveground daily (danger point)
4. **Grain Storage**: Finding where food was kept for those below

**Objects to Find**:
- `chalk_marks` — patrol timing visible in patterns
- `supply_cache` — hidden grain storage (repeatedly robbed by militia)
- `hidden_passage_dangers` — weak stones, potential collapses
- `water_extraction_tools` — rope, buckets (necessary but dangerous)

**Interactive Sequences**:
- Player retraces Grandpa's daily supply runs (navigation through "patrol hours")
- Examining the cellar entrance from militia perspective (how exposed is it?)
- Calculating: How often can Grandpa go for water without suspicion?

**The Realization**:
- Militia patrols happen 4 times daily
- Grandpa had 4 windows (early morning, midday, afternoon, evening)
- He was caught during one of these runs
- Ledger updates: "They took me on a Thursday. The cellar was two days from discovery."

**Success Condition**: Complete patrol timing map; identify vulnerability points; find supply cache

---

#### PUZZLE 3A.3: The Cost (act_3a_puzzle_3)
**Duration**: 5 minutes  
**Location**: Family Shrine

**Mechanics**:
- Finding a post-1994 letter from one of the hidden (written to Grandpa's memory)
- Discovering Grandpa's final journal entry (left for family, never shared)
- The emotional climax: gratitude mixed with loss

**Objects to Find**:
- `letter_from_survivor` — Mama Therese thanking Grandpa; she raised 5 more children after escape
- `grandpa_final_entry` — "I stayed behind so they would not know to look further. One life for seven."
- `post_genocide_accounts` — Oral histories confirming he was taken and killed

**Non-Mechanic, Pure Narrative**:
- This puzzle is reading; the evidence is already gathered
- The "puzzle" is emotional: processing what you've learned

**Success Condition**: Reading comprehension; player understands the sacrifice

---

### PATH B: The Escapist

#### PUZZLE 3B.1: The Lake Route (act_3b_puzzle_1)
**Duration**: 8 minutes  
**Location**: Lake Shore + Compound (Map Reading)

**Mechanics**:
- Cross-referencing the map with oral accounts
- Finding "safe houses" where boats stopped (marked by survivors' testimonies)
- Identifying which villages still had fishermen willing to help
- Tracking checkpoint locations that boats had to avoid

**Objects to Find**:
- `map_route_annotations` — villages marked as safe/unsafe
- `fisherman_contacts` — names of those who provided boats
- `checkpoint_locations` — militia posts on routes
- `survivor_testimony` — accounts of the 2-day journey across the lake
- `boat_manifest` — who was on each boat

**Interactive Sequences**:
- Tracing the full route (approximately 40km across open water)
- Identifying the nearest safe landing (Zaire/Congo)
- Calculating capacity: boats held 30-50 people max
- Multiple boat runs needed: this reveals the time constraint

**The Realization**:
- 87 people crossed in 6 boats
- The first boats left June 10; final boats left June 14
- After June 14, militia controlled the shore
- A second group of 47 people was left behind

**Moral Complexity**:
- Grandpa had to choose who was "strong enough" to cross in open water
- Children and elderly were prioritized
- Young men were excluded (militia would question them)
- This meant families were separated

**Success Condition**: Complete route; identify all 6 boat departures; name the stranded group

---

#### PUZZLE 3B.2: The Selection (act_3b_puzzle_2)
**Duration**: 8 minutes  
**Location**: Family Compound (Ledger Analysis)

**Mechanics**:
- Sorting names into categories based on ledger entries
- Understanding Grandpa's selection criteria
- Discovering the names that "couldn't go"

**Objects to Find**:
- `full_name_list` — 134 names with annotations
- `age_annotations` — Grandpa noted age/health status
- `family_groupings` — how families were split
- `rejected_entries` — names Grandpa considered but deemed "too risky"
- `military_age_males` — young men explicitly excluded (tactical reason: would be questioned by militia)

**Decision Points**:
- Woman + 2 children: takes 3 spots on a boat → takes spots
- Elderly man: needs help/slow: might endanger the group → dilemma
- Teenage boy: strong but identifiable to militia → rejected, stays behind
- Newborn infant: very weak, might cry on the boat and expose them → risk vs. life

**The Realization**:
- Grandpa was forced to triage human lives
- There was no "correct" answer; all choices meant someone died
- The criteria seem logical (children, families, non-military) but the decisions are devastating
- Ledger updates: "I chose mercy where I could. The rest is silence and 47 graves."

**Success Condition**: Correctly identify the selection criteria; acknowledge the moral weight

---

#### PUZZLE 3B.3: The Journey (act_3b_puzzle_3)
**Duration**: 8 minutes  
**Location**: Lake Shore to Ravine (Traversal + Discovery)

**Mechanics**:
- Retracing the actual route boats took
- Finding evidence of the journey scattered across landscape
- Discovering where one boat is believed to have sunk

**Objects to Find**:
- `survivor_accounts` — written by those who crossed
- `checkpoint_wreckage` — evidence of a firefight where a boat was attacked
- `clothing_debris` — items from the boats (torn clothing, lost possessions)
- `boat_remains` — splinters of wood from a vessel
- `final_survivor_letter` — someone who was on the fatal boat

**Environmental Sequences**:
- Player follows the boat route (approximated in the hills)
- Finds the place where a checkpoint ambushed one boat
- Realizes: of 6 boats, only 5 reached safety
- The 6th boat (with 30-40 people) was attacked midway

**The Realization**:
- The 87 who crossed does not include the 6th boat
- So actually, fewer survived than Grandpa intended
- Or survivors hid that they survived (living in exile, unreported)
- Ledger final entry: "The names I carry include those I never learned if they reached shore."

**Success Condition**: Find evidence of the attack; understand the loss; read survivor accounts

---

#### PUZZLE 3B.4: The Afterward (act_3b_puzzle_4)
**Duration**: 5 minutes  
**Location**: Family Shrine

**Mechanics**:
- Finding post-genocide letters from survivors
- Discovering that some of the "left behind" never contacted Grandpa
- Reconciling survival with loss

**Objects to Find**:
- `letters_from_survivors` (Zaire/Congo, dated 1995-2000) — gratitude, updates on new lives
- `missing_person_notices` — for those who never surfaced
- `unnamed_graves` — unmarked mass graves in the Zaire refuge
- `grandpa_final_entry` — "I saved 87 but could not save all. The weight of the 47 remains."

**Success Condition**: Read the letters; understand survival and loss coexist

---

### PATH C: The Observer

#### PUZZLE 3C.1: The Vantage Point (act_3c_puzzle_1)
**Duration**: 8 minutes  
**Location**: Ravine Overlooking Valley

**Mechanics**:
- Mapping what Grandpa could see from the ravine
- Marking locations of hiding spots he observed
- Marking militia movement routes he watched

**Objects to Find**:
- `observation_journal_entries` — dated by event/day
- `marked_locations` — stones pointing at specific sites
- `militia_movement_logs` — timestamps and unit sizes
- `hidden_group_locations` — where families were concealing
- `event_timeline` — the sequence of violence in the valley below

**Interactive Sequences**:
- Standing at the vantage, player uses binoculars (or UI) to identify locations
- Matching observed locations to ledger entries
- Realizing the timeline: Grandpa knew in advance where militia would go
- Realizing: he could have warned people, but didn't

**The Realization**:
- Grandpa had perfect intelligence
- He could have sent a runner to warn hidden groups
- He could have signaled from the height
- He did nothing
- Ledger entry: "I see the machetes. I see the running. I see, and I am silent."

**Success Condition**: Map 10+ locations; identify the militia units; read the full timeline

---

#### PUZZLE 3C.2: The Moral Inventory (act_3c_puzzle_2)
**Duration**: 8 minutes  
**Location**: Ravine Area + Compound

**Mechanics**:
- Discovering what Grandpa knew about hiding spots
- Finding entries where he documented locations but took no action
- Realizing the betrayal of knowledge

**Objects to Find**:
- `coded_location_notes` — Grandpa's map of where families hid
- `movement_logs` — he watched families move to hiding spots
- `militia_intelligence` — he knew patrol patterns
- `reconciliation_letters` — post-genocide, survivors wrote to Grandpa (some forgiving, some not)
- `unanswered_letters` — Grandpa's drafts to survivors, never sent

**The Realization**:
- Grandpa knew exactly where 23 families were hiding
- He knew militia patrol routes
- He never told the hidden families where militia would be
- He never warned the militia away
- His silence protected his own family but doomed others

**Moral Complexity**:
- If he warned the hidden families, militia would know to look harder
- If he warned militia away, his knowledge would be revealed
- There was genuinely no "good" choice
- But he chose inaction, and inaction had consequences

**Success Condition**: Find the coded location map; read the reconciliation letters; understand the moral ambiguity

---

#### PUZZLE 3C.3: The Rationalization (act_3c_puzzle_3)
**Duration**: 8 minutes  
**Location**: Family Shrine + Compound

**Mechanics**:
- Finding Grandpa's unsent letters
- Discovering his justifications for inaction
- Realizing he knew what he was doing and why

**Objects to Find**:
- `draft_letters_to_himself` — self-justification entries
- `family_protection_notes` — why he chose his own family over others
- `fear_journal` — documenting his terror and paralysis
- `survivor_guilt_entries` — post-genocide self-recrimination
- `philosophical_reflections` — wrestling with the meaning of survival

**Key Entries**:
1. "If I hide people, militia tortures me and I reveal them all."
2. "If I escape, my family has no protection and militia targets them."
3. "If I fight, I die in hours, my family dies with me."
4. "If I stay, unseen, we may survive."

**The Realization**:
- Grandpa's logic was not wrong
- But logic doesn't absolve him
- He lived in comfort (relatively) while watching others die
- Post-genocide: he never integrated back into the community
- He lived as an outsider, isolated by his own knowledge

**Success Condition**: Read all draft letters; understand the psychological weight; recognize both the logic and the cost

---

#### PUZZLE 3C.4: The Aftermath (act_3c_puzzle_4)
**Duration**: 5 minutes  
**Location**: Family Compound (Shrine)

**Mechanics**:
- Finding a visitor's account from post-genocide
- Discovering that the hidden families knew Grandpa knew
- Realizing that his isolation was not self-imposed

**Objects to Find**:
- `visitor_account` — someone who came to thank Grandpa, only to find him unreachable
- `community_silence` — post-genocide, the town never spoke of Grandpa
- `memorial_absence` — Grandpa was not listed among heroes or rescuers
- `grandpa_final_reflection` — "I lived because I was invisible. But invisibility lasts forever."

**The Final Question**:
- Grandpa's last entry ends with a question, not a statement
- "Was it enough to remain? Was remaining itself a choice?"
- No answer provided
- The question is left for future generations to contemplate

**Success Condition**: Read the visitor account; sit with the question; understand that some choices have no resolution

---

## Act 4: Reflection & Remembrance

### PUZZLE: Act 4 - Remembrance (act_4_remembrance)
**Duration**: 5 minutes  
**Location**: Family Compound

**Mechanics**:
- Non-puzzle reflection
- Player stands where they began
- The ledger is now complete (all pages read, all evidence gathered)
- Player chooses one final action:

**Options** (all valid, no "best" choice):
1. **Place the ledger on the shrine** → Honoring Grandpa, making peace with his choice
2. **Leave a note for future visitors** → Passing the story on, ensuring remembrance
3. **Photograph the ledger** → Preserving it digitally, sharing widely
4. **Sit in silence** → Simply being present to the weight of history

**Environmental Changes**:
- All locations remain explorable
- The landscape is the same, but player's understanding has changed
- Audio: soft, contemplative (wind, water, birds)

**Success Condition**: Player chooses at least one action; game concludes

---

## Puzzle Design Principles

### 1. **No Inventory Hell**
- Objects are discovered and logged in the ledger
- Player doesn't carry items; they're simply documented
- This keeps focus on meaning, not mechanics

### 2. **Environmental Interaction, Not Clicking**
- Puzzles involve **moving through space** and **observing**
- Not: "click this object 5 times"
- Yes: "stand here and use this vantage point to find 3 locations"

### 3. **Moral Weight, Not Combat**
- Puzzles never have "fail states"
- Player can't "die" or "lose"
- The puzzle is understanding, not optimizing

### 4. **Layered Discovery**
- Each location offers 4-6 pieces of evidence
- Player discovers in any order
- Ledger automatically contextualizes each piece

### 5. **Reverence Over Entertainment**
- No time pressure (except environmental: tides, mist)
- No jump scares or gotchas
- Tone is meditative, not thrilling

---

## Audio Design for Puzzles

### Cellar Puzzles
- Dripping water (constant, meditative)
- Muffled surface sounds (hint of danger above)
- Soft breathing (player's presence in confined space)

### Lake Shore Puzzles
- Water lapping, waves building/crashing
- Gulls (life persists)
- Wind carrying distant sounds

### Ravine Puzzles
- Wind through ravine (isolation)
- Echoes of distant shouting (memories of violence)
- Silence (the weight of inaction)

### Shrine/Compound Puzzles
- Creaking wood (age, decay)
- Rustling pages (the ledger being read)
- Silence emphasizing emptiness

---

## Success Metrics

A puzzle is successful if:
1. Player understands what Grandpa experienced
2. Player empathizes with the impossible choice
3. Player recognizes moral complexity (no clear "good" option)
4. Player leaves the experience changed by what they've learned
5. Player feels the weight of history and human choice
