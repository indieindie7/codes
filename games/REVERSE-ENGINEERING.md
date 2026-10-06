# Reverse engineering and decompiling: tools, methods, findings

Notes from the old-game modding work (Unreal II, Advent Rising, and the first look at
Hydrophobia), written 2026-10-05. The point is to make the next game faster: what tools are
installed, which tricks worked, and what each game turned out to be made of.

## 1. Tools on this PC

| Tool | Where | What for |
|---|---|---|
| Ghidra 12.1.4 | `Documents\Tools\ghidra\ghidra_12.1.4_PUBLIC`, start with `ghidraRun-jdk21.bat` | Decompiles native exes/DLLs to readable C. Needs Java 21: a portable Temurin JDK 21 sits in `Documents\Tools\jdk` (system Java is 8). Headless use: `support\analyzeHeadless.bat <projectDir> <project> -import <exe>` with `JAVA_HOME` set. First project: `Documents\Hydrophobia_research\HydroGhidra` (HydroPC.exe analysed). |
| Visual Studio 2026 Community (cl 19.51) | `C:\Program Files\Microsoft Visual Studio\18\Community` | Building proxy DLLs, native hooks, UCC launchers. |
| Zig | on PATH | A second C compiler, used for the U2EdBridge tool. |
| GitHub CLI 2.102 | `C:\Program Files\GitHub CLI\gh.exe` | Release downloads, API lookups. |
| Python 3 (+ a venv with numpy/Pillow at `Documents\Tools\kimodo\venv`) | | Format parsers, unpackers, image checks. |
| MSBuild of the d3d8to9 fork | `Documents\github\d3d8to9-gi` (branch gi-cascades) | Our Direct3D 8 -> 9 graphics layer (shadows, post, GI, PBR, decal rules). |

Worth adding when needed (all on GitHub, none installed yet): **x64dbg** (debugger),
**Cheat Engine** (find values in memory, trace what writes them), **ReClass.NET** (map structs in
memory), **Frida** (script hooks into a running game), **ImHex** (hex editor with a pattern
language) and **Kaitai Struct** (format descriptions -> parsers), **apitrace** (record/replay
Direct3D 9 calls; RenderDoc doesn't do D3D9), **MinHook / SafetyHook** (hooking libraries, used by
the Splinter Cell EnhancedSC project we keep as a reference in `Documents\github\EnhancedSC`),
**Reloaded-II** (mod loader for games without one). Engine-specific: **UE Explorer / UModel** (Unreal
1-3), **FModel / UE4SS** (UE4/5), **dnSpy / ILSpy / Il2CppDumper / AssetRipper** (Unity).
**QuickBMS** (archive scripts) is from its author's site, not GitHub.

## 2. Methods that worked

### 2.1 Unreal Engine 2 games (Unreal II, Advent Rising)
- **Export the script source first.** UE2 games carry their UnrealScript in the .u packages. Unreal
  II ships `ucc.exe` (batchexport). Advent shipped no ucc, so we wrote **AdventUCC**: a launcher
  that starts the game suspended, injects a DLL, redirects Core.dll's `StaticLoadClass` thunk (all
  Core exports are `E9 jmp` thunks: rewrite the rel32) and, at the first class load after
  `appInit`, flips `GIsUCC`/`GIsEditor` and runs the commandlet (`batchexport`, `make`) through the
  `UCommandlet` vtable. Result: 1,938 classes of real source in `Documents\AdventRising_src`, and a
  working compiler for our own package.
- **Load code without replacing stock files.** The GUIController class name in the ini, a
  `Mutator=` URL option in the user ini, and `DynamicLoadObject("Pkg.X")` falling back to
  `LoadLibrary(Pkg.dll)` when no .u exists: that last one gives a native DLL entry point with no
  native classes.
- **Graphics through a proxy d3d8.dll** (our fork of d3d8to9): every draw call passes through it,
  so shadows, post effects, GI, PBR materials and decal rules were added without touching the game.
  Textures are identified by a hash of their first 16 KB; draws by their pixel shader hash; frame
  phases by draw patterns (a fullscreen z-tested orthographic draw after the sky, the first HUD draw).
- **Find engine bugs by tracing.** Engine.dll's projector list bug (shadows handed back before the
  last flush) and the alpha write mask on shadow bitmaps were found by logging D3D calls from an
  injected tracer (`AdventNative`, d3dtrace.c), then patched with a few bytes at run time.
- **Binary formats:** Advent's packages differ from stock UE2 (int32 name lengths, 14-byte
  imports, 26-byte exports), which is why UModel fails; `tools/ukx.py` reads them, `ukx_mesh.py`
  writes .psk. `.psa` animation import works on build 2226.
- **Test harness over hand testing.** A pilot (script steps in an ini, screenshots at Present,
  off-screen window, logs) made every change measurable: brightness in numbers, not by eye.

### 2.2 Ghidra on a native exe
- Import, let auto-analysis run (a few minutes for a 12 MB exe). RTTI class names (`.?AV...`)
  survive in most C++ games and give the class hierarchy for free; Ghidra's RTTI analyzer
  recovers virtual tables from them.
- Strings are the map: console commands, ini keys, file extensions, format magic words. Start from
  a string, follow cross-references to the function that uses it.
- For a graphics change, the proxy-DLL route is usually faster than patching the exe.

## 3. What each game is made of

### Unreal II (2003)
UE2 build 2001 (Legend's branch). Ships UnrealEd and ucc. Karma physics. Our U2EdBridge scripts
UnrealEd through a pipe (u2ed.py). Mods: U2SoftShadows, U2Enemies, U2Seven, U2Hover, U2Prairie,
U2FairFights, U2TestHub, U2Wardrobe, U2Gore, U2Golem importer, U2Input hook.

### Advent Rising (2005)
UE2 build 2226 (UT2003 line), heavily modified by GlyphX. **Physics: Karma** (MathEngine's
engine, as in every UE2 game), used for ragdolls (`PHYS_KarmaRagdoll`) and rigid bodies; the PC
release shipped no `KarmaData\*.ka` ragdoll files, so we wrote our own (`tools/make_ka.py`,
lowercase part ids). No ucc shipped (see AdventUCC). Fixed-function character lighting with the
game's own ps_1_1 "skin shader"; pixel shaders are assembly text inside D3DDrv.dll. Engine bugs
found and patched: projector list hand-back, alpha writes on shadow bitmaps, an FPU precision
drop from a throwaway D3D device.

### Hydrophobia: Prophecy (2011), first look
- **Engine:** in-house HydroEngine, renderer "Blade GL" (the studio was Blade Interactive before
  Dark Energy Digital). 32-bit `HydroPC.exe`, Direct3D 9 (`d3d9.dll`, `d3dx9_43.dll`), XInput,
  X3DAudio. Middleware: Havok 2010.1 (physics + Behavior; **leave it alone, proprietary**), FBX SDK
  2011.3, zlib 1.2.3. RTTI class names present. Its own console-variable system (`BSLConsole*`)
  with developer commands such as `bladegl.dumptextures`; `ded.ini` is a plain-text quality table
  (water reflection/refraction map sizes with MSAA, shadow map sizes).
- **Archive format (cracked):** `hydro.dat` (3.5 GB) and `Patch.dat` (267 MB): `uint32 count`, then
  `count x {uint32 name hash, uint32 offset, uint32 size}` sorted by hash, files stored
  **uncompressed** and 0x800-aligned, no names. Patch entries override by hash.
  `Documents\Hydrophobia_research\hydro_unpack.py` unpacks both into `unpacked\` by kind with an
  `index.csv`. (Game assets: private, never in git.)
- **Contents:** 1,459 DDS textures: 530 plain and 929 wrapped in a 32-byte header (`e0 11 48`
  magic, header size 0x20, a format tag "DXT5"; the DDS follows at offset 32). These are the big
  ones: 4096x4096 and 2048x2048 atlases of ship panels, props, faces, clothes. 351 Havok `.hkx`.
  20 text files: shader sources in the studio's own "fragment" language (`fragment Bleach {
  vertex_shader ... }`), light struct definitions, string tables, HydroEdit event lists, a startup
  config (`g_bDisableMainMenu`, `g_bDisableSplash`, `g_bDisable3DMenu`...). 180 named shader /
  material pieces (Caustics, DepthOfField, MLAA, HDR, MotionBlur, DualParaboloidShadow,
  ParallaxMap, GlassSurface, HoloScan, NPCOutline...). 1,824 model/level chunks (`00 ee 11 ff`)
  referencing `.hull`, `.ght` and `.tga` paths under `hydrophobia\models\...`. A Scaleform-style UI
  with translations, and a 44 MB Havok container. Not decoded yet: the model chunks, the `02 11`
  files (31, 69 MB), `BSF` files (15; one holds pool-game strings from the studio's earlier games).
- **The exe is Steam-wrapped (SteamStub, `.bind` section, encrypted `.text`):** Ghidra saw 322
  functions until Steamless 3.1.0.5 (`Documents\Tools\steamless`) unpacked a copy
  (`Documents\Hydrophobia_research\exe\HydroPC.exe.unpacked.exe`): 26,136 functions, 2.76 M
  instructions, full analysis ~25 min headless. The exe embeds Lua.
- **Water simulation, first reading (Ghidra, names + allocations; code not yet followed):**
  1,484 RTTI classes; water ones: `HydWaterVisuals`, `HydWaterVisualsMesh`,
  `HydWaterReflectionRender`, `HydWaterRefractionRender`, `WaterRenderCompiler`,
  `HydWaterGridManager`, `HydWaterThreads`, plus Havok glue (`hkABIWaterForceModifier`,
  `hkABIWaterLevelPredicate`, `hkABIWaterRBInteractListener`: buoyancy and "picked up by water"
  for rigid bodies). Its init (`FUN_00c10040`) allocates two 160,000-byte buffers (= a 200 x 200
  float grid, double-buffered: the flow field; console `hydro.dumpflowfield`), a 0x400 table and a
  0x2D80 block. Level data carries "Region Water Vol" entries made of rectangles ("Add Rect %x to
  Region Water Vol %d"), with `Game_GetRegionWaterHeight` / `script_WaterLevelAtDoor` for the
  game script: so it is a Barotrauma-style room (region) model, with a 2D grid for the flow and
  surface, run on its own threads ("Havok Safe Window & Water Updates"). Rendering: planar
  reflection + refraction maps (sizes in ded.ini), shader fragments `reflectRefract.frg`,
  `reflectRefractPlanar.frg`, `wetbump.frg` (wet surfaces: `hydro.wetbump*` vars),
  `ripple_texcoord.frg`, caustic lights (`caustic_omnilight.frg`, `bladegl.causticdepthfactor`),
  `hydro.godraysoverwater`, "Render_WaterParticulates". Scripts: `Documents\Hydrophobia_research  ghidra_scripts\FindWaterCode.java` (regex over strings -> using functions, including pointer
  tables -> decompiled C into `water_code2\`).
- **Water, second reading (2026-10-05 night, Ghidra scripts DataRefs / RangeDump / CallersOf /
  DecompAt / InstrDump in `ghidra_scripts`):**
  - Frame order in the main update (`FUN_00d0e9d0`, profiler sections): `Update:WaitForWater`
    (`FUN_00bf4130`, waits on an event) -> `CycleSprayBfrs` -> `ResetRgnWtrH` (region water
    heights) -> `ConstructWG` (`FUN_00c148f0`: rebuilds the water sheets from the regions'
    rectangles, splits rects over 1200 cells, builds a 100-unit spatial index of up to 8 sheets
    per cell) -> `Update2` -> `FUN_00c0d470` -> `Update:StartWater` (`FUN_00c16df0` ->
    `FUN_00bf42e0`: queues jobs on the job system `FUN_009d8e20`; three events signal done).
  - The queued "water" jobs are RENDERING jobs: `job_00bf2460` -> `FUN_00bf0e20` builds each
    sheet's visual mesh (36-byte vertices, heights clamped at sheet edges, fog/alpha), and
    `FUN_00bf2440` -> `FUN_00bf00f0` builds the spray/particulate quads (28-byte vertices).
  - Data: 32 regions x 364 bytes (`DAT_01cb6984`), a table of up to 256 sheet pointers
    (`DAT_01cb6990`). A sheet (water surface grid) has: +4 cells wide, +0xc cells high, +8 stride
    base (row stride = width + 4: a 2-cell border), +0x10 cell size (20 units), +0x1c 1/cell,
    +0x7c/+0x80 world origin, +0x14 and +0x48/+0x50/+0x30/+0x54 float grids (height, velocity u/v,
    momentum = height x velocity at +0x34/+0x3c), +0xf8 dirty flag, +0x1ac next-sheet link,
    +0x1b0..+0x1bc boundary values, +0x1c8 region water volume, +0x6b "flat" flag with +0x6c..0x6f
    constant values for sheets without grids.
  - `FUN_00c12880` (per region, each frame): resets per-sheet accumulators, sums volumes over
    4-cell blocks (`FUN_00c0a540`), then for every character/object with radius r at (x,y)
    stamps its velocity into the sheets' u/v grids within r, weighted (1 - d^2/r^2), and the
    momentum grids = height x velocity: this is how walking, swimming and explosions push the
    water. `FUN_00c10560`: finite differences of neighbouring cells (slope / normals, spawns
    spray particles where the slope is steep). `FUN_00c0e5b0`: per-region bookkeeping.
  - **THE SOLVER, FOUND (2026-10-06 00:50):** the grid manager's job dispatcher
    `FUN_00c143e0` queues named phases per sheet (profiler strings): `HWGridMgr::StepFunc` ->
    `FUN_00c0ede0` -> **`FUN_00d5c9d0(sheet, dt)`** (9.7 KB, SSE, 4 cells at a time), then
    `PtclSpawnFn` (`job_00c113e0` -> `FUN_00c10560`, slopes -> spray), `FUN_00c0c8a0`
    (mesh/visual prep), `SaveHghtFn` (`FUN_00c0e580` -> `FUN_00c194d0`: inflow per cell from
    `DAT_01cb67bc`, volume, wet bounding box, average level, wave-speed factor `[9]`, then
    `FUN_00c192a0` normals), `PtclUpdFn1..3` (`job_00c12860`, particles).
    `FUN_00c0ede0` sub-steps: it calls the solver with the remaining time, the solver returns
    how much it consumed (a CFL-limited step), the remainder loops until below a threshold;
    `[0x10c]` counts steps.
    `FUN_00d5c9d0` is an explicit finite-volume **shallow-water** solver on the sheet's cells
    (cell size 20 units): the depth grid is double-buffered (`[*sheet + 10]` current, the other
    index next); momentum grids `[*sheet + 0xd]` (x) and `[0xf]` (y) are clamped to +-1000 x
    depth (a speed cap); pass 1 writes depth' = min(cap, max(depth - bed, floor) x scale) x
    depth, velocity u = mx / depth, v = my / depth into `[0x14]` / `[0x12]`, a wave-speed grid
    sqrt(depth x [9]) into `[0x13]`, and takes the maximum of |u| + c + |v| over the sheet: the
    CFL signal speed that sizes the step; pass 2 (lines 800-1466) computes the fluxes between
    each cell and its right/lower neighbour and updates depth and momentum; three 64-iteration
    loops handle edges.
  - **The flux scheme, read (2026-10-06 morning, lines 800-1100 of the decompile + the sheet
    initialiser `FUN_00c19d00`, which fills the 4-wide constant vectors):** a textbook
    **HLL approximate Riemann solver** per cell face, wet/dry-safe:
    1. *Hydrostatic reconstruction* (Audusse et al. 2004): with bed heights b from `[0x15]`,
       h_L* = max(0, h_L + min(b_L - b_R, 0)), h_R* = max(0, h_R + min(b_R - b_L, 0)), and the
       well-balancing source term g/2 (h^2 - h*^2) on each side (`[0x74..0x77]` = g/2, g = the
       sheet's `[9]`, a global).
    2. *Wave-speed estimate* = Toro's two-rarefaction form: u* = (u_L + u_R)/2 + (c_L - c_R),
       c* = (c_L + c_R)/2 + (u_L - u_R)/4 (`[0x7c]` = 0.5, `[0x80]` = 0.25; c = sqrt(g h) from
       pass 1, grid `[0x13]`), then S_L = min(u_L - c_L, u* - |c*|, 0), S_R = max(u_R + c_R,
       u* + |c*|, 0) (`[0x84..]` = 0 is the clamp).
    3. *HLL flux* F = (S_R F_L - S_L F_R + S_L S_R (U_R - U_L)) / max(S_R - S_L, 1e-10)
       (`[0x88]` = 1e-10, the `divps` by `(1,1,1,1)`), with F_L = (h_L* u_L, h_L* u_L^2 + ...),
       applied as F x dt / dx (`[0x78..0x7b]` = `[7]` = 1/20 = 1/cell). `[0x8c]` = 2e10 is the
       +infinity sentinel for min().
    So: explicit first-order Godunov/HLL finite volume on a 20-unit grid, CFL sub-stepped, SSE
    4 cells wide, with a 1000 x depth momentum cap. It is the same family as the GPU
    shallow-water papers (Brodtkorb / Kurganov-Petrova style, see bioshock-mod-ideas.md): a
    direct model for a blood-pool or flooding mod, ~60 lines of plain C per pass.
  - So Hydrophobia's water IS a real fluid simulation, but 2D: shallow-water per room surface
    (height + momentum, sub-stepped by CFL, SSE), fed by region levels (what pours in or out)
    and disturbed by objects; rooms exchange water through the region volumes, not through the
    grids. The 200 x 200 float pair at `DAT_01cb6ac4/ac8` is only allocated and freed in the
    code seen (likely the `hydro.dumpflowfield` scratch).
  - Design conclusion so far: regions carry a water level (set by level logic / script, e.g.
    `script_WaterLevelAtDoor`), each region's surface is a height+velocity grid at 20-unit
    cells that objects disturb; rendering is planar reflection/refraction + a per-sheet mesh +
    spray particles. Closer to Barotrauma's rooms-with-a-wave-surface than to a full fluid grid.

## 4. Rules we keep
- Decompiled sources, extracted meshes/textures and other game assets stay out of git.
- Don't ship other games' assets or code; mods are GPL / share-alike.
- Havok and other licensed middleware: don't redistribute, don't reverse beyond what a mod needs.
- Measure, don't eyeball: screenshots through the harness, numbers in the log.
