# Session notes: Unreal II modding, Sep 28 – Oct 1, 2026

Everything from one long Claude Code session, on branch `claude/pc-integration-notepad-6gp2ac`
(not merged into `master`). Nothing here has run inside Unreal II yet: the PC was off for the
whole session, so each item says how far it has been checked.

## Waiting on the PC (one sitting covers all of it)

1. **New `d3d8.dll`:** copy `tools/C/U2Shaders/d3d8-mingw.dll` over the game's `System\d3d8.dll`
   (keep the old one as a backup). It adds the shadow tint, the probes and the decal rule.
2. **Character + depth probe:** add `charprobe=1` to `System\U2Shaders.ini`, run
   `python u2pilot.py scripts/char_probe.txt --background`, then collect
   `System\U2Shaders\dump\chars.txt`, the `depth probe:` lines in `U2Shaders.log` and the
   `PilotDriver: dump` lines in `Unreal2.log`.
3. **Destruction probe:** copy `games/unreal2_mods/U2Destruct/Source/U2Destruct` into the game
   folder, add `EditPackages=U2Destruct`, run `UCC make`, then
   `python u2pilot.py scripts/destruct_probe.txt --background`; collect the `DestructProbe:` lines.
4. **Floor-fitted shadow fade:** rebuild `U2SoftShadows` with `UCC make`, look at characters on
   stairs and slopes (`bFitToFloor=False` turns it off to compare).
5. **Bullet holes:** run once with `log=1`, shoot a wall, find the decal textures in
   `System\U2Shaders\dump\`, add `decal=<hash> decal_parallax.hlsl`, tune `DEPTH`.
6. **Light re-bake test** on one map through U2EdBridge (not written yet: needs the exact editor
   commands checked first).
7. **U2FairFights additions:** rebuild with `UCC make` (the `.u` in `System` predates them), then
   check the `FairFights: kill beat / heavy hit beat / hurt kick` lines in `Unreal2.log`.
8. **Post-processing:** with the new dll, add `post=1` and `postsplit=1` to `U2Shaders.ini`, copy
   `post_*.hlsl` into `System\U2Shaders\`, and check that the HUD stays crisp (left half
   processed, right half not); then tune `bloom=`, `grade=`, `colour=`, `sharpen=`.

Before that: set up a way back in after reboots (Chrome Remote Desktop, or Claude Code starting
with Windows). See "PC access" below.

## What was built

### U2Gore (`games/unreal2_mods/U2Gore`): sketch, not compiled

Brutal Doom-style gore for Unreal II, in the same pattern as U2SoftShadows (mutator → one
manager per level → capped arrays of spawned actors).

| File | Does |
|---|---|
| `U2GoreMutator.uc` | spawns the manager; `MutatorTakeDamage` sends every hit to it |
| `U2GoreManager.uc` | blood decal on every hit, gibs when overkill ≥ `GibThreshold`, caps live gibs/decals/spurts, one hit controller per pawn |
| `U2Gib.uc`, `U2BloodDecal.uc`, `U2BloodSpurt.uc` | the spawned pieces (lifespan, fade, randomised size/spin) |
| `U2HitReactionController.uc` | partial ragdoll: loosens the hit bone for a while, full ragdoll on death |
| `U2GoreHookExample.uc` | fallback: the same hooks via `Died()`/`TakeDamage` in a Pawn subclass |

Enemy tiers: pawns with `HealthMax <= WeakHealthThreshold` (100) stagger on hits; tougher ones
only show the blood spurt, so they keep their threat. Tunables in `U2GoreManager` defaults.

Unverified: whether Unreal II calls `MutatorTakeDamage` like UT2004 does; base classes `Gib`,
`Decal`, `Emitter`; the per-bone Karma calls are stubs (`EnableBonePhysics`/`DisableBonePhysics`).
Next step for it: switch to the `GameRules` hooks (`NetDamage`, `PreventDeath`), which
U2FairFights and U2Enemies already use and have tested in Unreal II.

### U2FairFights: stakes, heavy hits, flinch

U2FairFights already had kill hitstop, per-shot view kick, hit ticks and more ragdolls (tested).
Added (not compiled yet; only calls the mod already uses):
- the kill beat grows with the stakes: x (enemy's starting health / 100) up to `KillToughMax`,
  and x `CloseCallMul` when you're below `CloseCallHealth` of your health;
- a shorter beat for a heavy hit that doesn't kill (`HeavyHitDamage`, `HeavyHitstop`,
  rate-limited by `HeavyHitCooldown`);
- the view flinches when you take damage (`HurtKick` per point, up to `HurtKickMax`).

### U2SoftShadows: fade fitted to the floor

`SSLightShadow.FitTipDepth` traces from the head along the light to where the head's shadow
really lands (at most every 0.1 s, eased), instead of assuming flat ground at the feet, which
cut shadows short or ran them long on stairs, slopes and ledges. Config: `bFitToFloor`. Not
compiled (needs the game's packages).

### U2Shaders (`tools/C/U2Shaders`): the d3d8to9 fork

- **`hlslcheck.sh`:** compiles the shaders with Microsoft's real `d3dcompiler_47` (as the fork
  does at runtime: `ps_2_a`, then `ps_2_b`) and prints the budget used. Runs natively in Git
  Bash or under Wine on Linux (fetches both fxc builds, uses whichever runs).
- **`shadowtint=R G B`:** per-channel shadow colour for the PCSS shadows (`1 1 1` = grey as
  before; e.g. `1.1 1.0 0.75` for cool shadows). Falls back to grey with an older dll.
- **`charprobe=1`:** logs how each opaque on-screen draw (characters) is lit: D3D lights,
  material, ambient, skinning, texture stages, and whether shadow silhouettes were drawn first
  that frame. Also checks whether scene depth can be read as a texture (INTZ/DF24/DF16/RAWZ).
- **`decal=<hash> file` + `decal_parallax.hlsl`:** bullet holes that look sunken into the wall
  (parallax occlusion, F.E.A.R.-style); no lights needed, works on projector decals and on
  walls without normals; keeps the decal's own blending so overlapping holes still layer.
- **`post=1`:** bloom, sharpening, exposure, colour balance, saturation, contrast and vignette on
  the finished 3D frame, applied right before the first 2D draw so the HUD stays crisp (or at
  Present when there is no HUD); every device state is restored afterwards. Tested under Wine:
  a bright panel glows, the HUD box and crosshair stay sharp. `postsplit=1` to compare.
- **`build-mingw.sh`:** builds `d3d8.dll` without Visual Studio. `d3d8-mingw.dll` is that build.
- **`test/run.sh`:** runs the dll outside the game under 32-bit Wine (silhouette, lit wall,
  decal). It confirmed the probes log correctly and the decal shader compiles and draws; it
  also caught a staircase artifact in the first decal version, now fixed.

Shader budgets now: `pcss_proj` 356/512 slots, **31/32 temp registers** (`ps_2_b`, the limit
any further penumbra change must fit); `decal_parallax` 178/512 (`ps_2_a`).

### U2Destruct (`games/unreal2_mods/U2Destruct`): probe, not compiled

Tests on the nearest solid map prop: can it be hidden and its collision turned off, can a
solid movable copy replace it, does Karma debris made from its mesh fall and land. All three
are needed for Black-style destruction of map props.

### U2Pilot scripts

`scripts/char_probe.txt`, `scripts/destruct_probe.txt`.

## Design notes

### Gore (from Brutal Doom)
Extra "extreme death" states when overkill passes a threshold; separate physics gibs with
randomised velocity; blood decals aligned to the hit surface; corpses stay shootable; counts
capped so it doesn't tank performance. Unreal II already has `Died()`, gib actors and decals,
so the mod extends them.

### Partial ragdoll ("semi-dynamic", like GTA IV)
GTA IV's Euphoria simulates muscles and balance while alive: out of reach for a mod. Doable:
the shot bone goes physics-driven for a moment while the rest keeps animating, then a full
Karma ragdoll on death.

### Reaction time, arena size, speed
- Reaction margin: `M = (T_tell + T_travel) − (T_react + T_motor)`.
  `T_travel = D / V_closing` (≈ 0 for hitscan); `T_react` ≈ 0.2–0.25 s for a reflex,
  0.4–0.6 s with a decision; `T_motor` includes input lag and the pawn's acceleration.
  `M > 0` fair, `≈ 0` frame-perfect, `< 0` unavoidable.
- The real knob is `D / V` (time to cross), not raw distance: doubling speed halves the arena.
- Strafe dodging works when `V_lateral × T_travel` exceeds the weapon's hit width.
- `TTK = HP / DPS`; a smaller arena shortens the player's effective TTK without touching damage.

### Feel and reward
- "Kinesthetic feel" (preferred term over "juiciness"): the coupling between input and
  response.
- The pleasure of victory is mostly **self-validation** (having been at risk and come
  through, proving something), more than mastery feedback alone, which can happen with no
  stakes. Design consequence: gate the payoff behind real risk (close calls, difficulty spikes
  before the kill), not just polish on the hit feedback.
- Weak enemies stagger and spurt on every hit: continuous proof of damage landing.

### References on game feel
Steve Swink, *Game Feel* (2009); Hicks et al., "Juicy Game Design" (CHI PLAY); Jan Willem
Nijman (Vlambeer), "The Art of Screenshake" (GDC talk). Search terms: "game feel",
"juiciness", venues CHI PLAY, FDG, DiGRA.

### Unreal lore
Unreal (1998): Prisoner 849 on Na Pali, Skaarj vs Nali. Unreal II (2003): John Dalton, the
TCA, artifacts, Skaarj and Drakk. Unreal Tournament: the Liandri tournament; UT2004's Xan
Kriegor campaign; UT3's Necris. No well-known official novels or comics (unlike Doom).

### Shadows
- Penumbra = the soft edge where a light is only partly blocked (umbra = the fully dark core).
  It widens with the gap between the shadow caster and the surface it falls on (contact
  hardening, what the PCSS does), not with distance from the player.
- Shadow darkness falling off with distance is separate: `MinStrength`/`FullIntensity` and the
  feet-to-head gradient.
- Ideas, in order of payoff: (1) per-shadow data in the shader (light-size penumbra, tint by
  zone) needs a script→shader channel; (2) self-shadowing needs light-space depth and a hook on
  the character's own draw: big; (3) screen-space contact shadows need readable depth (depth
  probe); (4) fade fitted to the real floor: done.
- The fork's per-surface shaders only reach alpha-blended draws; character skins are opaque,
  so self-shadowing and darker unlit sides both need a new hook (the character probe is the
  first step). Unlit sides looking too bright may be ambient, light setup or engine lighting:
  the probe tells which.

### Physics and lighting
- Karma is MathEngine's physics engine, compiled into `Engine.dll`. Replacing it with
  Jolt/Bullet/PhysX means reverse-engineering every call: not worth it. Small debris can be
  done in UnrealScript. Unreal II does use Karma ragdolls (U2FairFights raises `MaxRagdolls`
  from 5 to 12); how long bodies stay is script (`BodyTime`), not Karma.
- Lighting through the fork: doable now: bloom, tone mapping, colour grading; per-pixel
  character lighting if the probe shows D3D fixed-function lights; SSAO if depth is readable.
  Level lighting is baked in lightmaps and can't be relit at runtime.
- Light baking: re-bake at finer lightmap resolution through U2EdBridge (BSP only; props are
  vertex-lit); or smoother lightmap filtering in the fork; or an external GI baker (big).

### Destruction and effects
- Unreal II has particles, Karma and simple water surfaces; no fire or fluid simulation. A
  Far Cry 2-style spreading fire can be faked with a grid in UnrealScript; real fluids can't.
- Black: authored damage stages + debris: realistic if props can be replaced (U2Destruct
  probe). Red Faction Guerrilla: pre-fractured buildings with structural stress: only small
  authored set pieces here. F.E.A.R.: convincing impact decals: done as the parallax decals.

## Goobi

Puzzles don't fit your taste as a player (you prefer action), and that makes the work feel
like a chore. Making it more action-based could make it more enjoyable to build, but pin down
what "action" means for it (combat, time pressure, movement skill on top of puzzles) before
reworking, so the redesign doesn't sprawl. The hand-drawn art and comics that came out of it
were well received.

## PC access

- Remote Control sessions stop when the PC reboots: Claude Code doesn't restart by itself. On
  Oct 1 the "unreal modding" session restarted the PC, and all four PC sessions went
  `computer_unreachable`. Fix: resume each session on the PC and turn Remote Control on again;
  no reinstall needed.
- To avoid it: Chrome Remote Desktop (iOS app by Google LLC, or
  remotedesktop.google.com/access; set up the host on the PC once), or SSH (Windows OpenSSH
  Server + Termius/Blink on iOS + Tailscale outside home Wi-Fi).
- This cloud container can't reach the PC. It can compile shaders (fxc under Wine), build the
  dll (MinGW) and run it under Wine, but not run Unreal II.

## Phones (as of Sep 30, 2026)

- Claude Code on Android runs in Termux with Node.js; the AI runs on Anthropic's servers, so a
  cheap phone with Android 8+ and 4 GB+ RAM is enough. Under R$1.000 on Mercado Livre then:
  Galaxy A07 (~R$657), Redmi 14C (R$600–750), Moto G35 5G (~R$773), Galaxy A17 5G (~R$782),
  Redmi 15C (~R$835), Moto G15 (~R$899), Galaxy A16 (R$850–1.000). Prices move.
- The Claude iOS app needs iOS 18; the iPhone X stops at iOS 16. Safari → Share → Add to Home
  Screen on claude.ai works instead.
- iPhone X heating: the battery is most likely (check Settings → Battery → Battery Health);
  also remove the case, check background apps (YouTube was one; Live Activities keep it
  updating in the background), Reset All Settings. Cooling cases exist ("capa dissipador de
  calor iPhone X" on Mercado Livre); they help surface heat, not a worn battery.
