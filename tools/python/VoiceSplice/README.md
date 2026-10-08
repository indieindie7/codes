# VoiceSplice

Re-voices an edited dialogue line in the character's own voice (Unreal II first). It splices words he really said, and turns new words or names into his voice with Piper TTS plus kNN-VC voice conversion. Design, results and the game hookup plan are in `games/research_notes/Dialogue edit and voice splicing/design.md`.

This folder holds code only. Game audio, extracted text, banks, outputs, model weights and caches never go into git (see `.gitignore`).

| where | what |
|---|---|
| `%USERPROFILE%\Documents\VoiceSplice` (`VOICESPLICE_HOME`) | banks (clips, alignments, `bank.json`), `out\`, `requests\`, `voice_out\` |
| `H:\VoiceSplice\models` (`VOICESPLICE_MODELS`) | `WavLM-Large.pt` (1.26 GB), `prematch_g_02500000.pt` (66 MB), `knn-vc-src\` (bshall/knn-vc source) |
| `H:\VoiceSplice\cache` (`VOICESPLICE_CACHE`) | `<bank>.wavlm6.f16.npy`: the WavLM layer-6 matching set (Isaak: 135k frames, 276 MB) |

## Two Pythons

- `py -3.13` runs the main pipeline: numpy, scipy and piper-tts.
- `Documents\Tools\visualqa\Scripts\python.exe` (`VOICESPLICE_VC_PY`) runs `vc_knn.py`. It has CPU torch 2.14.1, scipy and pyworld 0.3.5.
- `synth.py` starts `vc_knn.py serve` as a JSON-lines worker on the first line that needs it.
- torchaudio is not used: no build exists for torch 2.14. The kNN-VC matcher is reimplemented in `vc_knn.py`, and only `wavlm/` and `hifigan/models.py` come from the upstream source.

## Use

```
py -3.13 voicesplice.py build u2 Isaak          # corpus + whisper/DTW alignment + bank (once, ~45 min CPU)
py -3.13 voicesplice.py matchset Isaak          # WavLM features for kNN-VC (once, ~4 min)
py -3.13 voicesplice.py say Isaak "The Skaarj are gathering near the colony gates." ogg=out.ogg [mode=...]
py -3.13 voicesplice.py serve [voice_root=<game>\Voice] [mode=...] [warm=Isaak]
py -3.13 evaluate.py Isaak [modes=splice,tts,piper,vcline,hybrid_raw,hybrid] [tag=eval]
```

Modes (`synth.MODES`; the default is `hybrid`):

- `hybrid`:
  - Keeps runs of words he really said.
  - Renders new words as one Piper phrase, converted with kNN-VC.
  - Applies WORLD F0/energy ramps across the joins.
  - Converts the whole line instead when splicing would be choppy: more than 50 % new words, or more than 60 % pause-less joins between different recordings.
- `hybrid_raw`: `hybrid` without the WORLD pass.
- `vcline`: the whole line from Piper, then kNN-VC.
- `splice`, `tts`, `phones`: the stage-1 planners.
- `piper`: plain Piper.

A serve request can carry `"mode"`.

Speed (CPU):
- A spliced line takes about 0.1 s.
- A converted line takes about 1–2 s once warm.
- The first converted line takes about 12 s while the models load. Use `warm=`.

## dlgcut.py: cut a line at its own pauses

`py -3.13 dlgcut.py show <Node>` lists the line's sentences and the pauses matched to them. `py -3.13 dlgcut.py cut <Node> keep=3-` keeps sentences 3 to the end and writes a game-format Ogg to `<game>\Voice\U2Cut\<Group>\<Node>.ogg`. It also prints a JSON line with the dotted name the game plays, the kept text, the length, and what whisper heard plus a word match.

The tool never edits the game's own voice files. Used by U2Sanctuary/open/make_cuts.py.

## Licences of what was downloaded

| item | source | licence |
|---|---|---|
| kNN-VC code | github.com/bshall/knn-vc (master) | MIT (Stellenbosch University MediaLab) |
| WavLM-Large weights | knn-vc release v0.1 (from microsoft/unilm WavLM) | MIT (Microsoft; header in `wavlm/WavLM.py`) |
| prematched HiFi-GAN vocoder | knn-vc release v0.1 | MIT (same repo) |
| pyworld 0.3.5 | PyPI | MIT (WORLD itself: modified BSD) |

Piper is GPL-3. Each Piper voice has its own dataset licence, so check its MODEL_CARD before any audio leaves this PC. The converted audio is built from the game's own recordings and stays local, like every bank.

Not installed:
- Montreal Forced Aligner. It is optional and needs conda.
- torchaudio. There is no build matching torch 2.14.1.
