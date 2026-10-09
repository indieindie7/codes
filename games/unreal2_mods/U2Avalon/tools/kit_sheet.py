"""Contact sheet of the kit parts without the GPU: build_parts (kit_parts.dump_tris) writes every part's render
triangles to Models/glb/kit_tris/<part>.json (Unreal frame, metres, palette colour per triangle); this draws each
one as a shaded painter's-algorithm view with matplotlib.

    py tools/kit_sheet.py [out=Models/renders/kit_sheet.png] [only=B_culvert,B_k_wall]
"""
import glob, json, math, os, sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
OUT = o.get("out", os.path.join(HERE, "Models", "renders", "kit_sheet.png"))
ONLY = set(o["only"].split(",")) if "only" in o else None
SRC = os.path.join(HERE, "Models", "glb", "kit_tris")
AZ, EL = math.radians(-35), math.radians(28)      # the view: from front-left, a little above
LIGHT = np.array([-0.4, -0.5, 0.75])
LIGHT /= np.linalg.norm(LIGHT)


def view(P):
    """Unreal (X, Y, Z) -> screen (u, v, depth); Y is right, so mirror it for a right-handed picture"""
    x, y, z = P[..., 0], -P[..., 1], P[..., 2]
    ca, sa = math.cos(AZ), math.sin(AZ)
    xr, yr = x * ca - y * sa, x * sa + y * ca
    ce, se = math.cos(EL), math.sin(EL)
    u = yr
    v = z * ce - xr * se
    d = xr * ce + z * se
    return u, v, d


def lin2srgb(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


files = sorted(glob.glob(os.path.join(SRC, "*.json")))
files = [f for f in files if not ONLY or os.path.basename(f)[:-5] in ONLY]
n = len(files)
cols = 6
rows = (n + cols - 1) // cols
fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.2, rows * 3.2), facecolor="#1e1e1e")
for ax in np.ravel(axes):
    ax.axis("off")
for ax, f in zip(np.ravel(axes), files):
    name = os.path.basename(f)[:-5]
    T = json.load(open(f))
    tri = np.array([t[0] for t in T], float)                  # n x 3 x 3
    col = np.array([t[1] for t in T], float)
    u, v, d = view(tri)
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    nrm = np.cross(e1, e2)
    ln = np.linalg.norm(nrm, axis=1)
    ok = ln > 1e-9
    nrm[ok] /= ln[ok, None]
    shade = 0.45 + 0.55 * np.clip(np.abs(nrm @ LIGHT), 0, 1)
    rgb = lin2srgb(col * shade[:, None] * 1.6)
    order = np.argsort(d.mean(1))                            # far first
    polys = np.stack([u, v], -1)[order]
    ax.add_collection(PolyCollection(polys, facecolors=rgb[order], edgecolors="none"))
    ax.set_xlim(u.min() - 0.3, u.max() + 0.3)
    ax.set_ylim(v.min() - 0.3, v.max() + 0.3)
    ax.set_aspect("equal")
    sz = tri.reshape(-1, 3).max(0) - tri.reshape(-1, 3).min(0)
    ax.set_title("%s\n%.1f x %.1f x %.1f m = %d x %d x %d UU" % (name, sz[0], sz[1], sz[2], sz[0] * 50, sz[1] * 50, sz[2] * 50),
                 color="w", fontsize=7)
fig.suptitle("U2Avalon story/kit parts (Unreal frame, X toward the viewer's left-front)", color="w", fontsize=10)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.tight_layout()
plt.savefig(OUT, dpi=110, facecolor=fig.get_facecolor())
print(n, "parts ->", OUT)
