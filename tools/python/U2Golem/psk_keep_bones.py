"""Give a .psk the exact skeleton of another .psk (same bone names), remapping the weights.

    python psk_keep_bones.py <mesh.psk> <skeleton.psk> <out.psk>

Why: blend2psk.py rebuilds every bone's axes from Blender's head/tail bones, and Blender does not keep the
original roll. The mesh still deforms correctly in Blender, but a game that plays EXISTING animations on those
bones (Unreal II's marines' set) rotates every joint about the wrong axes: the character leans, limbs splay
and the weapon mount is off. So: rig in Blender on a psk2blend.py scene, export with blend2psk.py, then run
this to put the source .psk's own bone records back. Points are not touched (psk2blend imports them as is).
"""
import struct, sys
from psk import Chunks, name_of

mesh, skel, out = sys.argv[1:4]
m, s = Chunks(mesh), Chunks(skel)
m_names = [name_of(r[:64]).lower() for r in m.records("REFSKELT")]
s_recs = s.records("REFSKELT")
s_names = [name_of(r[:64]).lower() for r in s_recs]
missing = [n for n in m_names if n not in s_names]
if missing:
    sys.exit(f"bones not in the skeleton file: {missing}")
remap = [s_names.index(n) for n in m_names]
w = struct.Struct("<fii")
recs = []
for r in m.records("RAWWEIGHTS"):
    wt, pt, b = w.unpack(r)
    recs.append(w.pack(wt, pt, remap[b]))
m.set_records("RAWWEIGHTS", recs)
m.set_records("REFSKELT", s_recs)
m.save(out)
print(f"PSK_KEEP_BONES {out}: {len(s_recs)} bones from {skel}, {len(recs)} weights remapped")
