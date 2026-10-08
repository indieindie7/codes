r"""The storm sky's dome (Q34, 2026-10-08): an inward-facing hemisphere with a skirt below the horizon, UVs
mapping render_sky.py's panorama (u = yaw, v = 0 at the zenith .. 1 at the horizon; the skirt keeps v = 1,
the haze). Written as ASE, then imported into StaticMeshes\AvalonSky.usx (Liandri.SkyDome) beside the game.

    py tools/make_sky_dome.py [import=1]

AvalonStorm spawns it in the sky zone and skins it with U2AvalonCards.StormSky while the storm is on.
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "U2Avalon", "tools"))
from ase import write_ase, tri_facing  # noqa

OUTDIR = os.path.join(HERE, "..", "Models", "sky")
os.makedirs(OUTDIR, exist_ok=True)
ASE = os.path.join(OUTDIR, "SkyDome.ase")
R, SEG, RINGS, SKIRT = 100.0, 64, 24, 4

verts, uvs, tris = [], [], []
rows = []
for r in range(RINGS + SKIRT + 1):
    if r <= RINGS:
        el = math.pi / 2 * (1 - r / RINGS)          # zenith .. horizon
        v = r / RINGS
    else:
        el = -math.radians(8) * (r - RINGS)          # skirt: down to -32 degrees, painted with the horizon row
        v = 0.999
    row = []
    for s in range(SEG + 1):                         # SEG+1: the seam gets its own column (u = 1)
        yaw = math.pi - 2 * math.pi * s / SEG       # ase.py mirrors X on write: this lands u at world yaw 2*pi*u
        verts.append((R * math.cos(el) * math.cos(yaw), R * math.cos(el) * math.sin(yaw), R * math.sin(el)))
        uvs.append((s / SEG, 1 - min(max(v, 0.001), 0.999)))   # the importer flips V (seen in game: the horizon slot showed at the zenith)
        row.append(len(verts) - 1)
    rows.append(row)
for r in range(len(rows) - 1):
    for s in range(SEG):
        a, b, c, d = rows[r][s], rows[r][s + 1], rows[r + 1][s], rows[r + 1][s + 1]
        for t in ((a, c, b), (b, c, d)):
            if len({verts[i] for i in t}) < 3:       # the zenith fan's degenerate triangles
                continue
            mid = [sum(verts[i][k] for i in t) / 3 for k in range(3)]
            tris.append(tri_facing(verts, t, tuple(-m for m in mid)))   # facing inward, at the centre
write_ase(ASE, "SkyDome", verts, uvs, tris)
print("dome ->", ASE, len(verts), "verts", len(tris), "tris")

if "import=1" in sys.argv[1:]:
    os.environ.setdefault("U2ED_WITH_GAME", "1")
    sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
    from uedlib import session, short_path  # noqa
    GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
    OUT = os.path.join(GAME, "StaticMeshes", "AvalonSky.usx")
    if os.path.exists(OUT):
        sys.exit(OUT + " exists (move it aside first: the game may have it loaded)")

    def job(ed):
        ed.exec("!answer yes")
        ed.import_staticmesh(os.path.abspath(ASE), "AvalonSky", "Liandri", "SkyDome")
        ed.save_package("AvalonSky", short_path(os.path.dirname(OUT)) + "\\AvalonSky.usx")
        print("saved", OUT)
    session(job)
