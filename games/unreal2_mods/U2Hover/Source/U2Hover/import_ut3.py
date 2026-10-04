"""Import UT3 Necris vehicles (as static meshes + one skin each) into StaticMeshes/U2HoverSM.usx.
    python import_ut3.py Viper [Nightshade ...]
Meshes come from Models/ase/<Name>Body.ase (tools/python/U2Golem/blend2ase.py),
skins from Textures/<Name>Skin.tga. The existing package (the Manta) is loaded first and kept."""
import sys
from build_editor import run, SM, H

names = sys.argv[1:] or ["Viper"]
cmds = [r'OBJ LOAD FILE="{SM}\U2HoverSM.usx"']
for n in names:
    cmds += [
        r'TEXTURE IMPORT FILE="{H}\Textures\%sSkin.tga" NAME="%sSkin" PACKAGE="U2HoverSM" GROUP="%s" MIPS=1' % (n, n, n),
        r'NEW StaticMeshFactory PACKAGE="U2HoverSM" GROUP="%s" NAME="%sBody" FILE="{H}\Models\ase\%sBody.ase"' % (n, n, n),
    ]
cmds += [r'OBJ SAVEPACKAGE PACKAGE="U2HoverSM" FILE="{SM}\U2HoverSM.usx"']
sys.exit(0 if run(cmds) else 1)
