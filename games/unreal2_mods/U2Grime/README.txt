U2Grime - dust where nobody walks (work in progress, source only)
=================================================================

Unreal II's floors are spotless. Real rooms gather dust where nobody walks and the air
doesn't move: corners, wall feet, under tables and stairs. Busy routes stay clean.
U2Grime works this out live when any map loads (no per-map work, stock maps included):

  1. Corners: from every AI navigation point, rays run out low across the floor. Where
     one meets a wall, the wall's foot is a candidate. It scores higher if another wall
     is close beside it (a corner), if something hangs over it (a table, stairs) or if
     the opposite wall is close (a narrow gap): a rough ambient occlusion.
  2. Traffic: the AI path network is where people walk. The further a candidate is from
     the nearest path, the dustier; beside a path it keeps a third of its dust.
  3. Wear (the live part): a character walking over a patch makes it lighter, three
     steps and it's gone, so routes that actually get used clear up as you play.

The best candidates (spaced apart, 160 at most) get a soft dust patch: a projector
straight down that darkens the floor slightly, warm-grey (GrimeSpot). Doors and terrain
are skipped. U2Shaders leaves these projectors alone (its PCSS pass logs "projector
without a known sharp map, left stock" a few times; that's them).

Build: copy Source\U2Grime into the game folder, add EditPackages=U2Grime to
[Editor.EditorEngine] in Unreal2.ini, run "UCC make" from System.
Install: add U2Grime.GrimeMutator to the Mutator= line in User.ini's [DefaultPlayer]
section (comma-separated). Uninstall: remove it from that line.

Test: python u2pilot.py scripts/grime_test.txt --background (tools/python/U2Pilot).
It stands in front of the dustiest spots with dust on and off, then walks over one.

Console (any time in a level):
  set GrimeManager bShow False      hide all dust (True brings it back)
  set GrimeManager ViewSpot 0       stand in front of spot 0 (the dustiest), 1, 2, ...
  set GrimeManager MaxSpots 300     then: set GrimeManager bRebuild True (re-runs it)
Other numbers to tune the same way (GrimeManager.uc has them all): OnPathDust, MinScore,
MinSize/MaxSize, CornerReach, CoverReach, PathNear/PathFar, ScuffPerSecond, bScuff.

Textures: tools\make_textures.py (Python 3, numpy, Pillow) writes Textures\Dust*.tga.
PB_Modulate doubles the texture, so 128 grey = no change; the border is exactly 128.

Not tested in the game yet (written in the cloud, no UCC there). Things that may need a
fix on the first run: the dust may also streak up the bottom of the wall (the projector
looks straight down past it; could be fine, could look wrong), and projectors cost a
little each, so watch the FPS with 160 of them.
