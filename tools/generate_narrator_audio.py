#!/usr/bin/env python3
"""
M19 — Narrator audio generation via Higgs-Audio v2.

Generates all narrator WAV clips for Witness Interactive 3D:
  - 50 ambient banter lines (location × era × 5)
  - 4 vista reflection lines
  - 4 breather sequence lines
  - 3 path reflection paragraphs
  - 16 ledger journal entries (body text read aloud)

Output: audios/narrator/<key>.wav  (24 kHz, normalized to -16 LUFS / -1 dBTP)
Manifest: audios/narrator/manifest.json

Usage:
    LD_LIBRARY_PATH=/usr/local/lib/ollama/cuda_v12:$LD_LIBRARY_PATH \\
        python3 -W ignore tools/generate_narrator_audio.py [--dry-run] [--key KEY]

Flags:
    --dry-run   Print manifest and exit without generating audio.
    --key KEY   Generate only the clip with this key (skip all others).
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR   = REPO_ROOT / "audios" / "narrator"

# Point HuggingFace cache at project model_cache/ so large models are reused.
os.environ.setdefault(
    "HF_HOME",
    str(REPO_ROOT / "model_cache" / "huggingface"),
)

# ---------------------------------------------------------------------------
# Narrator scene description — steers voice without a custom voice clone.
# Passed as the scene_desc block in the Higgs-Audio system message.

NARRATOR_SCENE_PROMPT = (
    "Audio is recorded in a quiet, dimly lit interior space at night. "
    "The speaker is one elderly man. He speaks English as a second language "
    "with a gentle East African cadence — unhurried, measured, reflective. "
    "The delivery is private and considered, the voice of someone reading from "
    "memory. No music, no background noise."
)

# Model identifier (HuggingFace) — v2 loaded via native transformers API.
MODEL_PATH = "bosonai/higgs-audio-v2-generation-3B-base"

# Acoustic codec used for decoding generated tokens back to waveform.
# The transformers HiggsAudioV2TokenizerModel is missing acoustic/quantizer
# weights in model.safetensors; they live in model.pth and are loaded via
# the local higgs_audio_src wrapper instead.
TOKENIZER_PATH = "bosonai/higgs-audio-v2-tokenizer"

# Audio stream marker IDs embedded by the generation model.
_AUDIO_BOS_ID = 1024
_AUDIO_EOS_ID = 1025

# ---------------------------------------------------------------------------
# Narrator manifest — all lines to generate.
# Structure: {"key": str, "text": str}
# Keys map 1-to-1 to audios/narrator/<key>.wav

MANIFEST: list[dict] = [

    # ------------------------------------------------------------------
    # Ambient banter — compound × present (5)
    {"key": "banter_compound_present_01", "text": "He cleared this ground himself. You can still see where his hands were."},
    {"key": "banter_compound_present_02", "text": "Thirty years. The eucalyptus remembers. It was here before any of this."},
    {"key": "banter_compound_present_03", "text": "He never planted a kitchen garden. I used to wonder why. I think I know now."},
    {"key": "banter_compound_present_04", "text": "The well is still clean. That surprised me when I came back."},
    {"key": "banter_compound_present_05", "text": "He chose every stone for this wall. Pressed his thumbnail into the mortar. I used to think that was pride."},

    # Ambient banter — compound × past (5)
    {"key": "banter_compound_past_01", "text": "Every night I check the door. Every night I tell myself this is the last night."},
    {"key": "banter_compound_past_02", "text": "My wife does not ask me what is in the cellar. We have agreed not to ask."},
    {"key": "banter_compound_past_03", "text": "I could hear them breathing below the floor. It became ordinary. That disturbs me now."},
    {"key": "banter_compound_past_04", "text": "The children playing outside — they must not know. Children cannot keep the kind of secrets that save lives."},
    {"key": "banter_compound_past_05", "text": "I planted beans along the wall. Something ordinary to look at from the road."},

    # Ambient banter — cellar × present (5)
    {"key": "banter_cellar_present_01", "text": "The cold stays here even in July. It stayed for thirty years."},
    {"key": "banter_cellar_present_02", "text": "Nine people. The space is too small to believe."},
    {"key": "banter_cellar_present_03", "text": "He came down here every morning. Brought food. Brought what quiet he could carry."},
    {"key": "banter_cellar_present_04", "text": "There were marks on the wall where someone counted the days."},
    {"key": "banter_cellar_present_05", "text": "He never told anyone. Not my mother, not me. We found out the way you're finding out now."},

    # Ambient banter — cellar × past (5)
    {"key": "banter_cellar_past_01", "text": "One candle at a time. The smoke would give us away if we burned more."},
    {"key": "banter_cellar_past_02", "text": "I told them three days. It became three weeks. No one said anything."},
    {"key": "banter_cellar_past_03", "text": "Innocent whispers prayers at night. I asked him to be quieter. He looked at me. He made his prayers quieter."},
    {"key": "banter_cellar_past_04", "text": "The children stopped crying by the second week. I am not sure that is better."},
    {"key": "banter_cellar_past_05", "text": "Today I brought mangoes. I had to eat one in the yard first so the weight did not show."},

    # Ambient banter — lakeshore × present (5)
    {"key": "banter_lakeshore_present_01", "text": "The reeds grow back. They don't remember which boats went through them."},
    {"key": "banter_lakeshore_present_02", "text": "Lake Kivu in July. Flat. Patient. It held all of them."},
    {"key": "banter_lakeshore_present_03", "text": "Somewhere out there, eighty-seven people began again."},
    {"key": "banter_lakeshore_present_04", "text": "I stood here at night and the water was too dark to see. He pushed off into that dark anyway."},
    {"key": "banter_lakeshore_present_05", "text": "The dock is gone. But the place where it was — you can still find it. The land remembers what the water won't."},

    # Ambient banter — lakeshore × past (5)
    {"key": "banter_lakeshore_past_01", "text": "No lights on the water. No lights on the shore. We move by touch."},
    {"key": "banter_lakeshore_past_02", "text": "I counted them twice as they got in. Then I stopped counting and just pushed off."},
    {"key": "banter_lakeshore_past_03", "text": "Someone started to cry and someone else put a hand over their mouth, gently. That is not cruelty. That is love under impossible conditions."},
    {"key": "banter_lakeshore_past_04", "text": "The second crossing I was alone coming back. The lake was very wide and very silent."},
    {"key": "banter_lakeshore_past_05", "text": "They did not thank me. There was no time. We do not shake hands in the dark."},

    # Ambient banter — ravine × present (5)
    {"key": "banter_ravine_present_01", "text": "He could see everything from here. The lake. The compound. The roads."},
    {"key": "banter_ravine_present_02", "text": "He came up here every morning. I used to think he was watching the hills."},
    {"key": "banter_ravine_present_03", "text": "The chalk marks are still on some of the stones. I did not know what they were until I read the ledger."},
    {"key": "banter_ravine_present_04", "text": "A man who sees everything and does nothing — what do we call him? I've been trying to find the right word."},
    {"key": "banter_ravine_present_05", "text": "He wasn't cruel. That's the part I keep coming back to. He wasn't cruel."},

    # Ambient banter — ravine × past (5)
    {"key": "banter_ravine_past_01", "text": "From here: the road south, the road east, the checkpoint at the junction. I can map all of it."},
    {"key": "banter_ravine_past_02", "text": "I write down what I see. The act of writing feels like witness. I am not sure it is."},
    {"key": "banter_ravine_past_03", "text": "The columns moved again last night. I heard them more than I saw them."},
    {"key": "banter_ravine_past_04", "text": "There is a shelter below the gully. I have known for two weeks. I tell myself I am protecting them by staying out of their story."},
    {"key": "banter_ravine_past_05", "text": "Every morning I expect to hear screaming. Every morning the birds sing first. The birds do not care."},

    # Ambient banter — heights × present (5)
    {"key": "banter_heights_present_01", "text": "You can see three countries from here, if the clouds lift. He used to say that."},
    {"key": "banter_heights_present_02", "text": "The genocide memorial is visible from the eastern ridge. He chose not to go there. I'm going tomorrow."},
    {"key": "banter_heights_present_03", "text": "All three paths begin from here, if you look straight down. He saw them all. He chose one, or he didn't choose, which is also a choice."},
    {"key": "banter_heights_present_04", "text": "After 1994, he came back to this country once. He stood somewhere and looked. I don't know where he stood. Maybe here."},
    {"key": "banter_heights_present_05", "text": "Silence from up here isn't peaceful. It's full."},

    # Ambient banter — heights × past (5)
    {"key": "banter_heights_past_01", "text": "At night, the fires are in three places. I know what each fire means."},
    {"key": "banter_heights_past_02", "text": "The hills held them. More than the camps, more than the roads, the hills."},
    {"key": "banter_heights_past_03", "text": "I am watching and I am keeping the record. Somewhere, someone will want this. I tell myself that."},
    {"key": "banter_heights_past_04", "text": "A group of maybe thirty passed below, moving north. Children among them. Fast. They knew where they were going or they were too afraid to stop."},
    {"key": "banter_heights_past_05", "text": "In the valley, someone is singing. Quietly. The singing stops. Then it starts again. I am too far to know if it is still the same person."},

    # ------------------------------------------------------------------
    # Vista reflection lines (4)
    {"key": "vista_compound_hills",  "text": "He built this compound so he could see the road from every room."},
    {"key": "vista_lake_water",      "text": "The water goes all the way to Zaire. He used to say you could see the other shore if you waited for the right light."},
    {"key": "vista_ravine_valley",   "text": "Eleven kilometers of valley. From here you can trace every route they used."},
    {"key": "vista_heights_silence", "text": "He came up here the morning after. He didn't speak for three days."},

    # ------------------------------------------------------------------
    # Breather sequence lines (4 — breather_pre_remembrance is sound+camera only, no text)
    {"key": "breather_return_to_shrine", "text": "He could have left. Many did. He stayed."},
    {"key": "breather_vista_hider",      "text": "The hills held them. Eleven people in a space meant for root vegetables."},
    {"key": "breather_vista_escapist",   "text": "He chose who could make it across the water. The others he did not choose."},
    {"key": "breather_vista_observer",   "text": "From here, you could see everything. That is all he ever claimed — that he saw."},

    # ------------------------------------------------------------------
    # Path reflection paragraphs — spoken after Act 3 completes (3)
    {
        "key": "reflection_hider",
        "text": (
            "He stayed. When the others left, when the hiding became impossible, "
            "when every day was a new kind of miracle — he stayed. Nine people came "
            "down through that cellar door. He was still there when the hill went quiet. "
            "He had chosen to be the secret's keeper. That is not a small thing. "
            "Some secrets keep people alive."
        ),
    },
    {
        "key": "reflection_escapist",
        "text": (
            "He chose who could go. And then he chose again. The mathematics of survival "
            "are not mathematics — they are mercy applied under unbearable conditions. "
            "Eighty-seven people stood on the other shore and breathed. Some of them had "
            "children who grew up never knowing his name. He had wanted it that way. "
            "He thought anonymity was the cleanest form of generosity."
        ),
    },
    {
        "key": "reflection_observer",
        "text": (
            "He saw. That is the truest thing we can say. He kept the record with "
            "discipline and care. He documented what he could not stop. Whether that "
            "was cowardice or preservation or something without a name — he lived with "
            "the question until he died. The record exists because he made it. "
            "The record is also the evidence of what he did not do. Both things are true."
        ),
    },

    # ------------------------------------------------------------------
    # Ledger journal entries — body text read aloud (16)
    {
        "key": "ledger_act_1_complete",
        "text": (
            "June, 1994. I have kept this book for eleven years. I record prices, weights, "
            "the measure of the harvest. Tonight I begin recording something else. "
            "There is no price for what I am about to write."
        ),
    },
    {
        "key": "ledger_found_cellar_evidence",
        "text": (
            "April 9, 1994. Nine people in the space below the well. I told them three nights "
            "at most. I said it because I needed it to be true. I knew on the third day that it was not."
        ),
    },
    {
        "key": "ledger_found_observer_evidence",
        "text": (
            "June 3, 1994. From the ravine at first light, I counted four columns. They moved "
            "north, then turned. They knew where the people were sheltering. I wrote the direction, "
            "the time, the number. I wrote it all down."
        ),
    },
    {
        "key": "ledger_found_boat_evidence",
        "text": (
            "May 17, 1994. We pushed off from the reeds before the moon rose. I asked people "
            "to leave behind everything heavy. One man would not leave his son's shoes. "
            "I let him keep them. The lake does not care about the weight of grief."
        ),
    },
    {
        "key": "ledger_found_family_records",
        "text": (
            "March 29, 1994. I write their names here so they cannot be forgotten: "
            "Felicite. Jean-Pierre. Innocent. Angele. Theophile. "
            "Twelve names on this page. I have committed them to memory as well. "
            "The page can burn. Memory is harder to destroy."
        ),
    },
    {
        "key": "ledger_puzzle_a1_complete",
        "text": (
            "April 14, 1994. Eight people now, not nine. Therese left in the night — "
            "I do not know where she went. The others sleep in shifts: four lying, four sitting. "
            "I brought down the two spare mats from the upper room. I told my wife they were old "
            "and worn out. She did not ask again."
        ),
    },
    {
        "key": "ledger_puzzle_a2_complete",
        "text": (
            "May 2, 1994. Every third day, one of us walks to the well at dawn. We go alone, "
            "we go naturally. We do not carry more than one bucket at a time. If they stop you "
            "and ask, you say you are making ugali and your wife sent you. I have rehearsed this. "
            "So has my son. He is eleven years old."
        ),
    },
    {
        "key": "ledger_puzzle_a3_complete",
        "text": (
            "This letter arrived in August, carried by a man I did not recognize. It is from "
            "Consolee, who was in the cellar from April until June. She says eight of the nine "
            "survived. She asks if I am alive. She does not know the answer. I am reading her "
            "letter, so yes — but she is in Goma and I cannot tell her yet."
        ),
    },
    {
        "key": "ledger_puzzle_b1_complete",
        "text": (
            "May 16, 1994. Forty names on the first list. I circled the ones the boat could "
            "hold and then I stopped. The people whose names I had not circled gathered on the "
            "shore and watched me write. I did not look up. Cowardice is sometimes the only honest thing."
        ),
    },
    {
        "key": "ledger_puzzle_b2_complete",
        "text": (
            "May 15, 1994. I measured the boat this morning. Forty sit safely. Forty-two if "
            "they are calm. The crossing to Zaire is four hours in the dark. If the water is "
            "rough — thirty-eight. I told myself I was doing mathematics. "
            "But mathematics does not choose who lives."
        ),
    },
    {
        "key": "ledger_puzzle_b3_complete",
        "text": (
            "May 21, 1994. Two crossings. Forty on the first night, forty-seven on the second. "
            "The third night, militia were at the lake. I counted: eighty-seven names. Later I "
            "found the passenger lists in an oilcloth sack I had forgotten I buried. I had counted "
            "correctly. I do not know why that matters to me now."
        ),
    },
    {
        "key": "ledger_puzzle_b4_complete",
        "text": (
            "This letter is dated September 1994. It is signed by Jean-Baptiste, who was on the "
            "second crossing. He describes the arrival in Goma, the camp, the walk to find family. "
            "He says he has told his children about the man who chose them. He got my name wrong. "
            "He wrote Bernard. My name is Barnabe. I kept the letter anyway."
        ),
    },
    {
        "key": "ledger_puzzle_c1_complete",
        "text": (
            "June 5, 1994. I can read the chalk marks they leave on the stones. I learned this "
            "in April. Three marks: a route. Two marks crossed: already searched. One mark circled: "
            "a shelter found. I have been keeping a record. I do not know who I am keeping it for."
        ),
    },
    {
        "key": "ledger_puzzle_c2_complete",
        "text": (
            "June 12, 1994. I knew about the families in the gully below the ravine. I had seen "
            "them arrive two weeks earlier. The checkpoint moved south on the morning of the fourteenth. "
            "I knew the direction. I did not walk down to warn them. I told myself it was too dangerous. "
            "That was true. It was also not the whole truth."
        ),
    },
    {
        "key": "ledger_puzzle_c3_complete",
        "text": (
            "June 18, 1994. I write this at the edge of darkness, the lamp turned low. If I fight, "
            "I die. If I hide them, we are found and we all die. If I take the boats, the militia "
            "watch the lake now. Staying invisible is the only weapon I have left. Invisible people "
            "do not save anyone else, but they survive to bury the dead. Someone must bury the dead."
        ),
    },
    {
        "key": "ledger_puzzle_c4_complete",
        "text": (
            "This account was recorded in 2002 by a research team documenting witness testimony. "
            "A woman named Esperance describes a figure she saw on the ravine high ground throughout "
            "June 1994. She says he watched. She saw his lantern at night. He never came down. "
            "She says: I am not angry. I am something worse than angry. I am certain he saw us. "
            "She did not know his name. But she described this compound exactly."
        ),
    },
]


# ---------------------------------------------------------------------------
# Helpers

def _seed_for_key(key: str) -> int:
    """Deterministic seed per key for reproducible generation."""
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16) % (2**31)


def _normalize(raw_path: Path, out_path: Path) -> None:
    """Two-pass ffmpeg loudnorm: -16 LUFS integrated, -1 dBTP true peak."""
    # Pass 1 — measure
    cmd1 = [
        "ffmpeg", "-y", "-i", str(raw_path),
        "-af", "loudnorm=I=-16:TP=-1:LRA=11:print_format=json",
        "-f", "null", "/dev/null",
    ]
    result = subprocess.run(cmd1, capture_output=True, text=True)
    output = result.stderr  # ffmpeg writes to stderr

    # Extract JSON block from loudnorm output
    match = re.search(r"\{[^}]+\}", output, re.DOTALL)
    if match:
        stats = json.loads(match.group())
        af = (
            f"loudnorm=I=-16:TP=-1:LRA=11"
            f":measured_I={stats['input_i']}"
            f":measured_LRA={stats['input_lra']}"
            f":measured_TP={stats['input_tp']}"
            f":measured_thresh={stats['input_thresh']}"
            f":offset={stats['target_offset']}"
            f":linear=true:print_format=summary"
        )
    else:
        # Fallback to single-pass linear if JSON parse fails
        af = "loudnorm=I=-16:TP=-1:LRA=11:linear=true"

    # Pass 2 — apply
    cmd2 = [
        "ffmpeg", "-y", "-i", str(raw_path),
        "-af", af,
        "-ar", "24000",
        "-sample_fmt", "s16",
        str(out_path),
    ]
    subprocess.run(cmd2, capture_output=True, check=True)


def _write_manifest(out_dir: Path, items: list[dict]) -> None:
    manifest = {}
    for item in items:
        key = item["key"]
        wav_path = out_dir / f"{key}.wav"
        manifest[key] = {
            "file": f"audios/narrator/{key}.wav",
            "text": item["text"],
            "exists": wav_path.exists(),
        }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Manifest written → {manifest_path}")


# ---------------------------------------------------------------------------
# Main

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print manifest and exit without generating audio.")
    parser.add_argument("--key", default=None,
                        help="Generate only this single key.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print(f"Manifest ({len(MANIFEST)} lines):")
        for item in MANIFEST:
            status = "EXISTS" if (OUT_DIR / f"{item['key']}.wav").exists() else "missing"
            print(f"  [{status:7}] {item['key']}")
        _write_manifest(OUT_DIR, MANIFEST)
        return

    # Filter to a single key if requested
    targets = MANIFEST
    if args.key:
        targets = [m for m in MANIFEST if m["key"] == args.key]
        if not targets:
            sys.exit(f"Key '{args.key}' not found in manifest.")

    # Count what actually needs generation
    pending = [m for m in targets if not (OUT_DIR / f"{m['key']}.wav").exists()]
    if not pending:
        print("All clips already exist. Nothing to do.")
        _write_manifest(OUT_DIR, MANIFEST)
        return

    print(f"Generating {len(pending)}/{len(targets)} clips "
          f"(skipping {len(targets) - len(pending)} existing)...")

    # ------------------------------------------------------------------
    # Load model via native transformers API (v2 architecture).
    try:
        import torch
        import soundfile as sf
        from transformers import AutoProcessor, HiggsAudioV2ForConditionalGeneration
    except ImportError as e:
        sys.exit(f"Import error: {e}\nEnsure transformers>=5.3.0 and soundfile are installed.")

    print("Loading Higgs-Audio v2 processor + generation model (cached after first run)...")
    processor = AutoProcessor.from_pretrained(MODEL_PATH)
    model = HiggsAudioV2ForConditionalGeneration.from_pretrained(
        MODEL_PATH,
        device_map="cuda:0",
        torch_dtype=torch.bfloat16,
    )
    model.eval()

    # Load acoustic codec for decoding.  The transformers HiggsAudioV2TokenizerModel
    # is missing acoustic/quantizer weights (they live in model.pth, not
    # model.safetensors).  Use the local higgs_audio_src wrapper instead — it loads
    # model.pth directly and has zero size mismatches.
    print("Loading v2 acoustic tokenizer (higgs_audio_src)...")
    sys.path.insert(0, str(REPO_ROOT / "tools" / "higgs_audio_src"))
    try:
        from boson_multimodal.audio_processing.higgs_audio_tokenizer import (
            load_higgs_audio_tokenizer,
        )
    except ImportError as e:
        sys.exit(f"Cannot import higgs_audio_src: {e}")
    v2_tokenizer = load_higgs_audio_tokenizer(TOKENIZER_PATH, device="cuda")
    v2_tokenizer.eval()

    # ------------------------------------------------------------------
    # Generate each clip
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        for idx, item in enumerate(pending, 1):
            key  = item["key"]
            text = item["text"]
            out_path = OUT_DIR / f"{key}.wav"

            print(f"\n[{idx}/{len(pending)}] {key}")

            # Ensure text ends with punctuation for clean TTS cadence.
            text_clean = text.strip()
            if text_clean and text_clean[-1] not in ".!?,;\"'":
                text_clean += "."

            conversation = [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": "Generate audio following instruction."}],
                },
                {
                    "role": "scene",
                    "content": [{"type": "text", "text": NARRATOR_SCENE_PROMPT}],
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": text_clean}],
                },
            ]

            inputs = processor.apply_chat_template(
                conversation,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                processor_kwargs={"sampling_rate": 24000},
            ).to(model.device)

            torch.manual_seed(_seed_for_key(key))

            try:
                with torch.inference_mode():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=2048,
                        do_sample=True,
                        temperature=0.9,
                        top_k=50,
                        top_p=0.95,
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR generating {key}: {exc}")
                continue

            raw_path = tmp_dir / f"{key}_raw.wav"

            # ── Decode audio tokens ──────────────────────────────────────────
            # outputs shape: (1, seq_len, num_codebooks)
            audio_ids = outputs[0]  # (seq_len, num_codebooks)

            # Find the last BOS position (start of generated audio)
            bos_mask = (audio_ids == _AUDIO_BOS_ID).all(-1)
            bos_idxs = bos_mask.nonzero(as_tuple=False)
            start = int(bos_idxs[-1, 0].item()) if len(bos_idxs) > 0 else 0
            audio_ids = audio_ids[start:]

            # Find first EOS after BOS
            eos_mask = (audio_ids == _AUDIO_EOS_ID).all(-1)
            eos_idxs = eos_mask.nonzero(as_tuple=False)
            end = int(eos_idxs[0, 0].item()) if len(eos_idxs) > 0 else audio_ids.shape[0]

            # Extract content frames (skip BOS at index 0, stop before EOS)
            audio_token_ids = audio_ids[1:end]  # (delay_frames + content, n_q)

            # Revert delay pattern (staggered by codebook index)
            seq_len_d, num_cb = audio_token_ids.shape
            slices = [
                audio_token_ids[i : seq_len_d - num_cb + 1 + i, i : i + 1]
                for i in range(num_cb)
            ]
            reverted = torch.cat(slices, dim=1)  # (content_frames, n_q)
            reverted = reverted.clip(0, _AUDIO_BOS_ID - 1)

            # Decode to waveform via higgs_audio_src (model.pth weights)
            vq_code = reverted.t().unsqueeze(0).cpu()  # (1, n_q, content_frames)
            audio_np = v2_tokenizer.decode(vq_code)     # numpy (1, 1, n_samples)
            audio_samples = audio_np[0, 0]              # (n_samples,)
            sf.write(str(raw_path), audio_samples, v2_tokenizer.sample_rate)

            try:
                _normalize(raw_path, out_path)
                print(f"  OK → {out_path.relative_to(REPO_ROOT)}")
            except subprocess.CalledProcessError as exc:
                print(f"  FFmpeg error for {key}: {exc.stderr[:200] if exc.stderr else exc}")
                import shutil
                shutil.copy(str(raw_path), str(out_path))
                print(f"  Saved un-normalised fallback → {out_path.relative_to(REPO_ROOT)}")

    # ------------------------------------------------------------------
    _write_manifest(OUT_DIR, MANIFEST)
    done = sum(1 for m in MANIFEST if (OUT_DIR / f"{m['key']}.wav").exists())
    print(f"\nDone. {done}/{len(MANIFEST)} clips present in {OUT_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
