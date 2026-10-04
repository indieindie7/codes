"""Reverses the triangle winding of .ase files (A B C -> A C B, for the faces and their
UV faces), for importers that mirror an axis on import and so turn the mesh inside out.

    python ase_flip.py <in.ase> <out.ase>
"""
import re, sys


def flip(text):
    def face(m):
        return "%sA:%sB:%sC:%s" % (m.group(1), m.group(2), m.group(4), m.group(3))
    text = re.sub(r"(\*MESH_FACE\s+\d+:\s+)A:(\s*\d+\s+)B:(\s*\d+\s+)C:(\s*\d+\s+)", face, text)
    text = re.sub(r"(\*MESH_TFACE\s+\d+\s+)(\d+)(\s+)(\d+)(\s+)(\d+)", lambda m: m.group(1) + m.group(2) + m.group(3) + m.group(6) + m.group(5) + m.group(4), text)
    return text


if __name__ == "__main__":
    src = open(sys.argv[1], encoding="latin-1").read()
    open(sys.argv[2], "w", encoding="latin-1", newline="").write(flip(src))
