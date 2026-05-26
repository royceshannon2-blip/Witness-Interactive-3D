/**
 * BanterLibrary
 *
 * All ambient narrator lines, vista reflections, path reflections, and
 * choice-overlay descriptions for the session. Content drafted for M17;
 * audio generation targets M19 (Higgs-Audio v2).
 *
 * Consumed by:
 *   - PassiveBanter (M23): `BANTER_LINES[location][era]` arrays
 *   - VistaSystem: `VISTA_LINES[narratorKey]` text (caption fallback)
 *   - BreatherSequences: `BREATHER_LINES[key]` text (caption fallback)
 *   - ChoiceOverlay: `CHOICE_DESCRIPTIONS[pathFlag]` paragraphs
 *   - RemembranceSequence: `REFLECTION_LINES[pathFlag]` paragraphs
 *
 * All text is in English; Kinyarwanda captions are a future pass.
 * The grandfather speaks in first person; the narrator lines are his
 * interior voice, 1994, or his descendant's reflection, 2026.
 */

// ---------------------------------------------------------------------------
// Types

export type LocationKey = "compound" | "cellar" | "lakeshore" | "ravine" | "heights";
export type EraKey = "present" | "past";
export type PathFlag =
  | "path_hider_chosen"
  | "path_escapist_chosen"
  | "path_silent_chosen";

export interface BanterLine {
  /** Audio key for Higgs-Audio v2 generation (M19). */
  key: string;
  text: string;
}

// ---------------------------------------------------------------------------
// Ambient banter lines — 5 per location per era (50 total)

export const BANTER_LINES: Record<LocationKey, Record<EraKey, BanterLine[]>> = {
  compound: {
    present: [
      {
        key: "banter_compound_present_01",
        text: "He cleared this ground himself. You can still see where his hands were.",
      },
      {
        key: "banter_compound_present_02",
        text: "Thirty years. The eucalyptus remembers. It was here before any of this.",
      },
      {
        key: "banter_compound_present_03",
        text: "He never planted a kitchen garden. I used to wonder why. I think I know now.",
      },
      {
        key: "banter_compound_present_04",
        text: "The well is still clean. That surprised me when I came back.",
      },
      {
        key: "banter_compound_present_05",
        text: "He chose every stone for this wall. Pressed his thumbnail into the mortar. I used to think that was pride.",
      },
    ],
    past: [
      {
        key: "banter_compound_past_01",
        text: "Every night I check the door. Every night I tell myself this is the last night.",
      },
      {
        key: "banter_compound_past_02",
        text: "My wife does not ask me what is in the cellar. We have agreed not to ask.",
      },
      {
        key: "banter_compound_past_03",
        text: "I could hear them breathing below the floor. It became ordinary. That disturbs me now.",
      },
      {
        key: "banter_compound_past_04",
        text: "The children playing outside — they must not know. Children cannot keep the kind of secrets that save lives.",
      },
      {
        key: "banter_compound_past_05",
        text: "I planted beans along the wall. Something ordinary to look at from the road.",
      },
    ],
  },

  cellar: {
    present: [
      {
        key: "banter_cellar_present_01",
        text: "The cold stays here even in July. It stayed for thirty years.",
      },
      {
        key: "banter_cellar_present_02",
        text: "Nine people. The space is too small to believe.",
      },
      {
        key: "banter_cellar_present_03",
        text: "He came down here every morning. Brought food. Brought what quiet he could carry.",
      },
      {
        key: "banter_cellar_present_04",
        text: "There were marks on the wall where someone counted the days.",
      },
      {
        key: "banter_cellar_present_05",
        text: "He never told anyone. Not my mother, not me. We found out the way you're finding out now.",
      },
    ],
    past: [
      {
        key: "banter_cellar_past_01",
        text: "One candle at a time. The smoke would give us away if we burned more.",
      },
      {
        key: "banter_cellar_past_02",
        text: "I told them three days. It became three weeks. No one said anything.",
      },
      {
        key: "banter_cellar_past_03",
        text: "Innocent whispers prayers at night. I asked him to be quieter. He looked at me. He made his prayers quieter.",
      },
      {
        key: "banter_cellar_past_04",
        text: "The children stopped crying by the second week. I am not sure that is better.",
      },
      {
        key: "banter_cellar_past_05",
        text: "Today I brought mangoes. I had to eat one in the yard first so the weight did not show.",
      },
    ],
  },

  lakeshore: {
    present: [
      {
        key: "banter_lakeshore_present_01",
        text: "The reeds grow back. They don't remember which boats went through them.",
      },
      {
        key: "banter_lakeshore_present_02",
        text: "Lake Kivu in July. Flat. Patient. It held all of them.",
      },
      {
        key: "banter_lakeshore_present_03",
        text: "Somewhere out there, eighty-seven people began again.",
      },
      {
        key: "banter_lakeshore_present_04",
        text: "I stood here at night and the water was too dark to see. He pushed off into that dark anyway.",
      },
      {
        key: "banter_lakeshore_present_05",
        text: "The dock is gone. But the place where it was — you can still find it. The land remembers what the water won't.",
      },
    ],
    past: [
      {
        key: "banter_lakeshore_past_01",
        text: "No lights on the water. No lights on the shore. We move by touch.",
      },
      {
        key: "banter_lakeshore_past_02",
        text: "I counted them twice as they got in. Then I stopped counting and just pushed off.",
      },
      {
        key: "banter_lakeshore_past_03",
        text: "Someone started to cry and someone else put a hand over their mouth, gently. That is not cruelty. That is love under impossible conditions.",
      },
      {
        key: "banter_lakeshore_past_04",
        text: "The second crossing I was alone coming back. The lake was very wide and very silent.",
      },
      {
        key: "banter_lakeshore_past_05",
        text: "They did not thank me. There was no time. We do not shake hands in the dark.",
      },
    ],
  },

  ravine: {
    present: [
      {
        key: "banter_ravine_present_01",
        text: "He could see everything from here. The lake. The compound. The roads.",
      },
      {
        key: "banter_ravine_present_02",
        text: "He came up here every morning. I used to think he was watching the hills.",
      },
      {
        key: "banter_ravine_present_03",
        text: "The chalk marks are still on some of the stones. I did not know what they were until I read the ledger.",
      },
      {
        key: "banter_ravine_present_04",
        text: "A man who sees everything and does nothing — what do we call him? I've been trying to find the right word.",
      },
      {
        key: "banter_ravine_present_05",
        text: "He wasn't cruel. That's the part I keep coming back to. He wasn't cruel.",
      },
    ],
    past: [
      {
        key: "banter_ravine_past_01",
        text: "From here: the road south, the road east, the checkpoint at the junction. I can map all of it.",
      },
      {
        key: "banter_ravine_past_02",
        text: "I write down what I see. The act of writing feels like witness. I am not sure it is.",
      },
      {
        key: "banter_ravine_past_03",
        text: "The columns moved again last night. I heard them more than I saw them.",
      },
      {
        key: "banter_ravine_past_04",
        text: "There is a shelter below the gully. I have known for two weeks. I tell myself I am protecting them by staying out of their story.",
      },
      {
        key: "banter_ravine_past_05",
        text: "Every morning I expect to hear screaming. Every morning the birds sing first. The birds do not care.",
      },
    ],
  },

  heights: {
    present: [
      {
        key: "banter_heights_present_01",
        text: "You can see three countries from here, if the clouds lift. He used to say that.",
      },
      {
        key: "banter_heights_present_02",
        text: "The genocide memorial is visible from the eastern ridge. He chose not to go there. I'm going tomorrow.",
      },
      {
        key: "banter_heights_present_03",
        text: "All three paths begin from here, if you look straight down. He saw them all. He chose one, or he didn't choose, which is also a choice.",
      },
      {
        key: "banter_heights_present_04",
        text: "After 1994, he came back to this country once. He stood somewhere and looked. I don't know where he stood. Maybe here.",
      },
      {
        key: "banter_heights_present_05",
        text: "Silence from up here isn't peaceful. It's full.",
      },
    ],
    past: [
      {
        key: "banter_heights_past_01",
        text: "At night, the fires are in three places. I know what each fire means.",
      },
      {
        key: "banter_heights_past_02",
        text: "The hills held them. More than the camps, more than the roads, the hills.",
      },
      {
        key: "banter_heights_past_03",
        text: "I am watching and I am keeping the record. Somewhere, someone will want this. I tell myself that.",
      },
      {
        key: "banter_heights_past_04",
        text: "A group of maybe thirty passed below, moving north. Children among them. Fast. They knew where they were going or they were too afraid to stop.",
      },
      {
        key: "banter_heights_past_05",
        text: "In the valley, someone is singing. Quietly. The singing stops. Then it starts again. I am too far to know if it is still the same person.",
      },
    ],
  },
};

// ---------------------------------------------------------------------------
// Vista narrator lines — single reflective sentence per vista anchor.
// Key matches `VistaDef.narratorKey` registered in main.ts.

export const VISTA_LINES: Record<string, BanterLine> = {
  vista_compound_hills: {
    key: "vista_compound_hills",
    text: "He built this compound so he could see the road from every room.",
  },
  vista_lake_water: {
    key: "vista_lake_water",
    text: "The water goes all the way to Zaire. He used to say you could see the other shore if you waited for the right light.",
  },
  vista_ravine_valley: {
    key: "vista_ravine_valley",
    text: "Eleven kilometers of valley. From here you can trace every route they used.",
  },
  vista_heights_silence: {
    key: "vista_heights_silence",
    text: "He came up here the morning after. He didn't speak for three days.",
  },
};

// ---------------------------------------------------------------------------
// Breather sequence narrator lines — caption fallback text for each audio key.
// Audio keys match BreatherSequences.ts Beat definitions.

export const BREATHER_LINES: Record<string, string> = {
  breather_return_to_shrine:
    "He could have left. Many did. He stayed.",
  breather_vista_hider:
    "The hills held them. Eleven people in a space meant for root vegetables.",
  breather_vista_escapist:
    "He chose who could make it across the water. The others he did not choose.",
  breather_vista_observer:
    "From here, you could see everything. That is all he ever claimed — that he saw.",
  breather_pre_remembrance:
    "", // sound and camera only — no caption text
};

// ---------------------------------------------------------------------------
// Choice overlay descriptions — shown before the player locks a path.

export const CHOICE_DESCRIPTIONS: Record<PathFlag, string> = {
  path_hider_chosen:
    "You hide them. You become the keeper of a secret that may not survive you. Every morning is a negotiation with risk. Every ordinary action — a walk to the well, a conversation at the market — is a performance. The deception is total. The cost is yours alone.",

  path_escapist_chosen:
    "You help them cross the water. You become the person who decides who goes first. This is not rescue — rescue would mean everyone. This is arithmetic. The boats have limits. You will not be thanked, and if you are, you will not deserve it any more than the ones who didn't go deserved what happened to them.",

  path_silent_chosen:
    "You watch. You document. You keep the record of what is happening so that someone, somewhere, will know the truth of what this looked like from the inside. You tell yourself this is witness. You tell yourself the record is a form of survival. Both things are true. Neither is enough.",
};

// ---------------------------------------------------------------------------
// Path reflection paragraphs — narrator speaks after Act 3 completes,
// before the shrine becomes interactable. Pre-baked audio key + caption text.

export const REFLECTION_LINES: Record<PathFlag, BanterLine> = {
  path_hider_chosen: {
    key: "reflection_hider",
    text: "He stayed. When the others left, when the hiding became impossible, when every day was a new kind of miracle — he stayed. Nine people came down through that cellar door. He was still there when the hill went quiet. He had chosen to be the secret's keeper. That is not a small thing. Some secrets keep people alive.",
  },
  path_escapist_chosen: {
    key: "reflection_escapist",
    text: "He chose who could go. And then he chose again. The mathematics of survival are not mathematics — they are mercy applied under unbearable conditions. Eighty-seven people stood on the other shore and breathed. Some of them had children who grew up never knowing his name. He had wanted it that way. He thought anonymity was the cleanest form of generosity.",
  },
  path_silent_chosen: {
    key: "reflection_observer",
    text: "He saw. That is the truest thing we can say. He kept the record with discipline and care. He documented what he could not stop. Whether that was cowardice or preservation or something without a name — he lived with the question until he died. The record exists because he made it. The record is also the evidence of what he did not do. Both things are true.",
  },
};
