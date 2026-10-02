# Character shadows in Unreal II: what we built and how it got there

Written 2026-10-02 for the Advent Rising chat, which is going to bring this shadow system to
Advent Rising (also Unreal Engine 2, but build 2226, the UT2003 line). It covers both layers:
the UnrealScript mod (**U2SoftShadows**) and the Direct3D layer (**U2Shaders**, our d3d8to9
fork), plus the bugs, dead ends and tools, so nothing has to be rediscovered.

## Where the code is

Repo: `C:\Users\john\Documents\github\codes` (GitHub: `indieindie7/codes`)

| What | Path |
|---|---|
| Script mod source | `games/unreal2_mods/U2SoftShadows/Source/U2SoftShadows/Classes/` (5 classes) |
| Options page patcher | `games/unreal2_mods/U2SoftShadows/ssmenu_v2.py` |
| Old experiments (contact blob, capsules) | `<Unreal II>\U2SoftShadows\Retired\` (game folder only) |
| D3D fork, PCSS code | `tools/C/U2Shaders/u2shaders.hpp` (bundle), full fork: `C:\Users\john\Documents\github\d3d8to9`, branch `u2shaders`, GitHub `indieindie7/d3d8to9` |
| PCSS shaders | `tools/C/U2Shaders/shaders/pcss_map.hlsl`, `pcss_proj.hlsl` |
| Built dll | `tools/C/U2Shaders/d3d8.dll` (MSVC) and `d3d8-mingw.dll` (cloud build, newer features) |
| Test console | `games/unreal2_mods/U2TestHub` ("hub info", "hub lamp", "hub view") |
| Test driver | `tools/python/U2Pilot` (scripts `shadow_*.txt`, `hub_lamp_*.txt`, `shadow_v2.txt`, `shadow_pcss.txt`) |
| PC test results of the newest shader features | `test-results/2026-10-01-pc/README.md` |

Unreal II game folder: `C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening`.

## The idea in one paragraph

Unreal II gives each character one blurry blob-ish shadow from one light. We give each
character up to N real projected silhouette shadows, one per nearby light (sun included), each
soft, each fading with distance from the feet, each as dark as that light's share of all the
light at that spot (so a shadow never fights the baked lighting), and blended when a character
walks from one lamp to the next instead of popping. On top, the D3D fork makes every one of those
shadows contact-hardening (PCSS): sharp where the feet touch the floor, softer further away.

## Layer 1: U2SoftShadows (UnrealScript)

Five classes:

- **SSShadowMutator**: loads the add-on (Mutator line in User.ini).
- **SSShadowManager**: one per level. Collects the level's lights ONCE and shares them;
  keeps a list of dynamic lights (rescanned at most every 0.15 s; short-lived ones with
  LifeSpan > 0, i.e. muzzle flashes, are ignored); bumps `LightsVersion` when that list changes.
  Gives every pawn a controller; adopts controller-less (scripted/posed) pawns after 2 s.
- **SSShadowController**: one per character. Scores lights, picks the set, assigns
  shadows, culls.
- **SSLightShadow** `extends ShadowProjector`: one shadow from one light.
- **SSMenuHelper**: Get/Set pairs for the options page (UIHelper).

### How a character's shadows are chosen (SSShadowController)

1. Score every light in range (brightness x falloff by distance; the sun via `IsA('SunLight')`,
   only if nothing blocks it within `SunClearance` 1000 units overhead toward it).
2. Keep the best `MaxShadows` (3; `PlayerMaxShadows` 4 for the player).
3. **Hold the set** until the character moves `RepickDistance` (32 units), changes distance
   tier, loses an assigned light, or the manager's `LightsVersion` changes. Without this the
   shadows shuffled while standing still (lights re-ranked by tiny animation movements).
4. **Darkness = the light's share of the light here** (`bRespectBaked`):
   `share = MinShare + (1 - MinShare) * score / (sum of scores + zone AmbientBrightness * AmbientWeight)`,
   `MinShare` 0.35. A lamp in a brightly lit room casts a faint shadow; the only lamp in a dark
   corridor casts a dark one. That is how the shadows sit on top of baked lightmaps instead of
   over-darkening them.
5. Distance tiers: within `NearDistance` (900) every shadow; within `MidDistance` (2000) one;
   beyond, none. `CullDistance` 3000. `bCameraCull`: no shadows for characters outside the
   view cone (+`CullFOVMargin` 20 degrees) for `UnseenTime` (0.3 s); the player's own pawn
   is exempt. Timers are staggered across controllers.

### One shadow (SSLightShadow)

- Built on the engine's own `ShadowProjector` so it uses Unreal II's render path (`PreRender`,
  `SetRes`, `GetShadowLocation`, `FrustumOrigin`). SquirrelZero's UT2004 projector skipped those
  and rendered nothing in Unreal II: that's why everything extends ShadowProjector.
- **Switching lights = fade out, swap, fade in** (`FadeRate`), and `LightShare` eases toward
  the controller's `TargetShare` (`LightShare += (TargetShare - LightShare) * min(1, dt*2)`), so
  walking between lamps blends.
- Darkness also scales with lamp intensity: `MinStrength` (0.2) for a dim/far lamp up to full
  at `FullIntensity` (128).
- Overhead lamps are tilted to at most `MaxSteepness`, otherwise the shadow hides under the
  body.
- Always soft: shadow texture 128 (`LampResolution`, `SunResolution`); the user's rule is
  "shadows should ALWAYS be soft", no sharp modes.
- **Feet-to-head fade** (`bGradient`): fade length = `GradientScale` (3.0) x the shadow's
  length, capped at `GradientLength` (2048). `bFitToFloor` (cloud chat, 2026-10-01, compiled but not
  yet seen on stairs): traces where the head's shadow really lands instead of assuming flat
  floor.

### Options page

Unreal II menus are text (`UIScripts\*.ui`). A control binds `Object=<helper>` +
`Variable=X`, and the helper is registered *inside the .ui* (`[Name]` / `Helper=Pkg$Class` /
`RegisterObj=Name` / `Component=Name`). Registering it via `Unreal2.ini PlugIn=` crashed the
game. `ssmenu_v2.py` turns the stock Options > MISC (Shadows) page into the mod's page (and
the wardrobe dropdown), idempotent, `--undo`, backups `*.before-ssv2`.

## Layer 2: U2Shaders, PCSS contact hardening (D3D8 -> D3D9 fork)

Chain: `Unreal2.exe -> d3d8.dll (our d3d8to9 fork) -> d3d9.dll (dgVoodoo 2)`. The fork can
replace fixed-function draws with HLSL pixel shaders per draw (`U2Shaders.ini`, e.g.
`shader=<texture hash> core.hlsl`, `pcss=1`). It's C++14 (no inline variables).

### How Unreal Engine 2 actually builds a character shadow (found by logging draw states)

1. The silhouette is drawn into a small render target **A** (stage 0 `SELECTARG1 TFACTOR`,
   tfactor `0x808080`, blend off). RGB is a constant 128; the shadow lives in **alpha** (255 lit,
   ~104 shadowed). **Red is free.**
2. Nine additive passes (`SRCALPHA / ONE`) sample A into the per-shadow target **B**
   (= 0.502 x alpha, i.e. a blur), plus one `SRCALPHA / INVSRCALPHA` border pass.
3. The projector pass (DESTCOLOR blend, projected texture on stage 0) samples **B** onto the
   world.

### What the fork does

- **Map pass:** `pcss_map.hlsl` replaces step 1 and writes the silhouette's world height into
  A's free red channel: `frac(z / 256)` (z from the inverse view matrix's 3rd column and
  camera-space texgen), keeping alpha as the game wants it.
- **Snapshot:** A is shared by every character. On the first blur pass after a map pass,
  `StretchRect` copies A into a texture of B's own (`BlurSource` map: B surface -> its snapshot).
  Without this, Dalton's animation leaked into everybody's shadows and shadows moved while
  standing still.
- **Projector pass:** binds that snapshot on sampler 3; `pcss_proj.hlsl` does a blocker search
  (12 golden-angle taps rotated per pixel) where `s.a < 0.9` is a blocker, takes the
  height gap between receiver and blocker (`d = frac(s.r - receiver + 0.125) * 256 - 32`),
  sets the filter radius `clamp(P.y + gap * P.z, P.y, P.w)`, filters with the same pattern
  twice (radius and 0.6 x radius rotated 90 degrees), and outputs `0.502 * lit`, the value B
  would have had.
- Fades: the projector's own fade textures (`Fade1`, `Fade2`) are kept.
- **Budget:** ps_2_a ran out (524 slots, 22 temps, 32 constants): the fork falls back to
  **ps_2_b** automatically. Now 356/512 slots and **31/32 temp registers**: any penumbra change
  must fit that.
- `OnLost` (device reset) clears MapTarget/BlurSource/MapDirty/CopiedFor.
- Debug: `pcssdebug=1` colours the gap (red at the feet .. blue at the head), `2` raw values,
  `3+` dumps A/B as raw BGRA to `U2Shaders\dump`, `5` logs the offscreen draw states, `6` stock
  map output. Tuning: `pcssparams=search min perUnit max` (UV units). `shadowtint=R G B`
  (cloud chat) tints shadows per channel.

## Timeline: what we tried, what broke, what we learned

| When | What |
|---|---|
| 2026-09-27 | **1.0 released** (Nexus): multi-light soft shadows. SquirrelZero's UT2004 code fully replaced (credited as inspiration only, so no third-party content). |
| 09-27 | Found: U2 level loading is tied to framerate; dgVoodoo forced VSync made loads 52 s instead of 3 s. |
| 09-29 | **Perf fix (1.2):** ~20-30 fps cost and 110-240 ms hitches when enemies spawned (every new controller scanned AllActors for lights; every controller scanned DynamicActors every 0.2 s). Fix: the manager collects lights once, shares the dynamic list, culls by distance/visibility, staggered timers. No more hitches. |
| 09-29 | "Mod shadows invisible, stock visible": **the real bug was the gradient**. Our fade ran from the projector plane to a short MaxTraceDistance (131-229 from a feet-to-head fit) while the engine uses 2048: the floor was half faded. Fix GradientScale 3.0 / GradientLength 2048. The earlier "invisible" verdicts and the tilt/slide/parallel experiments were all red herrings caused by this. Lesson: compare your projector field by field against the engine's own at the same spot (`hub info`). |
| 09-29 | Sun: `SunLight` is native with LightEffect LE_None in script, so `IsA('SunLight')`; a 16384-unit sky trace always hits the room around it, hence `SunClearance`. |
| 09-29 | Experiments: **contact blob** (projector straight down; needs FOV>0, FOV=0 renders nothing; PB_Modulate is 2x so 128 = unchanged; `bGradient` made it invisible), **capsule shadows** (10 soft ovals per character from Golem bone positions: `MeshGetNodeNamed("Merc L Thigh")` + `MeshNodeGetTranslation`, because `GetBoneCoords` returns nothing for Golem meshes), hard-to-soft sharp layer, weighted light pick, per-light softness. Capsules cost ~20 fps in fights. |
| 09-29 | Camera culling and distance tiers; options page; **1.3 released**. Fight benchmark 236 fps avg, min 175, 0 hitches. |
| 09-30 | **PCSS in the D3D fork works** (contact hardening for every shadow). This replaced the contact blob, capsules and the sharp layer, which were **removed in 2.0** (they "didn't look so good"). |
| 09-30 | Bugs from the user's video: animation leaking into other actors' shadows and shadows moving while standing still -> per-shadow snapshot of A. |
| 09-30 | **2.0** (installed, not released): held light sets (RepickDistance, LightsVersion), baked-light share, player gets 4 shadows, muzzle flashes ignored, controller-less pawns adopted, `hub info` prints "light here: total (lamps + ambient)". |
| 10-01 | Cloud chat: `bFitToFloor`, `shadowtint`, probes. On the PC: builds and runs without errors; stairs check still open. |

Open problems: no shadows on glass is wanted but shadows still land on transparent surfaces
(windows); the stairs/slopes fit isn't seen yet.

## Moving it to Advent Rising: what transfers and what to check

- **Same engine family, different build.** Advent is UE2 build 2226 (UT2003 line), Unreal II
  is a later Legend fork. First check that Advent has `ShadowProjector`, `ShadowBitmapMaterial`,
  `Projector` with `bGradient`/`MaxTraceDistance`/`FOV`, and how its pawns get their stock
  shadow (`bActorShadows`?). The exported sources are in `Documents\AdventRising_src`.
- **The script layer should port almost as is** (manager/controller/projector pattern, scoring,
  held sets, share-of-light darkness, fading, culling). Unreal II specifics to drop or replace:
  `SunLight` (check what Advent uses for the sun), Golem bone calls (not needed anymore),
  `U2Pawn`/`U2PlayerController` references, the `UIScripts` options page (Advent's menus are
  script classes, as AdventMod already does).
- **Loading:** Advent mutators work via `Mutator=` under `[DefaultPlayer]` in MyDefUser.ini
  (AdventMod.ModMutator already proves it) - same route as SSShadowMutator.
- **PCSS layer:** depends on Advent drawing shadows the same way (map into a small RT with
  alpha, additive blur into a second RT, DESTCOLOR projector). Log the offscreen draw states
  first (the fork's `pcssdebug=5` does exactly that) before porting. Advent Rising runs through
  D3D8 too? If it's D3D9 or something else, the fork itself doesn't apply and the hook goes into
  AdventNative instead (the Advent chat's `shadowfix.c` / `shadowalpha.c` already hook its
  shadow drawing).
- **Watch-outs we hit:** shared render target between characters (snapshot it), shader register
  limits (ps_2_b fallback), gradient/MaxTraceDistance mismatch with the engine, perf from
  per-controller actor scans (centralise in a manager), lights re-ranked every frame
  (hold the set).
- **Testing approach that worked:** a test console with "spawn a lamp at angle X", "third-person
  view" and "print every shadow's state"; scripted runs with screenshots before/after; compare
  against the stock shadow at the same spot.

## Advent Rising port: what was different (from the "advent rising modding" chat, 2026-10-02)

The script layer works in Advent for Gideon (real lamps, held light sets, light share, fades, long
gradient; stock blob gone). Advent-specific findings:

1. Advent's engine places and aims a ShadowProjector natively only for the **exact** class
   `ShadowProjector`; a script subclass (like `SSLightShadow`) keeps its spawn rotation and never
   renders a silhouette. So the port uses an `Info` helper (`ModLightShadow`) that steers a plain
   ShadowProjector.
2. The engine only updates shadows of pawns with `bActorShadows=True`. Clearing it (as
   `SSShadowManager.Adopt` does in Unreal II) kills every extra shadow; the stock shadow is kept
   with `ShadowDarkness 0` instead.
3. `DetachProjector` or `bShadowActive=false` stops the native updates for good: hide a shadow
   with darkness 0.
4. Advent lamps are often low (~17 degrees): long, thin, faint shadows. Added `MinSteepness` 35
   and a frustum distance cap of 600.
5. Debugging with the raw-texture view shows only the top shadow when a character has several:
   test with `MaxShadows=1`.

Next there: strength tuning, more scenes, NPCs, then PCSS.

## Open bug: characters turn black when a shadow is cast from a real light (2026-10-02)

Found during the stairs check (Sanctuary M08A1, concrete stairs around (-1024, -2784)). A test lamp
(`hub lamp 255 40 220`) behind the camera; with our shadows on, the character renders very dark
(pcss=0) or black (pcss=1), while the floor and walls stay lit. Shadows off: lit.

- It is the Unreal II engine, not our script: the game's own `ShadowProjector` with
  `bStaticLights=True` (sourced from the pawn's `PrimaryStaticLight`) blackens the character the
  same way. The stock game avoids it because its default shadow is directional (no light source).
- Excluding that lamp from our shadows (`MaxLightDistance` below its distance) lights it again.
- Not the cause: shadow darkness / strength 0, `bProjectActor=False`, spawning the shadow without
  an owner, `bActorShadows=True` on the pawn, collision / trace flags, the outfit, vertex shaders
  (every draw is fixed-function), PCSS or post (they only make it darker).
- Advent Rising's engine build does not do this (same approach, characters measured unchanged).
- Probes: `charprobe=1` (once showed the lamp's diffuse 0,0,0 on the character's draws) and
  `lightprobe` (U2Shaders\lightprobe.req: two frames of SetLight / LightEnable / draws; never saw a
  SetLight with zero diffuse; the character's own draws weren't identified for sure).
- Fix to try (the Advent chat's idea): in the d3d8 fork, snapshot the lighting state (lights,
  material, ambient, material sources) when the render target switches into a shadow bitmap and
  restore what the engine didn't set again when it switches back.

Test notes: `hub view` (third person) clips the camera into walls in narrow places (big flat
grey/black shapes); scripts `stairs_conc.txt`, `black_*.txt` in U2Pilot.
