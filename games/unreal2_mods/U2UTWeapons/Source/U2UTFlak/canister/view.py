"""Render Bio Rifle frames in three views, faces coloured from BioAtlas (sanity pictures)."""
import sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from PIL import Image
import ase

GAME = r"C:/Program Files (x86)/Steam/steamapps/common/Unreal II The Awakening/U2UTFlak"
atlas = np.array(Image.open(GAME + "/Textures/BioAtlas.tga").convert("RGB")) / 255.0


def colours(m, flipv=True):
    tv = np.array(m["tv"])
    out = []
    for tf in m["tf"]:
        uv = tv[list(tf)][:, :2].mean(0)
        u, v = uv[0] % 1, uv[1] % 1
        if flipv:
            v = 1 - v
        out.append(atlas[min(int(v * atlas.shape[0]), atlas.shape[0] - 1), min(int(u * atlas.shape[1]), atlas.shape[1] - 1)])
    return out


def draw(meshes, out):
    fig, axes = plt.subplots(len(meshes), 3, figsize=(15, 5 * len(meshes)))
    axes = np.atleast_2d(axes)
    for row, m in enumerate(meshes):
        v = np.array(m["v"]); f = np.array(m["f"]); c = m.get("c") or colours(m)
        for col, (a, b, name) in enumerate([(0, 1, "XY top"), (0, 2, "XZ side"), (1, 2, "YZ front")]):
            ax = axes[row, col]
            depth = v[f].mean(1)[:, 3 - a - b]
            order = np.argsort(depth)
            ax.add_collection(PolyCollection(v[f][order][:, :, [a, b]], facecolors=np.array(c)[order], edgecolors="k", linewidths=0.2))
            ax.set_xlim(v[:, a].min() - 10, v[:, a].max() + 10); ax.set_ylim(v[:, b].min() - 10, v[:, b].max() + 10)
            ax.set_aspect("equal"); ax.set_title(f"{m['name']} {name}")
    fig.savefig(out, dpi=70)


if __name__ == "__main__":
    ms = [ase.read(f"{GAME}/Models/" + (sys.argv[2] if False else "ase") + "/BioV{int(i):03d}.ase") for i in sys.argv[2:]]
    draw(ms, sys.argv[1])
