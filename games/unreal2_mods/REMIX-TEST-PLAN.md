# RTX Remix in Unreal II: first test

Goal: find out, in about an hour, whether RTX Remix (NVIDIA's path tracer for old fixed-function
DirectX 8/9 games) runs Unreal II on the PC's RTX 4070, and what it looks like out of the box.
Nothing is authored yet; this only answers "does it boot, and what breaks".

Remix and our shader pack (U2Shaders) don't mix: Remix path-traces the game's fixed-function
draws, and U2Shaders replaces some of those with pixel shaders. Test Remix without U2Shaders.
Game-logic mods (FairFights, Gore, Wardrobe, UTWeapons) are unaffected.

## 0. Before

- Latest NVIDIA driver for the RTX 4070.
- The latest **RTX Remix runtime** from https://github.com/NVIDIAGameWorks/rtx-remix/releases
  (the runtime package, not the Toolkit). Per the Remix runtime guide it contains `d3d9.dll`
  (the bridge) and a `.trex/` folder (the renderer).
- Someone at the PC: this is a visual test, and the game won't load while unfocused anyway.

## 1. Back up (everything this test touches)

Copy into `<game>\System\Backup-before-remix\`:
`d3d8.dll` (our U2Shaders fork), `d3d9.dll` (dgVoodoo), `dgVoodoo.conf`, `U2Shaders.ini`,
`Unreal2.ini`, `User.ini`.

## 2. Install

Unreal II's executable is in `System\`, so Remix goes there:

1. `d3d9.dll` and the `.trex\` folder from the Remix runtime → `System\` (this replaces
   dgVoodoo's `d3d9.dll`; Remix talks to the GPU itself).
2. A DirectX 8 → 9 bridge for `d3d8.dll`, one of:
   - **a)** the `d3d8.dll` that comes with the Remix runtime, if this release has one
     (NVIDIA says recent runtime releases include d3d8to9; not confirmed for this version);
   - **b)** otherwise keep our `d3d8.dll`, but move `U2Shaders.ini` out of `System\`: with no
     ini it adds nothing (U2Shaders.log should say `0 rule(s) ... pcss 0`).
   Try a) first; note which one was used.

## 3. First boot

Run `Unreal2.exe` directly (not through U2Pilot, so a crash shows). Write down:

- Does it reach the main menu? Does a level load (M08A1, the usual test spot)?
- If it crashes: any message, and the newest log files Remix wrote (in `System\` and/or a
  `rtx-remix\` folder next to it).

## 4. In the level

- **Alt+X** opens Remix's menu. In *Game Setup*, tag: the HUD textures as UI (otherwise the
  HUD is path-traced into the world), the sky textures (*Sky Parameters*), particles and decals.
  Settings save to `System\rtx.conf` by themselves.
- **The UE2 sky bug:** in UT2004 and SWAT 4, geometry vanishes when the sky comes into view
  (rtx-remix issue #88, still open, no workaround listed). Look up at the sky in an outdoor
  area: does the level disappear? Does tagging the sky textures change it?
- **Lighting:** Unreal II's level lights are baked into lightmaps, which Remix doesn't use as
  light. Expect dark areas, lit only by the sky and by the lights the game sends to Direct3D
  (characters' lights). Note how dark, and where.
- **Speed:** frame rate with DLSS on (Alt+X menu), standing still and fighting.
- Screenshots of the same views as `test-results/2026-10-01-pc/00-baseline` (same script
  spot: M08A1, two marines, the wall, the behind view), Remix vs stock.

## 5. A capture (only if it renders)

Alt+X → *Developer Settings* → *Enhancements* → **Capture Frame in USD**. It lands in
`System\rtx-remix\captures\`. This is the scene the Remix Toolkit edits (lights, materials).
Don't commit it if it's big: note its size and keep it on the PC.

## 6. Put back

Copy everything from `Backup-before-remix\` back into `System\`, remove `.trex\` and
`rtx.conf` (move them into the backup folder to keep the settings), and check the game starts
as before, with U2Shaders.

## 7. Results

`test-results/<date>-remix/`: the screenshots, `rtx.conf`, the Remix logs, and a README with:
boots y/n · level loads y/n · HUD ok after tagging y/n · sky bug y/n · how dark · FPS ·
which `d3d8.dll` (a or b) · capture size.

## What decides the next step

- **Won't boot or the sky bug makes it unplayable:** stay with baked lightmaps (lmcapture +
  bake_lightmaps.py) plus light probes for characters. That path is already half built.
- **Boots and renders, but dark:** the next project is lights. The map's lights are already
  readable from its T3D (U2Blender imports them with position, colour and radius); a script
  could turn them into Remix lights (USD), using the open-source Blender add-on blender-remix.
- **Looks good as is:** tune materials in the Remix Toolkit, keep U2Shaders for the non-Remix
  version.
