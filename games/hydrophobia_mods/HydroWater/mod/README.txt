HydroWater - water solver upgrade for Hydrophobia: Prophecy (PC)
================================================================

What it does
------------
Replaces the game's shallow-water solver with HydroWater, an open-source solver that
runs the same water grids the game already simulates, with safety clamps instead of the
original hard momentum cap (less exploding/jittering water at walls and wet/dry edges).
It also draws foam and air bubbles on the water where the flow is rough (breaking
fronts, falls, wakes), by adding them to the game's water shader. Gameplay and saves are
untouched. Later versions add object displacement and buoyancy.

Install
-------
1. Copy dinput8.dll and HydroWater.ini into the game folder, next to HydroPC.exe
   (Steam: steamapps\common\Hydrophobia).
2. Play. The mod loads with the game, no launcher, no exe patch.

The mod writes HydroWater.log in the game folder: "solver hooked" and
"sheet ...: now on HydroWater" mean it is working.

Uninstall: delete dinput8.dll (and HydroWater.ini, HydroWater.log, shaderCacheHW.bin).

Options (HydroWater.ini)
------------------------
mode = hw           run the water on HydroWater (default)
mode = passthrough  load the mod but leave the game's own solver in charge (for comparing)
clamps, recon       the upgrade stages (1 = on)
foam                foam and air bubbles on the water (1 = on)
foam_dump           1 = write the patched water shader to HydroWater_shaderN.hlsl
alpha, c_adapt, edge_damp  tuning, see the comments in the file
max_cells           grids with more cells than this stay on the game's solver

Notes
-----
* Only dinput8.dll's DirectInput8Create is proxied to the Windows copy; controllers and
  keyboard work as before.
* With foam on, the first level load is slower while the game compiles its shaders into
  shaderCacheHW.bin. The game's own shaderCacheDX.bin is not touched.
* If another mod already uses dinput8.dll in this folder, they cannot both load.
* If the game crashes with the mod, set mode = passthrough and post the HydroWater.log.

License
-------
GPL-3.0-or-later. Non-commercial fan work; contains no game assets.
Source: https://github.com/indieindie7/codes (games/hydrophobia_mods/HydroWater)
