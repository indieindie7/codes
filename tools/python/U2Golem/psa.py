"""ActorX .psa (skeletal animation) reader: bones, sequences and per-frame bone keys.

    python psa.py <file.psa>          lists the bones and the sequences (frames, rate)

Keys are parent-relative, like the .psk reference skeleton: position + quaternion (x, y, z, w);
as in .psk, child bone rotations are stored conjugated (psk2blend.py / blend2psk.py follow the same rule).
"""
import struct, sys


def read(path):
    d = open(path, "rb").read()
    o, ch = 0, {}
    while o + 32 <= len(d):
        cid = d[o:o + 20].split(b"\0")[0].decode("latin1")
        size, count = struct.unpack_from("<ii", d, o + 24)
        ch[cid] = (d[o + 32:o + 32 + size * count], size, count)
        o += 32 + size * count
    b, s, n = ch["BONENAMES"]
    bones = []
    for i in range(n):
        name = b[s * i:s * i + 64].split(b"\0")[0].decode("latin1")
        flags, kids, parent = struct.unpack_from("<Iii", b, s * i + 64)
        q = struct.unpack_from("<4f", b, s * i + 76)
        p = struct.unpack_from("<3f", b, s * i + 92)
        bones.append(dict(name=name, parent=parent, quat=q, pos=p))
    b, s, n = ch["ANIMINFO"]
    seqs = []
    for i in range(n):
        name = b[s * i:s * i + 64].split(b"\0")[0].decode("latin1")
        group = b[s * i + 64:s * i + 128].split(b"\0")[0].decode("latin1")
        total_bones, root_inc, comp, quota, reduction, track_time, rate, start_bone, first, nframes = \
            struct.unpack_from("<iiiifffiii", b, s * i + 128)
        seqs.append(dict(name=name, group=group, bones=total_bones, rate=rate, first=first, frames=nframes,
                         track_time=track_time))
    b, s, n = ch["ANIMKEYS"]
    keys = [struct.unpack_from("<3f4ff", b, s * i) for i in range(n)]
    return dict(bones=bones, seqs=seqs, keys=keys)


def frame(psa, seq, f):
    """[(pos, quat)] per bone for frame f of sequence seq (dict from read()['seqs'])."""
    nb = len(psa["bones"])
    base = (seq["first"] + f) * nb
    return [(k[0:3], k[3:7]) for k in psa["keys"][base:base + nb]]


if __name__ == "__main__":
    p = read(sys.argv[1])
    print("BONES", len(p["bones"]))
    for i, b in enumerate(p["bones"]):
        print(f"  {i:2d} {b['name']:24s} parent {b['parent']}")
    print("SEQUENCES", len(p["seqs"]))
    for s in p["seqs"]:
        print(f"  {s['name']:32s} frames {s['frames']:4d} rate {s['rate']:.1f}  ({s['frames'] / max(s['rate'], 1e-6):.2f}s)")
