"""Import UT3 vehicles into StaticMeshes/U2HoverSM.usx (the existing package, e.g. the Manta, is kept).
    python import_ut3.py Viper                 one static body: Models/ase/ViperBody.ase + Textures/ViperSkin.tga
    python import_ut3.py --rig Nightshade parts.txt
                                               rigid parts listed in parts.txt (from vehicle_parts.py):
                                               Models/ase/<part>.ase each, + Textures/NightshadeSkin.tga
Skins must be uncompressed TGA (UnrealEd reports RLE ones as "can't find file")."""
import sys
from build_editor import run, SM, H

cmds = [r'OBJ LOAD FILE="{SM}\U2HoverSM.usx"']
args = sys.argv[1:] or ["Viper"]
if args[0] == "--rig":
    n, parts = args[1], [p.strip() for p in open(args[2]) if p.strip()]
    cmds.append(r'TEXTURE IMPORT FILE="{H}\Textures\%sSkin.tga" NAME="%sSkin" PACKAGE="U2HoverSM" GROUP="%s" MIPS=1' % (n, n, n))
    for p in parts:
        cmds.append(r'NEW StaticMeshFactory PACKAGE="U2HoverSM" GROUP="%s" NAME="%s" FILE="{H}\Models\ase\%s.ase"' % (n, p, p))
else:
    for n in args:
        cmds += [
            r'TEXTURE IMPORT FILE="{H}\Textures\%sSkin.tga" NAME="%sSkin" PACKAGE="U2HoverSM" GROUP="%s" MIPS=1' % (n, n, n),
            r'NEW StaticMeshFactory PACKAGE="U2HoverSM" GROUP="%s" NAME="%sBody" FILE="{H}\Models\ase\%sBody.ase"' % (n, n, n),
        ]
cmds += [r'OBJ SAVEPACKAGE PACKAGE="U2HoverSM" FILE="{SM}\U2HoverSM.usx"']
sys.exit(0 if run(cmds) else 1)
