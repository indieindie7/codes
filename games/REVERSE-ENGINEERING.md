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
- **Not found yet:** the water simulation's data or code; that lives in the exe (Ghidra project
  made, not yet read).

## 4. Rules we keep
- Decompiled sources, extracted meshes/textures and other game assets stay out of git.
- Don't ship other games' assets or code; mods are GPL / share-alike.
- Havok and other licensed middleware: don't redistribute, don't reverse beyond what a mod needs.
- Measure, don't eyeball: screenshots through the harness, numbers in the log.
