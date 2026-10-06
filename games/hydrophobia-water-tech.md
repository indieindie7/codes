# How Hydrophobia simulates water

*Hydrophobia: Prophecy* (Dark Energy Digital, 2011; the 2010 Xbox 360 original was
*Hydrophobia*) was sold on one promise: water that behaves. Rooms flood, doors hold water back
until they open, waves wash crates and bodies around, and the player swims through all of it.
The studio called its technology **HydroEngine** and said very little about how it worked. This
is a reading of what the shipped PC game actually does, written for modders and graphics
programmers who want to build something similar. It describes the algorithms in plain words;
it contains no code or assets from the game.

## 1. The short version

Hydrophobia's water is **a real fluid simulation, but a two-dimensional one**. Every room that
can hold water has a *water level*. The surface of that water is a grid of cells, each 20 game
units across, and the game runs a **shallow-water simulation** on that grid: each cell keeps a
water depth and a momentum, and every frame the game moves water between neighbouring cells
according to how much higher one is than the other. Rooms exchange water through their levels
and their doors, not through the grid. On top of this sits a very good rendering layer: planar
reflections and refractions, a mesh that follows the grid, spray particles where the surface is
steep, caustics, and wet surfaces that stay wet.

So it is *not* a 3D fluid (no Navier-Stokes volume, no particles carrying the water). It is the
same family of model used by flood simulations and by most "realistic water" in games since,
chosen because it is cheap enough to run every frame on 2010 hardware and still gives waves,
sloshing and flooding that look right from the player's point of view.

## 2. The parts, from the outside in

### 2.1 Regions and water levels (the "rooms")

The level data describes **water regions**: each region is a set of rectangles on the map (a
room, a corridor, part of a deck) and holds one number, its current water level. Doors between
regions have their own water heights. The game's script layer talks to the water through two
kinds of calls: *what is the water height in this region* and *what is the water level at this
door*. Scripted events (a hull breach, a valve, a door opening) change region levels; the
simulation then does the rest.

This is the same idea as the room-and-gap model in *Barotrauma*: the "big" water state is one
level per room, which makes flooding a whole ship cheap and controllable by designers.

### 2.2 Sheets (the surface grids)

Each frame, the game rebuilds the **water sheets** from the regions' rectangles: a region's
rectangles are split into sheets of at most about 1,200 cells, and the sheets are registered in
a coarse spatial index (100-unit squares, up to 8 sheets each) so that objects can find the
water under them quickly. A sheet is a grid of 20-unit cells with a two-cell border all around.
Per cell it stores:

- water **depth** (two copies: the current one and the one being written, swapped each step),
- **momentum** in x and y (depth times velocity),
- the derived **velocity** in x and y and the local **wave speed**,
- the **bed height** (the floor under the water), and a few helper grids.

Rooms whose water is perfectly still don't get a grid at all: a "flat" sheet is just a height.

### 2.3 Objects pushing the water

Once per frame, for every character or object with a radius standing in a sheet, the game
**stamps the object's velocity into the sheet** within that radius, weighted so that it is
strongest at the centre and fades to nothing at the edge, and sets the momentum to depth times
that velocity. That single step is what makes walking, swimming, falling crates and explosions
disturb the water. Floating objects get the opposite effect through Havok: the physics engine's
water listeners apply buoyancy and drag based on the water height under each rigid body.

### 2.4 The simulation step

This is the heart of it, and it runs on worker threads, sub-stepped so that fast water doesn't
break it. Each sheet's update has two passes, written with SSE so that four cells are processed
at once.

**Pass 1, prepare.** For every cell: clamp the momentum to at most 1,000 times the depth (a speed
cap), derive the velocity u = momentum / depth, compute the local wave speed c = sqrt(g x depth),
and track the largest value of |u| + c + |v| over the sheet. That maximum is the **CFL condition**:
the step length is chosen so that no wave can cross more than one cell per step. If the frame's
time is larger than that, the solver runs again on the remainder.

**Pass 2, fluxes.** For every pair of neighbouring cells (right neighbour, then lower
neighbour), the game computes how much water and momentum crosses the shared edge, and applies
it to both cells. The method is a textbook one from the computational fluid dynamics
literature:

1. *Hydrostatic reconstruction* (Audusse and colleagues, 2004). Before comparing two cells, each
   side's depth is reduced by however much the other side's floor is higher. This is what keeps
   water from "climbing" steps on its own and lets the same code handle wet and dry cells
   without special cases: a dry cell is just depth zero.
2. *Wave-speed estimates* (Toro's two-rarefaction form). From the two sides' velocities and wave
   speeds, the solver estimates the fastest left-going and right-going signals at the edge:
   a middle velocity (the average of the two sides plus the difference of the wave speeds) and
   a middle wave speed (the average of the two wave speeds plus a quarter of the velocity
   difference), then the signal speeds are the minimum and maximum of the two sides and that
   middle state, clamped at zero.
3. *The HLL flux* (Harten, Lax and van Leer). With the two signal speeds S_L and S_R, the flux
   through the edge is a weighted blend of the left flux, the right flux and the jump between the
   two states, divided by S_R - S_L (guarded against zero). Each side's flux is depth times
   velocity for mass, and depth times velocity squared plus half g times depth squared for
   momentum, with the hydrostatic correction added.
4. The result, times the step length and divided by the cell size, is subtracted from one cell
   and added to the other.

In other words: **an explicit, first-order Godunov finite-volume shallow-water solver with an
HLL Riemann solver**, exactly what the GPU shallow-water papers of the late 2000s describe
(Kurganov-Petrova and Brodtkorb-style schemes). It is robust, it conserves water, it handles
dry floors, and a few hundred lines of SSE are enough. The trade-off is that first-order
schemes are diffusive: waves flatten quicker than in reality, which in a game reads as calm
water settling, which is exactly what you want.

### 2.5 After the step

Separate jobs then: measure each sheet's inflow, volume and average level (so region levels and
the sheets stay consistent and water can pour from one region to the next through doors),
compute surface normals from neighbouring heights, spawn **spray particles** where the surface
slope is steep, and update those particles.

### 2.6 Rendering

The look is a stack of well-known techniques, done carefully:

- **Planar reflection and refraction**: the scene is rendered mirrored for the reflection and
  once more behind the surface for the refraction, into maps whose sizes the quality settings
  choose. The surface shader blends them by the view angle (Fresnel), with ripple distortion
  from the normals.
- **A mesh per sheet** rebuilt each frame from the grid heights, with heights clamped at the
  sheet edges so the surface meets the walls, and depth-based fog and alpha.
- **Spray and particulates**: camera-facing quads built from the particle list.
- **Caustics** as projected omni lights with a depth factor, **god rays over water**, and a **wet
  bump** effect that keeps surfaces glistening after the water has left them.
- Post-processing on top: HDR, depth of field, motion blur, and MLAA for anti-aliasing.

## 3. Why this design

- A 2D height field is the cheapest fluid that still sloshes and floods. Everything a player
  notices about water in a corridor game (level rising, waves hitting walls, things being
  pushed) comes out of it.
- Per-room levels make flooding a *design tool*: a designer sets levels and door states, the
  simulation makes it believable.
- Threads and SSE made it fit a 2010 budget: the game simulates and renders the water on its
  own worker jobs while the main thread does gameplay and Havok.
- The limits are the ones every height-field water has: no breaking waves, no water on two
  levels in one column, no splashing volume. The game hides them with spray particles and
  camera work.

## 4. Building your own

If you want this kind of water in a mod or a small engine:

1. Start with a single grid: depth, momentum x, momentum y, bed height.
2. Implement the two passes above (prepare + HLL fluxes) in plain C or a compute shader. Keep
   the CFL sub-stepping; it is what makes it stable.
3. Add the hydrostatic reconstruction from day one, or wet/dry edges will explode.
4. Push velocity into the grid from objects with a radial falloff; read height back for
   buoyancy.
5. Render with a mesh from the heights, Fresnel-blended reflection/refraction, and particles
   where the slope is steep.

Good references: Audusse et al., "A fast and stable well-balanced scheme with hydrostatic
reconstruction for shallow water flows" (2004); Toro, *Shock-Capturing Methods for Free-Surface
Shallow Flows* (2001); Kurganov and Petrova, "A second-order well-balanced positivity preserving
central-upwind scheme for the Saint-Venant system" (2007); Brodtkorb, Sætra and Altinakar,
"Efficient shallow water simulations on GPUs" (2012); and the GPU Gems chapters on height-field
water.

## 5. How this was learned, and what is deliberately left out

The reading comes from the shipped PC executable, studied with the free Ghidra decompiler, and
from the game's own profiler labels and console variables (which name the systems quite
clearly). Nothing here is from the studio's source code or documents. This write-up explains
the algorithms in general terms, as a work of analysis and commentary, and intentionally
contains no decompiled code, no game data, no shader text and no instructions for working
around the game's copy protection. Hydrophobia and HydroEngine are the property of their
rights holders; buy the game, it is cheap and it still looks great.
