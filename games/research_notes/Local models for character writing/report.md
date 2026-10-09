# Local language models for character writing (Avalon creative team)

Research date: 2026-10-09 (a research agent; nothing was installed or downloaded). The machine: RTX 4070 Ti (12 GB VRAM,
~500 GB/s), 32 GB DDR4, i5-10600K (6 cores), Windows 10.
- Leaderboard numbers come from eqbench.com's data files as read that day; the page shows no "as of" date.
- Model facts come from the Hugging Face model cards and API.
- **All speeds are estimates, not measurements.**

Use case: rewriting the binder's characters so they act as if immersed in the setting, with their own goals, routines
and conditions. Possibly also 10-30 citizens running as agents in a simulated town for a few in-game days, with the
writer as drama manager reading the event log.

## Summary
1. **Best quality that runs here:**
   - **Qwen3.8-27B** (Apache, Aug 2026): EQ-Bench Creative Writing v3 Elo 1671.
   - **Meta Muse-Glimmer-30B** (Apache, Aug 2026): Elo 1798.

   On short pieces they score about where Claude Sonnet 4.5 / Opus 4.6 did. On 12 GB they only run part-offloaded
   to RAM, at about 4-15 tok/s.
2. **Best balance for this card:** **Gemma 4 26B-A4B**, a mixture-of-experts model with ~4B active parameters per
   token that offloads well (~20-35 tok/s). Run it as-is or as an RP tune:
   - **TheDrummer Orion-26B-A4B-v1.1**;
   - **Gryphe Pantheon-Reasoning-26B-A4B-1.1-V2**, trained to think about the character before answering.

   gemma_4_26b also came first on community votes in the small RP-Bench (Apr 2026).
3. **Cheap high-volume town simulation:** **Gemma 4 12B, QAT q4_0 or Q4_K_M (~7 GB), all on the GPU.** About 55-75
   tok/s for one request, ~150-300 tok/s across 6-8 parallel slots. A 20-agent x 3-day run is ~1-2 hours.
4. **Runner:** **llama.cpp `llama-server`** is the only one with all four needs:
   - parallel slots;
   - prompt caching;
   - JSON-schema / grammar output;
   - MoE expert offload (`--n-cpu-moe`).

   LM Studio is the easiest for trying models. KoboldCpp + SillyTavern suits hands-on RP. TabbyAPI/ExLlamaV3 is
   fastest but can't use system RAM.
5. **The gap to frontier models is real:**

   | Test | 12 GB-friendly local models | Frontier |
   |---|---|---|
   | Creative Writing v3 Elo | ~1290-1305 | ~2130 (Claude Opus 5) |
   | 8-chapter Longform | ~49-57 | 80-86 |

6. **So:** the writer / drama manager, final shipped dialogue and long continuous story go to a frontier model.
   Local models do the volume.
7. **Byte-level models** (Ai2 Bolmo 1B/7B, BLT, EvaByte, MambaByte, H-Net) are research checkpoints: no chat or RP
   tuning, no creative-writing scores, no runner support. Not usable here.
8. **Old favourites are outclassed:** Mistral Nemo 12B (881), Mistral Small 3.2 (1255). gpt-oss-20b is poor for
   writing (666).
9. **Licences:** nearly all Apache 2.0, Gemma 4 included. Odd ones are listed in section 6.
10. **Setup:**
    - Qwen3.8-27B IQ3_XS (or Pantheon / Orion Q4_K_M) for character rewriting;
    - Gemma 4 12B Q4 in llama-server with a JSON schema and a shared cached prompt prefix for the agents;
    - a frontier model once per in-game day as drama manager.

## 1. Models that fit this machine

Score columns: CW v3 = EQ-Bench Creative Writing v3 Elo. LF = EQ-Bench Longform (0-100). Higher is better. "-" =
not tested.

| Model (date) | Type / size | Quant for 12 GB VRAM + 32 GB RAM | Est. speed | Context | License | CW v3 | LF | Thinking |
|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B (2026-08) | dense 27B | IQ3_XS 12.8 GB (mostly GPU) / Q4_K_M 17.4 GB | IQ3 ~10-15 tok/s; Q4 ~4-7 | 262K | Apache 2.0 | 1671 | 53.3 | yes |
| Muse-Glimmer-30B (Meta, 2026-08) | dense ~29.6B | Q4_K_M 16.8 GB (+1.6 GB draft) | ~4-6 (draft may add 1.5-2x) | 131K | Apache 2.0 | 1798 | - | yes (effort in system prompt) |
| Gemma 4 31B-it (2026-03) | dense 31B | IQ3_XS 13.8 / Q4_K_M 19.6 GB | ~3-8 | 256K | Apache 2.0 | 1368 | 56.5 | yes |
| Gemma 4 26B-A4B-it (2026-03) | MoE 25.2B / 3.8B active | Q4_K_M 17.0 GB, experts in RAM | ~20-35 | 256K | Apache 2.0 | 1305 | 50.7 | yes |
| Gemma 4 12B-it (2026-05/06) | dense 12B | Q4_K_M 7.1 / QAT q4_0 7.0 / Q5_K_M 8.4 GB, all on GPU | ~55-75 single; ~150-300 batched | 256K (8-32K practical with slots) | Apache 2.0 | 1289 | 48.7 | yes |
| Qwen3.6-35B-A3B (2026-04) | MoE 35B / 3B active | Q4_K_M 22.3 GB, experts in RAM | ~20-30 | 262K | Apache 2.0 | - | - | yes |
| Nemotron-3.5-Lightning-30B-A3B (2026-08) | Mamba/MoE, 3B active | ~17-18 GB 4-bit, offloaded | ~25-40 | 1M | OpenMDW-1.1 | 1280 | - | yes |
| gpt-oss-20b (2025-08) | MoE 21B / 3.6B active | ~13 GB | fast | 128K | Apache 2.0 | 666 | 21.2 | yes |

**Community RP fine-tunes** (not on EQ-Bench; the praise is the model cards' own, so try them rather than trust them):
- **TheDrummer/Orion-26B-A4B-v1.1** (2026-09, Gemma 4 26B-A4B): an RP/creative tune at MoE speed, thinking or not. The
  best fit for 12 GB.
- **Gryphe/Pantheon-Reasoning-26B-A4B-1.1-V2** (2026-09, Apache): reasons about tone, beats and the character's
  reaction before writing. About 38 % of its data is text adventure, a strong match for "act as if immersed".
- **TheDrummer/Artemis-31B-v1.2** (2026-09, Gemma 4 31B): claims no personality bleed across characters at ~32K, and
  scenario adherence to 20K. Slow here.
- **LatitudeGames/Equinox-31B** (2026-05, Apache): by the AI Dungeon team; dark adventure plus slice-of-life depth.
  Slow here.
- Others: zerofata/G4-MeroMero-v2-31B, allura-org/Qwen3.8-27B-Dominatrix (tagged NSFW), ArliAI Qwen3.5 RpRMax.

**How the speeds were estimated:**
- Generation is limited by memory bandwidth: ~500 GB/s divided by the model's size.
- Each GB that spills into DDR4 (~35-40 GB/s) costs ~25-30 ms per token.
- MoE models read only their active experts, so they stay fast with the experts in RAM.
- Leave ~1.5-3 GB of VRAM for the KV cache.

## 2. Benchmarks and the gap

**EQ-Bench Creative Writing v3** (an LLM judge; rubric plus Elo; 140 models):

| Group | Models (Elo) |
|---|---|
| Frontier | gpt-6-astra 2173, Claude Opus 5 2133 |
| Huge open-weight | Kimi-K3 2082, GLM-5.3 2075 |
| Local-sized, best | Muse-Glimmer-30B 1798 (~Claude Opus 4.6's 1809), Qwen3.8-27B 1671 (~Claude Sonnet 4.5's 1678) |
| Local-sized, others | Gemma 4 31B 1368, Gemma 4 26B-A4B 1305, Gemma 4 12B 1289, Mistral Small 3.2 1255, Mistral Nemo 881, gpt-oss-20b 666 |

**EQ-Bench Longform** (an 8-chapter novella, the best test of long-run consistency):

| Group | Models (score) |
|---|---|
| Frontier | Claude Opus 5 86.3, Claude Fable 5 83.0, Kimi-K3 79.6 |
| Local-sized | Gemma 4 31B 56.5, Qwen3.8-27B 53.3, Gemma 4 26B-A4B 50.7, Gemma 4 12B 48.7 |

**Verdict:** on short scenes and bios, the best local 27-30B models now match late-2025 frontier models. On long-form
consistency the gap is ~30 points. The 12 GB-friendly models write decently but generically.

**Boards disagree.** A Digital Applied comparison (2026-08-31) found one model 1st on arena.ai's human votes and 6th
on EQ-Bench. Treat ranks as approximate.

**RP-specific evals are weak or young:**
- **RP-Bench** (2026-04/05, 12 models): tests consistency, user agency, lorebook use and temporal reasoning.
  gemma_4_26b led the community Elo; Claude Opus 4.6 led the judge Elo. A single snapshot with no paper.
- **UGI** mostly measures how uncensored a model is.
- **PingPong, RPEval, RMTBench, CharacterEval** are good methods with no current leaderboards.
- **BenchLM's "roleplay" page** uses stand-in scores. Ignore it.

## 3. Byte-level models ("bits instead of tokens")
Not usable for this.
- **Ai2 Bolmo 1B/7B** (Dec 2025; paper v2 Feb 2026; Stage1 checkpoints Aug 2026) is the most serious current effort:
  OLMo models converted to bytes. They are research checkpoints with no chat or RP tuning, no creative scores and no
  runner support.
- **BLT, EvaByte (6.5B), MambaByte and H-Net** are research models, well behind the 2026 Qwen and Gemma models on
  writing.
- Bytes help spelling and noisy text, not character voice. The Bolmo authors note that leading LLMs still use
  subword tokens.

## 4. Runners on Windows
Versions seen 2026-10: llama.cpp v0.6.0 (10-05), Ollama v0.40.2 (10-08), KoboldCpp v1.122.1 (09-26), ExLlamaV3 v1.6.0
(10-07), TabbyAPI (active), SillyTavern 1.19.0.
- **llama.cpp llama-server: best for the agent simulation.**
  - OpenAI-compatible server.
  - `-np N` parallel slots with continuous batching (the context is split across slots).
  - Prompt cache and slot save/restore.
  - `response_format` JSON schema and GBNF grammars.
  - `--n-cpu-moe` / `-ot` expert offload.
- **LM Studio 0.4+:** concurrent predictions (default 4), structured output, GUI offload. Easiest for trying models;
  not open source.
- **Ollama:** `OLLAMA_NUM_PARALLEL` (set it yourself) and `format` takes a JSON schema. Less control over offload.
  Fine for a prototype.
- **KoboldCpp:** OpenAI API, grammars, context-shift caching; queued requests with little batching. Best with
  SillyTavern for single-player RP.
- **TabbyAPI + ExLlamaV3:** real batching and the fastest, but the model must fit in VRAM, so no 27-31B here.
- **vLLM:** WSL2 only on Windows, VRAM-bound. Skip it.

## 5. Recommendation

**(a) Quality character rewriting (low volume)**
- **Qwen3.8-27B IQ3_XS** in llama-server (~10-15 tok/s): think at medium effort, then a non-thinking pass (the card
  suggests presence_penalty 1.5 for non-thinking).
- Alternative: **Muse-Glimmer-30B Q4_K_M** in overnight batches (~4-6 tok/s).
- Faster: **Pantheon-Reasoning-26B-A4B-V2** or **Orion-26B-A4B-v1.1**, Q4_K_M with experts in RAM (~20-35 tok/s).

**(b) Agent simulation (10-30 citizens)**
- **Gemma 4 12B QAT q4_0 / Q4_K_M**, all on the GPU, llama-server `-np 6-8`, ~4-8K context per slot, thinking off.
- Keep the shared system prompt (world rules, schedule format) identical and put per-agent details last, so the cache
  reuses the prefix.
- JSON-schema output: action, target, location, line, memory note.
- Budget: 20 agents x 3 days x ~100 decisions x ~150 tokens ≈ 0.9M tokens, ~1-2 h.
- If it reads too flat, use Gemma 4 26B-A4B / Orion (slower; batching helps less with experts in RAM).

**Use a frontier API for:**
- the drama manager reading the event log (long context and plot judgement, where local models lose ~30 Longform
  points);
- final shipped dialogue;
- anything over ~8-10K tokens of one continuous story.

A good split: local models for the citizens' turns, one frontier call per in-game day to summarise and steer.

## 6. Licences
- **Apache 2.0:** Gemma 4 (all sizes; this replaced the older Gemma terms), Qwen3.8-27B, Qwen3.6-35B-A3B,
  Muse-Glimmer-30B (no Llama-style user clause), gpt-oss, Pantheon, Equinox and MeroMero.
- **Odd ones:**
  - TheDrummer's Orion and Artemis cards declare no licence; they inherit Apache 2.0 from Gemma 4.
  - Qwen3.8-Flash-Next uses a custom qwen-community-1.0 licence (and is too big at 180B).
  - Nemotron 3.5 Lightning uses OpenMDW-1.1, permissive but uncommon.
  - GLM-5.3's "MIT" label on arena.ai conflicts with its model card.
- **RP tunes** are often trained on scraped data. Fine for non-commercial mods; don't present their outputs as
  licensed assets.
- These are text-only models, so the no-AI-voices rule is not affected.

## Sources
- https://eqbench.com/creative_writing.html (data file creative_writing.js, read 2026-10-09)
- https://eqbench.com/creative_writing_longform.html
- https://www.digitalapplied.com/blog/which-ai-model-writes-best-leaderboards-disagree (2026-08-31)
- https://benchmarklist.com/benchmarks/roleplay_bench/
- https://huggingface.co/spaces/DontPlanToEnd/UGI-Leaderboard
- https://github.com/IlyaGusev/ping_pong_bench · https://huggingface.co/papers/2505.13157 · https://arxiv.org/html/2507.20352v2
- https://huggingface.co/Qwen/Qwen3.8-27B · https://huggingface.co/bartowski/Qwen3.8-27B-GGUF
- https://huggingface.co/meta-models/Muse-Glimmer-30B · https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF
- https://huggingface.co/google/gemma-4-26B-A4B-it · https://huggingface.co/google/gemma-4-31B-it · https://huggingface.co/google/gemma-4-12B-it · https://huggingface.co/unsloth/gemma-4-12b-it-GGUF · https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B · https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4
- https://huggingface.co/TheDrummer/Orion-26B-A4B-v1.1 · https://huggingface.co/TheDrummer/Artemis-31B-v1.2 · https://huggingface.co/Gryphe/Pantheon-Reasoning-26B-A4B-1.1-V2 · https://huggingface.co/LatitudeGames/Equinox-31B · https://huggingface.co/zerofata/G4-MeroMero-v2-31B
- https://allenai.org/blog/bolmo · https://arxiv.org/abs/2512.15586 · https://huggingface.co/allenai/Bolmo-7B-Stage1
- https://github.com/ggml-org/llama.cpp/releases · https://huggingface.co/blog/Doctor-Shotgun/llamacpp-moe-offload-guide
- https://lmstudio.ai/docs/app/advanced/parallel-requests · https://lmstudio.ai/blog/0.4.0 · https://registry.ollama.ai/blog/structured-outputs
- https://github.com/LostRuins/koboldcpp · https://github.com/theroyallab/tabbyAPI · https://github.com/turboderp-org/exllamav3
