r"""AvalonSM2.usx: the round-2 concept buildings as geometry (build_buildings.py crane_tower ... water_tower ->
U2Avalon/tools/glb_to_ase.py pal=Pal2 stripes=16 material=1 -> Models/round2_ase), in a package of its own so
the game can load it while it runs (DynamicLoadObject; AvalonSM.usx stays untouched and loaded).

    py tools/make_sm2.py [name=AvalonSM2]

Run beside the game (U2ED_WITH_GAME=1 is set here). A package the running game has already loaded can't be
replaced: bump name= (AvalonSM3 ...) for a second round in the same session.
"""
import glob, os, sys

os.environ.setdefault("U2ED_WITH_GAME", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
from uedlib import session, short_path  # noqa

o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
PKG = o.get("name", "AvalonSM2")
SRC = o.get("src", os.path.join(HERE, "..", "Models", "round2_ase"))
PAL = o.get("pal", "Pal2")                             # the palette texture (and the ASE material) name
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
OUT = os.path.join(GAME, "StaticMeshes", PKG + ".usx")


def job(ed):
    ed.exec("!answer yes")
    ed.ok('TEXTURE IMPORT FILE="%s" NAME="%s" PACKAGE="%s" GROUP="Pal" MIPS=0' % (os.path.abspath(os.path.join(SRC, PAL + ".tga")), PAL, PKG))
    for f in sorted(glob.glob(os.path.join(SRC, "*.ase"))):
        n = os.path.splitext(os.path.basename(f))[0]
        ed.import_staticmesh(os.path.abspath(f), PKG, "Liandri", n)
        print("imported", PKG + ".Liandri." + n)
    ed.save_package(PKG, short_path(os.path.dirname(OUT)) + "\\" + PKG + ".usx")   # 8.3: the parser breaks on spaces
    print("saved", OUT)


if os.path.exists(OUT):
    sys.exit(OUT + " exists (the game may have it loaded): use name=AvalonSM3")
session(job)
