"""Exploded preview of gibsplit.py output: parts pushed out from the body, meat caps in red."""
import json, os, re, sys
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection


def read_ase(path):
    t = open(path).read()
    v = np.array([list(map(float, m.groups())) for m in re.finditer(r"\*MESH_VERTEX\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)", t)])
    f = [tuple(map(int, m.groups())) for m in re.finditer(r"\*MESH_FACE\s+\d+:\s+A:\s*(\d+)\s+B:\s*(\d+)\s+C:\s*(\d+).*?MTLID (\d+)", t)]
    return v, f


def preview(gibdir, out, explode=0.35):
    man = json.load(open([os.path.join(gibdir, f) for f in os.listdir(gibdir) if f.endswith("_gibs.json")][0]))
    meat = len(man["materials"]) - 1
    fig, axes = plt.subplots(1, 2, figsize=(14, 9))
    cols = plt.cm.tab20(np.linspace(0, 1, len(man["parts"])))
    for ax, (a, b) in zip(axes, [(0, 2), (1, 2)]):
        polys, fc = [], []
        for col, p in zip(cols, man["parts"]):
            v, f = read_ase(os.path.join(gibdir, p["file"]))
            c = np.array(p["pivot_mesh"])
            c = np.array([c[0], c[2], -c[1]]) if man["space"] == "zup" else c
            v = v + c * (1 + explode)
            for x, y, z, m in f:
                polys.append(v[[x, y, z]][:, [a, b]])
                fc.append((0.8, 0.1, 0.1, 1) if m == meat else col)
        depth = [0] * len(polys)
        ax.add_collection(PolyCollection(polys, facecolors=fc, edgecolors="none"))
        allv = np.vstack(polys)
        ax.set_xlim(allv[:, 0].min() - 5, allv[:, 0].max() + 5); ax.set_ylim(allv[:, 1].min() - 5, allv[:, 1].max() + 5)
        ax.set_aspect("equal"); ax.set_title(man["mesh"] + (" front" if a == 0 else " side"))
    fig.savefig(out, dpi=60)


if __name__ == "__main__":
    preview(sys.argv[1], sys.argv[2])
