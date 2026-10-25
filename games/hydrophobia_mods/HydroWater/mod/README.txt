HydroWater - water solver upgrade for Hydrophobia: Prophecy (PC)
================================================================

What it does
------------
Replaces the game's shallow-water solver with HydroWater, an open-source solver that
runs the same water grids the game already simulates, with safety clamps instead of the
original hard momentum cap (less exploding/jittering water at walls and wet/dry edges).
It also draws foam and air bubbles on the water where the flow is rough (breaking
fronts, falls, wakes), by adding them to the game's water shader, and leaves floors, walls
and Kate wet where the water has been until they dry. Gameplay and saves are
untouched. Later versions add object displacement and buoyancy.

Install
-------
1. Copy dinput8.dll and HydroWater.ini into the game folder, next to HydroPC.exe
   (Steam: steamapps\common\Hydrophobia).
2. Play. The mod loads with the game, no launcher, no exe patch.

The mod writes HydroWater.log in the game folder: "solver hooked" and
"sheet ...: now on HydroWater" mean it is working.

Uninstall: delete dinput8.dll (and HydroWater.ini, HydroWater.log and the shaderCache??.bin files
  other than the game's own shaderCacheDX.bin).

Options (HydroWater.ini)
------------------------
mode = hw           run the water on HydroWater (default)
mode = passthrough  load the mod but leave the game's own solver in charge (for comparing)
clamps, recon       the upgrade stages (1 = on)
foam                foam and air bubbles on the water (1 = on)
wet, wet_dry        wet surfaces where the water has been, and how fast they dry
drench              Kate soaked after a swim: wet skin, dark cloth, running water, drips
drench_splash       running through shallow water splashes her higher up in wet patches
foam_rim            thick foam is darker in the middle and lit at its edge (1 = default, 0 = off)
foam_cells          foam is a net of cells with water showing through the holes, like a ship wake (1 = default, 0 = off)
foam_dots           thin foam breaks into small dots instead of fading out (1 = default, 0 = off)
foam_glow           bioluminescent foam that glows faintly in the dark (0 = off, the default; 1 = full), glow_colour = r g b
debris_wake         foam trail and wake pull behind everything the game pushes through the water, crates and planks too (1 = default, 0 = off)
scum                a floating layer of algae or scum carried by the flow that parts around Kate (0 = off, the default; 0.6 = patchy mats), scum_colour = r g b
spray_draw          spray drops from breaking water drawn as particles over the water (1 = default, 0 = off); spray_size, spray_colour = r g b opacity, spray_rate
wake_pull           foam and silt behind Kate are dragged along into her wake (1 = default, 0 = off)
meniscus            the water bows down around Kate's body with a foam ring on the rim (1 = default, 0 = off)
drench_mask         0 = soak everywhere (default), 1 = only where the game's wetness mask allows, 2 = show it
spray_apic          drops carry the water's local velocity gradient and give it back on landing (1 = default, 0 = off)
spray_blob          drops drawn as merging blobs that flatten into the sheet when they touch it (1 = default, 0 = plain sprites)
foam_spec           bubble glints and a little specular on thick foam (1 = default, 0 = off, up to 2)
foam_blur           moving foam streaks along the flow, still foam stays crisp (1 = default, 0 = off, up to 3)
depth_tint          how fast deep water loses red then green (1 = default, 0 = clear, 2 = murky)
shore_wet           wet, darker, shinier ground where a sheet thins out (1 = default, 0 = off)
caustics            light web on floors and walls under the water, brighter where the surface slopes (1 = default, 0 = off)
under_fog           teal fog on what is under the water, thicker with depth (1 = default, 0 = off)
swim                swimmer wake once the water under Kate is deeper than swim_depth (100): bow bump, shoulder trough, kick strip (1 = default, 0 = off)
swim_spray          her strokes throw drops ahead every 0.6 s, one arm then the other (1 = default, 0 = off)
foam_dump           1 = write the patched water shader to HydroWater_shaderN.hlsl
alpha, c_adapt, edge_damp  tuning, see the comments in the file
max_cells           grids with more cells than this stay on the game's solver

Notes
-----
* Only dinput8.dll's DirectInput8Create is proxied to the Windows copy; controllers and
  keyboard work as before.
* With foam on, the first level load is slower while the game compiles its shaders into
  its own shaderCache??.bin (the two letters change with each version and with the wet
  switch, so old shaders are never reused). The game's own shaderCacheDX.bin is not touched;
  older mod caches can be deleted.
* If another mod already uses dinput8.dll in this folder, they cannot both load.
* Fixed: earlier builds could crash at startup (about one launch in three) when the Steam
  overlay was on, because both hooked the same Direct3D call. Update to this build. If a
  crash still happens, HydroWater_crash.txt next to the game says where.
* If the game crashes with the mod, set mode = passthrough and post the HydroWater.log.

License
-------
GPL-3.0-or-later. Non-commercial fan work; contains no game assets.
Source: https://github.com/indieindie7/codes (games/hydrophobia_mods/HydroWater)
