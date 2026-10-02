U2Destruct - groundwork for Black-style destruction in Unreal II (probe only)
==========================================================================

Destruction the way Black did it is mostly authored damage stages: a prop chips,
cracks and breaks, its mesh is swapped at each stage, and debris, dust and decals
are spawned. In Unreal II that needs three things the engine may not allow on a
map's placed props (StaticMeshActors, which are bStatic):

  1. hiding the original and switching its collision off
  2. a spawned, movable copy with the same mesh that blocks like the original
  3. debris made from that mesh that falls, bounces and comes to rest

First PC run (Oct 1, M08A1, test-results/2026-10-01-pc/03-destruct-probe): 1 and 2
work (hidden, collision off, copy spawned). Karma debris can't work: Unreal II switched
rigid-body Karma off ("physKarma: This physics type is obsolete in U2 829"; ragdolls
are separate), so debris is now DestructDebris: PHYS_Falling, bouncing off the world in
script, settling when slow. The single trace through the prop's origin hit nothing at
every stage, which said nothing: the target was a canopy overhead whose origin is empty
space. The probe now prefers props near eye height and fires nine rays across the prop.

DestructProbe tests all three on the nearest solid prop and logs the answers.
Nothing here changes the game yet; level walls (BSP) can never be destroyed.

Build: copy Source\U2Destruct into the game folder, add EditPackages=U2Destruct
to [Editor.EditorEngine] in Unreal2.ini, run "UCC make" from System.

Run:   python u2pilot.py scripts/destruct_probe.txt --background
       (tools/python/U2Pilot), then read the "DestructProbe:" lines in
       System\Unreal2.log and the screenshots.

Reading the result:
  stage 1  of nine rays aimed across the prop, how many hit the prop, the world, something
           else or nothing (does the original block shots?)
  stage 2  after hiding + SetCollision(off): is it still drawn / still hit?
  stage 3  the copy: spawned? does the trace now hit the copy?
  stage 4  debris: dropped ~160 units with a few bounces = landed on the floor (works),
           0 = never moved, far more = fell through the floor
