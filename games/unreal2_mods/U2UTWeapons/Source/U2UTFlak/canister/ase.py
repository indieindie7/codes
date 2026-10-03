"""Minimal reader/writer for the ue1_to_ase frame files (one mesh, positions, faces, UVs)."""
import re


def read(path):
    t = open(path).read()
    v = [tuple(map(float, m.groups())) for m in re.finditer(r"\*MESH_VERTEX\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)", t)]
    f = [tuple(map(int, m.groups())) for m in re.finditer(r"\*MESH_FACE\s+\d+:\s+A:\s*(\d+)\s+B:\s*(\d+)\s+C:\s*(\d+)", t)]
    tv = [tuple(map(float, m.groups())) for m in re.finditer(r"\*MESH_TVERT\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)", t)]
    tf = [tuple(map(int, m.groups())) for m in re.finditer(r"\*MESH_TFACE\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)", t)]
    return {"name": re.search(r'\*NODE_NAME "([^"]+)"', t).group(1), "v": v, "f": f, "tv": tv, "tf": tf, "text": t}
