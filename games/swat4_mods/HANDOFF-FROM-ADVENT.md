# SWAT 4 modding: hand-off from the Advent Rising chat (2026-10-17)

The user (10-17): "we will be archiving this project and just migrating all of our techstack to swat 4 modding,
the game is good but its time to start modding swat 4 as a focus."

Advent Rising modding is **archived**. SWAT 4 is now the main modding project, replacing the earlier plan of
a short AI study first (memory `ue2-next-games-plan`). Republic Commando is still queued after it.

## First steps for the SWAT 4 chat
1. Ask the user where SWAT 4 is installed (and which edition: Gold / The Stetchkov Syndicate, Steam or GOG).
   Do not download or install anything over 2 GB without asking; no multi-GB installs on C:.
2. Recon, done the Devastation way (skill `devastation-re`; `C:\re\devastation\NOTES.md` is the template):
   engine build, `System\*.u` package list, how scripts are loaded, whether an official SDK / UnrealEd /
   script source is available, D3D version, physics middleware. **Everything below marked "check" is
   unverified for SWAT 4.** Write findings into `games/swat4_mods/NOTES.md` as you go.
3. Read the AI first (officers + suspects: compliance, morale, surrender, flee, fire), as the user asked
   (10-16): "analyze the ais a little bit like devastation, and see what happens if we try porting our
   ai research from here to there".
4. Then pick the first real mod with the user.

## Techstack to carry over (all in `games/advent_rising_mods/`)
| Piece | Where | Carries to SWAT 4? |
|---|---|---|
| Creature minds: traits + fear/anger/pressure/stress, suppression, cover, fall back, panic, charge, squad flanks, hound packs, needs/ads, path costs | `AI-MINDS-DESIGN.md`, `AdventMod/Classes/ModMind*.uc` | Method yes; class hooks must be redone on SWAT 4's AI (it has its own tactical AI; check) |
| Enemy AI research (DOOM tokens, F.E.A.R. GOAP, Horizon HTN, L4D director, Halo, Alien: Isolation) | `games/reports/Game enemy AI architectures.md` | Yes, engine-neutral |
| Tension/director | `AdventMod/TENSION.md` | Method yes |
| Gore: decals, wall runs, drips, streaks, gibs, blood drops, plasma sears, bullet pass-through + exit drops | skill `gore-system`; `GORE-DESIGN.md`; `AdventMod/PLASMA-AND-PENETRATION.md`; `Classes/ModGore.uc`, `ModBloodDrop.uc`, `ModSear.uc` | UnrealScript ports with changes (bullet penetration fits SWAT 4 well; plasma does not) |
| Ragdoll / Karma work | skill `advent-mod` tree/03; memory `advent-physics-plan` | Only if SWAT 4 uses Karma (check; may be Havok) |
| Script compile launcher (from the SWRC-CT framework) | `AdventUCC/` (README.md, src) | Likely, after adjusting for SWAT 4's UCC (check) |
| Native injection DLL | `AdventMod/native/`, `System/AdventNative.dll` | Method yes; offsets are Advent-only |
| Pilot test driver (off-screen scripted runs, FPS line, gore log) | `AdventMod/test_run.ps1`; skill `advent-mod` tree/02 | Method yes. Gotcha: run with `& ./test_run.ps1` inside PowerShell (`-File` flattens arrays) |
| Shader layer (d3d8to9 fork + U2Shaders: PCSS, SSS, char_skin, parallax) | fork branch `gi-cascades`; `AdventMod/U2Shaders/`; skills `u2testhub`, `skin-shading`, `u2-no-dgvoodoo` | Only if SWAT 4 is D3D8 (check; if D3D9, a d3d9 proxy is needed instead) |
| Animation tools (kimodo retarget, jiggle rig/sim, clip sheets) | `tools/` | Yes for animation work |
| UE2 tool chain (UnrealEd bridge, input hook, Ghidra editor RE) | skills `ue2-script-tools`, `u2edbridge`, `u2input`, `u2-ghidra-editor` | Method yes |
| The modding loop (research, export, pilot, patch, measure, ship) | skill `old-game-mod-loop`; memory `old-game-modding-workflow` | Yes |
| Release rules (zip layout, README, Nexus) | skill `mod-release`; `AdventMod/RELEASE.md`, `NEXUS.md` | Yes |

## Rules that still hold
- Never commit game assets, decompiled code or leaked source. Mods are GPL, non-commercial; no GitHub links in Nexus text.
- No sign-ins or credentials; Nexus/YouTube uploads are the user's job.
- Launch the game hidden or minimized, never in front of the user's typing. No TTS or AI voices.
- The GPU token comes from the "Windows support" chat.
- Subagents are Sonnet only. Read cheaply.
- Push wt9 with `git push origin HEAD:master`; if it is rejected, merge origin/master. Never commit `research/karma-internals.md`.
- Avalon is a private commercial repo: method and numbers only, never GPL code.

## Advent loose ends (left as they are)
- The user never checked by eye the plasma sear glow size and the wall spray behind a target (PLASMA-AND-PENETRATION.md, last line).
- `AdventMod/System/AdventNative.dll` has a local rebuild (10-16 19:26, same size) that is not committed.
- `research/karma-internals.md` has local edits (never commit).
- Last commits: wt9 f47c3ec (merge 013176e). Way back in: `games/advent_rising_mods/HANDOFF.md`.
