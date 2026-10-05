"""Blood decal textures for U2Gore: writes Source/U2Gore/Textures/*.tga.

    python make_textures.py

The pictures come from the Advent Rising mod's generator (games/advent_rising_mods/AdventMod/Textures/
make_blood.py: a metaball field with a ragged edge, colour already mixed for the projector's 2x multiply,
plain Python, seeded so every build gives the same files). Here: red for humans and Skaarj, green for
Izarians and Araknids. Only the marks U2Gore uses: 4 splats, 2 sprays (thrown along +X), 1 pool each.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "advent_rising_mods", "AdventMod", "Textures"))
import make_blood as mb

mb.HERE = os.path.join(HERE, "..", "Source", "U2Gore", "Textures")
os.makedirs(mb.HERE, exist_ok=True)
GREEN = ((0.30, 0.62, 0.08), (0.14, 0.36, 0.05))
for prefix, pal in (("Blood", mb.RED), ("Ichor", GREEN)):
    for i in range(4):
        rng = random.Random(1000 + i)
        mb.render(128, mb.splat(rng), rng, edge_noise=0.8, name="%sSplat%d" % (prefix, i), palette=pal)
    for i in range(2):
        rng = random.Random(2000 + i)
        mb.render(128, mb.splat(rng, directional=True), rng, edge_noise=0.8, name="%sSpray%d" % (prefix, i), palette=pal)
    rng = random.Random(3000)
    mb.render(128, mb.pool(rng), rng, edge_noise=0.35, name="%sPool0" % prefix, palette=pal)
