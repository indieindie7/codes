r"""Test the 3D-modelling report's unverified claims in Unreal II's editor (games/research_notes/3D modelling for the
UE2 editor, "Open checks"), by building one small map and probing it in game:

  L_SPLIT   a closed CONCAVE brush (an L block) whose faces are all convex (the L caps split in two)
  L_CONCAVE the same L with each cap one concave 6-vertex polygon
  N20 / N16 a 20-sided and a 16-sided pillar (caps of 20 / 16 vertices: FPOLY_MAX_VERTICES)
  HULL      a 64 UU static-mesh box whose ASE also has an MCDCX_ hull 512 UU tall

Probes (pilot): teleport above each spot and read where the player comes to rest:
  on an L arm -> the arm's top; in the L's notch -> the floor (if the concave brush carved right)
  on a pillar -> its top cap (if the cap survived), else the floor
  on the HULL box -> 512 above the floor (the hull is the collision) or 64 (per-polygon)

    py tests\claims.py build     -> <game>\Maps\ClaimTest.un2, StaticMeshes\ClaimTestSM.usx, the pilot script
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
WORK = os.path.join(GAME, "U2EdTests")
PILOT = os.path.expanduser(r"~\Documents\github\codes\tools\python\U2Pilot\scripts\editor_claims.txt")
FLOOR = -1024        # the room: a subtracted box 8192 x 8192 x 2048 around the origin
TEX = "Engine.DefaultTexture"


def poly(vs, link):
    """one T3D polygon; vs in the editor's winding (normal = (v1-v0) x (v2-v0), outward)"""
    a, b, c = vs[0], vs[1], vs[2]
    u = [b[k] - a[k] for k in range(3)]
    w = [c[k] - a[k] for k in range(3)]
    n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
    ln = math.sqrt(sum(x * x for x in n)) or 1
    n = [x / ln for x in n]
    tu = [1.0, 0, 0] if abs(n[2]) > 0.5 else [-n[1], n[0], 0]
    tv = [n[1] * tu[2] - n[2] * tu[1], n[2] * tu[0] - n[0] * tu[2], n[0] * tu[1] - n[1] * tu[0]]
    s = "          Begin Polygon Texture=%s Link=%d\n" % (TEX, link)
    s += "             Origin   %+.6f,%+.6f,%+.6f\n" % tuple(a)
    s += "             Normal   %+.6f,%+.6f,%+.6f\n" % tuple(n)
    s += "             TextureU %+.6f,%+.6f,%+.6f\n" % tuple(tu)
    s += "             TextureV %+.6f,%+.6f,%+.6f\n" % tuple(tv)
    s += "".join("             Vertex   %+.6f,%+.6f,%+.6f\n" % tuple(v) for v in vs)
    return s + "          End Polygon\n"


def prism(loops_bottom, h, inward=False):
    """a prism over a footprint: CAPS = list of convex (or not) loops in CCW order seen from above, all sharing the
    outline OUTLINE (CCW). Returns polygons: the caps (top up, bottom down) and one quad per outline edge."""
    caps, outline = loops_bottom
    P = []
    for loop in caps:
        P.append([(x, y, h) for x, y in reversed(loop)])        # top: normal +z
        P.append([(x, y, 0) for x, y in loop])                  # bottom: normal -z
    for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]):
        P.append([(x0, y0, 0), (x0, y0, h), (x1, y1, h), (x1, y1, 0)])
    if inward:
        P = [list(reversed(p)) for p in P]
    return P


def fix_winding(P, centre):
    """make every polygon's normal point away from CENTRE (works for these simple shapes; the L uses fix_by_normal)"""
    out = []
    for p in P:
        a, b, c = p[0], p[1], p[2]
        u = [b[k] - a[k] for k in range(3)]
        w = [c[k] - a[k] for k in range(3)]
        n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        m = [sum(v[k] for v in p) / len(p) - centre[k] for k in range(3)]
        out.append(p if sum(n[k] * m[k] for k in range(3)) > 0 else list(reversed(p)))
    return out


def outward_by_side(P, outline_ccw):
    """side quads of a CCW outline face outward when wound (bottom-a, top-a, top-b, bottom-b) walking CCW? check the
    sign against the edge's right-hand normal and flip if needed; caps: top +z, bottom -z"""
    out = []
    for p in P:
        a, b, c = p[0], p[1], p[2]
        u = [b[k] - a[k] for k in range(3)]
        w = [c[k] - a[k] for k in range(3)]
        n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        zs = set(v[2] for v in p)
        if len(zs) == 1:                                  # a cap
            want = [0, 0, 1 if max(zs) > 0 else -1]
        else:                                             # a side: outward = right of the CCW edge direction
            (x0, y0, _), (x1, y1, _) = p[0], p[3]
            want = [y1 - y0, -(x1 - x0), 0]
        out.append(p if sum(n[k] * want[k] for k in range(3)) > 0 else list(reversed(p)))
    return out


def brush_actor(name, oper, loc, polys):
    s = "Begin Actor Class=Brush Name=%s\n    CsgOper=%s\n    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n" % (name, oper, *loc)
    s += "    Begin Brush Name=%sModel\n       Begin PolyList\n" % name
    s += "".join(poly(p, k) for k, p in enumerate(polys))
    s += "       End PolyList\n    End Brush\n    Brush=Model'MyLevel.%sModel'\nEnd Actor\n" % name
    return s


def box(w, d, h):
    loop = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    return outward_by_side(prism(([loop], loop), h), loop)


def ngon(n, r, h):
    loop = [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return outward_by_side(prism(([loop], loop), h), loop)


L_OUT = [(0, 0), (1024, 0), (1024, 256), (256, 256), (256, 1024), (0, 1024)]     # CCW from above


def l_split(h):
    caps = [[(0, 0), (1024, 0), (1024, 256), (0, 256)], [(0, 256), (256, 256), (256, 1024), (0, 1024)]]
    return outward_by_side(prism((caps, L_OUT), h), L_OUT)


def l_concave(h):
    return outward_by_side(prism(([L_OUT], L_OUT), h), L_OUT)


def ase_box_with_hull(path, name, size, hull_h):
    """two objects: NAME (a SIZE cube) and MCDCX_NAME (a SIZE x SIZE x HULL_H box) - the UT2003-era collision prefix"""
    def obj(nm, w, d, h):
        V = [(x, y, z) for z in (0, h) for y in (-d / 2, d / 2) for x in (-w / 2, w / 2)]
        F = [(0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6), (0, 1, 4), (1, 5, 4), (2, 6, 3), (3, 6, 7), (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)]
        if FLIP:
            F = [(a, c, b) for a, b, c in F]   # the writer negates X, which flips the winding
        L = ["*GEOMOBJECT {", '\t*NODE_NAME "%s"' % nm, "\t*MESH {", "\t\t*MESH_NUMVERTEX %d" % len(V), "\t\t*MESH_NUMFACES %d" % len(F),
             "\t\t*MESH_VERTEX_LIST {"]
        L += ["\t\t\t*MESH_VERTEX %d %.3f %.3f %.3f" % (k, -v[0], v[1], v[2]) for k, v in enumerate(V)]
        L += ["\t\t}", "\t\t*MESH_FACE_LIST {"]
        L += ["\t\t\t*MESH_FACE %d: A: %d B: %d C: %d AB: 1 BC: 1 CA: 1 *MESH_SMOOTHING 1 *MESH_MTLID 0" % (k, *t) for k, t in enumerate(F)]
        L += ["\t\t}", "\t\t*MESH_NUMTVERTEX 1", "\t\t*MESH_TVERTLIST {", "\t\t\t*MESH_TVERT 0 0.0 0.0 0.0", "\t\t}",
              "\t\t*MESH_NUMTVFACES %d" % len(F), "\t\t*MESH_TFACELIST {"]
        L += ["\t\t\t*MESH_TFACE %d 0 0 0" % k for k in range(len(F))]
        L += ["\t\t}", "\t}", "}"]
        return L
    L = ["*3DSMAX_ASCIIEXPORT 200"] + obj(name, size, size, size) + obj("MCDCX_" + name, size, size, hull_h)
    open(path, "w").write("\n".join(L) + "\n")


SPOTS = {   # name: (x, y), where the shape's origin goes; probes are (x, y) points with what to expect
    "L_SPLIT": (-2500, -2500), "L_CONCAVE": (-2500, 1000), "N20": (1500, -2000), "N16": (1500, 0), "HULL": (1500, 2000)}
H = 384
FLIP = True


def probes():
    P = [("floor", (0, -1500), FLOOR)]
    for nm in ("L_SPLIT", "L_CONCAVE"):
        x, y = SPOTS[nm]
        P += [(nm + " arm", (x + 800, y + 128), FLOOR + H), (nm + " arm2", (x + 128, y + 800), FLOOR + H),
              (nm + " notch", (x + 700, y + 700), FLOOR)]
    for nm in ("N20", "N16"):
        x, y = SPOTS[nm]
        P += [(nm + " top", (x, y), FLOOR + H)]
    x, y = SPOTS["HULL"]
    P += [("HULL box defaults (hull 512 / per-poly 64)", (x, y), FLOOR + 512),
          ("HULL box simple flags on (hull 512 / per-poly 64)", (x, y + 1000), FLOOR + 512)]
    return P


def build():
    os.makedirs(WORK, exist_ok=True)
    ase = os.path.join(WORK, "ClaimBox.ase")
    ase_box_with_hull(ase, "ClaimBox", 64, 512)
    ase_s = os.path.join(WORK, "ClaimBoxS.ase")
    ase_box_with_hull(ase_s, "ClaimBoxS", 64, 512)
    # brushes go through the builder brush (BRUSH IMPORT + MOVETO + ADD/SUBTRACT): Brush actors in a MAP IMPORTADD
    # are not built by MAP REBUILD (Nodes 0 -> 0). No MERGE=1: it would rejoin L_SPLIT's caps into one concave face.
    A = []
    shapes = [("ROOM", box(8192, 8192, 2048), (0, 0, FLOOR), "SUBTRACT")]
    for nm, polys in (("L_SPLIT", l_split(H)), ("L_CONCAVE", l_concave(H)), ("N20", ngon(20, 256, H)), ("N16", ngon(16, 256, H))):
        shapes.append((nm, polys, (SPOTS[nm][0], SPOTS[nm][1], FLOOR), "ADD"))
    brush_cmds = []
    for nm, polys, (x, y, z), op in shapes:
        bf = os.path.join(WORK, "brush_%s.t3d" % nm)
        open(bf, "w").write("Begin PolyList\n" + "".join(poly(p, k) for k, p in enumerate(polys)) + "End PolyList\n")
        brush_cmds.append((bf, x, y, z, op))
    A.append("Begin Actor Class=StaticMeshActor Name=ClaimHull\n    StaticMesh=StaticMesh'ClaimTestSM.Test.ClaimBox'\n"
             "    Location=(X=%.1f,Y=%.1f,Z=%.1f)\nEnd Actor\n" % (SPOTS["HULL"][0], SPOTS["HULL"][1], FLOOR))
    A.append("Begin Actor Class=StaticMeshActor Name=ClaimHullS\n    StaticMesh=StaticMesh'ClaimTestSM.Test.ClaimBoxS'\n"
             "    Location=(X=%.1f,Y=%.1f,Z=%.1f)\nEnd Actor\n" % (SPOTS["HULL"][0], SPOTS["HULL"][1] + 1000, FLOOR))
    A.append("Begin Actor Class=PlayerStart Name=ClaimStart\n    Location=(X=0,Y=-3000,Z=%.1f)\nEnd Actor\n" % (FLOOR + 100))
    A.append("Begin Actor Class=Light Name=ClaimLight\n    Location=(X=0,Y=0,Z=%.1f)\n    LightRadius=255\n    LightBrightness=255\nEnd Actor\n" % (FLOOR + 1500))
    t3d = os.path.join(WORK, "claims.t3d")
    open(t3d, "w").write("Begin Map\n" + "".join(A) + "End Map\n")
    import u2ed
    from uedlib import short_path as sp
    G = sp(GAME)
    # ClaimBoxS first, then the simple-collision flags on (SET reaches every static mesh loaded now - only this
    # package is saved), then ClaimBox with the defaults
    cmds = [r'NEW StaticMeshFactory PACKAGE="ClaimTestSM" GROUP="Test" NAME="ClaimBoxS" FILE="%s"' % sp(ase_s),
            r'SET StaticMesh UseSimpleBoxCollision True', r'SET StaticMesh UseSimpleLineCollision True',
            r'NEW StaticMeshFactory PACKAGE="ClaimTestSM" GROUP="Test" NAME="ClaimBox" FILE="%s"' % sp(ase),
            r'OBJ SAVEPACKAGE PACKAGE="ClaimTestSM" FILE="%s\StaticMeshes\ClaimTestSM.usx"' % G,
            ] + [c for bf, x, y, z, op in brush_cmds for c in (
                r'BRUSH IMPORT FILE="%s"' % sp(bf), r'BRUSH MOVETO X=%d Y=%d Z=%d' % (x, y, z), r'BRUSH %s' % op)] + [
            r'MAP IMPORTADD FILE="%s"' % sp(t3d), r'MAP REBUILD', r'LIGHT APPLY', r'MAP SAVE FILE="%s\Maps\ClaimTest.un2"' % G]
    ed = u2ed.Editor.start()
    try:
        ed.exec("!answer yes")
        for c in cmds:
            rc, out = ed.exec_rc(c)
            lines = out.strip().splitlines()
            print("== %s  [rc=%d]" % (c[:100], rc))
            for l in lines[-3:]:
                print("     " + l[:200])
    finally:
        ed.stop()
    # the pilot probes: teleport above, settle, read the player's Z
    L = ["# editor_claims: where does the player come to rest above each test shape (tools/C/U2EdBridge/tests/claims.py)",
         "background", "map ClaimTest?Mutator=U2TestHub.HubMutator", "waitcontrol 90", "wait 4", "console god"]
    for nm, (x, y), want in probes():
        L += ["mark %s want %.0f" % (nm, want), "console hub tp %.0f %.0f %.0f" % (x, y, FLOOR + 900), "wait 4", "dump U2PlayerSP Location"]
    L += ["quit"]
    open(PILOT, "w").write("\n".join(L) + "\n")
    print("pilot script:", PILOT)


if __name__ == "__main__":
    build()
