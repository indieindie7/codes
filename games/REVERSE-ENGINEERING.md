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
  - **The flux formula, read exactly (2026-10-06, lines 1075-1215 of the decompile for the x
    direction; y is the same with u and v swapped; `FUN_00c19d00` fills the constants):**
    per face between cell L (x) and R (x+1), with h the depth, b the bed (`[0x15]`), u, v the
    velocities (`[0x14]`, `[0x12]`), c = sqrt(g h) (`[0x13]`), g/2 = `[0x74]`, 1/dx = `[0x78]` =
    `[7]` = 1/20, wall = the per-cell grid `[0x19]` (1/dx on a wall cell, 0 otherwise):
    1. `hL* = max(0, hL + min(bL - bR, 0))`, `hR* = max(0, hR + min(bR - bL, 0))`
       (Audusse 2004 hydrostatic reconstruction; `[0x84]` = 0 is the clamp).
    2. `u* = (uL + uR)/2 + (cL - cR)`, `c* = (cL + cR)/2 + (uL - uR)/4` (`[0x7c]` = 0.5, `[0x80]` =
       0.25: Toro's two-rarefaction estimate), `SL = min(uL - cL, u* - |c*|, 0)`,
       `SR = max(uR + cR, u* + |c*|, 0)`, `k = 1 / max(SR - SL, 1e-10)` (`[0x88]`).
    3. HLL fluxes on the reconstructed states, `qL = hL* uL`, `qR = hR* uR`:
       `F_h  = k (qL SR - qR SL + (hR* - hL*) SL SR)`
       `F_hu = k ((uL qL + g/2 hL*^2) SR - (uR qR + g/2 hR*^2) SL + (qR - qL) SL SR)`
       `F_hv = k ((vL qL) SR - (vR qR) SL + (hR* vR - hL* vL) SL SR)`
    4. Hydrostatic source per side: `sL = g/2 (hL^2 - hL*^2)`, `sR = g/2 (hR^2 - hR*^2)`.
    5. Update, with `open = 1/dx - wall` (0 across a wall) and `a = dt/dx` (`dt` = min(time
       left, 0.5 dx / max(|u| + c + |v|)) over the sheet: `[8]` = 0.5 is the CFL number, `[4]` = 20
       the cell):
       `hR += a open F_h`, `hL -= a open F_h`
       `(hu)R += a (wall g/2 hR^2 + open (F_hu + sR))`, `(hu)L -= a (wall g/2 hL^2 + open (F_hu + sL))`
       `(hv)R += a open F_hv`, `(hv)L -= a open F_hv`
       so at a wall the mass and transverse fluxes vanish and the momentum feels the cell's own
       hydrostatic pressure: a reflecting boundary. Edge cells use an `[0x84]`/`[0x78]` mask so
       nothing leaves the sheet.
    6. Time stepping: the sheet's `[0x17]` = 2 selects a two-stage step: the first pass uses
       `a = 0.5 dt/dx` into the other buffer (`[*sheet] ^ 1`), velocities and wave speeds are
       recomputed from that half-step state, and a second pass applies the full `dt/dx`:
       the midpoint (second-order Runge-Kutta) method, first order in space (no slope
       reconstruction). Momentum is clamped to 1000 x depth before each pass.
    So: HLL / hydrostatic-reconstruction shallow water, first order in space, second order in
    time, CFL 0.5, reflecting walls, SSE 4 cells wide. Nothing exotic; it is the scheme of
    Audusse et al. with Toro's speeds, which is also what the open-source shallow-water codes
    use.
  - So Hydrophobia's water IS a real fluid simulation, but 2D: shallow-water per room surface
    (height + momentum, sub-stepped by CFL, SSE), fed by region levels (what pours in or out)
    and disturbed by objects; rooms exchange water through the region volumes, not through the
    grids. The 200 x 200 float pair at `DAT_01cb6ac4/ac8` is only allocated and freed in the
    code seen (likely the `hydro.dumpflowfield` scratch).
  - Design conclusion so far: regions carry a water level (set by level logic / script, e.g.
    `script_WaterLevelAtDoor`), each region's surface is a height+velocity grid at 20-unit
    cells that objects disturb; rendering is planar reflection/refraction + a per-sheet mesh +
    spray particles. Closer to Barotrauma's rooms-with-a-wave-surface than to a full fluid grid.

- **Modding entry points (2026-10-09; Ghidra `DataRefs`/`DecompAt`/`InstrDump` on the loader,
  not the water):**
  - **Archives and the override slot.** `WinMain` (`FUN_00971850`) mounts the main archive
    (`FUN_009dab10`: `HYDRO.dat`, with an optional `.zpack` index, magic `0x79ac79ac`, and a
    `.pat` sidecar, neither shipped), then `FUN_009da0b0("Patch.dat")` and
    `FUN_009da0b0("Patch2.dat")`: up to three patch archives, each `uint32 count` +
    `{hash, offset, size}` table that the game qsorts itself. **`Patch2.dat` is not shipped.**
    The lookup (`FUN_009da270(name)`) searches the patch archives newest first, then the main
    one, so a `Patch2.dat` dropped into the game folder overrides any file by name hash with
    hydro.dat and Patch.dat untouched; delete it and the game is stock. Two unshipped dev
    paths exist in the same function: a global (`DAT_018b77b0`) that makes every open go to
    `v:\rage\<name>` first, and a data-directory prefix (`DAT_018b772c` / `DAT_015dbd00`);
    with no archive mounted at all it falls back to plain `fopen(name)`.
  - **The name hash, cracked** (`FUN_009d8ea0`, the game's "mode 6"; 15 exe path strings
    match the table, e.g. `GameSetup.cfg`, `iwStartup.txt`, `Act1.dat`,
    `textures\EnvMaps\Baxter.dds`): case-insensitive, `.` and `\` are skipped (so slashes,
    backslashes and the extension dot are all the same), a trailing `(ps2)`/`(gc)` is dropped;
    `h = 0x71e315b1; per char v = (upper(c) - 0x20) & 0x3f: h += v * 0x20001;
    h = ((h >> 2) ^ h) * 31 + v`. Tools in `Documents\Hydrophobia_research`:
    `hydro_names.py` (hashes every path-like string in the exe and the archives, writes
    `names.csv`; `hydro_hash()` importable) and `hydro_pack.py` (`build <folder> Patch2.dat`,
    `list`, `get <archive> <name|hash> <out>` straight from the archive without a full unpack,
    `hash <name>`). Verified: `get hydro.dat GameSetup.cfg` returns the 784-byte config. A scan of every path-like string in the exe and the archives names 251 of the 4,057 entries outright and 696 with the `--deep` prefix cross-product (Havok .hkx, .nmp, .dds, .frg shader sources, .lpkpc, .tga); the rest need draw-time dumps or the strings inside the model chunks.
  - **Startup config in the archive, overridable:** `FUN_00d0cc50` reads `GameSetup.cfg`
    (section `__Setup__`, `key = value` lines, parsed by `FUN_00d0c5f0`): `g_bDisableMainMenu`,
    `g_bDisableSplash`, `g_bDisable3DMenu`, `g_bEnableJolt`, `g_bEnableInvincibilityToggle`,
    `g_bEnableSecurityOverride`, `g_bEnableFullVersion`, `g_bEnableFullMAVI`,
    `g_bUseEasyObjectives`, `g_bEnableFastRegenToggle`, `g_bEnableMaxItemStats`,
    `g_bDemoBuild`, `g_bCaptureBuild`, `g_bAllCheckpointsSavedSeparately`, the reload-hammer
    test switches... (shipped: all false except `g_bEnableFullVersion`,
    `g_bUseAnimatedNormalMaps`, `g_bDontReduceCharacters`). Then `iwStartup.txt`
    (`Map:%d`, a `Cam:` and a `Display:` line of hex floats: the editor's start map 25 and
    camera). A Lua script named `Startup` is loaded from the archive too ("Script "Startup"
    not found - falling back on defaults"); level scripts are `.lua` with a `ScriptVersion`
    check, and `FUN_00be90f0` registers the `script_*` / `Game_*` API (381 `script_` names,
    e.g. `script_CheatsEnabled`, `Game_GetRegionWaterHeight`, `Game_SetDrownParameters`).
  - **Command line** (`FUN_00970a70`: switches start with `-` or `/`, case-insensitive,
    `name:value` forms take the rest of the token): `darknrg` (developer mode; then `win x,y`
    window position and `nopause` are read), `captureWindow`, `fs`, `f16`, `ct`, `video:<dir>`,
    `screengrab:<dir>`, `joy:`, `DebugPorts`, and `640`/`800`/`1024`/`1280`/`1600`/`1920` for
    the resolution (`FUN_00cb9f60`). `iwStartup.txt`'s existence and `hydro.setcam` /
    `IWSetFreeCamera` suggest the editor camera survives in the shipped exe.
  - **Console variables** (`BSLConsole*`; 170 `hydro.*`, 46 `bladegl.*`, plus `iw.*`), the
    interesting ones: `hydro.infiniteammo`, `hydro.giveammo`, `hydro.givecollectible`,
    `hydro.door_cheat`, `hydro.doorstatus`, `hydro.setdifficulty`, `hydro.setcam`/`getcam`,
    `hydro.setframeratehack`, `hydro.dumpflowfield`, `hydro.getregionstats`,
    `hydro.nearregions`, `hydro.dumpmodels`/`dumptextures`/`listtextures`/`grabmesh`,
    `hydro.packfiledump`, `hydro.toggleprintpackfiles`, `hydro.togglehavokdebugger`,
    `hydro.profilethreads`, `hydro.dof_params`, `hydro.postprocess`, the `hydro.wetbump*` and
    `hydro.reflectionmap_*`/`refractionmap_*` tuning, `hydro.godraysoverwater`,
    `bladegl.ambientocclusion`, `bladegl.gamma`, `bladegl.lensflare`, `bladegl.drawlod`,
    `bladegl.dumptextures`. No in-game console UI was found (no key/toggle strings): the
    way in is an injected DLL calling the dispatcher, still to be located (start from the
    `Usage: bladegl.dumptextures` handler). `ded.ini` sections (`hydro.water.low/med/high`,
    `bladegl.*shadowmaps.*`, `bladegl.config`) are read with `FUN_009ce720(key, default)`.
  - **What transfers from the other games** (from the Advent and Unreal II sessions,
    2026-10-09): the injector (`tools/C/U2EdBridge/src/u2edinject.c`, launch-suspended +
    `LoadLibraryW`; or `AdventUCC/src/hook.c`) and the named-pipe command DLL shape
    (`u2edbridge.c`: pipe, dispatch, run on the game thread from a hooked per-frame
    function, never from the pipe thread); the byte-checked in-memory patch pattern
    (`AdventMod/native/karmafix.c`) with addresses as module base + RVA since the exe exports
    nothing; the D3D vtable tracer (`native/d3dtrace.c`, renumber the slots for
    `IDirect3DDevice9`); for graphics a `d3d9.dll` proxy, not the d3d8to9 fork, but the
    fork's passes (`source/u2shaders.hpp`, the `.hlsl` set, texture-hash rules, INTZ depth,
    crash.hpp, hotswap) take an `IDirect3DDevice9*` and lift over; `U2Input`'s dinput8 proxy
    for hidden test runs (check first how HydroPC reads input); `package.py` / RELEASE.md /
    README.txt as the release shape, with `Patch2.dat` as the whole install. Warnings carried
    over: never patch the Steam exe on disk (inject at run time), no leaked source, no AI
    voices, assets out of git, one GPU shared by three chats (announce runs).
  - **Housekeeping:** `Documents\Hydrophobia_research\unpacked\` was deleted (disk); `get`
    now reads single files from the archives instead, and `names.csv` is the index. Decompiles
    of the loader are in `loader_refs\` and `console_refs\`.
  - **HydroWater mod (2026-10-09, `HydroWater/mod/`):** a `dinput8.dll` proxy dropped into
    the game folder (HydroPC imports only `DirectInput8Create` from it; forwarded to
    `System32\dinput8.dll`). `DllMain` starts a thread that polls the solver entry
    (module base + `0xd5c9d0 - 0x400000`) every 20 ms for up to two minutes until the
    SteamStub has decrypted `.text` and the prologue `55 8B EC 83 E4 F0 81 EC A4 08 00 00` is
    there, then writes a 5-byte JMP (+NOP) over the first six bytes, with the six bytes copied
    to an RWX trampoline followed by a JMP back. `FUN_00d5c9d0(sheet, dt)` is cdecl but
    **returns the consumed dt in xmm0**, so the hook is a naked thunk (x87 return -> xmm0 and
    back). Solver calls arrive from the job threads in parallel, one per sheet; the mod keeps a
    sheet -> `hw_sheet` table under an SRWLOCK and copies planes in and out each step (copy
    rather than aliasing: the game's row stride is `[2]+4`, HydroWater's is `w+4`).
    Sheet dwords used: `[0]` current buffer, `[1]` w, `[2]` padded width, `[3]` h, `[4]` dx,
    `[8]` CFL, `[9]` g, `[10]/[11]` depth A/B, `[0xd]/[0xe]` hu, `[0xf]/[0x10]` hv, `[0x12]` v,
    `[0x13]` c = sqrt(g h), `[0x14]` u, `[0x15]` bed, `[0x19]` wall (1/dx on wall cells),
    `[0x1c]/[0x1d]` flow accumulators (`+= vel*[0x60]*dt + [0xb1]/[0xb2]*dt`), `[0x24]` last dt,
    `[0x17]` stage count (1 or 2) picking `[0x42]`/`[0x43]` as the step counter, `[0x6b]` flat
    flag (flat sheets go to the original). Planes are `(h+4)` rows of stride floats, interior
    cell (i,j) at row j+2, column i+2; the mod keeps the two-cell ring as wall. `tests\hooktest.c`
    checks all of this against a fake solver with the game's prologue bytes (note: GAS encodes
    `mov ebp,esp` as `89 E5`, MSVC as `8B EC`, so the fake emits `.byte`s).
  - **Foam in the game (stage 7, 2026-10-10):** three run-time patches, no exe change on disk.
    (1) Mesh colour: `FUN_00bf0e20(job)` writes each sheet's (w+1) x (h+1) 36-byte vertices
    (`job+0xc` sheet, `job+0x10` locked vertex pointer; colour bytes +33 G, +34 R) and then
    calls `FUN_009b7f00` (unlock) at `0xbf1448` with ESI = job. The mod retargets that E8's
    rel32 to a naked stub that writes R = 255 - foam, G = 255 - air from its own foam snapshot
    and jumps on to `FUN_009b7f00`. (2) Shader: the game composes its shaders as HLSL text and
    compiles them through its `d3dx9_43!D3DXCompileShader` import; every image dword holding
    that address is pointed at a hook that inserts the foam code after the water fragment's
    `reflectionColour = vReflectionSample * fFresRefl.xxxx;` line (falls back to the original
    text if it doesn't compile). (3) Cache: compiled shaders go to `shaderCacheDX.bin`, name
    string at `0xeaf830`; the mod changes it in memory to `shaderCacheHW.bin` (same length)
    before the renderer opens it, so the user's cache stays as it was.

## 4. Rules we keep
- Decompiled sources, extracted meshes/textures and other game assets stay out of git.
- Don't ship other games' assets or code; mods are GPL / share-alike.
- Havok and other licensed middleware: don't redistribute, don't reverse beyond what a mod needs.
- Measure, don't eyeball: screenshots through the harness, numbers in the log.
