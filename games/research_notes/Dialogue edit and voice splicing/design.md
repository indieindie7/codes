# Live dialogue editing with spliced voice for Unreal II

Design + offline prototype, 2026-10-08. No game or editor was run, and nothing was written into the game folder.
- **Verified** means read from the exported script (`Documents\Tools\u2_export\full_U2Dialog`, `full_Engine`, `full_UI`) or the game's files on disk (read only).
- **Measured** means the prototype was run on this PC.
- **Guess** means test it in the game first.

The user's idea: "if the dialogue text could be edited during console screen and voice text regenerated using the old tf2 phonetics mixing system".

## 0. Summary

1. **U2 voices need no editor and no package import.** Every dialogue line is a plain Ogg file: `<game>\Voice\<Pkg>\<Group>\<Name>.ogg` (1,867 files, 112 MB). The `.dlg` files are plain INI (`Speaker=`, `LongText=`, `SoundFile=Pkg.Group.Name`). The game plays a line with `Actor.PlayVoice(GetOggFilename(Filename))` when the Ogg exists (`DialogSession.LoadAndPlayAudioFile`, verified). So hot-loading a new voice clip means writing a new `.ogg` under `Voice\` and setting `DialogNode.Filename` to its dotted name. There is no `DynamicLoadObject` and no `.uax` rebuild.
2. **The text is a runtime field.** `DialogEngine.GetNode(Self, 'NodeName')` returns the live `DialogNode`. `LongText` is what `DisplayText` shows as the subtitle. U2Seven already rewrites `Filename`, `LongText` and `AudioDuration` this way.
3. **The splice pipeline works offline (measured).** The prototype is in `codes/tools/python/VoiceSplice/`. It builds a word and phone bank from a speaker's own lines and plans a new line: word runs first, then single words, then diphones, then a TTS fallback. It splices the units with crossfades and loudness and pitch smoothing, and writes a game-format Ogg (44.1 kHz mono Vorbis). It ran on a Piper stand-in corpus and on Isaak's 518 real lines (45 min) extracted locally. A spliced line plus its Ogg takes about 0.5 s on the CPU. A line with a Piper fallback takes about 3 s the first time, while the voice model loads.
4. **Quality:** lines built from words the character has said sound like him and are intelligible. Words he never said, built from diphones, are mostly not intelligible. That is the TF2 sentence-mix sound and its limit. For those words the planned route is **TTS + voice conversion into the character's voice** (kNN-VC or RVC, both MIT), trained or matched on the same local bank.

## 1. What "TF2 phonetics mixing" is, technically

There are two things the phrase can mean. Both are concatenation of recorded speech.

- **Fan "sentence mixing" (the likely meaning).** In the early Source Filmmaker / YouTube Poop era (about 2008–2014), people cut TF2's voice lines into words, syllables and single phonemes by hand in an audio editor and re-ordered them into new sentences. This is manual unit selection. The cuts sit at word gaps, or inside a sound that stays steady (vowels, s/sh/m). Pieces get small pitch and volume nudges and very short crossfades. The stitched sound is part of the charm.
- **Valve's engine-side systems (same family).**
  - Half-Life's VOX announcer: `sentences.txt` lists words from `sound/vox/*.wav` and plays them back to back, with per-word pitch, volume and start/end trims (`vox/(p105) warning ...`).
  - The Source `sentences.txt` sentence system: the same idea, with groups.
  - The Source `!SENTENCE`/response rules: these pick whole recorded lines.
  - Separately, Source stores phoneme and word timings inside the WAV (a VDAT chunk written by FacePoser's phoneme extractor) for lip sync. That is the "phonetic" data Valve kept per line.
  - These are described from memory; they were not re-checked online for this note.

**What the computer version needs** (all of it is in the prototype):

| step | classic way | used here | better / next |
|---|---|---|---|
| find words in a line | by ear | whisper word timestamps (which words were really said) + DTW against a Piper reading of the same text (where they are) | Montreal Forced Aligner (MIT, pretrained English model CC BY 4.0) or a wav2vec2 CTC aligner (torchaudio, BSD; fairseq weights MIT) |
| find phonemes | by ear | eSpeak NG phonemes per word (GPL-3, comes with Piper) + optimal segmentation of the MFCC frames with a duration prior | MFA phone tier |
| choose units | taste | unit selection (Hunt & Black 1996): target cost (sentence position, neighbour words, phone context) + join cost (pitch/energy jump), Viterbi | the same costs, tuned by listening |
| cut points | word gaps, mid-vowel | word edges snapped to the quietest 5 ms frame; diphones cut mid-phone | — |
| joins | short fades | 4–8 ms fades on words; 10 ms equal-power crossfade at the best-correlating offset (WSOLA-style) inside words | TD-PSOLA (`psola`, MIT) or WORLD (`pyworld`, MIT; WORLD modified-BSD) for real pitch/duration moves without resampling |
| prosody smoothing | ear | loudness to the bank median (gain capped ±6 dB); diphone pieces pitch-moved toward their mean by resampling (≤3 st) | PSOLA/WORLD contour fitting over the whole line |

**Voice conversion (the alternative and the fallback).** Synthesize the line with Piper and convert it into the character's voice:

- **kNN-VC** (bshall/knn-vc, MIT; WavLM-Large weights MIT, HiFi-GAN vocoder MIT): this is unit selection in feature space. Each frame of the source is replaced by the mean of its nearest frames from the target speaker's recordings. It needs only a few minutes of reference audio and no training. It is the closest modern relative of sentence mixing, and the first VC to try.
- **RVC** (Retrieval-based-Voice-Conversion-WebUI, MIT; HuBERT/RMVPE weights MIT): trains a per-voice model from about 10+ minutes of audio. Isaak has 45 min. It gives better quality at the cost of a training run (GPU slot, about 30–60 min).
- **OpenVoice v2** (MIT since 2024): zero-shot tone-colour transfer. It is easy, but the timbre match is weaker than RVC.
- **so-vits-svc-fork** is MIT (the original so-vits-svc is AGPL-3; AGPL is acceptable under the share-alike rule, but the fork is simpler).

Avoid or flag:
- **Coqui XTTS-v2**: Coqui Public Model Licence, non-commercial with extra limits. Not a share-alike licence.
- **F5-TTS** and **Meta MMS aligner** weights: CC BY-NC. Non-commercial is acceptable for mods, so they can be used if needed, but they are not the first pick.
- Piper is GPL-3 (piper1-gpl). Each Piper voice has its own dataset licence; check the voice's MODEL_CARD before shipping any audio made from it.

**Licence of the output.** The spliced audio is made from the game's own recordings. It stays local and is never committed, put in a video or uploaded (the old-game assets rule). A mod release can ship the tool, and each user builds their own bank from their own copy of the game.

## 2. The U2 side: where things live (verified)

- `.dlg` (`<game>\Dialog\**\*.dlg`, 215 files) is INI. Its keys include `Speaker`, `LongText` (the subtitle text, word for word), `ShortText`, `SoundFile=Pkg.Group.Name`, `AudioDuration`, `NextNode`, `Event`, `SoundActor`, `LipSync` and others. Line counts with sound: Player 897, Isaak 527, Aida 183, Meyer 113, Neban 76.
- `DialogNode` fields: `LongText`, `Filename`, `bUseOggVoice`, `transient sound Voice`, `AudioDuration`, `bDoLipSync` (default true), `Volume`, `SoundRadius`, `SubtitleRadius`.
- How a line plays (`DialogSession.Talk`):
  1. `PlaySoundFile` → `LoadAndPlayAudioFile`: if `GetOggDuration(GetOggFilename(Filename)) > 0`, it calls `PlayVoice(oggfile, Volume, Radius)`. Otherwise it falls back to `DynamicLoadObject(Filename, class'Sound')` + `PlaySound(SLOT_Dialog)`.
  2. `DoLipSync`: plays an animation named like the last part of `Filename` on the `LipSync` channel, if the mesh has one.
  3. `GetAudioLength`: the Voice duration, then `AudioDuration`, then the text length ÷ 25 chars/s.
  4. `DisplayText`: `BroadcastStatusMessage(LongText, ..., "DialogSubtitlesHolder", bClearExisting=true)`.
- `DialogEngine` (singleton) holds `Sessions[]` (each with `CurNode`, `SpeakingDC`), `Trees[]`, and `GetNode(name)`. It also has native `LoadDialogFiles(Directory, File)`.
- Ogg location: the comment in `LoadAndPlayAudioFile` says Ogg files are relative to the `Voice` subdirectory. The folder layout matches `Pkg\Group\Name.ogg` exactly (checked on `M06_Acheron_A.Acheron_10.Acheron_10_002`).

**Guesses to test in game:**
- G1: `GetOggFilename` handles a two-part name (`VoiceSplice.e0007` → `Voice\VoiceSplice\e0007.ogg`). If not, use three parts: `VoiceSplice.Edits.e0007`.
- G2: `GetOggDuration` and `PlayVoice` open a file created after the game started. A new name per edit avoids any cache.
- G3: whether stock characters have per-line lip-sync anims at all. If they do, an edited line loses its own anim. Options: `bDoLipSync=false` (talk gestures still run), or the per-phoneme visemes below.

## 3. Pipeline (prototype, measured)

Code is in `codes/tools/python/VoiceSplice/` (code only; `.gitignore` blocks audio, jsonl and banks). Data and output go to `%USERPROFILE%\Documents\VoiceSplice\` (`VOICESPLICE_HOME`), outside git.

| file | does |
|---|---|
| `corpus.py` | `u2 <Speaker>`: parses every `.dlg`, maps `SoundFile` to the Ogg, decodes to 22.05 kHz WAV clips + `lines.jsonl`. Reads the game folder only. `u2 --list` shows speakers. `piper <bank> [voice]`: stand-in corpus from `test_corpus.txt` (original text). |
| `align_words.py` | runs in the whisper venv: faster-whisper small, word timestamps, known text as the prompt → `asr.jsonl`. `--transcribe` is used by the evaluation. |
| `align_dtw.py` | Piper reads the known text word by word (exact word edges). MFCC+energy (CMVN) DTW to the real clip carries the edges over → `dtw.jsonl`. |
| `bank.py` | whisper decides **which** words are trustworthy (text match, p ≥ 0.3); DTW gives **where**. Edges are snapped to energy minima and silence is trimmed. eSpeak phonemes are segmented per word, and f0/RMS are taken at every unit edge → `bank.json`. |
| `synth.py` | text → plan → splice → WAV/Ogg + `.plan.json` (see §1 table). `oov=phones` (diphones) or `oov=tts` (Piper word, pitch-moved to the bank median: the VC slot). |
| `evaluate.py` | round trip: splices a test set, whisper transcribes it, word error rate (WER) per mode. |
| `vc_knn.py` | (stage 2, runs in the `Tools\visualqa` torch venv) kNN-VC matching set / conversion, WORLD join smoothing, WavLM embeddings; a JSON-lines worker that `synth.py` starts |
| `voicesplice.py` | `build`, `say`, and `serve`: the edit watcher. `requests\*.json` → `<voice_root>\VoiceSplice\<id>.ogg` + `<id>.done.json` (`filename`, `seconds`, plan). |

Run (Isaak, about 30 min of CPU, once):
```
py -3.13 voicesplice.py build u2 Isaak
py -3.13 voicesplice.py say Isaak "Welcome back, boss. The ship is ready." ogg=%USERPROFILE%\Documents\VoiceSplice\out\test.ogg
```

### Results

Banks (measured):
- `piper_hfc`: a stand-in of 49 Piper lines (en_US-hfc_male). 432/553 words aligned, vocabulary 285, 1,543 phones.
- `Isaak`: 518 real game lines, 45 min. 6,853/8,545 words aligned, vocabulary 700, 26,768 phones, f0 median 146 Hz. The bank build takes about 77 s. Whisper alignment took about 25 min on the CPU and DTW about 20 min (both once, run in parallel).

Alignment check on the stand-in: switching word edges from whisper-only to whisper+DTW cut the mean WER from 0.60 to 0.43, and later to 0.41 with diphones.

Round-trip WER: whisper small transcribes the spliced line. Lower is better. 7 test lines, original text. "in" = every word was said by the speaker, "mix" = some words are new, "new" = names and words he never said.

| bank | mode | in | mix | new | all |
|---|---|---|---|---|---|
| piper_hfc | units (new words as diphones) | 0.12 | 0.41 | 0.83 | 0.41 |
| piper_hfc | tts (new words from Piper john, pitch-moved) | 0.12 | 0.46 | 0.35 | 0.28 |
| piper_hfc | every word as diphones | 0.07 | 0.46 | 0.94 | 0.43 |
| Isaak | units | 0.23 | 0.72 | 1.38 | 0.77 |
| Isaak | tts | 0.23 | 0.51 | 0.44 | 0.41 |
| Isaak | every word as diphones | 0.25 | 0.63 | 0.88 | 0.59 |

Examples (Isaak, units mode):
- "Welcome back, boss. The ship is ready." was heard as "Welcome back, boss. The ship is already f-". Every word came from Isaak's own lines.
- "We picked up a signal from the old mining station" was heard as "...the old mind-slash him". "Mining station" was built from diphones.
- With tts for new words it was heard as "...the new mining station".

What the numbers say:
- Lines made only of words the speaker said work on both banks (WER 0.12 and 0.23).
- The errors are on short function words and on word edges. On Isaak's real takes, which have breaths, emphasis and room tone, a word slice sometimes drags in a bit of the next word ("ready" → "already f-"). Stage 1 tunes this.
- Diphone chains for unseen words are the weak part, and much weaker on real acted speech than on clean Piper speech: the joins are audible and whisper often mishears the word. This is the sentence-mix sound: a style, not a dependable way to say new words.
- A Piper word moved toward the bank pitch roughly halves the error on new words (Isaak: 1.38 → 0.44), but it is plainly another voice. That slot is where voice conversion (kNN-VC/RVC) goes, and it is the main next step for quality.
- Whisper WER is a floor for intelligibility, not a quality score. Listen to `out\<bank>\eval\*.wav`.

### Stage 2: voice conversion + hybrid planner (2026-10-08, measured)

**What was downloaded and installed** (approved by the user):

| item | size | where | licence |
|---|---|---|---|
| kNN-VC source (bshall/knn-vc master) | 0.3 MB | `H:\VoiceSplice\models\knn-vc-src` | MIT |
| WavLM-Large weights (knn-vc release v0.1, from microsoft/unilm) | 1.26 GB | `H:\VoiceSplice\models\WavLM-Large.pt` | MIT |
| prematched HiFi-GAN vocoder (knn-vc v0.1) | 66 MB | `H:\VoiceSplice\models\prematch_g_02500000.pt` | MIT |
| pyworld 0.3.5 (pip, into the `Tools\visualqa` torch venv) | 0.2 MB | venv | MIT (WORLD: modified BSD) |

- The existing CPU torch 2.14.1 is reused, and no new venv was made.
- torchaudio was **not** installed. The PyTorch CPU index stops at torchaudio 2.11 (torchaudio is in maintenance), so there is no build for torch 2.14.1. `vc_knn.py` therefore re-implements the small kNN-VC matcher (cosine top-k, mean, vocode) with scipy resampling and an energy trim. It uses only `wavlm/` and `hifigan/models.py` from upstream.
- Weights load with `torch.load(weights_only=True)`.
- MFA was skipped (it needs conda). It stays optional.

**What was built** (code in `VoiceSplice/`, see its README):

- `vc_knn.py`: the torch-side worker (JSON lines over stdin/stdout). It handles:
  - `matchset`: WavLM layer-6 features of all 518 clips, giving 134,917 frames (45.0 min). They are cached at `H:\VoiceSplice\cache\Isaak.wavlm6.f16.npy` (276 MB). The build takes about 3.5 min on the CPU.
  - `convert`: kNN-VC, k=4.
  - `smooth`: WORLD F0/energy ramps at the joins.
  - `embed`: the speaker check.
- `synth.py` modes:
  - `hybrid` (the new default):
    - It plans with recorded words and n-gram runs as before. Words the bank lacks become one Piper phrase per run (john, pitch-moved to the bank median), converted with kNN-VC.
    - If the line would be choppy, it converts the whole line instead. "Choppy" means more than 50 % new words, or more than 60 % of the pause-less word joins falling between different recordings.
    - It then runs WORLD (pyworld dio/stonemask/cheaptrick/d4c) over ±100 ms around each pause-less join. Log-F0 and log-energy are ramped so that the two sides meet halfway. Only those windows are re-synthesised, and they are crossfaded back into the original.
  - `hybrid_raw`: the same, without the WORLD pass.
  - `vcline`: the whole line from Piper, then kNN-VC.
  - `piper`: plain Piper.
  - The stage-1 modes stay as they were. `splice` is the old `units`.
- `voicesplice.py`:
  - `serve` uses `hybrid` by default. Override it with `mode=` or with a request's `"mode"`.
  - `warm=Isaak` preloads the models.
  - New `matchset <bank>` command.
- `evaluate.py` adds a speaker score `spk`, computed as follows:
  - Each output gets a WavLM layer-6 mean embedding.
  - The embedding is centred on the midpoint between Isaak's matching-set centroid and plain Piper john reading the same lines.
  - The score is the cosine along that axis. +1 means on Isaak's side and −1 means on Piper john's side.
  - It is cheap and crude: an axis between two voices, not speaker verification.

**Results** (Isaak bank, the same 7 test lines as above, whisper small):
- WER is the mean of two full runs. Piper is not deterministic, so single runs of the Piper-based modes move by ±0.1.
- spk is the mean of the two runs.
- Real Isaak clips score spk 0.33 (the ceiling).
- Splice-only keeps 0.41 because it *is* his audio.

| mode | in | mix | new | all | spk | ms/line (warm CPU) |
|---|---|---|---|---|---|---|
| splice (stage 1, new words as diphones) | 0.23 | 0.72 | 1.38 | 0.77 | 0.41 | 100 |
| tts (stage 1, Piper words pitch-moved) | 0.23 | 0.56 | 0.38 | 0.41 | 0.20 | 500 |
| piper (plain Piper john) | 0.09 | 0.06 | 0.12 | 0.09 | −0.71 | 140 |
| vcline (Piper → kNN-VC, whole line) | 0.36 | 0.06 | 0.22 | 0.19 | −0.01 | 2,200 |
| hybrid_raw | 0.23 | 0.08 | 0.22 | 0.17 | 0.12 | 830 |
| **hybrid** (default) | **0.15** | **0.08** | 0.28 | **0.17** | 0.09 | 840 |

The first converted line after a start takes about 12 s while WavLM, HiFi-GAN and the 276 MB matching set load. After that a converted line takes about 1–2 s.

Source-voice sweep (vcline only, one run each):

| source voice | WER at k=4 | WER at k=8 | spk at k=4 | spk at k=8 |
|---|---|---|---|---|
| john | 0.07 | 0.16 | 0.00 | 0.04 |
| hfc_male | 0.10 | 0.09 | 0.07 | 0.09 |
| alan | 0.05 | 0.06 | 0.04 | 0.05 |
| northern_english_male | 0.29 | 0.35 | −0.04 | −0.02 |

All are within the noise except northern_english_male, which is worse. john at k=4 stays the default. hfc_male is the candidate if listening agrees; check its MODEL_CARD/dataset licence first.

What the numbers say:
- **New words and names are now intelligible in a converted voice.**
  - On the "new" lines, WER fell from 1.38 (diphones) to about 0.2–0.3.
  - On the mixed lines, it fell from 0.72 to 0.08.
  - Whole-line conversion is far more intelligible than any splicing that has to cover a gap.
- **The choppiness rule matters more than the conversion of single words.**
  - With the rule off, hybrid kept splicing word by word around the converted phrase, and "mix" stayed at about 0.68 (first run).
  - Every mixed and new test line tripped the rule, so in practice hybrid = "his real words when the line is mostly his own runs, else convert the whole line".
  - The test set never exercised a spliced line with a converted gap. It needs lines that are mostly long runs plus one name.
- **WORLD smoothing helped the spliced lines:** "in" went from 0.23 to 0.15, and "the ship is ready" is no longer heard as "already f-".
- **kNN-VC moves the voice only halfway on this axis.**
  - Converted lines sit at spk ≈ 0, against −0.7 for Piper and +0.33 for real Isaak.
  - The output is made only of Isaak's WavLM frames, so what the score still sees is the source's prosody and pacing plus the 16 kHz HiFi-GAN vocoder. Isaak's acted delivery is not carried over.
  - This is the main remaining quality gap. Listen before trusting it.
- Some failures repeat. "I'll wait here" comes out as "take you a time" through VC, and "Ne'Ban" is heard as "then it". Names need a respelling or phoneme hint for Piper.

Listen: `Documents\VoiceSplice\out\Isaak\final1\*.wav`, `final2\*.wav` (one file per mode and line), and `sweep_*\`.

## 4. In-game side (design only)

### Flow
1. **Pick the line.**
   - GMMaster (U2GM) polls `DialogEngine.GetInstance(Self).Sessions[i].CurNode` every tick. It keeps the last 8 spoken nodes in a new `config array<string> DlgRecent` in `U2GM.ini`: `node|speaker|filename|LongText`.
   - The fork already reads `U2GM.ini` every 10 frames.
   - `gm dlg find <speaker> [text]` can also list nodes from `DialogEngine.Trees`.
2. **Edit with the console open.**
   - The console-open signal exists: the Console.ui patch fires `gm con big|quick 1|0`, which becomes `con=` in `PanelState` (U2GM sketch work).
   - While `con != 0`, the fork's ImGui shows a "Line" strip like the sketch strip. It has the recent lines, an editable text box with the current `LongText`, a speaker/bank tag, and Regenerate / Play / Revert buttons.
   - Input is held through U2Input's `U2InputHoldMouse`, as the panel does now.
3. **Request.**
   - The fork (C++) writes `VOICESPLICE_HOME\requests\eNNNN.json` (`id`, `bank` = the speaker, `node`, UTF-8 `text`) itself. The text never goes through a console command, which avoids the ASCII limits of the sketch notes.
4. **Generate.** `voicesplice.py serve voice_root=<game>\Voice` (like `gm_commit.py --watch`):
   - It splices the line and writes `<game>\Voice\VoiceSplice\eNNNN.ogg`.
   - It answers in `U2GMPanel.txt` in its own q-line session (≥ 2^30, as gm_commit does): `gm dlg set <node> eNNNN <seconds> <text, %XX-escaped>`.
   - Measured: about 0.6 s per line on the CPU, plus the 0.25 s panel poll.
5. **Apply (GMMaster, UnrealScript).**
   - Set `DN = class'DialogEngine'.static.GetNode(Self, Node)`. Node names are converted with `SetPropertyText`, as U2Seven does.
   - Set `DN.LongText = unescaped text`, `DN.Filename = "VoiceSplice.eNNNN"` and `DN.AudioDuration = seconds`. Set `DN.bDoLipSync` per G3.
   - Then `PanelState dlg=eNNNN ok`.
6. **Hear it now.** `gm dlg play <node>` calls `Speaker.PlayVoice(GetOggFilename(DN.Filename), DN.Volume, DN.SoundRadius)` on the speaker's actor (`DialogEngine.StringToActor(DN.Speaker)`), or on the player when the speaker isn't present (radio lines).
7. **Subtitle live.**
   - If the edited node is `CurNode` of a running session, GMMaster re-broadcasts `BroadcastStatusMessage(newText, remaining, DE.SubtitleFont, ..., "DialogSubtitlesHolder", true, WrapX)`. `bClearExisting=true` replaces the old text, as `DisplayText` does.
   - Otherwise the new text shows the next time the node plays.
8. **Keep it.**
   - Edits live in `DialogNode` objects, which are rebuilt from `.dlg` on every level load. So GMMaster keeps `DlgEdits[]` (node|id|seconds|text) in `U2GM.ini` and re-applies them after `DialogEngine` loads the level's trees. This is the same journal idea as the GM ops.
   - Revert = drop the entry and restore the stored original `Filename`/`LongText`.
   - A later "commit" step can write an override `.dlg` set into a mod folder, if `LoadDialogFiles(<dir>)` can load extra directories (guess G4).

### Lip sync (optional)
U2 lip sync is one animation per line, named after the file. The bank already has phone times for every spliced unit, so a spliced line has a phone track for free (like Source's VDAT).
- **Cheap:** turn `bDoLipSync` off and rely on talk gestures.
- **Better:** GMMaster drives a jaw/viseme channel from a `<id>.phones` sidecar (time, viseme). This needs per-bone posing, which the U2Wardrobe notes say is blocked in script, so it would be a fork-side feature. Park it.

## 5. Staged plan and estimates

| stage | what | estimate | state |
|---|---|---|---|
| 0 | offline prototype: corpus from U2 files, whisper + DTW alignment, bank, unit selection, diphones, splice, Ogg, round-trip WER, request watcher | — | **done** (this note) |
| 1 | listen pass with the user on Isaak/Aida lines; tune costs (pause lengths, function-word choice, pitch); add a `bank.py` blacklist for bad units; bank Aida, Neban, Meyer | 0.5 day | next |
| 2 | downloads + kNN-VC (Piper → Isaak) + hybrid planner + WORLD join smoothing + speaker score (§3, stage 2) | 1 day | **done** 2026-10-08 |
| 2b | next quality steps: listen pass; respelling/phoneme hints for names (Ne'Ban, Skaarj); a bigger test set (≥ 30 lines) including "mostly runs + one name" lines; tune the choppiness thresholds by ear; carry Isaak's prosody (pitch contour from a similar recorded line, WORLD duration fit) into converted lines; try hfc_male as the source; RVC on the 45 min if kNN-VC stays at "halfway" | 1–2 days | next |
| 3 | game hookup (needs the unreal chat for installs/restarts): GMMaster `gm dlg set/play/find/revert`, `DlgRecent`/`DlgEdits` journal, subtitle re-broadcast; serve with `voice_root=<game>\Voice`; check G1–G3 with one hand-made Ogg first | 1–1.5 days | |
| 4 | fork ImGui "Line" strip on `con != 0`: recent lines, text box, Regenerate/Play/Revert, request JSON writer, status from `PanelState` | 1 day | |
| 5 | voice conversion: kNN-VC part done in stage 2 (`mode=hybrid/vcline`); left: compare with RVC trained on Isaak's 45 min (GPU slot) | 1 day | kNN-VC done |
| 6 | persistence/commit: re-apply edits on level load, optional override `.dlg` folder (G4), export/import of an edit list | 0.5 day | |
| 7 | (optional) lip-sync from phone tracks in the fork | 2+ days | parked |

Downloads:
- Done in stage 2: pyworld, kNN-VC, WavLM-Large and the prematched vocoder (1.33 GB on H:). The existing CPU torch is reused.
- Still optional:
  - RVC and its HuBERT/RMVPE weights (MIT, a GPU slot for training).
  - MFA (conda, about 1 GB).
  - A torchaudio build, only if a future torch has one.

## 6. Rules kept

- The game folder was only read: the `.dlg` files and `Voice\*.ogg`.
- Clips, banks, transcripts and outputs are in `Documents\VoiceSplice\` (outside git). The tool folder has a `.gitignore` for audio and jsonl.
- `test_corpus.txt` and the evaluation lines are original text written for the tool.
- Nothing was committed.
