# How Unreal II's UnrealEd bakes light, and what we can do about it

Read from the Ghidra decompile of `Editor.dll` / `Engine.dll` / `Core.dll` (build of Mar 14 2003;
project `Documents\U2_research\ghidra\U2Ed.gpr`, dumps in its `decomp\` folder), 2026-10-07.
Nothing was run in the editor or the game for this. Companion: [EDITOR_OPS.md](EDITOR_OPS.md) (the
bridge commands), prototype baker: `codes/tools/python/U2Bake`.

**Verified** = read in decompiled code/assembly. **Measured** = from a log or a run. **Guess** = test it.

## 1. The LIGHT APPLY path

```
LIGHT APPLY [SELECTED=b] [CHANGED=b]            Exec_Light (Editor 0x1024dbc0)
 └ UEditorEngine::shadowIlluminateBsp(Level, Selected, Changed)     (vtable 0x254)
     1. every actor: PreRaytrace(), ClearRenderData()
     2. Level->Model->Illuminate(LevelInfo, Changed)                 BSP lightmaps (GPU, see 1.2)
     3. every actor not hidden-by-group (unless the rebuild option "only visible" is set):
          Mover -> SetBrushRaytraceKey();  GetPrimitive()->Illuminate(Actor, Changed);  PostRaytrace()
            UStaticMesh::Illuminate      static mesh vertex lighting (CPU rays)
            UTerrainPrimitive::Illuminate terrain vertex lighting (CPU rays)
     4. clear bLightChanged on every actor; log "Illumination: N seconds"
```

**`SELECTED=` is parsed and then ignored (verified in the assembly: the argument is never read).**
Every `LIGHT APPLY SELECTED=1` in U2Avalon (`lowsun.py`, `island_batch.py`, `carve.py`) was a full
relight of BSP, terrain and every static mesh. That is also why every carve shifts the look of all
meshes slightly (the level team's point 2). **`CHANGED=1` is real** (see 1.2 and 1.3).

### 1.1 Which lights a surface or actor can get: the BSP light lists

All three bakers (BSP, static meshes, terrain) take their lights from per-leaf lists that only
**`MAP REBUILD`** builds (`FEditorVisibility::TestVisibility`, "TestLights"/"FormLights"):
every actor with `LightType != LT_None` and (`bStatic` or flag 0x2000) is filtered through the BSP
portals; each leaf gets `iPermeating` = a NULL-terminated run in `Model->Lights`.
Consequences (verified):
- a light added, moved or re-imported after the last `MAP REBUILD` lights nothing (or lights from its
  old place) until the next rebuild; deleted lights linger in the lists;
- a light reaches a surface only if `bSpecialLit` matches (light flag vs. the surface's PF_SpecialLit /
  the actor's `bSpecialLit`), it is within `WorldLightRadius` (+ the actor's bounds), or it is a
  Sunlight (LightEffect 0x16) in the same zone and the surface faces it; lights with flag
  `actor+0x268 & 2` only light their own zone;
- dynamic actors in the game use **the same lists** (section 4).

### 1.2 BSP lightmaps: rendered on the GPU, one bit per texel per light

`UModel::Illuminate(LevelInfo, Changed)` (Engine 0x103caab0):
- **Changed=0**: throws away all lightmaps; makes 512x512 layout pages; gives each surface a
  lightmap whose texel size is the surface's `LightMapScale`, doubled until the map is at most 256
  texels a side (+2 border) (`FUN_103c9ad0`, "LightMapLayout.AddSurface").
- for every lightmap, gathers candidate lights from the light lists of the BSP nodes it covers
  (`FUN_103ca440` -> `FUN_103c9640`); with Changed=1 it first drops entries of lights flagged
  `bLightChanged` and only adds lights that are flagged.
- **shadows are rasterised, not ray traced**: for each (lightmap, light) pair it renders an
  `FPointLightMapSceneNode` / `FDirectionalLightMapSceneNode` into a viewport named
  **"LightingViewport"** at that bitmap's slot in a 512x512 page (`FUN_103ca810`), then reads the frame
  back (render device slot 0x9c) and sets the texel's bit **only if the pixel is exactly
  (255,255,255)** (`FUN_103ca630`). The log line is "UModel::Illuminate: 0 rays".
  The viewport is opened as a 128x128 window ("Enter SetRes: 128x128" in Editor.log) and its
  size fields are then forced to 512x512.
- what is stored is only the per-light visibility bitmaps. **Texel colours are computed at render
  time** by `FLightMap::GetTextureData` (Engine 0x10407be0): fill with the zone's ambient
  (`FGetHSV(AmbientHue, AmbientSaturation) * AmbientBrightness` of the surface's zone, else LevelInfo),
  then add each light (bitmap x falloff x incidence), cached in GCache. So there are no baked texels
  we could overwrite; changing them means a light, a zone ambient, or patching that function.

### 1.3 Static meshes: CPU rays per vertex per light

`UStaticMesh::Illuminate(Actor, Changed)` (Engine 0x1043e3b0):
- only `bStatic` actors (others get no instance: lit dynamically), and not `bHiddenEd`/`bHiddenEdGroup`
  (hidden actors keep whatever they had: re-imported + hidden = black);
- lights = the light lists of the BSP leaves the actor's box touches, filtered as in 1.1;
- per vertex per light: back-facing test with the vertex normal, then (if the actor's shadow flag
  `+0x268 & 0x10` is set) one ray `Level->SingleLineCheck` (vtable 0xe4, trace flags 0x197) from the
  vertex to the light; result = 1 visibility bit;
- stored in a new `UStaticMeshInstance` (actor+0x1c8): `Lights[]` = {light, bits} (0x14 each) and a
  per-vertex `FRawColorStream` (+0x34, colours at +0x38, zeroed, revision bumped). Both are saved
  with the map (`UStaticMeshInstance::Serialize`).
  **Verified (section 7):** the colours are filled from the bits at draw time by `FUN_10408ef0`
  ("StaticLight"), but only when a light's saved `Applied` flag disagrees with its state (first draw after
  Illuminate, light toggles); otherwise the saved colours are drawn as they are. No ambient in them.

### 1.4 Terrain

`UTerrainPrimitive::Illuminate` ray traces per vertex per light per sector, then
`UTerrainSector::StaticLight` writes per-vertex `FColor`s (sector+0x48) = zone ambient +
`FDynamicLight::SampleIntensity` x visible, for every light in the sector's list (sector+0x6c).
`StaticLight(0)` recomputes only if one of the sector's lights is flagged changed.

### 1.5 Sunlight and ambient

- Sunlight = LightEffect 0x16: no distance test, zone-limited, direction = its rotation; BSP uses
  `FDirectionalLightMapSceneNode`, meshes/terrain cast rays along the direction.
- Zone ambient (`AmbientBrightness/Hue/Saturation` of the ZoneInfo, LevelInfo for zone 0) is added at
  render time to BSP texels, terrain colours and dynamic actors (max over the actor's zones, plus its
  `AmbientGlow`). It is the only "indirect" light UE2 has: **no bounce anywhere**.

### 1.6 Where the time goes (measured)

Editor.log, last run (2026-10-07, TutA family map):
`UModel::Illuminate: 0 rays, 1.28 seconds` and `Illumination: 20.40 seconds` - the BSP is ~6 %,
the other **~19 s is the per-actor CPU ray casting** (static meshes + terrain), one thread, on the
editor's main thread, every vertex x every light in reach x one `SingleLineCheck`. Changed=1 skips
actors whose lights and self did not change. Blender is not involved in any of this (section 5).

## 2. Why TutA's tower goes dark and blotchy (hypotheses, ranked)

Fact that reframes it: the "good" runs (`SELECTED=1`) and the "bad" full run executed **the same
code** (section 1). So the darkness is not caused by relighting the BSP as such; it depends on the
state the editor was in.

1. **GPU readback (strongest).** BSP shadow bits come from rasterising into "LightingViewport" and
   accepting only pure-white pixels. Anything that alters pixels turns lit texels into shadow:
   a back buffer smaller than the 512x512 layout (the window is 128x128; atlas slots that fall outside
   whatever the device really renders to are never drawn - surfaces placed there go black), driver
   overrides (forced AA/FXAA, colour/gamma), the parked off-screen editor (`u2ed.Background`), or a
   d3d8.dll wrapper in the editor. Blotches = whole lightmaps or atlas regions going dark at once,
   matching "dark and blotchy". **Test:** two full `LIGHT APPLY`s on copies of TutA, one with the editor
   on-screen with a maximised single perspective viewport (U2ED_PARK=0), one parked as usual;
   compare the tower. If they differ, the bridge can fix it (force the lighting viewport/back buffer to
   >= 512x512, or patch `FUN_103ca630` to accept "nearly white").
2. **Stale light lists.** Editor.log has 93 `Invalid name: Light` warnings from T3D imports: lights
   were re-imported. Re-imported lights are new objects not in the BSP light lists until
   `MAP REBUILD`; the old entries point at deleted lights. **Test:** `!lightsat` inside the tower
   (EDITOR_OPS.md) - zero or wrong lights = this cause; fix = `MAP REBUILD` before `LIGHT APPLY`, or
   never re-import lights.
3. **Lights inside fixture meshes / hidden groups.** Interior lamps sitting inside a lamp mesh are
   occluded in the GPU pass (meshes are drawn as occluders) and by the CPU rays for meshes. Hidden
   static meshes are not relit at all. **Test:** `!lights <a dark interior mesh>`.
4. **Zone or LightMapScale changes after a T3D round trip.** If the tower's zone changed (portals
   lost in the T3D import) its ambient and its Sunlight membership change; T3D-imported brushes may
   come back with default LightMapScale (coarser shadows). **Test:** `!lightsat` gives the zone and its
   ambient.

## 3. Improvements: what is realistic

| Idea | Verdict |
|---|---|
| Stop using `SELECTED=1`; use `!light <meshes>` (bridge, static meshes only) and `LIGHT APPLY CHANGED=1` | do now; removes the "every carve shifts everything" effect together with `!select`/`!move` (no more re-import of all StaticMeshActors) |
| Multithread UnrealEd's per-actor loop by patching it | not realistic: `SingleLineCheck` uses the level's collision hash and shared scratch state; races would corrupt it. Our own baker is the multithreaded path |
| Faster shadow test in the editor | same: replace it, don't patch it (our kernel does ~1M rays/s/thread vs. the editor's 19 s for all) |
| Skip unchanged actors | already exists: `CHANGED=1`; `!light` targets exactly the edited actors |
| Fix the BSP GPU pass | worth one test (section 2.1); a small in-memory patch if it confirms |
| Bounce / sky light written into BSP texels | not directly (texels are computed at render time from bitmaps). Options: (a) **fill lights** placed by our baker (engine-native, persists, lights BSP + meshes + terrain + dynamic actors; costs lights: D3D allows 8 per actor), (b) per-zone ambient tuned from the bake, (c) the d3d8 fork's realtime `gi=1` |
| Bounce into static meshes / terrain | write per-vertex colours through the editor (`UStaticMeshInstance` colour stream, terrain sector colours) once we confirm they persist (1.3 guess); else fill lights |

## 4. Dynamic actors on TutA render nearly black

How dynamic actors are lit (verified, `FActorSceneNode::Render` 0x103fde00, `AActor::UpdateRenderData`):
- lights = the **BSP light lists of the leaves the actor is in** (same lists as 1.1), dropped when
  `bSpecialLit` differs, kept if within the light's radius + actor radius (Sunlight: always), then
  dynamic (non-`bStatic`) lights from the level scan; sorted, at most 8 by the D3D driver.
  Static lights are skipped only for `bStatic` static-mesh actors (they are baked).
- ambient = the brightest zone ambient over the actor's leaves, plus `AmbientGlow`.
- In the game the level's dynamic-light scan starts at `iFirstDynamicActor` and skips `bStatic`
  actors, so a plain `Light` (bStatic) never acts as a dynamic light; it reaches dynamic actors only
  through the leaf lists.

So a spawned `CardMesh`/B_* goes black when its spot has (a) no lights in its leaves' lists (lights
added after the last MAP REBUILD, or out of radius; outdoor spots on a terrain map often have only
the Sunlight, and only if it is in that zone), (b) zone ambient 0, (c) `bSpecialLit` mismatch, or
(d) the engine disabling its lights when a shadow is drawn (the black-character bug; the fork's
`relight` only fixes matched draws). There is also an early path in `UpdateRenderData` that, for some
actors in the game, takes ambient from `AmbientGlow` only and skips the leaf lookup (condition
`FUN_10360840`, not decoded).
**Test:** `!lightsat` at the spawn spot in the editor (zone, ambient, lights).
**Fixes**, cheapest first: per-zone `AmbientBrightness` (but it also brightens BSP/terrain);
a mutator-spawned **non-static light with `bSpecialLit=True`** plus `bSpecialLit=True` on the spawned
actors (lights only them, guess: test); `AmbientGlow` per actor from a **light probe** the baker writes
(nearest-probe brightness; grey only) - the scene bake below produces those probes for free.

## 5. Blender's part

Blender is not in the level-lighting path: `LIGHT APPLY` is pure UnrealEd (section 1.6, 20 s).
Blender is used offline per asset: `bake_textures.py` bakes sky bounce + occlusion (Cycles, diffuse
indirect only, white sky dome, 48 samples, 256 px) into one texture per building, alone, so it knows
nothing of neighbours, terrain or the level's lights; the engine's lights go on top. It runs once per
asset, not per edit, so it does not slow the edit loop. (Correction of the user's guess.)

## 6. The scene-wide bounce baker (decided direction)

Goal: light that sees the placed scene - sun and lights with shadows, 1-2 diffuse bounces, sky
occlusion - computed by our own code, written back so the engine shows it, and fast enough to rerun
after every edit (incremental).

**Data in**
- now: a T3D (`MAP EXPORT` or the generator's actor T3D) + the ASE sources of AvalonSM meshes
  (`U2Avalon/Models/ase`, `Models/kiln`). Stock meshes (Flora_M, Terran_DecoM, ...) need exporting
  with umodel (`Documents\Tools\umodel`) or a bounds proxy.
- next: the editor's live data through the bridge, exact and with no file round trip: per mesh the
  engine's own vertex buffer (`UStaticMesh+0x64`, 0x18 bytes per vertex: position, normal - read in
  `UStaticMesh::Illuminate`), actor transforms, the post-CSG BSP (`Model` points/verts/surfs/nodes),
  terrain heights, lights, zones. A `!dumpscene <file>` command writes it all as one binary file.

**The bake** (`U2Bake/bake_kernel.c`, built; C, BVH, threads): per sample point (welded vertex) direct
= sun + point lights with shadow rays; sky = cosine-weighted hemisphere rays that escape x sky colour;
bounce = albedo(hit) x (direct + sky) at the hit point, 2nd bounce optional (recursive, few rays).
Albedo from the AvalonSM palette swatches; textures later. Outputs the three terms separately so the
engine-side direct light is not counted twice.

**Data out**, in order of certainty:
1. probes (zone/grid ambient for dynamic actors, `AmbientGlow` per spawned actor) - simple, safe;
2. fill lights (a few low-brightness `bStatic` lights fitted to the bounce field; engine bakes them into
   BSP, meshes, terrain; dynamic actors get them through the leaf lists) - engine-native, persists;
3. per-vertex colours into `UStaticMeshInstance` / terrain sectors via a bridge command
   (`!setcolors <file>`), matched to engine vertices by mesh-space position - only after the
   persistence test in 1.3;
4. BSP texels: not stored by the engine; only via 2 or the fork.

**Incremental mode** (built in the prototype): `--changed PATTERN --radius R` re-bakes the changed
actors and every actor within R (bounce reach); the whole scene still occludes and reflects. With the
bridge, `!move` already knows what changed.

**Measured (prototype, Avalon actor T3D, 146,042 triangles from 153 placed ASE meshes, 207 stock-mesh
actors skipped, 4 threads):** all 82,632 vertices, 64 rays, 1 bounce: **2.4 s** (+1.5 s parsing);
20 buildings with 2 bounces: 3.7 s; incremental (dorm changed, 1500-unit reach, 12 actors): 0.6 s.
Sanity: roofs ~55 % sky, buried bases ~0 %. Not yet compared against the engine's own lighting
(brightness scale `--light-scale`, UE2's exact falloff and HSV are approximations).

**Compared with improving the per-building Blender bake** (dropped by the user, kept for the record):
cluster bakes in Blender would see neighbours but cost Cycles minutes per cluster and still need
re-baking textures + re-importing packages after each edit; the scene baker reruns in seconds and
writes data, not textures.

**Next steps:** (1) bridge `!dumpscene` and `!setcolors`, (2) the persistence test, (3) calibration
against an engine bake of the same spot, (4) BSP and terrain geometry in the baker, (5) probes file for
the live-edit mutator.

## 7. Write-back (2026-10-07)

Read from the Engine.dll decompile (full ghidra-bridge export now in
`Documents\U2_research\ghidra\bridge-exports\Engine`, config `Tools\ghidra-bridge\engine.yaml`).
Built, **never run**: `bin\U2EdBridge_ops.dll` (new commands), `U2Bake/bake.py` + `bake_kernel.dll`
(engine falloff, dump reader, U2BK/fill/zone writers). bake.py's dump route was exercised offline on a
synthetic dump made from the Avalon T3D (445k engine-style vertices: 12 s bake, 4 threads).

### 7.1 Static-mesh vertex colours (route 1)

**How the engine stores and draws them (verified).**
- `UStaticMeshInstance` (actor+0x1c8): `Lights` TArray at +0x28, 0x14 per entry {`AActor* Light`,
  `TArray<BYTE> Bits` (1 bit per vertex), `UBOOL Applied` at +0x10}; `FRawColorStream` at +0x34 with
  `TArray<FColor>` at +0x38 (one per **render vertex**, FColor memory order B,G,R,A) and `Revision` at +0x4c.
  `Serialize` saves the colour stream (LicenseeVer >= 13) and every light entry *including Applied*.
- Render vertices = `UStaticMesh+0x64`, `TArray<FStaticMeshVertex>` {Position, Normal} 0x18 each, mesh space;
  triangles = `FRawIndexBuffer` at +0xc0 (`TArray<WORD>` at +0xc4); sections at +0x54 (0x14, IsStrip at +4).
  Actor's mesh = actor+0x38, LocalToWorld = `GetActorRenderData()+8` (4x4, world = (x,y,z,1)·M).
- **StaticLight** `FUN_10408ef0(UStaticMesh*, Instance*, FDynamicActor*)`, cdecl: zero the colours,
  Revision++, for every light whose render data says static: `colour += FColor(light.Color ·
  SampleIntensity(worldPos, worldNormal))` where its bit is set, Applied = 1; then multiply by the mesh's own
  vertex colours if mesh+0x128, alpha from the mesh. Ambient is *not* in the stream (added at draw time:
  FDynamicActor+0xb8, or SetAmbientLight).
- Called from (a) the per-actor draw path `FUN_104097b0` only when, for some light, "dynamic now" == Applied
  (so: first draw after Illuminate, or a light toggles), and (b) `FStaticMeshBatchVertexStream::GetStreamData`
  every time a batch is built. Batches exist only in the game (`ULevel::PostLoad`, `!GIsEditor`) with
  `UseStaticMeshBatching` - **False** in the user's `Unreal2.ini [Engine.GameEngine]`.
- Consequence: colours written into the stream and saved with `Applied=1` are drawn **as saved** in the game
  with no patch at all (guess until test 7 below: it assumes `GetLightRenderData` is non-NULL for static lights
  in the game); in the editor they survive until the next StaticLight call for that actor.

**What the bridge does (built).** `!bakeload FILE` redirects both StaticLight call sites (rel32 patch at
Engine+0x10233b and +0x109aa9, after checking the GetStreamData export address, the prologue and both call
targets; refuses otherwise) to `BakeStaticLight`, which calls the original and then adds (mode add) or puts
(mode replace) the actor's baked colours. For each actor in the file it checks name, vertex count and that
the instance is valid by the engine's own test, records the colours, `Modify()`s the instance (undo + dirty
package) and calls StaticLight through the hook so the stream holds engine light + bake with Applied=1.
**Save the map** to keep it. Persistence without a side file: when the hook first meets an instance (or the
engine relit it), it keeps `saved stream - engine recompute` (saturating) as that actor's bake, so a reloaded
baked map keeps its bake even through light toggles while the ops DLL is in. Caveat: if a light moved or
changed since the last relight, that difference is taken for "bake" - `!bakeinfo derive off` disables this,
`!bakeclear PAT|all` goes back to the engine's colours. A full `LIGHT APPLY` or `!light` makes a new zeroed
instance: the bake of those actors is gone (re-run bake.py + `!bakeload`).

**Vertex order.** `!meshverts [PAT] FILE` dumps every matching StaticMeshActor's mesh in render-vertex order
(U2MV, format in `editor_ops.c`), so bake.py bakes exactly the engine's vertices (no ASE, no welding; seam
duplicates are baked separately). The same dump gives the 207 stock-mesh actors (Flora_M, Terran_DecoM...)
their geometry, the engine's current colours (calibration), zones and all lights with engine values.

**Exchange format U2BK v1** (bake.py `--u2bk`): `"U2BK"`, int32 version 1, int32 mode (0 add, 1 replace),
int32 count, then per actor: int32 length + UTF-16 name, int32 nverts, uint32[nverts] colours as
0xAARRGGBB (alpha ignored), engine vertex order. Default terms: add = sky+bounce (the engine keeps its own
direct light and shadows), replace = direct+sky+bounce (ours entirely; no BSP/terrain shadows in our scene yet).

### 7.2 Fill lights for BSP and dynamic actors (route 2)

- **No light flag skips the shadow test** (searched: `UStaticMesh::Illuminate`, `UTerrainPrimitive::Illuminate`,
  `UModel::Illuminate`/`FUN_103ca810`). Mesh shadow rays depend on the *receiving* actor's flag
  (actor+0x268 & 0x10), terrain sun rays on the terrain actor's flag, and the BSP shadows are always rasterised.
  Lights with flags 0x40000/0x100000 (dynamic) are skipped by the static mesh baker.
- Static bakers take lights only from the BSP leaf light lists, which only **MAP REBUILD** builds (1.1). So
  `MAP IMPORTADD` + `LIGHT APPLY CHANGED=1` is **not** enough: the new lights reach nothing until MAP REBUILD,
  and after MAP REBUILD the BSP has no lightmaps, so a full `LIGHT APPLY` follows. Terrain additionally needs
  LT_Steady, bStatic, the 0x2000 actor flag and the same zone (`UTerrainPrimitive::Illuminate`).
- Dynamic actors get them through the same leaf lists after the rebuild (section 4; verified for the lists,
  not run). They count against the 8 hardware lights per actor: keep fill lights few and wide.
- bake.py `--fill N --fill-t3d F` (built): weighted k-means of the samples by indirect luminance, one light per
  cluster placed max(48, extent/2) in front of the cluster along its mean normal, radius 2.5x extent, joint
  non-negative least squares on the engine falloff (unshadowed), colour fitted to FGetHSV; written as
  `Class=Light`, Group/Tag `BakeFill`. Fit quality on the synthetic test: mean error 75 % - a rough fill, not
  a reproduction. The engine WILL shadow them (place-in-front helps). Don't add `bounce` per vertex too
  (double counting): use `--terms sky` with fill lights.

### 7.3 Zone ambient (route 3)

Verified: `AmbientVector = FGetHSV(AmbientHue, AmbientSaturation, AmbientBrightness)` (ULevel::PostLoad;
AZoneInfo::PostEditChange recomputes it and clears every actor's render data). Bytes: Brightness +0x3c8,
Hue +0x3c9, Saturation +0x3ca. Dynamic actors use the max over their zones + AmbientGlow (FDynamicActor+0xb8).
`SET ZoneInfo ...` is class-wide (all zones), so the bridge has **`!setprop NAME PROP VALUE`** (one actor:
`Modify`, the property's own `ImportText` - vtable slot found at runtime by matching UByteProperty's export -
then `PostEditChange`). bake.py `--zones F` writes `!setprop` lines per zone from a low percentile (30) of
sky+bounce over the zone's samples (zone per actor from the dump; `LevelInfo0` = zone 0). Guess: the BSP
texel path uses the same AmbientVector (section 1.2 read it as HSV x brightness; not re-checked).

### 7.4 Calibration: the engine's static vertex light (verified)

Per vertex, per light with its bit set (Engine.dll `FDynamicLight::Update` 0x10407460,
`SampleIntensity` 0x104049a0, `FUN_10404900`, `FGetHSV` 0x10465140, `FColor(FPlane)` 0x10317af0,
`WorldLightRadius` 0x10301e60):

```
colour  = FGetHSV(LightHue, LightSaturation, 255) * LightBrightness/255 * LevelInfo.Brightness
          (LT_Steady: intensity 1.0; LevelInfo+0x5fc read as Brightness - the name is a guess)
FGetHSV(H,S,V): b = V*1.4/255;  b = clamp(b*0.7/(0.01+sqrt(b)), 0, 1)        (V=255 -> 0.8213)
                hue = H<86: ((85-H)/85, H/85, 0)  H<171: (0, (170-H)/85, (H-85)/85)  else: ((H-170)/85, 0, (255-H)/84)
                rgb = (hue + S/255*(1-hue)) * b
point light (LightEffect none):  I = 2 * cos(theta) * (1 - 3t^2 + 2t^3),  t = dist / R,  0 if dist >= R or cos <= 0
                                 R = WorldLightRadius = 25 * (LightRadius + 1)
sunlight (LE_Sunlight 0x16):     I = 2 * cos(theta)     (no distance term)
byte    = clamp(floor(255 * colour * I), 0, 255) per light, summed with saturation (FColor +=)
shadow  = one SingleLineCheck (flags 0x197) from 4 units off the vertex toward the light (sun: 262144 units),
          only if the RECEIVING actor has flag 0x268&0x10; bit cleared if back-facing (N.L < 0)
```
Other effects (SampleIntensity): 0x0c/0x08 spot cone, 0x11 `2*(1-dxy^2/R^2)`, 0x0d `2*sqrt(1.02-d/R)`,
0x17 `2*(1.02-d^2/R^2)`; bake.py treats them as plain point lights and counts them.
bake.py now works in these units (1.0 = byte 255) and the kernel uses this formula; `--calib` compares our
direct with the engine colours in a `!meshverts` dump taken after LIGHT APPLY (differences expected where
BSP/terrain shadow, which our scene lacks).

### 7.5 Test plan for the editor session (on a COPY of TutA, e.g. `TutA_Bake.un2`)

Inject both DLLs as in EDITOR_OPS.md (`ops = Ops.attach_to(ed.pid)`); paths below are examples.
1. `!opsinfo`, then `!meshverts * C:\tmp\tuta.u2mv` -> "N meshes, M actors, K lights". "refused" = an
   offset check failed: report the line.
2. Offline: `py bake.py --scene C:\tmp\tuta.u2mv --calib --out ""` -> ratio engine/ours should be ~1.0
   (0.8-1.2) on actors away from BSP shadows; send the calib lines back. If far off, report it with one
   actor's name and `!lights NAME`.
3. `py bake.py --scene C:\tmp\tuta.u2mv --u2bk C:\tmp\tuta.u2bk --mode add` then `!bakeload C:\tmp\tuta.u2bk`
   -> "baked N actor(s)"; screenshot the tower before/after (meshes in shadow should lift a little).
   `!bakeinfo` -> hook installed.
4. Strong visual check: `--mode replace --terms sky --gain 3`, `!bakeload` again: meshes show only the sky
   occlusion (dark under overhangs). Then `!bakeclear all` -> back to the engine look.
5. Persistence: bake (step 3), save as TutA_Bake, restart the editor WITHOUT the ops DLL, load it,
   screenshot: the bake should still be there.
6. Relight: `!light <one baked actor>` -> that actor loses its bake (expected); `LIGHT APPLY CHANGED=1`
   with nothing changed -> no actor loses it.
7. Game (when the user allows a run): play TutA_Bake; the baked look must match the editor's. If meshes show
   plain engine light instead, the game recomputes (guess about `GetLightRenderData`/batching wrong): the
   hook then has to go into a game-side DLL too (the code in editor_ops.c is self-contained).
8. Zones: `py bake.py --scene ... --zones C:\tmp\zones.txt`; run one zone's `!setprop` lines; `!lightsat` in
   that zone shows the new AmbientBrightness; spawned actors on TutA should no longer be black.
9. Fill lights: `--fill 16 --fill-t3d C:\tmp\fill.t3d` (+ `--u2bk ... --terms sky` if combining), then
   `MAP IMPORTADD FILE=C:\tmp\fill.t3d`, `MAP REBUILD`, full `LIGHT APPLY`; `!lightsat` near one fill light
   -> listed; screenshot BSP walls near clusters. Remove via group BakeFill if it looks wrong.
10. Undo: after a `!bakeload`, Ctrl+Z once should restore the previous colours (instance was Modify()'d) - guess.

Known gaps: BSP and terrain are not in bake.py's scene (no occlusion/reflection from them); albedo is a
constant (or the AvalonSM swatch mean) for dump meshes; per-light byte flooring is not modelled (<= 1 byte per
light); the ASE route's normal heuristic gives flat grass meshes downward normals (Avalon Ground*Grass:
direct 0) - the dump route uses the engine's normals instead.
