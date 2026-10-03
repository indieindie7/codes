"""Writes import_meshes.txt: UnrealEd commands that build StaticMeshes\\U2UTFlakSM.usx
(the flak's first-person frames + flak chunks as static meshes, with their
textures). Run inside UnrealEd's command bar:  exec <path to import_meshes.txt>

Unreal II never textures vertex meshes, and UCC crashes building static meshes
from #exec, so the meshes are built once in the editor and loaded from the .usx.
"""
import os, sys

# --canister: the Bio Rifle frames with the slung fuel canister (canister/build_canister.py),
# and the package saved to U2UTFlak\U2UTFlakSM.usx (a staging copy, not the live one)
CANISTER = "--canister" in sys.argv

GAME = r"C:\PROGRA~2\Steam\STEAMA~1\common\UNREAL~2"   # 8.3 path: Unreal filenames can't contain spaces
ASE = os.path.join(GAME, "U2UTFlak", "Models", "ase")
TEX = os.path.join(GAME, "U2UTFlak", "Textures")
PKG = "U2UTFlakSM"

lines = []
# no materials in the meshes (the ASE importer crashes with them): the weapon
# and chunks set their textures through Skins[0] (FlakAtlas / chunk glow frames)
for i in range(100):
    lines.append(f'NEW StaticMeshFactory PACKAGE="{PKG}" GROUP="View" NAME="FlakV{i:03d}" '
                 f'FILE="{os.path.join(ASE, "FlakV%03d.ase" % i)}"')
for c in ["chunkM", "chunk2M", "chunk3M", "chunk4M"]:
    lines.append(f'NEW StaticMeshFactory PACKAGE="{PKG}" GROUP="Chunks" NAME="{c}" '
                 f'FILE="{os.path.join(ASE, c + "_000.ase")}"')
for i in range(75):                                   # UT's Ripper (Razor2), 75 frames
    lines.append(f'NEW StaticMeshFactory PACKAGE="{PKG}" GROUP="Ripper" NAME="RipV{i:03d}" '
                 f'FILE="{os.path.join(ASE, "RipV%03d.ase" % i)}"')
lines.append(f'NEW StaticMeshFactory PACKAGE="{PKG}" GROUP="Ripper" NAME="RipBlade" '
             f'FILE="{os.path.join(ASE, "RipBlade000.ase")}"')
for i in range(91):                                   # UT's GES Bio Rifle (BRifle2), 91 frames
    lines.append(f'NEW StaticMeshFactory PACKAGE="{PKG}" GROUP="Bio" NAME="BioV{i:03d}" '
                 f'FILE="{os.path.join(ASE + "_can" if CANISTER else ASE, "BioV%03d.ase" % i)}"')
for name, f in [("BioGelFly", "BioGelFly000.ase"), ("BioGelStuck", "BioGelStuck023.ase")]:
    lines.append(f'NEW StaticMeshFactory PACKAGE="{PKG}" GROUP="Bio" NAME="{name}" FILE="{os.path.join(ASE, f)}"')
SAVE = os.path.join(GAME, "U2UTFlak", PKG + ".usx") if CANISTER else os.path.join(GAME, "StaticMeshes", PKG + ".usx")
lines.append(f'OBJ SAVEPACKAGE PACKAGE="{PKG}" FILE="{SAVE}"')

out = os.path.join(GAME, "U2UTFlak", "import_meshes.txt")
open(out, "w").write("\n".join(lines) + "\n")
print(len(lines), "commands ->", out)
